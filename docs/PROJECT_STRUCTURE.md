# Andhra Kitchen Agent - Project Structure

## Directory Overview

```
andhra-kitchen-agent/
├── .kiro/                          # Kiro AI configuration and specs
│   ├── specs/andhra-kitchen-agent/ # Complete feature specification
│   │   ├── requirements.md         # Requirements document
│   │   ├── design.md              # Design document with 50 properties
│   │   └── tasks.md               # Implementation tasks
│   └── settings/                   # Kiro settings (if any)
│
├── config/                         # Application configuration
│   └── env.py                     # Environment configuration loader
│
├── docs/                          # Documentation
│   ├── security/                 # Security documentation
│   │   ├── INDEX.md             # Security docs index
│   │   ├── README.md            # Main security documentation
│   │   ├── DEPLOYMENT.md        # SECURE: Production deployment guide
│   │   ├── FIXES.md             # Technical implementation details
│   │   ├── AUDIT.md             # Original security audit
│   │   └── QUICK_REFERENCE.md   # Developer quick reference
│   ├── summaries/                 # Project summaries
│   │   ├── PROJECT_STATUS_SUMMARY.md
│   │   ├── MVP_COMPLETE_SUMMARY.md
│   │   ├── DEPLOYMENT_COMPLETE_SUMMARY.md
│   │   ├── INTEGRATION_COMPLETE_SUMMARY.md
│   │   ├── FRONTEND_IMPLEMENTATION_SUMMARY.md
│   │   └── DOCUMENTATION_UPDATE_SUMMARY.md
│   ├── validation/                # Validation reports
│   │   ├── VALIDATION_REPORT.md
│   │   └── FINAL_SYSTEM_VALIDATION.md
│   ├── agentcore_configuration.md # AgentCore setup guide
│   └── PROJECT_STRUCTURE.md       # This file
│
├── examples/                      # Example usage scripts
│   ├── reminder_endpoints_demo.py
│   ├── reminder_service_demo.py
│   └── shopping_list_endpoint_demo.py
│
├── infrastructure/                # AWS deployment infrastructure
│   ├── cloudformation/           # CloudFormation templates
│   │   ├── api-gateway-fixed.yaml # SECURE: Unified API Gateway with all security fixes
│   │   ├── encryption-config.yaml # KMS encryption and encrypted resources
│   │   ├── rate-limit-table.yaml # Rate limiting DynamoDB table
│   │   ├── api-gateway.yaml     # DEPRECATED: Legacy API Gateway (use api-gateway-fixed.yaml)
│   │   ├── api-gateway-auth.yaml # DEPRECATED: Legacy auth (use api-gateway-fixed.yaml)
│   │   └── main-stack.yaml      # DEPRECATED: Legacy main stack
│   ├── config/                   # Infrastructure configuration
│   │   └── env.template         # Environment template
│   ├── data/                     # Sample data
│   │   └── market-prices-sample.json
│   ├── lambda/                   # Lambda functions
│   │   ├── reminder_executor.py # Reminder execution Lambda
│   │   ├── iam-policy.json     # IAM policies
│   │   └── requirements.txt    # Lambda dependencies
│   ├── scripts/                  # Deployment scripts
│   │   ├── deploy-api-gateway.sh # SECURE: Deploy api-gateway-fixed.yaml
│   │   ├── deploy.sh           # DEPRECATED: Legacy deployment
│   │   ├── deploy-lambda.sh    # Lambda deployment
│   │   ├── populate-market-prices.sh
│   │   ├── teardown.sh         # Cleanup script
│   │   ├── validate.sh         # Validation script
│   │   ├── validate_security_config.py # Pre-deployment security validation
│   │   └── cleanup_orphan_images.py # Orphaned S3 object cleanup
│   ├── API_DOCUMENTATION.md     # REST API documentation
│   ├── DEPLOYMENT_GUIDE.md      # DEPRECATED: Legacy deployment guide
│   ├── DEPLOYMENT_CHECKLIST.md  # Deployment checklist
│   ├── QUICK_START.md          # DEPRECATED: Legacy quick start
│   └── README.md               # Infrastructure overview
│
├── schemas/                      # JSON schemas
│   ├── inventory_schema.json   # Inventory data schema
│   ├── recipe_schema.json      # Recipe data schema
│   └── shopping_list_schema.json # Shopping list schema
│
├── src/                         # Source code
│   ├── agentcore_config.py     # AgentCore configuration
│   ├── agentcore_orchestrator.py # Bedrock AgentCore integration
│   ├── api_client.py           # API client for frontend
│   ├── api_handler.py          # API request handlers
│   ├── auth_client.py          # Cognito authentication client
│   ├── auth_utils.py           # Authentication utilities
│   ├── kitchen_agent_core.py   # Main orchestrator
│   ├── rate_limiter.py         # DynamoDB-based rate limiting
│   ├── recipe_generator.py     # Recipe generation tool
│   ├── reminder_service.py     # Reminder scheduling tool
│   ├── security_utils.py       # Security validation and sanitization
│   ├── shopping_optimizer.py   # Shopping list optimization tool
│   ├── validators.py           # JSON schema validators
│   ├── vision_analyzer.py      # Image analysis tool
│   └── __init__.py
│
├── tests/                       # Test suite
│   ├── fixtures/               # Test fixtures
│   │   ├── test_inventory.json
│   │   ├── test_recipe.json
│   │   └── test_shopping_list.json
│   ├── test_*.py              # Unit and integration tests
│   └── __init__.py
│
├── ui/                         # Frontend UI modules (refactored)
│   ├── components.py          # UI rendering components
│   ├── handlers.py            # Event handlers and API integration
│   ├── state.py               # Session state management
│   ├── styles.py              # CSS styles (warm Andhra aesthetic)
│   └── translations.py        # Bilingual text (English/Telugu)
│
├── backups/                    # Backup files
│   └── app_old.py             # Original monolithic app.py
│
├── .env.template               # Environment variables template
├── .gitignore                 # Git ignore rules
├── AGENTS.md                  # Security guidelines
├── app.py                     # Streamlit frontend (refactored, modular)
├── CONTRIBUTING.md            # Contribution guidelines
├── DOCKER_SETUP.md            # Docker setup guide
├── QUICKSTART.md             # Quick start guide
├── README.md                 # Main project documentation
├── REFACTORING_SUMMARY.md    # UI refactoring documentation
└── requirements.txt          # Python dependencies
```

## Key Files

### Root Level
- **app.py** - Streamlit frontend application (main entry point, refactored to 150 lines)
- **requirements.txt** - Python package dependencies
- **.env.template** - Template for environment configuration
- **README.md** - Project overview and setup instructions
- **QUICKSTART.md** - 5-minute quick start guide
- **CONTRIBUTING.md** - Developer contribution guidelines
- **AGENTS.md** - Security guidelines and best practices
- **DOCKER_SETUP.md** - Docker development environment guide
- **REFACTORING_SUMMARY.md** - UI refactoring documentation

### Source Code (`src/`)
- **kitchen_agent_core.py** - Main orchestrator coordinating all components
- **agentcore_orchestrator.py** - Bedrock AgentCore integration for workflow orchestration
- **vision_analyzer.py** - Claude 3 Sonnet integration for ingredient detection
- **recipe_generator.py** - Claude 3 Haiku integration for recipe generation
- **shopping_optimizer.py** - Shopping list optimization with market prices
- **reminder_service.py** - EventBridge-based reminder scheduling
- **api_client.py** - Frontend API client with error handling
- **api_handler.py** - Backend API request handlers
- **validators.py** - JSON schema validation utilities

### UI Modules (`ui/`)
- **components.py** - All UI rendering functions (login, navbar, tabs)
- **handlers.py** - Event handlers, API integration, and data processing
- **state.py** - Session state initialization and authentication management
- **styles.py** - Complete CSS stylesheet with warm Andhra aesthetic
- **translations.py** - Bilingual UI text (English/Telugu)

### Infrastructure (`infrastructure/`)
- **cloudformation/api-gateway-fixed.yaml** - SECURE: Unified API Gateway with all security fixes
- **cloudformation/encryption-config.yaml** - KMS encryption and encrypted resources
- **cloudformation/rate-limit-table.yaml** - Rate limiting DynamoDB table
- **scripts/deploy-api-gateway.sh** - SECURE: Deploy api-gateway-fixed.yaml
- **scripts/deploy-lambda.sh** - Lambda function deployment
- **DEPLOYMENT_GUIDE.md** - DEPRECATED: Legacy deployment (use docs/security/DEPLOYMENT.md)
- **API_DOCUMENTATION.md** - Complete REST API reference

### Documentation (`docs/`)
- **security/** - Security audit, fixes, and secure deployment guide
- **summaries/** - Project status and completion summaries
- **validation/** - Test results and system validation reports
- **agentcore_configuration.md** - AgentCore setup and configuration
- **PROJECT_STRUCTURE.md** - This file

### Tests (`tests/`)
- **test_*.py** - Unit tests for all components
- **test_*_integration.py** - Integration tests for workflows
- **test_*_endpoint.py** - API endpoint tests
- **fixtures/** - Test data and mock objects

### Specifications (`.kiro/specs/andhra-kitchen-agent/`)
- **requirements.md** - Complete requirements specification
- **design.md** - Detailed design with 50 correctness properties
- **tasks.md** - Implementation task breakdown

## File Naming Conventions

### Python Files
- **snake_case** for all Python files and modules
- **test_*.py** for test files
- **validate_*.py** for validation scripts (deprecated, moved to tests/)

### Documentation
- **UPPERCASE.md** for root-level documentation (README, CONTRIBUTING, etc.)
- **lowercase.md** for nested documentation
- **PascalCase_SUMMARY.md** for summary documents

### Configuration
- **.env.template** for environment templates
- **config.yaml** or **config.json** for configuration files

## Important Notes

### What's in Version Control
- All source code (`src/`, `tests/`)
- Documentation (`docs/`, `README.md`, etc.)
- Infrastructure templates (`infrastructure/cloudformation/`)
- Deployment scripts (`infrastructure/scripts/`)
- Configuration templates (`.env.template`)
- JSON schemas (`schemas/`)

### What's NOT in Version Control (`.gitignore`)
- `.env` - Actual environment variables (contains secrets)
- `.venv/` - Python virtual environment
- `__pycache__/` - Python bytecode cache
- `.pytest_cache/` - Pytest cache
- `.kiro/settings/mcp.json` - Local MCP configuration
- `backups/` - Backup files (including app_old.py)
- AWS credentials and secrets

### Deprecated/Removed Files
The following files were removed during cleanup:
- `test_*.py` in root (moved to `tests/` directory)
- `validate_*.py` in root (deprecated, tests cover validation)
- `add_methods.py` (temporary development file)
- `ESSENTIAL_FILES.md` (outdated)
- `IMPROVEMENTS_SUMMARY.md` (empty file, removed)
- `EXTERNAL_SECURITY_AUDIT_REPORT.md` (empty file, removed)

### Refactored Files
The following files were refactored for better maintainability:
- **app.py** - Reduced from 1375 lines to 150 lines (89% reduction)
  - Original backed up to `backups/app_old.py`
  - Functionality split into modular `ui/` components
  - Maintains 100% feature parity with improved code organization

## Quick Navigation

### For New Users
1. Start with [README.md](../README.md)
2. Follow [QUICKSTART.md](../QUICKSTART.md)
3. Check [docs/security/DEPLOYMENT.md](security/DEPLOYMENT.md) for secure deployment

### For Developers
1. Read [CONTRIBUTING.md](../CONTRIBUTING.md)
2. Review [docs/summaries/PROJECT_STATUS_SUMMARY.md](summaries/PROJECT_STATUS_SUMMARY.md)
3. Check [.kiro/specs/andhra-kitchen-agent/](../.kiro/specs/andhra-kitchen-agent/) for specifications
4. Review [docs/security/QUICK_REFERENCE.md](security/QUICK_REFERENCE.md) for security guidelines

### For DevOps
1. Read [docs/security/DEPLOYMENT.md](security/DEPLOYMENT.md) for secure deployment
2. Use [infrastructure/scripts/deploy-api-gateway.sh](../infrastructure/scripts/deploy-api-gateway.sh)
3. Review [docs/security/FIXES.md](security/FIXES.md) for security implementations

### For QA/Testing
1. Check [docs/validation/VALIDATION_REPORT.md](validation/VALIDATION_REPORT.md)
2. Review [docs/validation/FINAL_SYSTEM_VALIDATION.md](validation/FINAL_SYSTEM_VALIDATION.md)
3. Run tests: `pytest tests/`

---

**Last Updated**: March 2026  
**Maintained By**: Project Team
