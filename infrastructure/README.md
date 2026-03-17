# Andhra Kitchen Agent - Infrastructure Setup

This directory contains the AWS infrastructure configuration for the Andhra Kitchen Agent application.

## Overview

The infrastructure is defined using AWS CloudFormation and includes:

- **IAM Roles**: Execution roles for Lambda functions with least-privilege permissions
- **DynamoDB Tables**: Sessions, market prices, and reminders storage with TTL
- **S3 Bucket**: Image storage with 24-hour lifecycle policy
- **API Gateway**: REST API with rate limiting and CORS configuration
- **Lambda Functions**: Kitchen Agent Core and Reminder Executor
- **CloudWatch**: Log groups and alarms for monitoring

## Prerequisites

1. **AWS Account**: You need an active AWS account
2. **AWS CLI**: Install and configure AWS CLI
   ```bash
   # Install AWS CLI
   pip install awscli
   
   # Configure credentials
   aws configure
   ```
3. **Permissions**: Your AWS user needs permissions to create:
   - IAM roles and policies
   - DynamoDB tables
   - S3 buckets
   - API Gateway
   - Lambda functions
   - CloudWatch resources

## Region

All resources are deployed to **ap-south-1 (Mumbai)** region, which is closest to Andhra Pradesh for optimal latency.

## Deployment

### Quick Start

```bash
# Validate the app/security config first
python scripts/validate_security_config.py

# Export the API Lambda ARN and deploy the secure unified API stack
export LAMBDA_FUNCTION_ARN=arn:aws:lambda:ap-south-1:123456789012:function:kitchen-agent-api-dev
export ALLOWED_ORIGIN=http://localhost:8501
bash infrastructure/scripts/deploy-api-gateway.sh
```

WARNING: `infrastructure/scripts/deploy.sh` and the legacy split API templates are deprecated.
Secure alternative: deploy `infrastructure/cloudformation/api-gateway-fixed.yaml`
through `infrastructure/scripts/deploy-api-gateway.sh`.

### Manual Deployment

```bash
# Validate template
aws cloudformation validate-template \
  --template-body file://infrastructure/cloudformation/api-gateway-fixed.yaml \
  --region ap-south-1

# Deploy secure API + Cognito stack
aws cloudformation create-stack \
  --stack-name kitchen-agent-api-dev \
  --template-body file://infrastructure/cloudformation/api-gateway-fixed.yaml \
  --parameters \
      ParameterKey=Environment,ParameterValue=dev \
      ParameterKey=LambdaFunctionArn,ParameterValue=arn:aws:lambda:ap-south-1:123456789012:function:kitchen-agent-api-dev \
      ParameterKey=AllowedOrigin,ParameterValue=http://localhost:8501 \
      ParameterKey=AlarmNotificationTopicArn,ParameterValue= \
      ParameterKey=ApplicationLogGroupName,ParameterValue=/aws/lambda/kitchen-agent-api-dev \
  --capabilities CAPABILITY_IAM \
  --region ap-south-1

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name kitchen-agent-api-dev \
  --region ap-south-1

# Get outputs
aws cloudformation describe-stacks \
  --stack-name kitchen-agent-api-dev \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs'
```

## Stack Outputs

After deployment, the stack provides these outputs:

- **ApiEndpoint**: API Gateway endpoint URL
- **ImageBucketName**: S3 bucket name for images
- **SessionsTableName**: DynamoDB sessions table name
- **MarketPricesTableName**: DynamoDB market prices table name
- **RemindersTableName**: DynamoDB reminders table name
- **KitchenAgentCoreRoleArn**: IAM role ARN for main Lambda
- **ReminderExecutorRoleArn**: IAM role ARN for reminder Lambda

## Resource Details

### IAM Roles

**KitchenAgentCoreRole**:
- Bedrock model invocation (Claude 3 Haiku and Sonnet)
- S3 read/write/delete for image bucket
- DynamoDB read/write for all tables
- EventBridge rule creation for reminders
- CloudWatch Logs write access

**ReminderExecutorRole**:
- DynamoDB update for reminders table
- EventBridge rule deletion
- CloudWatch Logs write access

### DynamoDB Tables

**kitchen-agent-sessions**:
- Partition Key: `session_id` (String)
- Sort Key: `data_type` (String)
- TTL: 7 days (attribute: `expiry_timestamp`)
- Billing: On-demand

**kitchen-agent-market-prices**:
- Partition Key: `ingredient_name` (String)
- Sort Key: `market_name` (String)
- GSI: `last_updated_index` for querying by update time
- Billing: On-demand

**kitchen-agent-reminders**:
- Partition Key: `session_id` (String)
- Sort Key: `reminder_id` (String)
- GSI: `status_index` for querying by status
- TTL: 7 days (attribute: `expiry_timestamp`)
- Billing: On-demand

### S3 Bucket

**kitchen-agent-images-{account-id}-{env}**:
- Encryption: AES256
- Public access: Blocked
- Lifecycle: Delete objects after 24 hours
- CORS: Enabled for web uploads

### API Gateway

**kitchen-agent-api**:
- Type: REST API
- Endpoint: Regional
- Rate limiting: 100 requests/minute, burst 20
- Throttling: Enabled
- Logging: Full request/response logging
- CORS: Enabled

### Lambda Functions

**KitchenAgentCore**:
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 30 seconds
- Handler: index.lambda_handler

**ReminderExecutor**:
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 30 seconds
- Handler: index.lambda_handler

### CloudWatch

**Log Groups** (7-day retention):
- `/aws/lambda/KitchenAgentCore-{env}`
- `/aws/lambda/ReminderExecutor-{env}`
- `/aws/apigateway/kitchen-agent-api-{env}`

**Alarms**:
- High error rate (>10 5XX errors in 5 minutes)
- High latency (>5000ms average over 3 minutes)

## AWS Free Tier Compliance

The infrastructure is designed to stay within AWS Free Tier limits:

### Lambda
- ✓ 1M requests/month (expected: ~10K)
- ✓ 400K GB-seconds compute (expected: ~50K)

### DynamoDB
- ✓ 25 GB storage
- ✓ 25 read/write capacity units
- ✓ On-demand pricing for burst traffic

### S3
- ✓ 5 GB storage (24-hour retention keeps usage minimal)
- ✓ 20K GET requests/month
- ✓ 2K PUT requests/month

### API Gateway
- ✓ 1M API calls/month (expected: ~10K)

### CloudWatch
- ✓ 5 GB log ingestion/month
- ✓ 10 custom metrics
- ✓ 10 alarms

## Cost Estimation

For typical usage (10 concurrent users):
- **Free Tier**: $0/month
- **Beyond Free Tier**: ~$5-10/month
  - Bedrock API calls: ~$3-5
  - DynamoDB on-demand: ~$1-2
  - S3 storage: <$1
  - Other services: <$1

## Monitoring

### CloudWatch Dashboards

Create a custom dashboard to monitor:
- API Gateway request count and latency
- Lambda invocations and errors
- DynamoDB read/write capacity
- S3 bucket size and requests

### Alarms

The secure API stack includes:
1. **API 5XX alarm**: Triggers when API 5XX responses exceed the threshold
2. **API latency alarm**: Triggers when average latency exceeds 5 seconds
3. **Optional rate limiter failure alarm**: Enabled when `ApplicationLogGroupName` is provided
4. **Optional image cleanup failure alarm**: Enabled when `ApplicationLogGroupName` is provided

Configure SNS topics to receive alarm notifications.

## Updating Infrastructure

```bash
# Update existing stack
bash infrastructure/scripts/deploy-api-gateway.sh

# Or manually
aws cloudformation update-stack \
  --stack-name kitchen-agent-api-dev \
  --template-body file://infrastructure/cloudformation/api-gateway-fixed.yaml \
  --parameters \
      ParameterKey=Environment,ParameterValue=dev \
      ParameterKey=LambdaFunctionArn,ParameterValue=arn:aws:lambda:ap-south-1:123456789012:function:kitchen-agent-api-dev \
      ParameterKey=AllowedOrigin,ParameterValue=http://localhost:8501 \
      ParameterKey=AlarmNotificationTopicArn,ParameterValue= \
      ParameterKey=ApplicationLogGroupName,ParameterValue=/aws/lambda/kitchen-agent-api-dev \
  --capabilities CAPABILITY_IAM \
  --region ap-south-1
```

## Teardown

To delete all infrastructure resources:

```bash
# Delete dev environment
./infrastructure/scripts/teardown.sh dev

# Delete prod environment
./infrastructure/scripts/teardown.sh prod
```

**Warning**: This will permanently delete all data including:
- All DynamoDB table data
- All S3 images
- All CloudWatch logs
- All Lambda functions

## Troubleshooting

### Stack Creation Failed

1. Check CloudFormation events:
   ```bash
   aws cloudformation describe-stack-events \
     --stack-name andhra-kitchen-agent-dev \
     --region ap-south-1
   ```

2. Common issues:
   - Insufficient IAM permissions
   - Resource name conflicts
   - Service quotas exceeded
   - Invalid parameter values

### Lambda Function Errors

1. Check CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/KitchenAgentCore-dev \
     --follow \
     --region ap-south-1
   ```

2. Common issues:
   - Missing environment variables
   - IAM permission errors
   - Timeout issues
   - Memory limits

### API Gateway 403 Errors

1. Check API Gateway execution logs
2. Verify CORS configuration
3. Check rate limiting settings
4. Verify Lambda permissions

### DynamoDB Throttling

1. Check CloudWatch metrics for throttled requests
2. Consider switching to provisioned capacity
3. Review access patterns and optimize queries

## Security Best Practices

1. **IAM Roles**: Use least-privilege permissions
2. **S3 Bucket**: Block all public access
3. **API Gateway**: Enable request validation
4. **Lambda**: Use environment variables for secrets
5. **CloudWatch**: Enable detailed logging
6. **VPC**: Consider VPC deployment for production

## Next Steps

After infrastructure deployment:

1. **Deploy Lambda Code**: Package and deploy application code
2. **Populate Market Prices**: Load Vijayawada market price data
3. **Configure Bedrock**: Ensure Bedrock models are enabled in your region
4. **Test API**: Use Postman or curl to test endpoints
5. **Deploy Frontend**: Deploy Streamlit application
6. **Set Up Monitoring**: Configure CloudWatch dashboards and alarms
7. **Enable Backups**: Configure DynamoDB point-in-time recovery for production

## Support

For issues or questions:
1. Check CloudFormation events and logs
2. Review AWS service quotas
3. Consult AWS documentation
4. Contact AWS support if needed

## License

This infrastructure configuration is part of the Andhra Kitchen Agent project.
