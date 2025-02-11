import pulumi
from pulumi_azure_native import recoveryservices

def create_backup_plan(vm1, vm2, resource_group):
    # Create a Recovery Services Vault with the correct PublicNetworkAccess parameter for Azure Resources
    vault = recoveryservices.Vault(
        "backupVault",
        resource_group_name=resource_group.name,
        location="westeurope",
        sku={
            "name": "Standard"
        },
        properties={
            "publicNetworkAccess": "Enabled",  # Allow access over public networks
            "softDeleteFeatureState": "Enabled"
        }
    )

    # Export the vault name
    pulumi.export("backupVaultName", vault.name)

