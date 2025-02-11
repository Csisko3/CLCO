import pulumi
import pulumi_azure_native as azure_native
from pulumi_azure_native.cognitiveservices import Account, SkuArgs, list_account_keys
from pulumi_azure_native.network import VirtualNetwork, Subnet, PrivateZone
from pulumi_azure_native.web import AppServicePlan, WebApp, SiteConfigArgs
from pulumi import Output

# Create the Resource Group
resource_group = azure_native.resources.ResourceGroup("resourceGroup", resource_group_name="rg_a7")

# Create the Azure Service (Language Service)
language_service = Account(
    "CLCOA7",
    resource_group_name=resource_group.name,
    kind="CognitiveServices",
    sku=SkuArgs(name="S0"),  
    location="westeurope",
    properties={"publicNetworkAccess": "Enabled"},  # Allow public access 
)

# Create Virtual Network
vnet = VirtualNetwork(
    "myVnet",
    resource_group_name=resource_group.name,
    location="westeurope",
    address_space={"addressPrefixes": ["10.0.0.0/16"]},
)

# Subnet for Web App
web_app_subnet = Subnet(
    "webAppSubnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
)

# Subnet for AI Service
ai_service_subnet = Subnet(
    "aiServiceSubnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.2.0/24",
)

# Create Private DNS Zone
dns_zone = PrivateZone(
    "privateDnsZone",
    resource_group_name=resource_group.name,
    private_zone_name="privatelink.cognitiveservices.azure.com", 
    location="global",  # Private DNS Zones are global resources
)

# Create Virtual Network Link
dns_link = azure_native.network.VirtualNetworkLink(
    "dnsLink",
    location="global",
    private_zone_name="privatelink.cognitiveservices.azure.com",  # DNS Zone name
    resource_group_name=resource_group.name,
    virtual_network={
        "id": vnet.id,  # Reference the Virtual Network ID
    },
    registration_enabled=False,
    virtual_network_link_name="dnsLink1",
)

# Disable public network access for Service
language_service_private = Account(
    "languageServicePrivate",
    resource_group_name=resource_group.name,
    kind="CognitiveServices",
    sku=SkuArgs(name="S0"),
    location="westeurope",
    properties={"publicNetworkAccess": "Disabled"}, # Disable public access for security reasons
    # was open before so keys can be fetched
)

# Fetch the account keys directly 
keys = list_account_keys(    #fetching keys with "list_account_keys" API call 
    resource_group_name=resource_group.name,
    account_name=language_service.name,  #  language_service.name = CLCOA7 (dyn)
)

# Extract the primary key (key1)
primary_key = keys.key1

# Construct the endpoint URL
endpoint = Output.concat("https://", language_service.name, ".cognitiveservices.azure.com/")

# Create an App Service Plan
app_service_plan = AppServicePlan(
    "myAppServicePlan",
    resource_group_name=resource_group.name,
    location="westeurope",
    sku={
        "name": "F1",  # Free Tier for testing
        "tier": "Free",
    },
)

# Create the Web App
web_app = WebApp(
    "myWebApp",
    resource_group_name=resource_group.name,
    location="westeurope",
    server_farm_id=app_service_plan.id,
    https_only=True,  # HTTPS only
    site_config=SiteConfigArgs(
        app_settings=[
            {"name": "AZ_ENDPOINT", "value": endpoint},  # Use service endpoint
            {"name": "AZ_KEY", "value": primary_key},  # Use the first key
        ],
    ),
)

# Export Outputs
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("web_app_url", web_app.default_host_name.apply(lambda host_name: f"https://{host_name}"))
