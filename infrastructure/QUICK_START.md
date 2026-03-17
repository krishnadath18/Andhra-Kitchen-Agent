# Quick Start Guide

**IMPORTANT**: This guide covers the legacy deployment flow. For secure production deployment with all security fixes, use:
```bash
# Secure deployment path
./infrastructure/scripts/deploy-api-gateway.sh
```

See `docs/security/DEPLOYMENT.md` for complete secure deployment instructions.

---

Get the Andhra Kitchen Agent infrastructure up and running in 10 minutes (legacy flow).

## Prerequisites

- AWS Account
- AWS CLI installed and configured
- `jq` installed (for JSON processing)

## 5-Step Deployment

### 1. Configure AWS CLI

```bash
aws configure
# Enter your credentials
# Region: ap-south-1
```

### 2. Enable Bedrock Models

Go to AWS Console → Bedrock → Model access → Enable:
- Claude 3 Haiku
- Claude 3 Sonnet

### 3. Make Scripts Executable

```bash
chmod +x infrastructure/scripts/*.sh
```

### 4. Deploy Infrastructure

```bash
./infrastructure/scripts/deploy.sh dev
```

Wait 5-10 minutes for completion.

### 5. Validate & Populate Data

```bash
# Validate deployment
./infrastructure/scripts/validate.sh dev

# Load market prices
./infrastructure/scripts/populate-market-prices.sh dev
```

## Get Your API Endpoint

```bash
aws cloudformation describe-stacks \
  --stack-name andhra-kitchen-agent-dev \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

## Test Your API

```bash
API_ENDPOINT="<your-endpoint-from-above>"

curl -X POST ${API_ENDPOINT}/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "message": "Hello",
    "language": "en"
  }'
```

## What's Deployed?

✓ IAM roles with least-privilege permissions  
✓ DynamoDB tables (sessions, market prices, reminders)  
✓ S3 bucket with 24-hour lifecycle policy  
✓ API Gateway with rate limiting  
✓ Lambda functions (placeholder code)  
✓ CloudWatch logging and alarms  

## Next Steps

1. Deploy your Lambda application code
2. Set up Streamlit frontend
3. Configure monitoring dashboards
4. Test end-to-end workflow

## Teardown

To delete everything:

```bash
./infrastructure/scripts/teardown.sh dev
```

## Need Help?

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.
