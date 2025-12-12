# Azure OpenAI Setup Guide

This guide will help you configure Azure OpenAI to replace Gemini and solve API rate limit issues.

## Quick Start

### Option 1: Automated Provisioning (Recommended)

1. **Run the provisioning script:**
   ```powershell
   cd i:\projects\op_veritas_2
   .\scripts\provision_azure_openai.ps1
   ```

2. **Copy the output to your `.env` file:**
   The script will output configuration values. Add them to your `.env` file.

3. **Restart Docker containers:**
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

### Option 2: Manual Configuration

If you already have an Azure OpenAI resource:

1. **Update `.env` file:**
   ```bash
   INGESTION_AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
   INGESTION_AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
   INGESTION_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
   INGESTION_AZURE_OPENAI_API_VERSION=2024-05-01-preview
   INGESTION_ENTERPRISE_LLM_API_KEY=your_azure_openai_api_key
   INGESTION_ENTERPRISE_EMBEDDING_API_KEY=your_azure_openai_api_key
   MODEL_PROVIDERS_PRIMARY=azure-openai
   ```

2. **Restart Docker containers:**
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

## Verification

### 1. Check Logs
```powershell
docker-compose logs api | Select-String "Azure"
```

You should see logs indicating Azure OpenAI initialization.

### 2. Test API
```powershell
curl http://localhost:8001/agents/chat -X POST `
  -H "Content-Type: application/json" `
  -d '{"message": "Test Azure OpenAI integration"}'
```

### 3. Monitor Usage
- Go to [Azure Portal](https://portal.azure.com)
- Navigate to your Azure OpenAI resource
- Check **Metrics** for API calls

## Troubleshooting

### Issue: "Azure OpenAI not found"
- Verify `INGESTION_AZURE_OPENAI_ENDPOINT` is set correctly
- Check that the endpoint URL is accessible

### Issue: "Deployment not found"
- Verify deployment names match exactly
- Check Azure Portal → Your OpenAI Resource → Deployments

### Issue: "Authentication failed"
- Verify API key is correct
- Check that the key hasn't expired

### Rollback to Gemini
If you need to revert:
```bash
MODEL_PROVIDERS_PRIMARY=gemini
```
Then restart containers.

## Cost Optimization

Azure OpenAI pricing is based on tokens:
- **GPT-4o**: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- **Embeddings**: ~$0.10 per 1M tokens

Monitor usage in Azure Portal to avoid unexpected costs.

## Advanced Configuration

### Using Different Models
Edit `.env` to change models:
```bash
INGESTION_AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-35-turbo  # Cheaper option
```

### Rate Limits
Azure OpenAI has higher default limits than Gemini:
- Standard: 240K tokens/min
- Can request increases via Azure Support

## Next Steps

Once configured, the application will automatically:
- Use Azure OpenAI for all LLM calls
- Use Azure OpenAI for embeddings
- Fall back to Gemini if Azure OpenAI fails (if configured as secondary)
