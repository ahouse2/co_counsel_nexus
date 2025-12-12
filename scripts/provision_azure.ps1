# Azure Provisioning Script for Co-Counsel
# Usage: .\provision_azure.ps1 -SubscriptionId <your-subscription-id> -Location <location>

param (
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [string]$Location = "eastus",
    [string]$ResourceGroupName = "rg-cocounsel-prod",
    [string]$AcrName = "acrcocounsel$((Get-Random -Minimum 1000 -Maximum 9999))",
    [string]$PostgresServerName = "psql-cocounsel-$((Get-Random -Minimum 1000 -Maximum 9999))",
    [string]$StorageAccountName = "stcocounsel$((Get-Random -Minimum 1000 -Maximum 9999))"
)

# Error handling
$ErrorActionPreference = "Stop"

Write-Host "Starting Azure Provisioning..." -ForegroundColor Cyan

# 1. Login and Set Subscription
Write-Host "Verifying Azure Login..."
az account show > $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please login to Azure first using 'az login'" -ForegroundColor Red
    exit 1
}

Write-Host "Setting Subscription to $SubscriptionId..."
az account set --subscription $SubscriptionId

# 2. Create Resource Group
Write-Host "Creating Resource Group '$ResourceGroupName' in '$Location'..."
az group create --name $ResourceGroupName --location $Location

# 3. Create Azure Container Registry (ACR)
Write-Host "Creating ACR '$AcrName'..."
az acr create --resource-group $ResourceGroupName --name $AcrName --sku Basic --admin-enabled true

# 4. Create Azure Container Apps Environment
Write-Host "Creating Container Apps Environment..."
az containerapp env create --name "cae-cocounsel" --resource-group $ResourceGroupName --location $Location

# 5. Create Azure Database for PostgreSQL (Flexible Server)
Write-Host "Creating PostgreSQL Flexible Server '$PostgresServerName'..."
# Note: This will prompt for admin password if not provided via env vars, or generate one.
# For automation, we'll generate a random password.
$AdminPassword = -join ((33..126) | Get-Random -Count 16 | % { [char]$_ })
Write-Host "Generated Postgres Password: $AdminPassword" -ForegroundColor Yellow
# Save this password!

az postgres flexible-server create `
    --resource-group $ResourceGroupName `
    --name $PostgresServerName `
    --location $Location `
    --admin-user "cocounsel_admin" `
    --admin-password $AdminPassword `
    --sku-name Standard_B1ms `
    --tier Burstable `
    --version 16 `
    --storage-size 32 `
    --yes

# Allow access from Azure services
az postgres flexible-server firewall-rule create `
    --resource-group $ResourceGroupName `
    --name $PostgresServerName `
    --rule-name "AllowAzureServices" `
    --start-ip-address 0.0.0.0 `
    --end-ip-address 0.0.0.0

# 6. Create Storage Account
Write-Host "Creating Storage Account '$StorageAccountName'..."
az storage account create `
    --name $StorageAccountName `
    --resource-group $ResourceGroupName `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2

# Create Containers
$StorageKey = $(az storage account keys list --resource-group $ResourceGroupName --account-name $StorageAccountName --query "[0].value" -o tsv)
az storage container create --name "documents" --account-name $StorageAccountName --account-key $StorageKey
az storage container create --name "graphs" --account-name $StorageAccountName --account-key $StorageKey

# 7. Output Configuration
Write-Host "Provisioning Complete!" -ForegroundColor Green
Write-Host "----------------------------------------"
Write-Host "Resource Group: $ResourceGroupName"
Write-Host "ACR Name: $AcrName"
Write-Host "Postgres Server: $PostgresServerName"
Write-Host "Postgres Admin: cocounsel_admin"
Write-Host "Postgres Password: $AdminPassword"
Write-Host "Storage Account: $StorageAccountName"
Write-Host "Storage Key: $StorageKey"
Write-Host "----------------------------------------"
Write-Host "Please save these credentials for the deployment step."
