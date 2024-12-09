import pulumi
import base64
import pulumi_azuread as azuread
import pulumi_azure_native as azure_native
from pulumi_azure_native import resources, network, compute, authorization, insights, operationalinsights
from pulumi import Output
import uuid

# Configurations
config = pulumi.Config()
subscription_id = config.require("subscriptionId")
azure_location = config.get("location")
resource_group_name = config.get("resourceGroup") or "rg_IaaS"

# Create a Resource Group
resource_group = resources.ResourceGroup(
    "myResourceGroup",
    resource_group_name=resource_group_name,
    location=azure_location
)

# Create a Virtual Network and Subnet
virtual_network = network.VirtualNetwork(
    "vnet",
    resource_group_name=resource_group.name,
    virtual_network_name=f"{resource_group_name}-vnet",
    location=azure_location,
    address_space={"address_prefixes": ["10.0.0.0/16"]},
)

subnet = network.Subnet(
    "subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name=f"{resource_group_name}-subnet",
    address_prefix="10.0.1.0/24",
)

# Create a Network Security Group (NSG) with rules
nsg = network.NetworkSecurityGroup(
    "nsg",
    resource_group_name=resource_group.name,
    network_security_group_name=f"{resource_group_name}-nsg",
    location=azure_location,
)

# Allow HTTP traffic
network.SecurityRule(
    "allowHTTP",
    resource_group_name=resource_group.name,
    network_security_group_name=nsg.name,
    security_rule_name="Allow-HTTP",
    priority=100,
    direction="Inbound",
    access="Allow",
    protocol="Tcp",
    source_port_range="*",
    destination_port_range="80",
    source_address_prefix="*",
    destination_address_prefix="*",
)
# Allow SSH traffic
network.SecurityRule(
    "allowSSH",
    resource_group_name=resource_group.name,
    network_security_group_name=nsg.name,
    security_rule_name="Allow-SSH",
    priority=200,
    direction="Inbound",
    access="Allow",
    protocol="Tcp",
    source_port_range="*",
    destination_port_range="22",  # Port 22 for SSH
    source_address_prefix="*",
    destination_address_prefix="*",
)

# Create a Public IP Address
public_ip = network.PublicIPAddress(
    "publicIp",
    resource_group_name=resource_group.name,
    public_ip_address_name=f"{resource_group_name}-publicIp",
    location=azure_location,
    sku={"name": "Standard"},
    zones=["1", "2", "3"],  
    public_ip_allocation_method="Static",
)

# Create a Load Balancer
load_balancer = network.LoadBalancer(
    "loadBalancer",
    resource_group_name=resource_group.name,
    load_balancer_name=f"{resource_group_name}-loadBalancer",
    location=azure_location,
    sku={"name": "Standard"},
    frontend_ip_configurations=[
        {
            "name": "frontendConfig",
            "public_ip_address": {"id": public_ip.id},
        }
    ],
    backend_address_pools=[
        {
            "name": "backendPool"
        }
    ],
    probes=[
        {
            "name": "httpProbe",
            "protocol": "Http",
            "port": 80,
            "request_path": "/",
            "interval_in_seconds": 15,
            "number_of_probes": 2,
        }
    ],
    load_balancing_rules=[
        {
            "name": "httpRule",
            "frontend_ip_configuration": {"id": Output.concat("/subscriptions/", subscription_id, "/resourceGroups/", resource_group_name, "/providers/Microsoft.Network/loadBalancers/", resource_group_name, "-loadBalancer/frontendIPConfigurations/frontendConfig")},
            "backend_address_pool": {"id": Output.concat("/subscriptions/", subscription_id, "/resourceGroups/", resource_group_name, "/providers/Microsoft.Network/loadBalancers/", resource_group_name, "-loadBalancer/backendAddressPools/backendPool")},
            "probe": {"id": Output.concat("/subscriptions/", subscription_id, "/resourceGroups/", resource_group_name, "/providers/Microsoft.Network/loadBalancers/", resource_group_name, "-loadBalancer/probes/httpProbe")},
            "protocol": "Tcp",
            "frontend_port": 80,
            "backend_port": 80,
            "enable_floating_ip": False,
            "idle_timeout_in_minutes": 4,
            "load_distribution": "Default",
        }
    ],
)

# Create Network Interfaces
nic1 = network.NetworkInterface(
    "nic1",
    resource_group_name=resource_group.name,
    location=azure_location,
    network_interface_name=f"{resource_group_name}-nic1",
    ip_configurations=[
        {
            "name": "ipConfig1",
            "subnet": {"id": subnet.id},
            "private_ip_allocation_method": "Dynamic",
            "load_balancer_backend_address_pools": [
                {"id": Output.concat(load_balancer.id, "/backendAddressPools/backendPool")}
            ],
        }
    ],
    network_security_group={"id": nsg.id},
)

nic2 = network.NetworkInterface(
    "nic2",
    resource_group_name=resource_group.name,
    location=azure_location,
    network_interface_name=f"{resource_group_name}-nic2",
    ip_configurations=[
        {
            "name": "ipConfig2",
            "subnet": {"id": subnet.id},
            "private_ip_allocation_method": "Dynamic",
            "load_balancer_backend_address_pools": [
                {"id": Output.concat(load_balancer.id, "/backendAddressPools/backendPool")}
            ],
        }
    ],
    network_security_group={"id": nsg.id},
)

# Function to Assign Reader Role to Users

email_Roland = "wi22b003@technikum-wien.at"
email_Andras = "wi22b042@technikum-wien.at"

# Role Assignment Function with Error Handling
def assign_role(user_email, resource_group, role_name_suffix):
    user = azuread.get_user(user_principal_name=user_email)
    role_assignment_name = str(uuid.uuid4())  # Ensure unique name
    return authorization.RoleAssignment(
    f"readerRoleAssignment-{role_name_suffix}",
    scope=resource_group.id,
    role_assignment_name=role_assignment_name,
    principal_id=user.object_id,
    role_definition_id=(
        f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/"
        "roleDefinitions/acdd72a7-3385-48ef-bd42-f606fba81ae7"  # Reader Role ID
    ),
    principal_type="User",
    opts=pulumi.ResourceOptions(replace_on_changes=["role_assignment_name"]),
)

# Assign Reader Role to Users
assign_role(email_Roland, resource_group, "user1")
assign_role(email_Andras, resource_group, "user2")

# Define nginx_setup script
nginx_setup = """
#cloud-config
package_update: true
packages:
  - nginx
runcmd:
  - echo '<head><title>Hello World</title></head><body><h1>Web Portal</h1><p>Hello World from {vm_name}</p></body>' > /var/www/html/index.nginx-debian.html
  - systemctl restart nginx
"""

# Base64 encode the script
encoded_nginx_setup_vm1 = base64.b64encode(nginx_setup.format(vm_name="VM1").encode("utf-8")).decode("utf-8")
encoded_nginx_setup_vm2 = base64.b64encode(nginx_setup.format(vm_name="VM2").encode("utf-8")).decode("utf-8")

# Create Virtual Machines with encoded nginx_setup for Nginx installation
vm1 = compute.VirtualMachine(
    "vm1",
    resource_group_name=resource_group.name,
    vm_name=f"{resource_group_name}-vm1",
    location=azure_location,
    hardware_profile={"vm_size": "Standard_B2s"},
    os_profile={
        "computer_name": "vm1",
        "admin_username": "azureuser",
        "admin_password": "P@ssw0rd1234!",
        "custom_data": encoded_nginx_setup_vm1,  # Inject Base64-encoded script
    },
    storage_profile={
        "image_reference": {
            "publisher": "Canonical",
            "offer": "0001-com-ubuntu-server-jammy",
            "sku": "22_04-lts-gen2",
            "version": "latest",
        },
        "os_disk": {
            "create_option": "FromImage",
            "managed_disk": {
                "storage_account_type": "Standard_LRS",
            },
        },
        "data_disks": [
            {
                "lun": 0,
                "create_option": "Empty",
                "disk_size_gb": 4,  # Additional data disk
            }
        ]
    },
    diagnostics_profile={
        "boot_diagnostics": {
            "enabled": True
        }
    },
    network_profile={"network_interfaces": [{"id": nic1.id}]},
)

vm2 = compute.VirtualMachine(
    "vm2",
    resource_group_name=resource_group.name,
    vm_name=f"{resource_group_name}-vm2",
    location=azure_location,
    hardware_profile={"vm_size": "Standard_B2s"},
    os_profile={
        "computer_name": "vm2",
        "admin_username": "azureuser",
        "admin_password": "P@ssw0rd1234!",
        "custom_data": encoded_nginx_setup_vm2,  # Inject Base64-encoded script
    },
    storage_profile={
        "image_reference": {
            "publisher": "Canonical",
            "offer": "0001-com-ubuntu-server-jammy",
            "sku": "22_04-lts-gen2",
            "version": "latest",
        },
        "os_disk": {
            "create_option": "FromImage",
            "managed_disk": {
                "storage_account_type": "Standard_LRS",
            },
        },
        "data_disks": [
            {
                "lun": 0,
                "create_option": "Empty",
                "disk_size_gb": 4,  # Additional data disk
            }
        ]
    },
    diagnostics_profile={
        "boot_diagnostics": {
            "enabled": True
        }
    },
    network_profile={"network_interfaces": [{"id": nic2.id}]},
)

# Create an Action Group
action_group = insights.ActionGroup(
    "action-group",
    location="global",
    resource_group_name=resource_group.name,
    action_group_name=pulumi.Output.concat(
        resource_group.name,
        "-action-group",
    ),
    group_short_name="action-short",
    enabled=True,
    email_receivers=[
        insights.EmailReceiverArgs(
            name="Roland",
            email_address="wi22b003@technikum-wien.at"
        ),
    ],
)

# Create CPU Metric Alert
cpu_metric_alert = azure_native.insights.MetricAlert(
    "cpu-metric-alert",
    resource_group_name=resource_group.name,
    rule_name="HighCpuUsageAlert",
    description="Trigger an alert when CPU usage exceeds 80 percent over a 5-minute period.",
    severity=3,  # Medium severity (1=critical, 2=error, 3=warning, 4=informational)
    enabled=True,
    location="global",
    target_resource_region="westeurope", 
    target_resource_type="Microsoft.Compute/virtualMachines",  # VM resource type
    scopes=[vm1.id, vm2.id],  # Resources being monitored
    criteria=azure_native.insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
        odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
        all_of=[
            azure_native.insights.MetricCriteriaArgs(
                criterion_type="StaticThresholdCriterion",
                name="High CPU Usage",  # Name of the criteria
                metric_name="Percentage CPU",  # Metric to monitor
                metric_namespace="Microsoft.Compute/virtualMachines",
                time_aggregation=azure_native.insights.AggregationTypeEnum.AVERAGE,  # Average CPU over time
                operator=azure_native.insights.ConditionOperator.GREATER_THAN,  # Trigger if greater than threshold
                threshold=80,  # Threshold for high CPU usage
            )
        ],
    ),
    actions=[
        azure_native.insights.MetricAlertActionArgs(
            action_group_id=action_group.id,  # Action group to send notifications
        )
    ],
    evaluation_frequency="PT1M",  # Evaluate every minute
    window_size="PT5M",  # Monitor over a 5-minute sliding window
)


# Outputs
pulumi.export("PublicIP", public_ip.ip_address)
pulumi.export("httpEndpoint", Output.concat("http://", public_ip.ip_address))