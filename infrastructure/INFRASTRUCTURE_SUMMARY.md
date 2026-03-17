# Infrastructure Summary

**IMPORTANT**: This document describes the legacy infrastructure. For secure production deployment with all security fixes:
- **Secure Template**: `infrastructure/cloudformation/api-gateway-fixed.yaml`
- **Deployment Script**: `infrastructure/scripts/deploy-api-gateway.sh`
- **Security Documentation**: `docs/security/DEPLOYMENT.md`

The legacy templates are retained for reference but are deprecated.

---

## Overview

This document summarizes the AWS infrastructure setup for the Andhra Kitchen Agent.

## Architecture Components

### 1. IAM Roles (2 roles)

**KitchenAgentCoreRole**
- Purpose: Execution role for main Lambda function
- Permissions:
  - Bedrock: InvokeModel, InvokeAgent (Claude 3 Haiku & Sonnet)
  - S3: PutObject, GetObject, DeleteObject (image bucket)
  - DynamoDB: GetItem, PutItem, UpdateItem, Query (all tables)
  - EventBridge: PutRule, PutTargets (reminder scheduling)
  - CloudWatch: Logs write access

**ReminderExecutorRole**
- Purpose: Execution role for reminder Lambda function
- Permissions:
  - DynamoDB: UpdateItem, GetItem (reminders table)
  - EventBridge: RemoveTargets, DeleteRule (cleanup)
  - CloudWatch: Logs write access

### 2. DynamoDB Tables (3 tables)

**kitchen-agent-sessions-{env}**
- Purpose: Store user sessions, preferences, allergies, conversation history
- Keys: session_id (PK), data_type (SK)
- TTL: 7 days (expiry_timestamp)
- Billing: On-demand

**kitchen-agent-market-prices-{env}**
- Purpose: Store Vijayawada market prices for ingredients
- Keys: ingredient_name (PK), market_name (SK)
- GSI: last_updated_index (for querying by update time)
- Billing: On-demand

**kitchen-agent-reminders-{env}**
- Purpose: Store scheduled reminders for users
- Keys: session_id (PK), reminder_id (SK)
- GSI: status_index (for querying by status)
- TTL: 7 days (expiry_timestamp)
- Billing: On-demand

### 3. S3 Bucket (1 bucket)

**kitchen-agent-images-{account-id}-{env}**
- Purpose: Store uploaded fridge/pantry images
- Encryption: AES256
- Public Access: Blocked
- Lifecycle: Delete objects after 24 hours
- CORS: Enabled for web uploads

### 4. API Gateway (1 REST API)

**kitchen-agent-api-{env}**
- Type: REST API
- Endpoint: Regional (ap-south-1)
- Stage: v1
- Rate Limiting: 100 requests/minute, burst 20
- CORS: Enabled
- Logging: Full request/response to CloudWatch
- Resources:
  - POST /chat (with OPTIONS for CORS)

### 5. Lambda Functions (2 functions)

**KitchenAgentCore-{env}**
- Purpose: Main application logic (chat, vision, recipes, shopping)
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 30 seconds
- Trigger: API Gateway

**ReminderExecutor-{env}**
- Purpose: Execute scheduled reminders
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 30 seconds
- Trigger: EventBridge

### 6. CloudWatch (3 log groups + 2 alarms)

**Log Groups** (7-day retention):
- /aws/lambda/KitchenAgentCore-{env}
- /aws/lambda/ReminderExecutor-{env}
- /aws/apigateway/kitchen-agent-api-{env}

**Alarms**:
- HighErrorRate: Alert when 5XX errors > 10 in 5 minutes
- HighLatency: Alert when average latency > 5000ms over 3 minutes

## Resource Naming Convention

All resources follow the pattern: `{service}-{purpose}-{account-id?}-{environment}`

Examples:
- `kitchen-agent-sessions-dev`
- `kitchen-agent-images-123456789012-prod`
- `KitchenAgentCore-dev`

## Region

All resources are deployed to **ap-south-1 (Mumbai)** for optimal latency to Andhra Pradesh.

## AWS Free Tier Compliance

The infrastructure is designed to stay within AWS Free Tier limits:

| Service | Free Tier Limit | Expected Usage | Status |
|---------|----------------|----------------|--------|
| Lambda | 1M requests/month | ~10K requests | ✓ Well within |
| Lambda | 400K GB-seconds | ~50K GB-seconds | ✓ Well within |
| DynamoDB | 25 GB storage | <1 GB | ✓ Well within |
| DynamoDB | 25 RCU/WCU | <10 RCU/WCU | ✓ Well within |
| S3 | 5 GB storage | <100 MB (24hr retention) | ✓ Well within |
| S3 | 20K GET requests | ~1K requests | ✓ Well within |
| S3 | 2K PUT requests | ~100 requests | ✓ Well within |
| API Gateway | 1M calls/month | ~10K calls | ✓ Well within |
| CloudWatch | 5 GB logs | <500 MB | ✓ Well within |
| CloudWatch | 10 metrics | 3 metrics | ✓ Well within |
| CloudWatch | 10 alarms | 2 alarms | ✓ Well within |

**Estimated Monthly Cost (beyond Free Tier):** $5-10
- Bedrock API calls: $3-5
- DynamoDB on-demand: $1-2
- Other services: <$1

## Security Features

1. **IAM**: Least-privilege permissions for all roles
2. **S3**: Public access blocked, HTTPS-only policy
3. **API Gateway**: Request validation, rate limiting, CORS
4. **DynamoDB**: Encryption at rest (default)
5. **Lambda**: Environment variables for configuration
6. **CloudWatch**: Comprehensive logging for audit trail

## Deployment Files

### CloudFormation Template
- `cloudformation/main-stack.yaml` - Complete infrastructure definition

### Scripts
- `scripts/deploy.sh` - Deploy or update infrastructure
- `scripts/validate.sh` - Validate deployed resources
- `scripts/teardown.sh` - Delete all resources
- `scripts/populate-market-prices.sh` - Load sample data

### Configuration
- `config/env.template` - Environment variables template

### Data
- `data/market-prices-sample.json` - Sample Vijayawada market prices (32 items)

### Documentation
- `README.md` - Infrastructure overview
- `DEPLOYMENT_GUIDE.md` - Detailed deployment instructions
- `QUICK_START.md` - 5-step quick start guide
- `INFRASTRUCTURE_SUMMARY.md` - This document

## Stack Outputs

After deployment, the CloudFormation stack provides:

| Output | Description | Example |
|--------|-------------|---------|
| ApiEndpoint | API Gateway URL | https://abc123.execute-api.ap-south-1.amazonaws.com/v1 |
| ImageBucketName | S3 bucket name | kitchen-agent-images-123456789012-dev |
| SessionsTableName | Sessions table | kitchen-agent-sessions-dev |
| MarketPricesTableName | Market prices table | kitchen-agent-market-prices-dev |
| RemindersTableName | Reminders table | kitchen-agent-reminders-dev |
| KitchenAgentCoreRoleArn | Main Lambda role ARN | arn:aws:iam::123456789012:role/... |
| ReminderExecutorRoleArn | Reminder Lambda role ARN | arn:aws:iam::123456789012:role/... |

## Monitoring & Observability

### CloudWatch Metrics

**API Gateway:**
- Request count
- Latency (p50, p90, p99)
- 4XX/5XX errors
- Integration latency

**Lambda:**
- Invocations
- Duration
- Errors
- Throttles
- Concurrent executions

**DynamoDB:**
- Read/write capacity units consumed
- Throttled requests
- User errors
- System errors

### CloudWatch Logs

All logs are retained for 7 days with structured logging:
- Request/response payloads
- Error stack traces
- Performance metrics
- User actions

### Alarms

Two alarms are configured:
1. High error rate (>10 5XX errors in 5 minutes)
2. High latency (>5000ms average over 3 minutes)

Configure SNS topics to receive notifications.

## Maintenance

### Regular Tasks

**Weekly:**
- Review CloudWatch logs for errors
- Check DynamoDB capacity metrics
- Monitor S3 bucket size

**Monthly:**
- Update market prices data
- Review AWS costs
- Check for AWS service updates
- Update Lambda runtime if needed

**Quarterly:**
- Review and update IAM policies
- Audit security configurations
- Update CloudFormation template
- Review and optimize costs

### Updates

To update infrastructure:
```bash
./infrastructure/scripts/deploy.sh dev
```

CloudFormation handles updates safely with automatic rollback on failure.

## Disaster Recovery

### Backup Strategy

**DynamoDB:**
- On-demand backups available
- Point-in-time recovery (optional, not in Free Tier)
- Consider enabling for production

**S3:**
- Versioning disabled (not needed for 24-hour retention)
- Cross-region replication (optional for production)

**Lambda:**
- Code stored in CloudFormation template
- Easy to redeploy

### Recovery Procedures

**Complete Stack Loss:**
1. Redeploy CloudFormation stack
2. Restore DynamoDB data from backup
3. Redeploy Lambda code
4. Repopulate market prices

**Data Loss:**
1. Restore DynamoDB tables from backup
2. Reload market prices from source

**Lambda Failure:**
1. Check CloudWatch logs
2. Redeploy Lambda code
3. Verify environment variables

## Scaling Considerations

### Current Capacity

- 10 concurrent users
- 100 requests/minute
- 512 MB Lambda memory
- On-demand DynamoDB billing

### Scaling Options

**For 100+ users:**
- Increase API Gateway rate limits
- Add Lambda reserved concurrency
- Consider DynamoDB provisioned capacity
- Add CloudFront CDN
- Implement caching layer

**For 1000+ users:**
- Multi-region deployment
- DynamoDB Global Tables
- Lambda@Edge for edge computing
- ElastiCache for caching
- Application Load Balancer

## Cost Optimization

### Current Optimizations

1. **S3**: 24-hour lifecycle policy minimizes storage
2. **DynamoDB**: 7-day TTL auto-deletes old data
3. **Lambda**: Right-sized memory (512 MB)
4. **CloudWatch**: 7-day log retention
5. **API Gateway**: Rate limiting prevents abuse

### Additional Optimizations

1. **Caching**: Add CloudFront or ElastiCache
2. **Compression**: Enable gzip for API responses
3. **Batching**: Batch DynamoDB operations
4. **Reserved Capacity**: For predictable workloads
5. **Spot Instances**: For batch processing (future)

## Compliance & Governance

### Tags

All resources are tagged with:
- Project: AndraKitchenAgent
- Environment: dev/prod
- ManagedBy: CloudFormation

### Policies

- IAM: Least-privilege access
- S3: Block public access
- API Gateway: Request validation
- Lambda: Environment-based configuration

### Audit

- CloudWatch Logs: 7-day retention
- CloudTrail: Optional for production
- AWS Config: Optional for compliance

## Troubleshooting

### Common Issues

**Stack Creation Failed:**
- Check IAM permissions
- Verify Bedrock model access
- Check service quotas

**Lambda Timeout:**
- Increase timeout (max 30s for API Gateway)
- Optimize code
- Check Bedrock API latency

**DynamoDB Throttling:**
- Review access patterns
- Add caching
- Consider provisioned capacity

**API Gateway 403:**
- Check Lambda permissions
- Verify CORS configuration
- Check rate limits

### Support Resources

- CloudFormation events and logs
- AWS service quotas
- AWS documentation
- AWS support (if needed)

## Next Steps

After infrastructure deployment:

1. ✓ Infrastructure deployed
2. ⏳ Deploy Lambda application code
3. ⏳ Set up Streamlit frontend
4. ⏳ Configure monitoring dashboards
5. ⏳ Load production market prices
6. ⏳ Test end-to-end workflow
7. ⏳ User acceptance testing
8. ⏳ Production deployment

## Conclusion

The infrastructure is production-ready with:
- ✓ AWS Free Tier compliance
- ✓ Security best practices
- ✓ Comprehensive monitoring
- ✓ Automated deployment
- ✓ Easy maintenance
- ✓ Scalability options

Total deployment time: **5-10 minutes**  
Total resources: **15+ AWS resources**  
Estimated cost: **$0-10/month**
