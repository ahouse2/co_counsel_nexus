# Azure OpenAI Provisioning Script
# This script provisions an Azure OpenAI resource with chat and embedding deployments

param (
    [Parameter(Mandatory = $false)]
    [string]$SubscriptionId,

    [string]$Location = "eastus2",
    [string]$ResourceGroupName = "rg-cocounsel-prod",
    [string]$OpenAIResourceName = "cocounsel-openai-prod",
    [string]$ChatDeploymentName = "gpt-4o",
    [string]$ChatModelName = "gpt-4o",
    [string]$ChatModelVersion = "2024-05-13",
    [string]$EmbeddingDeploymentName = "text-embedding-ada-002",
    [string]$EmbeddingModelName = "text-embedding-ada-002",
    [string]$EmbeddingModelVersion = "2",
    [int]$ChatCapacity = 10,
    [int]$EmbeddingCapacity = 10
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure OpenAI Provisioning Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set subscription if provided
if ($SubscriptionId) {
    Write-Host "Setting Azure subscription to: $SubscriptionId" -ForegroundColor Yellow
    az account set --subscription $SubscriptionId
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to set subscription. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Check if resource group exists
Write-Host "Checking if resource group exists: $ResourceGroupName" -ForegroundColor Yellow
$rgExists = az group exists --name $ResourceGroupName
if ($rgExists -eq "false") {
    Write-Host "Resource group does not exist. Creating..." -ForegroundColor Yellow
    az group create --name $ResourceGroupName --location $Location
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create resource group. Exiting." -ForegroundColor Red
        exit 1
    }
    Write-Host "Resource group created successfully." -ForegroundColor Green
}
else {
    Write-Host "Resource group already exists." -ForegroundColor Green
}

# Create Azure OpenAI resource
Write-Host ""
Write-Host "Creating Azure OpenAI resource: $OpenAIResourceName" -ForegroundColor Yellow
az cognitiveservices account create `
    --name $OpenAIResourceName `
    --resource-group $ResourceGroupName `
    --kind OpenAI `
    --sku S0 `
    --location $Location `
    --yes

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create Azure OpenAI resource. Exiting." -ForegroundColor Red
    exit 1
}
Write-Host "Azure OpenAI resource created successfully." -ForegroundColor Green

# Wait for resource to be ready
Write-Host "Waiting for resource to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Deploy Chat Model
Write-Host ""
Write-Host "Deploying chat model: $ChatDeploymentName ($ChatModelName)" -ForegroundColor Yellow
az cognitiveservices account deployment create `
    --name $OpenAIResourceName `
    --resource-group $ResourceGroupName `
    --deployment-name $ChatDeploymentName `
    --model-name $ChatModelName `
    --model-version $ChatModelVersion `
    --model-format OpenAI `
    --sku-capacity $ChatCapacity `
    --sku-name "Standard"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to deploy chat model. Exiting." -ForegroundColor Red
    exit 1
}
Write-Host "Chat model deployed successfully." -ForegroundColor Green

# Deploy Embedding Model
Write-Host ""
Write-Host "Deploying embedding model: $EmbeddingDeploymentName ($EmbeddingModelName)" -ForegroundColor Yellow
az cognitiveservices account deployment create `
    --name $OpenAIResourceName `
    --resource-group $ResourceGroupName `
    --deployment-name $EmbeddingDeploymentName `
    --model-name $EmbeddingModelName `
    --model-version $EmbeddingModelVersion `
    --model-format OpenAI `
    --sku-capacity $EmbeddingCapacity `
    --sku-name "Standard"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to deploy embedding model. Exiting." -ForegroundColor Red
    exit 1
}
Write-Host "Embedding model deployed successfully." -ForegroundColor Green

# Get endpoint and keys
Write-Host ""
Write-Host "Retrieving endpoint and API key..." -ForegroundColor Yellow
$endpoint = az cognitiveservices account show `
    --name $OpenAIResourceName `
    --resource-group $ResourceGroupName `
    --query "properties.endpoint" `
    --output tsv

$apiKey = az cognitiveservices account keys list `
    --name $OpenAIResourceName `
    --resource-group $ResourceGroupName `
    --query "key1" `
    --output tsv

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Azure OpenAI Provisioning Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration Details:" -ForegroundColor Cyan
Write-Host "----------------------" -ForegroundColor Cyan
Write-Host "Endpoint:                 $endpoint" -ForegroundColor White
Write-Host "Chat Deployment:          $ChatDeploymentName" -ForegroundColor White
Write-Host "Embedding Deployment:     $EmbeddingDeploymentName" -ForegroundColor White
Write-Host "API Key:                  $apiKey" -ForegroundColor White
Write-Host ""
Write-Host "Add these to your .env file:" -ForegroundColor Yellow
Write-Host "INGESTION_AZURE_OPENAI_ENDPOINT=$endpoint" -ForegroundColor White
Write-Host "INGESTION_AZURE_OPENAI_CHAT_DEPLOYMENT=$ChatDeploymentName" -ForegroundColor White
Write-Host "INGESTION_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$EmbeddingDeploymentName" -ForegroundColor White
Write-Host "INGESTION_AZURE_OPENAI_API_VERSION=2024-05-01-preview" -ForegroundColor White
Write-Host "INGESTION_ENTERPRISE_LLM_API_KEY=$apiKey" -ForegroundColor White
Write-Host "INGESTION_ENTERPRISE_EMBEDDING_API_KEY=$apiKey" -ForegroundColor White
Write-Host "MODEL_PROVIDERS_PRIMARY=azure-openai" -ForegroundColor White
Write-Host ""
