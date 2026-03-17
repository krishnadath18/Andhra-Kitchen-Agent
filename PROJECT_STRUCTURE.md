# Project Structure
**Andhra Kitchen Agent**

This document describes the complete project structure and organization.

---

## 📁 Root Directory

```
andhra-kitchen-agent/
├── app.py                      # Streamlit frontend application
├── requirements.txt            # Python dependencies
├── README.md                   # Project overview and setup
├── QUICKSTART.md              # Quick start guide
├── CONTRIBUTING.md            # Contribution guidelines
├── AGENTS.md                  # Agent configuration
├── .env.template              # Environment variables template
└── PROJECT_STRUCTURE.md       # This file
```

---

## 📂 Source Code (`src/`)

```
src/
├── __init__.py
├── kitchen_agent_core.py      # Main agent orchestration
├── agentcore_orchestrator.py  # Bedrock AgentCore integration
├── vision_analyzer.py          # Image analysis (Claude 3 Sonnet)
├── recipe_generator.py         # Recipe generation (Claude 3 Haiku)
├── shopping_optimizer.py       # Shopping list optimization
├── reminder_service.py         # Reminder scheduling
├── api_handler.py             # Lambda API handler
├── api_client.py              # API client for frontend
├── validators.py              # Data validation utilities
├── security_utils.py          # Security validation & sanitization
└── rate_limiter.py            # Per-session rate limiting
```

### Key Components

- **kitchen_agent_core.py**: Main orchestration, session management, S3 uploads
- **agentcore_orchestrator.py**: Bedrock AgentCore workflow execution
- **vision_analyzer.py**: Image analysis using Claude 3 Sonnet
- **recipe_generator.py**: Recipe generation with nutrition calculation
- **shopping_optimizer.py**: Shopping list generation with market prices
- **reminder_service.py**: EventBridge-based reminder scheduling
- **security_utils.py**: Input validation, sanitization, security headers
- **rate_limiter.py**: DynamoDB-based rate limiting

---

## 🔧 Configuration (`config/`)

```
config/
├── __init__.py
└── env.py                     # Environment configuration
```

- Centralized configuration management
- Environment variable loading
- AWS service configuration

---

## 🧪 Tests (`tests/`)

```
tests/
├── __init__.py
├── fixtures/                  # Test data
│   ├── test_inventory.json
│   ├── test_recipe.json
│   └── test_shopping_list.json
├── test_*.py                  # Unit tests
└── test_*_integration.py      # Integration tests
```

### Test Coverage

- Unit tests for all core components
- Integration tests for workflows
- Fixture data for consistent testing

---

## 📊 Data Schemas (`schemas/`)

```
schemas/
├── inventory_schema.json      # Inventory JSON schema
├── recipe_schema.json         # Recipe JSON schema
└── shopping_list_schema.json  # Shopping list JSON schema
```

- JSON Schema definitions
- Data validation rules
- API contract specifications

---

## 🏗️ Infrastructure (`infrastructure/`)

```
infrastructure/
├── cloudformation/
│   ├── main-stack.yaml           # Main CloudFormation stack
│   ├── api-gateway.yaml          # API Gateway configuration
│   ├── api-gateway-auth.yaml     # Cognito authentication
│   └── encryption-config.yaml    # Encryption at rest
├── lambda/
│   ├── reminder_executor.py      # Reminder Lambda function
│   ├── requirements.txt          # Lambda dependencies
│   └── iam-policy.json          # IAM policies
├── scripts/
│   ├── deploy.sh                # Main deployment script
│   ├── deploy-lambda.sh         # Lambda deployment
│   ├── deploy-api-gateway.sh   # API Gateway deployment
│   ├── populate-market-prices.sh # Data seeding
│   ├── validate.sh              # Validation script
│   └── teardown.sh              # Cleanup script
├── data/
│   └── market-prices-sample.json # Sample market data
├── config/
│   └── env.template             # Infrastructure env template
├── README.md                    # Infrastructure documentation
├── DEPLOYMENT_GUIDE.md          # Deployment instructions
└── QUICK_START.md               # Quick deployment guide
```

### Infrastructure Components

- **CloudFormation**: Infrastructure as Code templates
- **Lambda**: Serverless function code
- **Scripts**: Deployment automation
- **Data**: Sample and seed data

---

## 📚 Documentation (`docs/`)

```
docs/
├── README.md                   # Documentation overview
├── PROJECT_STRUCTURE.md        # Project architecture
├── agentcore_configuration.md  # AgentCore setup
├── security/                   # Security documentation
│   ├── INDEX.md               # Security docs index
│   ├── README.md              # Main security guide
│   ├── QUICK_REFERENCE.md     # Developer reference
│   ├── DEPLOYMENT.md          # Security deployment
│   ├── AUDIT.md               # Security audit report
│   └── FIXES.md               # Implementation details
├── summaries/                  # Project summaries
│   ├── MVP_COMPLETE_SUMMARY.md
│   ├── DEPLOYMENT_COMPLETE_SUMMARY.md
│   ├── INTEGRATION_COMPLETE_SUMMARY.md
│   └── PROJECT_STATUS_SUMMARY.md
├── validation/                 # Validation reports
│   ├── VALIDATION_REPORT.md
│   └── FINAL_SYSTEM_VALIDATION.md
└── archive/                    # Historical documents
    ├── CLEANUP_SUMMARY.md
    └── RESTRUCTURING_HISTORY.md
```

### Documentation Structure

- **Root**: Main project documentation
- **security/**: Complete security documentation
- **summaries/**: Project milestone summaries
- **validation/**: Testing and validation reports
- **archive/**: Historical documents

---

## 🎨 Frontend Configuration (`.streamlit/`)

```
.streamlit/
└── config.toml                # Streamlit security configuration
```

- XSRF protection settings
- Cookie security
- Server configuration
- Theme settings

---

## 📝 Examples (`examples/`)

```
examples/
├── reminder_service_demo.py        # Reminder service usage
├── reminder_endpoints_demo.py      # API endpoint examples
└── shopping_list_endpoint_demo.py  # Shopping list examples
```

- Usage examples
- API demonstrations
- Integration patterns

---

## 🔐 Specifications (`.kiro/specs/`)

```
.kiro/specs/
└── andhra-kitchen-agent/
    ├── requirements.md         # Feature requirements
    ├── design.md              # System design
    └── tasks.md               # Implementation tasks
```

- Formal specifications
- Design documents
- Task tracking

---

## 🗄️ AWS Resources

### DynamoDB Tables
- `kitchen-agent-sessions-{env}` - User sessions
- `kitchen-agent-market-prices-{env}` - Market pricing data
- `kitchen-agent-reminders-{env}` - Scheduled reminders
- `kitchen-agent-rate-limits-{env}` - Rate limiting data

### S3 Buckets
- `kitchen-agent-images-{env}-{account-id}` - Image storage
- `kitchen-agent-logs-{env}-{account-id}` - Application logs

### Lambda Functions
- `kitchen-agent-api-handler-{env}` - API request handler
- `kitchen-agent-reminder-executor-{env}` - Reminder execution

### API Gateway
- `kitchen-agent-api-{env}` - REST API endpoints

### Cognito
- `kitchen-agent-users-{env}` - User pool

### KMS
- `kitchen-agent-{env}-encryption` - Encryption key

---

## 🔄 Data Flow

```
User → Streamlit (app.py)
  ↓
API Gateway → Lambda (api_handler.py)
  ↓
Kitchen Agent Core (kitchen_agent_core.py)
  ↓
AgentCore Orchestrator (agentcore_orchestrator.py)
  ↓
Tools:
  - Vision Analyzer (vision_analyzer.py) → Bedrock Claude 3 Sonnet
  - Recipe Generator (recipe_generator.py) → Bedrock Claude 3 Haiku
  - Shopping Optimizer (shopping_optimizer.py) → DynamoDB
  - Reminder Service (reminder_service.py) → EventBridge
  ↓
DynamoDB / S3 / EventBridge
```

---

## 🛡️ Security Components

### Input Validation
- `src/security_utils.py` - Validation functions
- `src/validators.py` - Data validators

### Rate Limiting
- `src/rate_limiter.py` - Rate limiting logic
- DynamoDB table for tracking

### Authentication
- `infrastructure/cloudformation/api-gateway-auth.yaml` - Cognito setup
- API Gateway authorizer

### Encryption
- `infrastructure/cloudformation/encryption-config.yaml` - KMS and encryption
- DynamoDB encryption at rest
- S3 bucket encryption

---

## 📦 Dependencies

### Python (requirements.txt)
- `boto3` - AWS SDK
- `streamlit` - Frontend framework
- `requests` - HTTP client
- `jsonschema` - Schema validation
- `python-dotenv` - Environment management

### AWS Services
- Amazon Bedrock (Claude 3 models)
- DynamoDB (data storage)
- S3 (image storage)
- Lambda (serverless compute)
- API Gateway (REST API)
- EventBridge (scheduling)
- Cognito (authentication)
- KMS (encryption)
- CloudWatch (monitoring)

---

## 🚀 Deployment Environments

### Development (`dev`)
- Local testing
- Development DynamoDB tables
- Development S3 bucket
- No authentication required

### Staging (`staging`)
- Pre-production testing
- Staging DynamoDB tables
- Staging S3 bucket
- Authentication enabled

### Production (`prod`)
- Live environment
- Production DynamoDB tables
- Production S3 bucket
- Full security enabled
- Monitoring and alarms

---

## 📊 Monitoring & Logging

### CloudWatch Logs
- Lambda function logs
- API Gateway access logs
- Application logs

### CloudWatch Metrics
- API request counts
- Lambda invocations
- DynamoDB operations
- Error rates

### CloudWatch Alarms
- Authentication failures
- Rate limit violations
- Lambda errors
- DynamoDB throttling

---

## 🔧 Development Workflow

1. **Local Development**
   - Edit code in `src/`
   - Run tests in `tests/`
   - Test locally with Streamlit

2. **Testing**
   - Unit tests: `pytest tests/`
   - Integration tests: `pytest tests/test_*_integration.py`
   - Security tests: `python src/security_utils.py`

3. **Deployment**
   - Deploy infrastructure: `./infrastructure/scripts/deploy.sh`
   - Deploy Lambda: `./infrastructure/scripts/deploy-lambda.sh`
   - Deploy API Gateway: `./infrastructure/scripts/deploy-api-gateway.sh`

4. **Validation**
   - Run validation: `./infrastructure/scripts/validate.sh`
   - Check CloudWatch logs
   - Test endpoints

---

## 📝 Configuration Files

### Root Level
- `.env.template` - Environment variables template
- `requirements.txt` - Python dependencies
- `.gitignore` - Git ignore rules

### Streamlit
- `.streamlit/config.toml` - Streamlit configuration

### Infrastructure
- `infrastructure/config/env.template` - Infrastructure env template

---

## 🎯 Key Features by Component

### Frontend (app.py)
- Multilingual UI (English/Telugu)
- Voice input support
- Image upload
- Recipe display
- Shopping list management

### Backend (src/)
- Image analysis
- Recipe generation
- Shopping optimization
- Reminder scheduling
- Session management

### Security (src/security_utils.py, src/rate_limiter.py)
- Input validation
- Rate limiting
- HTTPS enforcement
- Log sanitization

### Infrastructure (infrastructure/)
- CloudFormation templates
- Lambda functions
- Deployment scripts
- Monitoring setup

---

## 📖 Documentation Quick Links

- **Getting Started**: [README.md](README.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Security**: [docs/security/README.md](docs/security/README.md)
- **Infrastructure**: [infrastructure/README.md](infrastructure/README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Version**: 2.0  
**Last Updated**: 2026-03-13  
**Maintained By**: Development Team
