# Quick Deployment Guide

## Prerequisites
- AWS CLI configured with credentials
- Python 3.11+ installed
- Bash shell (Linux/macOS/Git Bash on Windows)

## Deploy in 5 Steps

### 1. Configure Environment
```bash
cp .env.template .env
# Edit .env with your AWS account details
```

### 2. Deploy Lambda Functions
```bash
cd infrastructure/scripts
./deploy-lambda.sh
```

### 3. Deploy API Gateway
```bash
./deploy-api-gateway.sh
```

### 4. Grant API Gateway Permissions
```bash
API_ID=$(aws cloudformation describe-stacks \
  --stack-name kitchen-agent-api-gateway \
  --query 'Stacks[0].Outputs[?OutputKey==`APIId`].OutputValue' \
  --output text)

aws lambda add-permission \
  --function-name reminder-executor \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*"
```

### 5. Update .env with API Endpoint
```bash
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name kitchen-agent-api-gateway \
  --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
  --output text)

echo "API_BASE_URL=$API_ENDPOINT" >> .env
```

## Run the Application
```bash
streamlit run app.py
```

## Cleanup
```bash
./teardown.sh
```

For detailed instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
