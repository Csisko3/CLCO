import pulumi
import pulumi_azure_native as azure_native
import pulumi_random as random

# Create a Resource Group
resource_group = azure_native.resources.ResourceGroup("rg_a12", resource_group_name="rg_a12")

# Create a Storage Account for Boot Diagnostics
random_string = random.RandomString("randstr", length=8, special=False, upper=False)
storage_account_name = pulumi.Output.concat("metricsstorage", random_string.result)

storage_account = azure_native.storage.StorageAccount(
    "storageAccount",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    account_name=storage_account_name.apply(lambda name: name[:24]),  # Ensure the name is within the allowed length
    sku=azure_native.storage.SkuArgs(name="Standard_LRS"),
    kind="StorageV2",
)

# Create a Virtual Network and Subnet
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

# Create a Network Interface
nic = azure_native.network.NetworkInterface(
    "nic",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[{
        "name": "ipConfig",
        "subnet": {"id": subnet.id},
    }],
)

# Define and Deploy a Linux Virtual Machine with Boot Diagnostics Enabled
vm_name = "A12-linux-vm"

# Create the virtual machine
vm = azure_native.compute.VirtualMachine(
    "vm",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    network_profile={"network_interfaces": [{"id": nic.id}]},
    hardware_profile={"vm_size": "Standard_B1s"},
    os_profile={
        "admin_username": "adminuser",
        "admin_password": "SecureP@ssw0rd123",  # Replace with a secure password
        "computer_name": vm_name,
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
    diagnostics_profile=azure_native.compute.DiagnosticsProfileArgs(
        boot_diagnostics=azure_native.compute.BootDiagnosticsArgs(
            enabled=True,
            storage_uri=storage_account.primary_endpoints.apply(lambda endpoints: endpoints["blob"]),
        )
    ),
)

# Export Outputs
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("vm_name", vm.name)
pulumi.export("storage_account_name", storage_account_name)