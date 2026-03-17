# Deployment Checklist

Use this checklist to ensure successful infrastructure deployment.

## Pre-Deployment

### AWS Account Setup
- [ ] AWS account created
- [ ] AWS Account ID noted: ________________
- [ ] Billing alerts configured
- [ ] Free Tier usage monitored

### AWS CLI Setup
- [ ] AWS CLI installed
- [ ] AWS CLI version verified: `aws --version`
- [ ] AWS credentials configured: `aws configure`
- [ ] Default region set to: `ap-south-1`
- [ ] Credentials tested: `aws sts get-caller-identity`

### Bedrock Access
- [ ] Navigated to AWS Console → Bedrock
- [ ] Model access page opened
- [ ] Claude 3 Haiku enabled
- [ ] Claude 3 Sonnet enabled
- [ ] Access status: Granted

### Tools Installation
- [ ] `jq` installed and verified: `jq --version`
- [ ] `git` installed (if cloning repo)
- [ ] Text editor available

### Repository Setup
- [ ] Repository cloned or downloaded
- [ ] Changed to project directory
- [ ] Scripts made executable: `chmod +x infrastructure/scripts/*.sh`

## Deployment

### Template Validation
- [ ] Template validated: `aws cloudformation validate-template ...`
- [ ] No validation errors
- [ ] Template syntax correct

### Stack Deployment
- [ ] Environment chosen: [ ] dev [ ] prod
- [ ] Deploy script executed: `./infrastructure/scripts/deploy.sh <env>`
- [ ] Stack creation initiated
- [ ] Waited for completion (5-10 minutes)
- [ ] Stack status: CREATE_COMPLETE or UPDATE_COMPLETE

### Stack Outputs
- [ ] Stack outputs retrieved
- [ ] API Endpoint noted: ________________
- [ ] Image Bucket noted: ________________
- [ ] Sessions Table noted: ________________
- [ ] Market Prices Table noted: ________________
- [ ] Reminders Table noted: ________________

## Post-Deployment Validation

### Infrastructure Validation
- [ ] Validation script executed: `./infrastructure/scripts/validate.sh <env>`
- [ ] CloudFormation stack: ✓
- [ ] S3 bucket: ✓
- [ ] S3 lifecycle policy: ✓
- [ ] S3 encryption: ✓
- [ ] DynamoDB sessions table: ✓
- [ ] DynamoDB market prices table: ✓
- [ ] DynamoDB reminders table: ✓
- [ ] TTL enabled on sessions table: ✓
- [ ] TTL enabled on reminders table: ✓
- [ ] Lambda KitchenAgentCore: ✓
- [ ] Lambda ReminderExecutor: ✓
- [ ] Lambda memory: 512 MB ✓
- [ ] Lambda timeout: 30 seconds ✓
- [ ] API Gateway endpoint: ✓
- [ ] API Gateway stage: v1 ✓
- [ ] CloudWatch log groups: ✓
- [ ] Log retention: 7 days ✓
- [ ] IAM roles: ✓

### Data Population
- [ ] Market prices script executed: `./infrastructure/scripts/populate-market-prices.sh <env>`
- [ ] 32 items loaded successfully
- [ ] Data verified in DynamoDB console

### API Testing
- [ ] API endpoint URL copied
- [ ] Test request prepared
- [ ] POST /chat endpoint tested
- [ ] Response received: 200 OK
- [ ] Placeholder response verified

## Configuration

### Environment Variables
- [ ] `.env` file created from template
- [ ] AWS_ACCOUNT_ID filled in
- [ ] AWS_REGION verified: ap-south-1
- [ ] ENVIRONMENT set: dev or prod
- [ ] Table names updated from stack outputs
- [ ] Bucket name updated from stack outputs
- [ ] API endpoint updated from stack outputs
- [ ] Bedrock model IDs verified

### Monitoring Setup
- [ ] CloudWatch Console accessed
- [ ] Dashboard created (optional)
- [ ] Alarms reviewed
- [ ] SNS topic configured for alarms (optional)
- [ ] Email notifications set up (optional)

## Security Review

### IAM
- [ ] Roles follow least-privilege principle
- [ ] No overly permissive policies
- [ ] Service-specific permissions only

### S3
- [ ] Public access blocked
- [ ] Encryption enabled
- [ ] HTTPS-only policy active
- [ ] Lifecycle policy configured

### API Gateway
- [ ] Rate limiting enabled: 100 req/min
- [ ] Burst limit set: 20
- [ ] CORS configured correctly
- [ ] Request validation enabled

### DynamoDB
- [ ] TTL enabled where needed
- [ ] Encryption at rest (default)
- [ ] On-demand billing active

### Lambda
- [ ] Environment variables used (no hardcoded secrets)
- [ ] Execution roles properly configured
- [ ] Timeout set appropriately

## Cost Management

### Free Tier Verification
- [ ] Lambda usage within limits
- [ ] DynamoDB usage within limits
- [ ] S3 usage within limits
- [ ] API Gateway usage within limits
- [ ] CloudWatch usage within limits

### Cost Monitoring
- [ ] AWS Cost Explorer accessed
- [ ] Filters set for project resources
- [ ] Billing alerts configured
- [ ] Budget set (optional)

## Documentation

### Information Recorded
- [ ] AWS Account ID: ________________
- [ ] Region: ap-south-1
- [ ] Environment: ________________
- [ ] Stack Name: ________________
- [ ] API Endpoint: ________________
- [ ] Deployment Date: ________________
- [ ] Deployed By: ________________

### Files Updated
- [ ] `.env` file configured
- [ ] API endpoint documented
- [ ] Resource names documented
- [ ] Access credentials secured

## Next Steps

### Application Deployment
- [ ] Lambda application code ready
- [ ] Lambda deployment package created
- [ ] Lambda functions updated with real code
- [ ] Environment variables configured in Lambda

### Frontend Setup
- [ ] Streamlit application configured
- [ ] API endpoint updated in frontend
- [ ] Frontend dependencies installed
- [ ] Frontend tested locally

### Testing
- [ ] Unit tests written
- [ ] Integration tests prepared
- [ ] End-to-end test plan created
- [ ] Test data prepared

### Production Readiness
- [ ] Load testing planned
- [ ] Performance benchmarks set
- [ ] Monitoring dashboards created
- [ ] Incident response plan documented
- [ ] Backup strategy defined
- [ ] Disaster recovery plan documented

## Troubleshooting

### If Stack Creation Failed
- [ ] CloudFormation events reviewed
- [ ] Error message identified
- [ ] Root cause determined
- [ ] Fix applied
- [ ] Stack deleted if needed
- [ ] Redeployment attempted

### If Validation Failed
- [ ] Specific failure identified
- [ ] AWS Console checked
- [ ] Resource status verified
- [ ] Logs reviewed
- [ ] Issue resolved
- [ ] Validation re-run

### If API Test Failed
- [ ] Lambda logs checked
- [ ] API Gateway logs reviewed
- [ ] CORS configuration verified
- [ ] Lambda permissions checked
- [ ] Issue resolved
- [ ] Test re-run

## Sign-Off

### Deployment Completed By
- Name: ________________
- Date: ________________
- Environment: [ ] dev [ ] prod
- Status: [ ] Success [ ] Failed [ ] Partial

### Verification Completed By
- Name: ________________
- Date: ________________
- All checks passed: [ ] Yes [ ] No
- Issues noted: ________________

### Approval (for Production)
- Approved By: ________________
- Date: ________________
- Signature: ________________

## Notes

Use this space for any additional notes, issues encountered, or special configurations:

_______________________________________________________________________________

_______________________________________________________________________________

_______________________________________________________________________________

_______________________________________________________________________________

_______________________________________________________________________________

## Rollback Plan

If rollback is needed:

1. [ ] Backup any critical data
2. [ ] Run teardown script: `./infrastructure/scripts/teardown.sh <env>`
3. [ ] Verify all resources deleted
4. [ ] Document reason for rollback
5. [ ] Plan corrective actions
6. [ ] Schedule redeployment

## Support Contacts

- AWS Support: https://console.aws.amazon.com/support/
- Project Lead: ________________
- DevOps Team: ________________
- On-Call Engineer: ________________

---

**Checklist Version:** 1.0  
**Last Updated:** 2024-01-15  
**Next Review:** After first production deployment
