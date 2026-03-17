#!/bin/bash

# Andhra Kitchen Agent - Populate Market Prices Script
# This script loads sample market price data into DynamoDB

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
DATA_FILE="infrastructure/data/market-prices-sample.json"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Andhra Kitchen Agent - Populate Market Prices${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if data file exists
if [ ! -f "$DATA_FILE" ]; then
    echo -e "${RED}Error: Data file not found: ${DATA_FILE}${NC}"
    exit 1
fi

# Get table name from CloudFormation stack
echo -e "${YELLOW}Retrieving table name from stack...${NC}"
TABLE_NAME=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`MarketPricesTableName`].OutputValue' \
    --output text)

if [ -z "$TABLE_NAME" ]; then
    echo -e "${RED}Error: Could not retrieve table name from stack${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Table name: ${TABLE_NAME}${NC}"

# Count items in data file
ITEM_COUNT=$(jq '. | length' ${DATA_FILE})
echo -e "${YELLOW}Loading ${ITEM_COUNT} items...${NC}"

# Load data into DynamoDB
COUNTER=0
while IFS= read -r item; do
    aws dynamodb put-item \
        --table-name ${TABLE_NAME} \
        --item "$(echo $item | jq -c '{
            ingredient_name: {S: .ingredient_name},
            market_name: {S: .market_name},
            price_per_unit: {N: (.price_per_unit | tostring)},
            unit: {S: .unit},
            last_updated: {S: .last_updated},
            source: {S: .source},
            confidence: {N: (.confidence | tostring)}
        }')" \
        --region ${REGION} > /dev/null
    
    COUNTER=$((COUNTER + 1))
    echo -ne "${YELLOW}Progress: ${COUNTER}/${ITEM_COUNT}\r${NC}"
done < <(jq -c '.[]' ${DATA_FILE})

echo ""
echo -e "${GREEN}✓ Successfully loaded ${ITEM_COUNT} items into ${TABLE_NAME}${NC}"

# Verify data
echo -e "${YELLOW}Verifying data...${NC}"
ACTUAL_COUNT=$(aws dynamodb scan \
    --table-name ${TABLE_NAME} \
    --select COUNT \
    --region ${REGION} \
    --query 'Count' \
    --output text)

echo -e "${GREEN}✓ Table contains ${ACTUAL_COUNT} items${NC}"

# Show sample data
echo ""
echo -e "${GREEN}Sample data from table:${NC}"
aws dynamodb scan \
    --table-name ${TABLE_NAME} \
    --limit 3 \
    --region ${REGION} \
    --output table

echo ""
echo -e "${GREEN}Market prices loaded successfully!${NC}"
