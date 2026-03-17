# Secure Deployment Guide - Fixed Infrastructure

## Overview
This guide covers deploying the secure, unified CloudFormation template that fixes all infrastructure security issues.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Lambda function deployed and ARN available
3. Domain name for production (for CORS configuration)

## Quick Start

### Development Deployment
```bash
cd infrastructure/cloudformation

aws cloudformation deploy \
  --template-file api-gateway-fixed.yaml \
  --stack-name kitchen-agent-api-dev \
  --parameter-overrides \
    Environment=dev \
    LambdaFunctionArn=arn:aws:lambda:us-east-1:123456789012:function:kitchen-agent-dev \
    AllowedOrigin='*' \
    AlarmNotificationTopicArn='' \
    ApplicationLogGroupName='/aws/lambda/kitchen-agent-dev' \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Production Deployment
```bash
cd infrastructure/cloudformation

aws cloudformation deploy \
  --template-file api-gateway-fixed.yaml \
  --stack-name kitchen-agent-api-prod \
  --parameter-overrides \
    Environment=prod \
    LambdaFunctionArn=arn:aws:lambda:us-east-1:123456789012:function:kitchen-agent-prod \
    AllowedOrigin='https://yourdomain.com' \
    AlarmNotificationTopicArn='arn:aws:sns:us-east-1:123456789012:kitchen-agent-alerts' \
    ApplicationLogGroupName='/aws/lambda/kitchen-agent-prod' \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

## Get Stack Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name kitchen-agent-api-prod \
  --query 'Stacks[0].Outputs' \
  --output table
```

Expected outputs:
- `APIEndpoint` - API Gateway URL
- `UserPoolId` - Cognito User Pool ID
- `UserPoolClientId` - Cognito App Client ID
- `CognitoRegion` - Cognito Region
- `UsagePlanId` - Usage Plan ID
- `CognitoAuthorizerId` - Authorizer ID

## Configure Environment Variables

### Lambda Function
Update your Lambda environment variables:
```bash
aws lambda update-function-configuration \
  --function-name kitchen-agent-prod \
  --environment Variables="{
    ENVIRONMENT=prod,
    ALLOWED_ORIGIN=https://yourdomain.com,
    COGNITO_REGION=us-east-1,
    COGNITO_USER_POOL_ID=<UserPoolId from outputs>,
    COGNITO_APP_CLIENT_ID=<UserPoolClientId from outputs>
  }"
```

### Frontend (.env)
```bash
API_ENDPOINT=<APIEndpoint from outputs>
COGNITO_REGION=<CognitoRegion from outputs>
COGNITO_USER_POOL_ID=<UserPoolId from outputs>
COGNITO_APP_CLIENT_ID=<UserPoolClientId from outputs>
ENVIRONMENT=prod
```

## Testing

### 1. Test CORS Preflight
```bash
curl -X OPTIONS \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/chat \
  -H "Origin: https://yourdomain.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type" \
  -v
```

Should return:
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://yourdomain.com
Access-Control-Allow-Methods: POST,OPTIONS
Access-Control-Allow-Headers: Content-Type,Authorization,X-Amz-Date,X-Api-Key
```

### 2. Create Test User
```bash
aws cognito-idp admin-create-user \
  --user-pool-id <UserPoolId> \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS
```

### 3. Test Authentication
Use the Streamlit frontend or:
```bash
# Get token (requires AWS CLI + jq)
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <UserPoolClientId> \
  --auth-parameters USERNAME=test@example.com,PASSWORD=YourPassword123! \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Call API
curl -X POST \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"Hello","language":"en"}'
```

## Monitoring

### CloudWatch Logs
```bash
# API Gateway logs
aws logs tail /aws/apigateway/kitchen-agent-api-prod --follow

# Lambda logs
aws logs tail /aws/lambda/kitchen-agent-prod --follow
```

### Orphan Image Cleanup
Run the cleanup utility in dry-run mode first:

```bash
python scripts/cleanup_orphan_images.py \
  --bucket <image-bucket> \
  --sessions-table <sessions-table> \
  --json
```

Add `--delete` only after reviewing the candidate list.

### X-Ray Traces
```bash
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s)
```

## Troubleshooting

### CORS Errors
**Symptom**: Browser shows CORS error
**Fix**: Verify `AllowedOrigin` parameter matches your frontend domain exactly

### 401 Unauthorized
**Symptom**: API returns 401
**Fix**: 
1. Verify Cognito token is valid
2. Check token is in `Authorization: Bearer <token>` header
3. Verify User Pool ID matches

### 403 Forbidden
**Symptom**: API returns 403
**Fix**:
1. Check usage plan limits
2. Verify API key if required
3. Check Lambda execution role permissions

### Missing OPTIONS Method
**Symptom**: Preflight fails with 403
**Fix**: Verify resource has OPTIONS method in template

## Rollback

If deployment fails:
```bash
aws cloudformation delete-stack --stack-name kitchen-agent-api-prod
```

Then redeploy with corrected parameters.

## Migration from Old Stacks

### Step 1: Export Configuration
```bash
# Get old stack outputs
aws cloudformation describe-stacks \
  --stack-name kitchen-agent-api-old \
  --query 'Stacks[0].Outputs' > old-outputs.json
```

### Step 2: Delete Old Stacks
```bash
# Delete in reverse dependency order
aws cloudformation delete-stack --stack-name kitchen-agent-auth-prod
aws cloudformation wait stack-delete-complete --stack-name kitchen-agent-auth-prod

aws cloudformation delete-stack --stack-name kitchen-agent-api-prod
aws cloudformation wait stack-delete-complete --stack-name kitchen-agent-api-prod
```

### Step 3: Deploy New Stack
Follow "Production Deployment" steps above.

### Step 4: Update Users
If migrating Cognito users, use:
```bash
aws cognito-idp admin-create-user \
  --user-pool-id <new-pool-id> \
  --username <email> \
  --user-attributes Name=email,Value=<email>
```

## Security Checklist

Before going to production:

- [ ] `AllowedOrigin` set to specific domain (not `*`)
- [ ] HTTPS configured on frontend
- [ ] CloudWatch logging enabled
- [ ] Optional security alarms configured with `AlarmNotificationTopicArn`
- [ ] Optional log-based alarms configured with `ApplicationLogGroupName`
- [ ] X-Ray tracing enabled
- [ ] Usage plan limits appropriate
- [ ] MFA enabled for admin users
- [ ] Cognito advanced security enabled
- [ ] Lambda environment variables secured
- [ ] API Gateway resource policy reviewed
- [ ] Test CORS preflight on all endpoints
- [ ] Test authentication flow end-to-end

## Support

For issues:
1. Check CloudWatch logs
2. Review X-Ray traces
3. Verify configuration matches outputs
4. See `INFRASTRUCTURE_SECURITY_FIXES.md` for details

## Next Steps

1. Set up CI/CD pipeline
2. Configure custom domain
3. Add WAF rules
4. Set up CloudWatch alarms
5. Configure backup/disaster recovery
