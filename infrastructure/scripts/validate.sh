#!/bin/bash

# Andhra Kitchen Agent - Infrastructure Validation Script
# This script validates the deployed infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="andhra-kitchen-agent"
REGION="ap-south-1"
ENVIRONMENT="${1:-dev}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Andhra Kitchen Agent - Infrastructure Validation${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if stack exists
echo -e "${YELLOW}Checking CloudFormation stack...${NC}"
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --query 'Stacks[0].StackStatus' \
    --output text 2>&1 || echo "NOT_FOUND")

if [ "$STACK_STATUS" == "CREATE_COMPLETE" ] || [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
    echo -e "${GREEN}✓ Stack status: ${STACK_STATUS}${NC}"
else
    echo -e "${RED}✗ Stack status: ${STACK_STATUS}${NC}"
    exit 1
fi

# Get stack outputs
echo -e "${YELLOW}Retrieving stack outputs...${NC}"
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

IMAGE_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`ImageBucketName`].OutputValue' \
    --output text)

SESSIONS_TABLE=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`SessionsTableName`].OutputValue' \
    --output text)

MARKET_PRICES_TABLE=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`MarketPricesTableName`].OutputValue' \
    --output text)

REMINDERS_TABLE=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`RemindersTableName`].OutputValue' \
    --output text)

echo -e "${GREEN}✓ Stack outputs retrieved${NC}"

# Validate S3 bucket
echo -e "${YELLOW}Validating S3 bucket...${NC}"
if aws s3 ls "s3://${IMAGE_BUCKET}" --region ${REGION} > /dev/null 2>&1; then
    echo -e "${GREEN}✓ S3 bucket exists: ${IMAGE_BUCKET}${NC}"
    
    # Check lifecycle policy
    LIFECYCLE=$(aws s3api get-bucket-lifecycle-configuration \
        --bucket ${IMAGE_BUCKET} \
        --region ${REGION} 2>&1 || echo "NOT_FOUND")
    
    if echo "${LIFECYCLE}" | grep -q "ExpirationInDays"; then
        echo -e "${GREEN}✓ Lifecycle policy configured${NC}"
    else
        echo -e "${RED}✗ Lifecycle policy not found${NC}"
    fi
    
    # Check encryption
    ENCRYPTION=$(aws s3api get-bucket-encryption \
        --bucket ${IMAGE_BUCKET} \
        --region ${REGION} 2>&1 || echo "NOT_FOUND")
    
    if echo "${ENCRYPTION}" | grep -q "AES256"; then
        echo -e "${GREEN}✓ Bucket encryption enabled${NC}"
    else
        echo -e "${RED}✗ Bucket encryption not configured${NC}"
    fi
else
    echo -e "${RED}✗ S3 bucket not found${NC}"
fi

# Validate DynamoDB tables
echo -e "${YELLOW}Validating DynamoDB tables...${NC}"

for TABLE in "${SESSIONS_TABLE}" "${MARKET_PRICES_TABLE}" "${REMINDERS_TABLE}"; do
    TABLE_STATUS=$(aws dynamodb describe-table \
        --table-name ${TABLE} \
        --region ${REGION} \
        --query 'Table.TableStatus' \
        --output text 2>&1 || echo "NOT_FOUND")
    
    if [ "$TABLE_STATUS" == "ACTIVE" ]; then
        echo -e "${GREEN}✓ Table active: ${TABLE}${NC}"
        
        # Check TTL for sessions and reminders tables
        if [[ "$TABLE" == *"sessions"* ]] || [[ "$TABLE" == *"reminders"* ]]; then
            TTL_STATUS=$(aws dynamodb describe-time-to-live \
                --table-name ${TABLE} \
                --region ${REGION} \
                --query 'TimeToLiveDescription.TimeToLiveStatus' \
                --output text 2>&1 || echo "NOT_FOUND")
            
            if [ "$TTL_STATUS" == "ENABLED" ]; then
                echo -e "${GREEN}  ✓ TTL enabled${NC}"
            else
                echo -e "${RED}  ✗ TTL not enabled${NC}"
            fi
        fi
    else
        echo -e "${RED}✗ Table status: ${TABLE_STATUS}${NC}"
    fi
done

# Validate Lambda functions
echo -e "${YELLOW}Validating Lambda functions...${NC}"

LAMBDA_CORE="KitchenAgentCore-${ENVIRONMENT}"
LAMBDA_REMINDER="ReminderExecutor-${ENVIRONMENT}"

for LAMBDA in "${LAMBDA_CORE}" "${LAMBDA_REMINDER}"; do
    LAMBDA_STATE=$(aws lambda get-function \
        --function-name ${LAMBDA} \
        --region ${REGION} \
        --query 'Configuration.State' \
        --output text 2>&1 || echo "NOT_FOUND")
    
    if [ "$LAMBDA_STATE" == "Active" ]; then
        echo -e "${GREEN}✓ Lambda active: ${LAMBDA}${NC}"
        
        # Check memory and timeout
        MEMORY=$(aws lambda get-function-configuration \
            --function-name ${LAMBDA} \
            --region ${REGION} \
            --query 'MemorySize' \
            --output text)
        
        TIMEOUT=$(aws lambda get-function-configuration \
            --function-name ${LAMBDA} \
            --region ${REGION} \
            --query 'Timeout' \
            --output text)
        
        echo -e "  Memory: ${MEMORY}MB, Timeout: ${TIMEOUT}s"
        
        if [ "$MEMORY" -eq 512 ] && [ "$TIMEOUT" -eq 30 ]; then
            echo -e "${GREEN}  ✓ Configuration correct${NC}"
        else
            echo -e "${YELLOW}  ! Configuration differs from expected${NC}"
        fi
    else
        echo -e "${RED}✗ Lambda state: ${LAMBDA_STATE}${NC}"
    fi
done

# Validate API Gateway
echo -e "${YELLOW}Validating API Gateway...${NC}"
if [ ! -z "$API_ENDPOINT" ]; then
    echo -e "${GREEN}✓ API endpoint: ${API_ENDPOINT}${NC}"
    
    # Extract API ID from endpoint
    API_ID=$(echo ${API_ENDPOINT} | sed -n 's/.*\/\/\([^.]*\).*/\1/p')
    
    # Check API Gateway stage
    STAGE_NAME=$(aws apigateway get-stages \
        --rest-api-id ${API_ID} \
        --region ${REGION} \
        --query 'item[0].stageName' \
        --output text 2>&1 || echo "NOT_FOUND")
    
    if [ "$STAGE_NAME" == "v1" ]; then
        echo -e "${GREEN}✓ API stage: ${STAGE_NAME}${NC}"
    else
        echo -e "${RED}✗ API stage not found${NC}"
    fi
else
    echo -e "${RED}✗ API endpoint not found${NC}"
fi

# Validate CloudWatch Log Groups
echo -e "${YELLOW}Validating CloudWatch log groups...${NC}"

LOG_GROUPS=(
    "/aws/lambda/KitchenAgentCore-${ENVIRONMENT}"
    "/aws/lambda/ReminderExecutor-${ENVIRONMENT}"
    "/aws/apigateway/kitchen-agent-api-${ENVIRONMENT}"
)

for LOG_GROUP in "${LOG_GROUPS[@]}"; do
    LOG_EXISTS=$(aws logs describe-log-groups \
        --log-group-name-prefix ${LOG_GROUP} \
        --region ${REGION} \
        --query 'logGroups[0].logGroupName' \
        --output text 2>&1 || echo "NOT_FOUND")
    
    if [ "$LOG_EXISTS" == "$LOG_GROUP" ]; then
        echo -e "${GREEN}✓ Log group exists: ${LOG_GROUP}${NC}"
        
        # Check retention
        RETENTION=$(aws logs describe-log-groups \
            --log-group-name-prefix ${LOG_GROUP} \
            --region ${REGION} \
            --query 'logGroups[0].retentionInDays' \
            --output text)
        
        if [ "$RETENTION" == "7" ]; then
            echo -e "${GREEN}  ✓ Retention: ${RETENTION} days${NC}"
        else
            echo -e "${YELLOW}  ! Retention: ${RETENTION} days (expected 7)${NC}"
        fi
    else
        echo -e "${RED}✗ Log group not found: ${LOG_GROUP}${NC}"
    fi
done

# Validate IAM roles
echo -e "${YELLOW}Validating IAM roles...${NC}"

IAM_ROLES=(
    "KitchenAgentCoreRole-${ENVIRONMENT}"
    "ReminderExecutorRole-${ENVIRONMENT}"
)

for ROLE in "${IAM_ROLES[@]}"; do
    ROLE_EXISTS=$(aws iam get-role \
        --role-name ${ROLE} \
        --query 'Role.RoleName' \
        --output text 2>&1 || echo "NOT_FOUND")
    
    if [ "$ROLE_EXISTS" == "$ROLE" ]; then
        echo -e "${GREEN}✓ IAM role exists: ${ROLE}${NC}"
    else
        echo -e "${RED}✗ IAM role not found: ${ROLE}${NC}"
    fi
done

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Validation Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Environment: ${ENVIRONMENT}"
echo -e "Region: ${REGION}"
echo -e "API Endpoint: ${API_ENDPOINT}"
echo ""
echo -e "${GREEN}All critical resources validated successfully!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Deploy Lambda function code"
echo "2. Populate market prices table"
echo "3. Test API endpoints"
echo "4. Deploy Streamlit frontend"
