# Andhra Kitchen Agent - Deployment Guide

**IMPORTANT**: This guide covers the legacy deployment flow. For secure production deployment with all security fixes, use:
- **Secure Template**: `infrastructure/cloudformation/api-gateway-fixed.yaml`
- **Deployment Script**: `infrastructure/scripts/deploy-api-gateway.sh`
- **Security Guide**: `docs/security/DEPLOYMENT.md`

The legacy templates (`main-stack.yaml`, `api-gateway.yaml`, `api-gateway-auth.yaml`) are retained for reference but are deprecated.

---

This guide walks you through deploying the AWS infrastructure for the Andhra Kitchen Agent.

## Prerequisites

### 1. AWS Account Setup

1. Create an AWS account at https://aws.amazon.com
2. Note your AWS Account ID (12-digit number)
3. Ensure you have access to the **ap-south-1 (Mumbai)** region

### 2. Install AWS CLI

**macOS/Linux:**
```bash
pip install awscli
```

**Windows:**
Download from https://aws.amazon.com/cli/

**Verify installation:**
```bash
aws --version
```

### 3. Configure AWS Credentials

```bash
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `ap-south-1`
- Default output format: `json`

### 4. Enable Bedrock Models

1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access" in the left sidebar
3. Click "Manage model access"
4. Enable:
   - Claude 3 Haiku
   - Claude 3 Sonnet
5. Wait for access to be granted (usually instant)

### 5. Install Required Tools

```bash
# jq (for JSON processing)
# macOS
brew install jq

# Linux
sudo apt-get install jq

# Windows
# Download from https://stedolan.github.io/jq/
```

## Deployment Steps

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd andhra-kitchen-agent
```

### Step 2: Make Scripts Executable

```bash
chmod +x infrastructure/scripts/*.sh
```

### Step 3: Validate CloudFormation Template

```bash
aws cloudformation validate-template \
  --template-body file://infrastructure/cloudformation/main-stack.yaml \
  --region ap-south-1
```

Expected output: Template details without errors

### Step 4: Deploy Infrastructure

**For Development Environment:**
```bash
./infrastructure/scripts/deploy.sh dev
```

**For Production Environment:**
```bash
./infrastructure/scripts/deploy.sh prod
```

This will:
- Create IAM roles with appropriate permissions
- Set up DynamoDB tables with TTL
- Create S3 bucket with lifecycle policies
- Configure API Gateway with rate limiting
- Deploy Lambda functions (placeholder code)
- Set up CloudWatch logging and alarms

**Expected Duration:** 5-10 minutes

### Step 5: Validate Deployment

```bash
./infrastructure/scripts/validate.sh dev
```

This checks:
- CloudFormation stack status
- S3 bucket configuration
- DynamoDB table status and TTL
- Lambda function configuration
- API Gateway setup
- CloudWatch log groups
- IAM roles

### Step 6: Populate Market Prices

```bash
./infrastructure/scripts/populate-market-prices.sh dev
```

This loads sample Vijayawada market price data into DynamoDB.

### Step 7: Get Stack Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name andhra-kitchen-agent-dev \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table
```

Save these values:
- **ApiEndpoint**: Your API Gateway URL
- **ImageBucketName**: S3 bucket for images
- **SessionsTableName**: DynamoDB sessions table
- **MarketPricesTableName**: DynamoDB market prices table
- **RemindersTableName**: DynamoDB reminders table

### Step 8: Update Environment Configuration

```bash
cp infrastructure/config/env.template .env
```

Edit `.env` and fill in:
- AWS_ACCOUNT_ID
- API_ENDPOINT (from stack outputs)
- Table names (from stack outputs)
- Bucket name (from stack outputs)

## Post-Deployment Tasks

### 1. Test API Gateway

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name andhra-kitchen-agent-dev \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

# Test endpoint
curl -X POST ${API_ENDPOINT}/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "message": "Hello",
    "language": "en"
  }'
```

Expected: 200 OK with placeholder response

### 2. Deploy Lambda Code

The CloudFormation stack creates Lambda functions with placeholder code. You'll need to:

1. Package your application code
2. Upload to Lambda functions
3. Update environment variables

See the main application README for Lambda deployment instructions.

### 3. Set Up Monitoring

1. Go to CloudWatch Console
2. Create a dashboard with:
   - API Gateway metrics (requests, latency, errors)
   - Lambda metrics (invocations, duration, errors)
   - DynamoDB metrics (read/write capacity)
3. Configure SNS topics for alarm notifications

### 4. Configure CORS (if needed)

If you need to allow additional origins:

```bash
# Update API Gateway CORS settings
aws apigateway update-rest-api \
  --rest-api-id <API_ID> \
  --patch-operations \
    op=replace,path=/cors/allowOrigins,value='["https://your-domain.com"]' \
  --region ap-south-1
```

## Verification Checklist

- [ ] CloudFormation stack status is CREATE_COMPLETE or UPDATE_COMPLETE
- [ ] All DynamoDB tables are ACTIVE with TTL enabled
- [ ] S3 bucket exists with lifecycle policy and encryption
- [ ] Lambda functions are Active with correct memory/timeout
- [ ] API Gateway endpoint is accessible
- [ ] CloudWatch log groups exist with 7-day retention
- [ ] IAM roles have correct permissions
- [ ] Market prices data is loaded
- [ ] Bedrock models are accessible

## Troubleshooting

### Stack Creation Failed

**Check CloudFormation events:**
```bash
aws cloudformation describe-stack-events \
  --stack-name andhra-kitchen-agent-dev \
  --region ap-south-1 \
  --max-items 20
```

**Common issues:**
- Insufficient IAM permissions → Add required permissions to your user
- Resource name conflicts → Delete conflicting resources or use different environment name
- Service quotas exceeded → Request quota increase in AWS Console
- Bedrock not enabled → Enable Bedrock models in Console

### Lambda Function Errors

**View logs:**
```bash
aws logs tail /aws/lambda/KitchenAgentCore-dev \
  --follow \
  --region ap-south-1
```

**Common issues:**
- Missing environment variables → Check Lambda configuration
- IAM permission errors → Verify role policies
- Timeout → Increase timeout or optimize code
- Memory limit → Increase memory allocation

### API Gateway 403 Errors

**Check:**
- Lambda permissions for API Gateway invocation
- API Gateway resource policies
- CORS configuration
- Rate limiting settings

### DynamoDB Throttling

**Check metrics:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=kitchen-agent-sessions-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region ap-south-1
```

**Solutions:**
- Optimize query patterns
- Add caching layer
- Consider provisioned capacity for predictable workloads

## Updating Infrastructure

To update the infrastructure after making changes to the CloudFormation template:

```bash
./infrastructure/scripts/deploy.sh dev
```

CloudFormation will automatically detect changes and update only modified resources.

## Rollback

If deployment fails, CloudFormation automatically rolls back. To manually rollback:

```bash
aws cloudformation cancel-update-stack \
  --stack-name andhra-kitchen-agent-dev \
  --region ap-south-1
```

## Teardown

To delete all infrastructure resources:

```bash
./infrastructure/scripts/teardown.sh dev
```

**Warning:** This permanently deletes:
- All DynamoDB data
- All S3 images
- All CloudWatch logs
- All Lambda functions
- API Gateway configuration

## Cost Management

### Monitor Costs

1. Go to AWS Cost Explorer
2. Filter by:
   - Service: Lambda, DynamoDB, S3, API Gateway, Bedrock
   - Tag: Project=AndraKitchenAgent

### Stay Within Free Tier

The infrastructure is designed for Free Tier compliance:

**Monthly limits:**
- Lambda: 1M requests, 400K GB-seconds
- DynamoDB: 25 GB storage, 25 RCU/WCU
- S3: 5 GB storage, 20K GET, 2K PUT
- API Gateway: 1M calls
- CloudWatch: 5 GB logs, 10 metrics, 10 alarms

**To stay within limits:**
- Use 24-hour S3 lifecycle policy (already configured)
- Use 7-day TTL on DynamoDB (already configured)
- Implement request caching
- Monitor usage regularly

### Set Up Billing Alerts

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name billing-alert \
  --alarm-description "Alert when estimated charges exceed $10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --region us-east-1
```

## Security Best Practices

1. **IAM Roles**: Use least-privilege permissions (already configured)
2. **S3 Bucket**: Block public access (already configured)
3. **API Gateway**: Enable request validation (already configured)
4. **Lambda**: Use environment variables for secrets
5. **CloudWatch**: Enable detailed logging (already configured)
6. **VPC**: Consider VPC deployment for production

## Production Deployment

For production deployment:

1. Use `prod` environment:
   ```bash
   ./infrastructure/scripts/deploy.sh prod
   ```

2. Enable additional features:
   - DynamoDB point-in-time recovery
   - S3 versioning
   - CloudTrail logging
   - AWS WAF for API Gateway
   - Multi-AZ deployment

3. Set up CI/CD pipeline:
   - Use AWS CodePipeline
   - Automate testing
   - Implement blue-green deployment

4. Configure monitoring:
   - Set up CloudWatch dashboards
   - Configure SNS notifications
   - Enable X-Ray tracing

## Support

For issues:
1. Check CloudFormation events and logs
2. Review AWS service quotas
3. Consult AWS documentation
4. Contact AWS support if needed

## Next Steps

After successful deployment:

1. **Deploy Application Code**: Package and deploy Lambda functions
2. **Configure Streamlit**: Set up frontend application
3. **Test End-to-End**: Verify complete workflow
4. **Load Production Data**: Add real market prices
5. **Set Up Monitoring**: Configure dashboards and alerts
6. **Document APIs**: Create API documentation
7. **User Testing**: Conduct user acceptance testing

## Resources

- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [AWS Free Tier](https://aws.amazon.com/free/)
