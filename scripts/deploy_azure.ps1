# Azure Deployment Script for Co-Counsel
# Usage: .\deploy_azure.ps1 -ResourceGroupName <rg-name> -AcrName <acr-name> -PostgresServerName <psql-name> -PostgresPassword <password> -StorageAccountName <storage-name> -StorageKey <key>

param (
    [Parameter(Mandatory = $true)] [string]$ResourceGroupName,
    [Parameter(Mandatory = $true)] [string]$AcrName,
    [Parameter(Mandatory = $true)] [string]$PostgresServerName,
    [Parameter(Mandatory = $true)] [string]$PostgresPassword,
    [Parameter(Mandatory = $true)] [string]$StorageAccountName,
    [Parameter(Mandatory = $true)] [string]$StorageKey,
    [string]$Location = "eastus",
    [string]$EnvironmentName = "cae-cocounsel"
)

$ErrorActionPreference = "Stop"

# 1. Login to ACR
Write-Host "Logging into ACR '$AcrName'..."
az acr login --name $AcrName

$AcrServer = "$AcrName.azurecr.io"

# 2. Build and Push Backend
Write-Host "Building Backend Image..."
docker build -t "$AcrServer/cocounsel-api:latest" -f ./backend/Dockerfile ./backend
Write-Host "Pushing Backend Image..."
docker push "$AcrServer/cocounsel-api:latest"

# 3. Build and Push Frontend
Write-Host "Building Frontend Image..."
docker build -t "$AcrServer/cocounsel-frontend:latest" -f ./frontend/Dockerfile ./frontend
Write-Host "Pushing Frontend Image..."
docker push "$AcrServer/cocounsel-frontend:latest"

# 4. Deploy Neo4j (Container App)
Write-Host "Deploying Neo4j..."
az containerapp create `
    --name neo4j `
    --resource-group $ResourceGroupName `
    --environment $EnvironmentName `
    --image neo4j:5.23.0 `
    --target-port 7474 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 1 `
    --env-vars NEO4J_AUTH=neo4j/password # Change this!
# Note: For production, mount Azure Files for persistence

# 5. Deploy Qdrant (Container App)
Write-Host "Deploying Qdrant..."
az containerapp create `
    --name qdrant `
    --resource-group $ResourceGroupName `
    --environment $EnvironmentName `
    --image qdrant/qdrant:latest `
    --target-port 6333 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 1
# Note: For production, mount Azure Files for persistence

# 6. Deploy Backend API
Write-Host "Deploying Backend API..."
az containerapp create `
    --name api `
    --resource-group $ResourceGroupName `
    --environment $EnvironmentName `
    --image "$AcrServer/cocounsel-api:latest" `
    --target-port 8000 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 3 `
    --registry-server $AcrServer `
    --env-vars `
    POSTGRES_HOST="$PostgresServerName.postgres.database.azure.com" `
    POSTGRES_USER="cocounsel_admin" `
    POSTGRES_PASSWORD="$PostgresPassword" `
    POSTGRES_DB="cocounsel" `
    NEO4J_URI="neo4j://neo4j:7687" `
    QDRANT_URL="http://qdrant:6333" `
    AZURE_STORAGE_ACCOUNT="$StorageAccountName" `
    AZURE_STORAGE_KEY="$StorageKey" `
    DOCUMENT_STORAGE_PATH="azure://$StorageAccountName/documents"

# 7. Deploy Frontend
Write-Host "Deploying Frontend..."
# Get API URL
$ApiUrl = $(az containerapp show --name api --resource-group $ResourceGroupName --query properties.configuration.ingress.fqdn -o tsv)
Write-Host "API URL: https://$ApiUrl"

az containerapp create `
    --name frontend `
    --resource-group $ResourceGroupName `
    --environment $EnvironmentName `
    --image "$AcrServer/cocounsel-frontend:latest" `
    --target-port 80 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 2 `
    --registry-server $AcrServer `
    --env-vars `
    VITE_API_BASE_URL="https://$ApiUrl"

Write-Host "Deployment Complete!"
$FrontendUrl = $(az containerapp show --name frontend --resource-group $ResourceGroupName --query properties.configuration.ingress.fqdn -o tsv)
Write-Host "Frontend URL: https://$FrontendUrl"
