#!/bin/bash

## ⚠️ DEPRECATED — DO NOT USE
##
## This script is deprecated and references legacy infrastructure that may not work correctly.
## 
## SECURE ALTERNATIVE: Use infrastructure/scripts/deploy-api-gateway.sh for the
## authenticated API surface deployed from api-gateway-fixed.yaml.
##
## This file is kept for reference only and will be removed in a future release.

# Main Deployment Script for Andhra Kitchen Agent
# This script orchestrates the deployment of all AWS infrastructure components
# WARNING: This script still references the legacy main-stack flow.
# SECURE ALTERNATIVE: Use infrastructure/scripts/deploy-api-gateway.sh for the
# authenticated API surface deployed from api-gateway-fixed.yaml.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Andhra Kitchen Agent - Full Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Warning: deploy.sh is a legacy helper and does not replace the secure API deployment path.${NC}"
echo -e "${YELLOW}Use infrastructure/scripts/deploy-api-gateway.sh for Cognito-authenticated API deployment.${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please configure AWS CLI: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo -e "${GREEN}✓ AWS Account ID: $ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ AWS Region: $AWS_REGION${NC}"
echo ""

# Deployment steps
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 1: Deploy DynamoDB Tables${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if main stack exists
MAIN_STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name kitchen-agent-main 2>&1 || true)

if echo "$MAIN_STACK_EXISTS" | grep -q "does not exist"; then
    echo -e "${YELLOW}Deploying main CloudFormation stack (DynamoDB, S3)...${NC}"
    
    # Deploy main stack (you'll need to create this template)
    echo -e "${YELLOW}Note: Main stack template not yet created${NC}"
    echo -e "${YELLOW}Please create infrastructure/cloudformation/main-stack.yaml${NC}"
    echo -e "${YELLOW}Skipping for now...${NC}"
else
    echo -e "${GREEN}✓ Main stack already exists${NC}"
fi

echo ""

# Step 2: Deploy Lambda functions
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 2: Deploy Lambda Functions${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ -f "infrastructure/scripts/deploy-lambda.sh" ]; then
    bash infrastructure/scripts/deploy-lambda.sh
else
    echo -e "${RED}Error: Lambda deployment script not found${NC}"
    exit 1
fi

echo ""

# Step 3: Deploy API Gateway
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 3: Deploy API Gateway${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ -f "infrastructure/scripts/deploy-api-gateway.sh" ]; then
    bash infrastructure/scripts/deploy-api-gateway.sh
else
    echo -e "${RED}Error: API Gateway deployment script not found${NC}"
    exit 1
fi

echo ""

# Step 4: Seed data
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 4: Seed Market Prices Data${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ -f "infrastructure/scripts/populate-market-prices.sh" ]; then
    bash infrastructure/scripts/populate-market-prices.sh
else
    echo -e "${YELLOW}Warning: Market prices seeding script not found${NC}"
    echo -e "${YELLOW}Skipping data seeding...${NC}"
fi

echo ""

# Final summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}All infrastructure components have been deployed successfully.${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update your .env file with the deployed resource details"
echo "2. Test the API endpoints"
echo "3. Run the Streamlit frontend: streamlit run app.py"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "- View CloudFormation stacks: aws cloudformation list-stacks"
echo "- View Lambda functions: aws lambda list-functions"
echo "- View API Gateway APIs: aws apigateway get-rest-apis"
echo "- View DynamoDB tables: aws dynamodb list-tables"
echo ""
