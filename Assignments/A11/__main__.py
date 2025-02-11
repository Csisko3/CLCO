import pulumi
import pulumi_azure_native as azure_native
import base64

# Create a resource group
resource_group = azure_native.resources.ResourceGroup("rg_a11")

# Create a public IP address
public_ip = azure_native.network.PublicIPAddress(
    "publicIP",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    public_ip_allocation_method="Dynamic",
)

# Create a virtual network and subnet
vnet = azure_native.network.VirtualNetwork(
    "vnet",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    address_space={"addressPrefixes": ["10.0.0.0/16"]},
)

subnet = azure_native.network.Subnet(
    "subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
)

# Create a network security group and allow HTTP (port 80)
nsg = azure_native.network.NetworkSecurityGroup(
    "nsg",
    resource_group_name=resource_group.name,
    location=resource_group.location,
)

allow_http_rule = azure_native.network.SecurityRule(
    "allowHttp",
    resource_group_name=resource_group.name,
    network_security_group_name=nsg.name,
    protocol="Tcp",
    source_port_range="*",
    destination_port_range="80",
    source_address_prefix="*",
    destination_address_prefix="*",
    access="Allow",
    priority=100,
    direction="Inbound",
)

# Create a network interface
nic = azure_native.network.NetworkInterface(
    "nic",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[{
        "name": "ipConfig",
        "subnet": {"id": subnet.id},
        "privateIPAddressVersion": "IPv4",
        "public_ip_address": {"id": public_ip.id},
        "networkSecurityGroup": {"id": nsg.id},
    }],
    opts=pulumi.ResourceOptions(depends_on=[public_ip])  # fixed missing dependency
)



# Define a startup script for Nginx installation
nginx_startup_script = """#!/bin/bash
sudo apt update
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
echo "<h1>Welcome to Task A11 VM</h1>" | sudo tee /var/www/html/index.html
"""
custom_data = base64.b64encode(nginx_startup_script.encode("utf-8")).decode("utf-8")

# Create a Linux virtual machine
vm = azure_native.compute.VirtualMachine(
    "vm",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    network_profile={"network_interfaces": [{"id": nic.id}]},
    hardware_profile={"vm_size": "Standard_B1s"},
    os_profile={
        "admin_username": "adminuser",
        "admin_password": "SecureP@ssw0rd123",
        "computer_name": "vm-a11",
        "custom_data": custom_data,
        "linuxConfiguration": {
            "disablePasswordAuthentication": False,
        },
    },
    storage_profile={
        "os_disk": {"create_option": "FromImage"},
        "image_reference": {
            "publisher": "Canonical",
            "offer": "UbuntuServer",
            "sku": "18.04-LTS",
            "version": "latest",
        },
    },
)

# Export Outputs with Apply
pulumi.export(
    "public_ip",
    public_ip.id.apply(
        lambda _: azure_native.network.get_public_ip_address_output(
            resource_group_name=resource_group.name,
            public_ip_address_name=public_ip.name
        ).ip_address
    )
)

# Export NSG rules (Only port 80 is allowed)
pulumi.export(
    "nsg_rules",
    azure_native.network.get_network_security_group_output(
        resource_group_name=resource_group.name,
        network_security_group_name=nsg.name
    ).security_rules
)