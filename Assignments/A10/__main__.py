import subprocess
import json
import pulumi
from pulumi import Config
import pulumi_azure_native as azure_native

# Read the user email from Pulumi configuration
config = Config()
user_email = config.require("userEmail")
subscription_id = config.require("subscription_id")

# Create a resource group
resource_group = azure_native.resources.ResourceGroup("rg_a10")

# Get the object ID of the user by email
user_object_id_cmd = [
    "az", "ad", "user", "show",
    "--id", user_email,
    "--query", "id",
    "--output", "tsv"
]
user_object_id = subprocess.check_output(user_object_id_cmd, shell=True).decode().strip()

# List available roles and their IDs
role_definitions_cmd = [
    "az", "role", "definition", "list",
    "--output", "json"
]
role_definitions_json = subprocess.check_output(role_definitions_cmd, shell=True, encoding='utf-8', errors='ignore').strip()
role_definitions = json.loads(role_definitions_json)

# Extract relevant information about roles and limit to 20
available_roles = [
    {
        "roleName": rd["roleName"],
        "roleDefinitionId": rd["id"]
    }
    for rd in role_definitions[:20]  # Limit to 20 roles there are 600+ roles
]

# Export the available roles
pulumi.export("available_roles", available_roles)

# Find the "Reader" role definition
reader_role = next(rd for rd in role_definitions if rd["roleName"] == "Reader")
reader_role_id = reader_role["id"]
reader_role_name = reader_role["roleName"]

# Export the role assignment details
pulumi.export("role_assignment", {
    "assignee": user_email,
    "roleName": reader_role_name,
    "scope": resource_group.id
})