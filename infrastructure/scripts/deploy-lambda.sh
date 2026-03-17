#!/bin/bash

# Deploy Reminder Executor Lambda Function
# Requirements: 11.2, 18.4, 18.5

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploying Reminder Executor Lambda${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Load environment variables
if [ -f "../config/.env" ]; then
    source ../config/.env
elif [ -f "../../.env" ]; then
    source ../../.env
else
    echo -e "${YELLOW}Warning: .env file not found, using defaults${NC}"
fi

# Set variables
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-kitchen-agent-reminder-executor}"
REGION="${AWS_REGION:-ap-south-1}"
RUNTIME="python3.11"
HANDLER="reminder_executor.lambda_handler"
MEMORY_SIZE=512
TIMEOUT=30
ROLE_NAME="${LAMBDA_ROLE_NAME:-kitchen-agent-reminder-executor-role}"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "Function Name: $FUNCTION_NAME"
echo "Region: $REGION"
echo "Runtime: $RUNTIME"
echo "Memory: ${MEMORY_SIZE}MB"
echo "Timeout: ${TIMEOUT}s"

# Create deployment package
echo -e "\n${YELLOW}Creating deployment package...${NC}"
cd ../lambda
rm -f reminder-executor.zip

# Create a temporary directory for the package
mkdir -p package
cp reminder_executor.py package/

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -t package/ --quiet
fi

# Create zip file
cd package
zip -r ../reminder-executor.zip . -q
cd ..
rm -rf package

echo -e "${GREEN}✓ Deployment package created${NC}"

# Check if IAM role exists, create if not
echo -e "\n${YELLOW}Checking IAM role...${NC}"
if ! aws iam get-role --role-name "$ROLE_NAME" --region "$REGION" &> /dev/null; then
    echo "Creating IAM role..."
    
    # Create trust policy
    cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create role
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --region "$REGION"
    
    # Attach policy
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "${ROLE_NAME}-policy" \
        --policy-document file://iam-policy.json \
        --region "$REGION"
    
    echo -e "${GREEN}✓ IAM role created${NC}"
    echo -e "${YELLOW}Waiting 10 seconds for IAM role to propagate...${NC}"
    sleep 10
else
    echo -e "${GREEN}✓ IAM role exists${NC}"
fi

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text --region "$REGION")
echo "Role ARN: $ROLE_ARN"

# Check if function exists
echo -e "\n${YELLOW}Checking if Lambda function exists...${NC}"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &> /dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://reminder-executor.zip \
        --region "$REGION"
    
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --handler "$HANDLER" \
        --memory-size "$MEMORY_SIZE" \
        --timeout "$TIMEOUT" \
        --environment "Variables={REMINDERS_TABLE=${DYNAMODB_REMINDERS_TABLE:-kitchen-agent-reminders}}" \
        --region "$REGION"
    
    echo -e "${GREEN}✓ Lambda function updated${NC}"
else
    echo "Creating new function..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$ROLE_ARN" \
        --handler "$HANDLER" \
        --zip-file fileb://reminder-executor.zip \
        --memory-size "$MEMORY_SIZE" \
        --timeout "$TIMEOUT" \
        --environment "Variables={REMINDERS_TABLE=${DYNAMODB_REMINDERS_TABLE:-kitchen-agent-reminders}}" \
        --region "$REGION"
    
    echo -e "${GREEN}✓ Lambda function created${NC}"
fi

# Get function ARN
FUNCTION_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text --region "$REGION")
echo "Function ARN: $FUNCTION_ARN"

# Grant EventBridge permission to invoke Lambda
echo -e "\n${YELLOW}Configuring EventBridge permissions...${NC}"
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "AllowEventBridgeInvoke" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --region "$REGION" 2>/dev/null || echo "Permission already exists"

echo -e "${GREEN}✓ EventBridge permissions configured${NC}"

# Clean up
rm -f reminder-executor.zip
rm -f /tmp/trust-policy.json

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Lambda Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nFunction Name: ${GREEN}$FUNCTION_NAME${NC}"
echo -e "Function ARN: ${GREEN}$FUNCTION_ARN${NC}"
echo -e "\nAdd this ARN to your .env file:"
echo -e "${YELLOW}REMINDER_LAMBDA_ARN=$FUNCTION_ARN${NC}"
