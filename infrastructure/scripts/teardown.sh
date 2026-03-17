#!/bin/bash

# Andhra Kitchen Agent - Infrastructure Teardown Script
# This script deletes the CloudFormation stack and cleans up resources

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

echo -e "${RED}========================================${NC}"
echo -e "${RED}Andhra Kitchen Agent - Infrastructure Teardown${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${YELLOW}WARNING: This will delete all infrastructure resources!${NC}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${GREEN}Teardown cancelled${NC}"
    exit 0
fi

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Empty S3 bucket before deletion
echo -e "${YELLOW}Emptying S3 bucket...${NC}"
BUCKET_NAME="kitchen-agent-images-${AWS_ACCOUNT_ID}-${ENVIRONMENT}"

if aws s3 ls "s3://${BUCKET_NAME}" 2>&1 | grep -q 'NoSuchBucket'; then
    echo -e "${YELLOW}Bucket does not exist, skipping...${NC}"
else
    aws s3 rm "s3://${BUCKET_NAME}" --recursive --region ${REGION}
    echo -e "${GREEN}✓ S3 bucket emptied${NC}"
fi

# Delete CloudFormation stack
echo -e "${YELLOW}Deleting CloudFormation stack...${NC}"
aws cloudformation delete-stack \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION}

echo -e "${YELLOW}Waiting for stack deletion to complete...${NC}"
aws cloudformation wait stack-delete-complete \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION}

echo -e "${GREEN}✓ Stack deleted successfully${NC}"
echo ""
echo -e "${GREEN}All infrastructure resources have been removed${NC}"
