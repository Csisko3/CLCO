#A9: Storage 
import base64
import pulumi
import backup_plan
from pulumi_azure_native import compute, network, resources

config = pulumi.Config("azure-native")
subscription_id = config.require("subscriptionId")

# Static resource group name
resource_group_name = "a9_rg"
resource_group = resources.ResourceGroup("a9_rg")

# Create a Virtual Network (VNet)
vnet = network.VirtualNetwork(
    "vnet",
    resource_group_name=resource_group.name,
    address_space={"address_prefixes": ["10.0.0.0/16"]}
)

# Create a Subnet within the VNet
subnet = network.Subnet(
    "subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24"
)

# Create Public IPs
public_ip1 = network.PublicIPAddress(
    "vm1PublicIp",
    resource_group_name=resource_group.name,
    public_ip_allocation_method="Dynamic" # Dynamic: Cheap, non critical 
)

public_ip2 = network.PublicIPAddress(
    "vm2PublicIp",
    resource_group_name=resource_group.name,
    public_ip_allocation_method="Dynamic"
)

# Create Network Interfaces
nic1 = network.NetworkInterface(
    "nic1",
    resource_group_name=resource_group.name,
    ip_configurations=[{
        "name": "ipconfig1",
        "subnet": {"id": subnet.id},
        "private_ip_address_version": "IPv4",
        "public_ip_address": {"id": public_ip1.id}
    }]
)

nic2 = network.NetworkInterface(
    "nic2",
    resource_group_name=resource_group.name,
    ip_configurations=[{
        "name": "ipconfig2",
        "subnet": {"id": subnet.id},
        "private_ip_address_version": "IPv4",
        "public_ip_address": {"id": public_ip2.id}
    }]
)

# Create Managed Disks
disk1 = compute.Disk(
    "disk1",
    resource_group_name=resource_group.name,
    disk_size_gb=1024,
    sku={"name": "Premium_LRS"},
    creation_data={"create_option": "Empty"}
)

disk2 = compute.Disk(
    "disk2",
    resource_group_name=resource_group.name,
    disk_size_gb=1024,
    sku={"name": "Premium_LRS"},
    creation_data={"create_option": "Empty"}
)

# Encode the custom data script for NGINX installation
custom_data_script = """#!/bin/bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
"""
encoded_custom_data = base64.b64encode(custom_data_script.encode("utf-8")).decode("utf-8")

vm1 = compute.VirtualMachine(
    "vm1",
    resource_group_name=resource_group.name,
    network_profile={"network_interfaces": [{"id": nic1.id}]},
    hardware_profile={"vm_size": "Standard_DS1_v2"},
    os_profile={
        "computer_name": "vm1",
        "admin_username": "azureuser",
        "admin_password": "SecureP@ssw0rd!",
        "custom_data": encoded_custom_data, 
    },
    storage_profile={
        "image_reference": {
            "publisher": "Canonical",
            "offer": "UbuntuServer",
            "sku": "18.04-LTS",
            "version": "latest"
        },
        "os_disk": {"create_option": "FromImage"},
        "data_disks": [{
            "lun": 0,
            "name": disk1.name,
            "create_option": "Attach",
            "managed_disk": {"id": disk1.id}
        }]
    }
)

vm2 = compute.VirtualMachine(
    "vm2",
    resource_group_name=resource_group.name,
    network_profile={"network_interfaces": [{"id": nic2.id}]},
    hardware_profile={"vm_size": "Standard_DS1_v2"},
    os_profile={
        "computer_name": "vm2",
        "admin_username": "azureuser",
        "admin_password": "SecureP@ssw0rd!",
        "custom_data": encoded_custom_data,  # Use base64-encoded script
    },
    storage_profile={
        "image_reference": {
            "publisher": "Canonical",
            "offer": "UbuntuServer",
            "sku": "18.04-LTS",
            "version": "latest"
        },
        "os_disk": {"create_option": "FromImage"},
        "data_disks": [{
            "lun": 0,
            "name": disk2.name,
            "create_option": "Attach",
            "managed_disk": {"id": disk2.id}
        }]
    }
)

# Retrieve the dynamically assigned public IPs
vm1_public_ip = network.get_public_ip_address_output(
    resource_group_name=resource_group.name,
    public_ip_address_name=public_ip1.name
)

vm2_public_ip = network.get_public_ip_address_output(
    resource_group_name=resource_group.name,
    public_ip_address_name=public_ip2.name
)

# Export the actual public IPs
pulumi.export("vm1_public_ip", vm1_public_ip.ip_address)
pulumi.export("vm2_public_ip", vm2_public_ip.ip_address)

backup_plan.create_backup_plan(vm1, vm2, resource_group)

