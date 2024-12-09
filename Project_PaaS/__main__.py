import pulumi
import pulumi_azure_native as azure_native
from pulumi_azure_native.cognitiveservices import Account, SkuArgs, list_account_keys
from pulumi_azure_native.network import VirtualNetwork, Subnet, PrivateZone
from pulumi_azure_native.web import AppServicePlan, WebApp, SiteConfigArgs
from pulumi_azure_native.web import WebAppSourceControl
from pulumi_azure_native import consumption
from pulumi import Output, Config

# Create the Resource Group
resource_group = azure_native.resources.ResourceGroup(
    "resourceGroup", 
    resource_group_name="rg_PaaS"  
)

# Create the Azure Cognitive Services (Language Service)
language_service = Account(
    "CLCO_PaaS", 
    resource_group_name=resource_group.name,  
    kind="TextAnalytics",  # Specifies the type of AI service
    sku=SkuArgs(name="F0"),  # Pricing tier
    location="westeurope",  
    properties={
        "publicNetworkAccess": "Disabled",  # Disabled for private endpoint
        "customSubDomainName": "clco-paas",  
    },
)

# Create a Virtual Network (VNet)
vnet = VirtualNetwork(
    "myVnet", 
    resource_group_name=resource_group.name,  
    location="westeurope",  
    address_space={"addressPrefixes": ["10.0.0.0/16"]},  
)

# Create Subnet for the Web App
web_app_subnet = Subnet(
    "webAppSubnet",  
    resource_group_name=resource_group.name,  
    virtual_network_name=vnet.name,  
    address_prefix="10.0.1.0/24",  
)

# Create Subnet for the AI Service
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
    location="global",  
)

# Create a Private Endpoint for the Cognitive Services account
private_endpoint = azure_native.network.PrivateEndpoint(
    "cognitiveServicesPrivateEndpoint",
    resource_group_name=resource_group.name,
    location="westeurope",
    subnet={
        "id": ai_service_subnet.id,
    },
    private_link_service_connections=[{
        "name": "cognitiveServicesPrivateConnection",
        "private_link_service_id": language_service.id,
        "group_ids": ["account"],  # For Cognitive Services
    }]
)

# Create a Virtual Network Link for the DNS Zone
dns_link = azure_native.network.VirtualNetworkLink(
    "dnsLink",  
    location="global",  
    private_zone_name="privatelink.cognitiveservices.azure.com",  
    resource_group_name=resource_group.name,  
    virtual_network={"id": vnet.id},  
    registration_enabled=False,  
    virtual_network_link_name="dnsLink1",  
)

# Fetch the Account Keys for the Language Service
keys = language_service.name.apply(lambda name: azure_native.cognitiveservices.list_account_keys(
    resource_group_name=resource_group.name,
    account_name=name,
))

# Extract the primary key (key1)
primary_key = keys.apply(lambda k: k.key1) 

# Construct the endpoint URL for the Language Service
endpoint = Output.concat("https://", language_service.name, ".privatelink.cognitiveservices.azure.com/")

# Create an App Service Plan
app_service_plan = AppServicePlan(
    "myAppServicePlan",
    resource_group_name=resource_group.name,
    location="westeurope",
    sku={"name": "B1", "tier": "Basic", "capacity": 3},  
    kind="Linux",  
    reserved=True
)

# Create the Web App
web_app_name = f"CLCOWebApp-{pulumi.get_stack()}"

web_app = WebApp(
    web_app_name,  
    resource_group_name=resource_group.name,
    location="westeurope",
    server_farm_id=app_service_plan.id,
    https_only=True,
    kind="app,linux",  
    site_config=SiteConfigArgs(
        linux_fx_version="PYTHON|3.9",
        always_on=True,
        ftps_state="Disabled",
        app_settings=[
            {"name": "AZ_ENDPOINT", "value": endpoint},
            {"name": "AZ_KEY", "value": primary_key},
            {"name": "WEBSITE_RUN_FROM_PACKAGE", "value": "0"},
        ],
    ),
)

source_control = WebAppSourceControl(
    "sourceControl",
    name=web_app.name,
    resource_group_name=resource_group.name,
    repo_url="https://github.com/Csisko3/clco-demo" ,
    branch="main",
    is_manual_integration=True,
    deployment_rollback_enabled=True,
    is_git_hub_action=False,
)

# Define the budget
budget = consumption.Budget(
    "azure_budget",
    scope=f"/subscriptions/c96c9bcd-9264-4416-8813-4819a41ef77e",  # Scope is the subscription
    amount=50.0,  # Budget in Dollar
    time_grain="Monthly",  # Budget resets monthly
    category="Cost",  # Track actual costs
    time_period=consumption.BudgetTimePeriodArgs(
        start_date="2024-12-01",  # Start is required
        end_date="2025-12-31",    # end is optional
    ),
    notifications={
        "ActualCostThreshold": consumption.NotificationArgs(
            enabled=True,
            operator="GreaterThanOrEqualTo",  # = or >=
            threshold=30.0,  
            contact_emails=["wi22b003@technikum-wien.at"],  # Notification email
        ),
        "ForecastedCostThreshold": consumption.NotificationArgs(
            enabled=True,
            operator="GreaterThanOrEqualTo",
            threshold=20.0,
            contact_emails=["wi22b003@technikum-wien.at"],
        ),
    },
)

# Export Outputs
pulumi.export("web_app_url", web_app.default_host_name.apply(lambda host_name: f"https://{host_name}"))
