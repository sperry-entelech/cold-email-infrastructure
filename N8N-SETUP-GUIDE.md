# n8n Claude Icebreaker Setup Guide

This guide shows you how to set up the n8n workflow for Claude-powered icebreaker generation.

## 🎯 Why Use n8n for Icebreakers?

### Benefits:
- **Visual Workflow Management**: See the entire icebreaker process in a visual interface
- **Easy Debugging**: Monitor each step and catch issues quickly
- **Flexible Templates**: Modify prompts without changing Python code
- **Rate Limiting**: Built-in request throttling and retry logic
- **Monitoring**: Track performance and errors in real-time
- **Scaling**: Easy to add parallel processing or batch operations

### vs Direct API:
- **Direct Claude API**: Simpler, faster setup, fewer moving parts
- **n8n Workflow**: More control, monitoring, and easier customization

## 🚀 Quick Setup (15 minutes)

### Option A: Self-Hosted n8n (Free)

1. **Install n8n**:
```bash
# Via npm
npm install -g n8n

# Via Docker
docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n
```

2. **Access n8n**: Open `http://localhost:5678`

3. **Import Workflow**:
   - Go to Workflows → Import from File
   - Select `n8n-workflows/claude-icebreaker-generator.json`
   - Save the workflow

4. **Configure Claude API Credentials**:
   - Go to Settings → Credentials
   - Create new "HTTP Header Auth" credential
   - Name: `Claude API Key`
   - Header Name: `x-api-key`
   - Header Value: `your_claude_api_key_here`

5. **Activate Workflow**:
   - Click the workflow toggle to "Active"
   - Note the webhook URL (e.g., `http://localhost:5678/webhook/claude-icebreaker`)

### Option B: n8n Cloud (Paid - Easiest)

1. **Sign up**: Go to [n8n.cloud](https://n8n.cloud)
2. **Import workflow** from `n8n-workflows/claude-icebreaker-generator.json`
3. **Configure Claude credentials** (same as above)
4. **Get webhook URL** from your n8n cloud instance

## ⚙️ Configuration

### Update Your .env File:
```bash
# Set AI provider to Claude
AI_PROVIDER=claude

# Claude API key (for direct API fallback)
CLAUDE_API_KEY=your_claude_api_key_here

# n8n webhook URL (primary method)
N8N_ICEBREAKER_WEBHOOK_URL=http://localhost:5678/webhook/claude-icebreaker
```

### Workflow Configuration Options:

The n8n workflow accepts these parameters:
```json
{
  "company_name": "Test Company",
  "industry": "Marketing", 
  "first_name": "John",
  "last_name": "Smith",
  "title": "CEO",
  "website": "https://test.com",
  "template": "Love your approach to {specific_observation}..."
}
```

## 🧪 Testing

### Test n8n Connection:
```bash
# Test the n8n client
python n8n_icebreaker_client.py

# Test full system integration
python cold_email_processor.py test
```

### Test Webhook Directly:
```bash
curl -X POST http://localhost:5678/webhook/claude-icebreaker \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "industry": "Marketing",
    "first_name": "John",
    "last_name": "Smith",
    "title": "CEO"
  }'
```

## 🔧 Customizing the Workflow

### Modify the Prompt:
1. Open the workflow in n8n
2. Click the "Claude API Call" node
3. Edit the message content to customize the prompt
4. Save and test

### Add Error Handling:
- The workflow includes automatic fallback to template-based icebreakers
- Errors are logged and returned with status information
- Failed requests don't break the lead processing pipeline

### Rate Limiting:
- Built-in throttling prevents API rate limit issues
- Configurable delays between requests
- Automatic retries with exponential backoff

## 📊 Monitoring & Analytics

### n8n Dashboard:
- View execution history
- Monitor success/failure rates
- See execution times
- Debug failed runs

### Logs:
- All icebreaker generation is logged
- Error details are captured
- Performance metrics tracked

## 🔄 Fallback Strategy

The system uses a **graceful fallback approach**:

1. **n8n Workflow** (if configured)
2. **Direct Claude API** (if n8n fails)  
3. **Template-based** (if all AI fails)

This ensures your cold email system never stops working, even if one component has issues.

## 💡 Advanced Features

### Batch Processing:
The n8n client supports batch processing of multiple leads:

```python
from n8n_icebreaker_client import N8nIcebreakerClient

client = N8nIcebreakerClient()
results = client.batch_generate_icebreakers(leads, max_concurrent=5)
```

### Custom Templates:
You can pass custom templates per request:

```python
custom_template = "Noticed your work on {specific_project}, impressive {achievement}"
result = client.generate_icebreaker(lead, template=custom_template)
```

## 🚨 Troubleshooting

### Common Issues:

**"Connection refused"**
- Check n8n is running on the correct port
- Verify webhook URL in .env file

**"Claude API error"**
- Verify Claude API key is correct
- Check API key permissions and credits

**"Workflow not found"** 
- Ensure workflow is imported and activated
- Check webhook path matches configuration

**"Template not working"**
- Verify template format uses correct placeholders
- Check that required lead fields are provided

## 🎯 Production Deployment

### For Production Use:

1. **Use n8n Cloud** or deploy n8n on a reliable server
2. **Set up monitoring** and alerting for workflow failures  
3. **Configure backups** of your workflow definitions
4. **Use environment variables** for sensitive configuration
5. **Set up load balancing** if processing high volumes

### Security:
- Use HTTPS for webhook URLs
- Secure your n8n instance with authentication
- Rotate API keys regularly
- Monitor for unusual usage patterns

---

## 📋 Quick Commands Summary

```bash
# Install and test
pip install anthropic
python n8n_icebreaker_client.py

# Test full integration
python cold_email_processor.py test

# Run with n8n workflow
N8N_ICEBREAKER_WEBHOOK_URL=your_webhook_url python cold_email_processor.py
```

**Ready to generate personalized icebreakers with visual workflow management!** 🚀