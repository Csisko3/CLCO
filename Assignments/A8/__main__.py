#A8: Load Balancing
import pulumi
import pulumi_azure_native as azure_native
import base64

# Create a resource group
resource_group = azure_native.resources.ResourceGroup("resourceGroup", resource_group_name="rg_a8")

# Create a virtual network
vnet = azure_native.network.VirtualNetwork(
    "vnet",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    address_space={"addressPrefixes": ["10.0.0.0/16"]},
)

# Create a subnet for the virtual machines
subnet = azure_native.network.Subnet(
    "subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
)

# Create two network interfaces for the virtual machines
nic1 = azure_native.network.NetworkInterface(
    "nic1",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[{
        "name": "ipConfig1",
        "subnet": {"id": subnet.id},
        "privateIPAddressVersion": "IPv4",
        "loadBalancerBackendAddressPools": [
            {"id": pulumi.Output.concat(load_balancer.id, "/backendAddressPools/", lb_backend_pool_name)},
        ],
    }]
)

nic2 = azure_native.network.NetworkInterface(
    "nic2",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[{
        "name": "ipConfig2",
        "subnet": {"id": subnet.id},
        "privateIPAddressVersion": "IPv4",
        "loadBalancerBackendAddressPools": [
            {"id": pulumi.Output.concat(load_balancer.id, "/backendAddressPools/", lb_backend_pool_name)},
        ],
    }]
)


# Define a startup script for Nginx setup
nginx_startup_script = """#!/bin/bash
sudo apt update
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
echo "<h1>Welcome to VM $(hostname)</h1>" | sudo tee /var/www/html/index.html
"""
custom_data = base64.b64encode(nginx_startup_script.encode("utf-8")).decode("utf-8")

# Create two virtual machines with Nginx installed
vm_size = "Standard_B1s"  # VM size for the virtual machines

vm1 = azure_native.compute.VirtualMachine(
    "vm1",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    network_profile={"network_interfaces": [{"id": nic1.id}]},
    hardware_profile={"vm_size": vm_size},
    os_profile={
        "admin_username": "adminuser",
        "admin_password": "SecureP@ssw0rd123",
        "computer_name": "vm1",
        "custom_data": custom_data,
        "linuxConfiguration": {
            "disablePasswordAuthentication": False
        },
    },
    storage_profile={
        "os_disk": {"create_option": "FromImage", "name": "osdisk1"},
        "image_reference": {
            "publisher": "Canonical",
            "offer": "UbuntuServer",
            "sku": "18.04-LTS",
            "version": "latest",
        },
    },
)

vm2 = azure_native.compute.VirtualMachine(
    "vm2",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    network_profile={"network_interfaces": [{"id": nic2.id}]},
    hardware_profile={"vm_size": vm_size},
    os_profile={
        "admin_username": "adminuser",
        "admin_password": "SecureP@ssw0rd123",
        "computer_name": "vm2",
        "custom_data": custom_data,
        "linuxConfiguration": {
            "disablePasswordAuthentication": False
        },
    },
    storage_profile={
        "os_disk": {"create_option": "FromImage", "name": "osdisk2"},
        "image_reference": {
            "publisher": "Canonical",
            "offer": "UbuntuServer",
            "sku": "18.04-LTS",
            "version": "latest",
        },
    },
)

# Create a Public IP
public_ip = azure_native.network.PublicIPAddress(
    "publicIP",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku={"name": "Standard"},
    public_ip_allocation_method="Static", # Static for stability. DNS config, LB, etc.
    zones=["1", "2", "3"],
)

# Backend Pool, Frontend IP, and Probes IDs
lb_name = "loadBalancer"
lb_backend_pool_name = "BackendPool"
lb_frontend_ip_config_name = "LoadBalancerFrontend"
lb_probe_name = "httpHealthProbe"

# Create the Load Balancer
load_balancer = azure_native.network.LoadBalancer(
    "loadBalancer",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku={"name": "Standard"},
    frontend_ip_configurations=[
        {
            "name": lb_frontend_ip_config_name,
            "publicIPAddress": {"id": public_ip.id},
        }
    ],
    backend_address_pools=[
        {
            "name": lb_backend_pool_name,
        }
    ],
    probes=[
        {
            "name": lb_probe_name,
            "protocol": "Http",
            "port": 80,
            "requestPath": "/",
            "interval_in_seconds": 5,
            "number_of_probes": 2,
        }
    ],
)

# Export Outputs
pulumi.export("vm1_name", vm1.name)
pulumi.export("vm2_name", vm2.name)
pulumi.export("public_ip", public_ip.ip_address)

pulumi.export("backend_pool_id", pulumi.Output.concat(load_balancer.id, "/backendAddressPools/", lb_backend_pool_name))
pulumi.export("nic1_id", nic1.id)
pulumi.export("nic2_id", nic2.id)

# BUG: IP Address gives timeout (not solved)