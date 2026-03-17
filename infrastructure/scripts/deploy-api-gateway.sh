#!/bin/bash

# Deploy the secure unified API Gateway + Cognito stack.
# WARNING: The legacy api-gateway.yaml/api-gateway-auth.yaml split stack is
# deprecated due circular dependencies and inconsistent CORS/auth behavior.

set -e

# Configuration
STACK_NAME="${STACK_NAME:-kitchen-agent-api-${ENVIRONMENT:-dev}}"
TEMPLATE_FILE="infrastructure/cloudformation/api-gateway-fixed.yaml"
ENVIRONMENT="${ENVIRONMENT:-dev}"
ALLOWED_ORIGIN="${ALLOWED_ORIGIN:-*}"
LAMBDA_ARN="${LAMBDA_FUNCTION_ARN:-}"
ALARM_TOPIC_ARN="${ALARM_NOTIFICATION_TOPIC_ARN:-}"
APPLICATION_LOG_GROUP_NAME="${APPLICATION_LOG_GROUP_NAME:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}API Gateway Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file not found: $TEMPLATE_FILE${NC}"
    exit 1
fi

if [ -z "$LAMBDA_ARN" ]; then
    echo -e "${RED}Error: LAMBDA_FUNCTION_ARN is not set${NC}"
    echo "Export the ARN of the API handler Lambda before running this script."
    exit 1
fi

if [ "$ENVIRONMENT" = "prod" ] && [ "$ALLOWED_ORIGIN" = "*" ]; then
    echo -e "${RED}Error: ALLOWED_ORIGIN='*' is not allowed in production${NC}"
    exit 1
fi

echo -e "${GREEN}Lambda ARN: $LAMBDA_ARN${NC}"
echo -e "${GREEN}Allowed Origin: $ALLOWED_ORIGIN${NC}"
if [ -n "$APPLICATION_LOG_GROUP_NAME" ]; then
    echo -e "${GREEN}Application Log Group: $APPLICATION_LOG_GROUP_NAME${NC}"
fi
echo ""

# Validate CloudFormation template
echo -e "${YELLOW}Validating CloudFormation template...${NC}"
aws cloudformation validate-template --template-body file://$TEMPLATE_FILE > /dev/null
echo -e "${GREEN}✓ Template is valid${NC}"
echo ""

# Check if stack exists
STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME 2>&1 || true)

if echo "$STACK_EXISTS" | grep -q "does not exist"; then
    # Create new stack
    echo -e "${YELLOW}Creating new API Gateway stack...${NC}"
    aws cloudformation create-stack \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --parameters \
            ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
            ParameterKey=LambdaFunctionArn,ParameterValue=$LAMBDA_ARN \
            ParameterKey=AllowedOrigin,ParameterValue=$ALLOWED_ORIGIN \
            ParameterKey=AlarmNotificationTopicArn,ParameterValue=$ALARM_TOPIC_ARN \
            ParameterKey=ApplicationLogGroupName,ParameterValue=$APPLICATION_LOG_GROUP_NAME \
        --capabilities CAPABILITY_IAM \
        --tags \
            Key=Project,Value=AndhraKitchenAgent \
            Key=Environment,Value=$ENVIRONMENT
    
    echo -e "${YELLOW}Waiting for stack creation to complete...${NC}"
    aws cloudformation wait stack-create-complete --stack-name $STACK_NAME
    echo -e "${GREEN}✓ Stack created successfully${NC}"
else
    # Update existing stack
    echo -e "${YELLOW}Updating existing API Gateway stack...${NC}"
    UPDATE_OUTPUT=$(aws cloudformation update-stack \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --parameters \
            ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
            ParameterKey=LambdaFunctionArn,ParameterValue=$LAMBDA_ARN \
            ParameterKey=AllowedOrigin,ParameterValue=$ALLOWED_ORIGIN \
            ParameterKey=AlarmNotificationTopicArn,ParameterValue=$ALARM_TOPIC_ARN \
            ParameterKey=ApplicationLogGroupName,ParameterValue=$APPLICATION_LOG_GROUP_NAME \
        --capabilities CAPABILITY_IAM 2>&1 || true)
    
    if echo "$UPDATE_OUTPUT" | grep -q "No updates are to be performed"; then
        echo -e "${YELLOW}No updates needed - stack is already up to date${NC}"
    else
        echo -e "${YELLOW}Waiting for stack update to complete...${NC}"
        aws cloudformation wait stack-update-complete --stack-name $STACK_NAME
        echo -e "${GREEN}✓ Stack updated successfully${NC}"
    fi
fi

echo ""

# Get API Gateway endpoint
echo -e "${YELLOW}Retrieving API Gateway endpoint...${NC}"
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

API_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`APIId`].OutputValue' \
    --output text)

USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
    --output text)

USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
    --output text)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}API Gateway Endpoint:${NC} $API_ENDPOINT"
echo -e "${GREEN}API Gateway ID:${NC} $API_ID"
echo -e "${GREEN}User Pool ID:${NC} $USER_POOL_ID"
echo -e "${GREEN}User Pool Client ID:${NC} $USER_POOL_CLIENT_ID"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update your .env file with the stack outputs:"
echo "   API_BASE_URL=$API_ENDPOINT"
echo "   COGNITO_USER_POOL_ID=$USER_POOL_ID"
echo "   COGNITO_APP_CLIENT_ID=$USER_POOL_CLIENT_ID"
echo ""
echo "2. Validate security-sensitive config before app deployment:"
echo "   python scripts/validate_security_config.py"
echo ""
echo "3. Run orphan-image cleanup in dry-run mode after first uploads:"
echo "   python scripts/cleanup_orphan_images.py --json"
echo ""
echo "4. Test CORS preflight and authenticated API access"
echo ""
