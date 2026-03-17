# Andhra Kitchen Agent 🍛

An AI-powered multilingual kitchen assistant for Andhra cuisine, built with Amazon Bedrock, AWS services, and Streamlit.

## Overview

The Andhra Kitchen Agent helps users discover authentic Andhra recipes, manage kitchen inventory through image recognition, optimize shopping lists with local market prices, and get cooking reminders. The system supports both English and Telugu languages.

## Features

- 🍳 **Recipe Generation**: AI-powered recipe suggestions based on available ingredients
- 📸 **Image Recognition**: Identify ingredients from kitchen photos using Claude 3 Sonnet
- 🛒 **Smart Shopping Lists**: Optimized shopping lists with local Vijayawada market prices
- ⏰ **Cooking Reminders**: Scheduled reminders for time-sensitive ingredients
- 🌐 **Multilingual**: Full support for English and Telugu
- 🎤 **Voice Input**: Speak your requests in English or Telugu
- 💚 **Health-Conscious**: Low-oil recipe options with nutrition information
- 🎉 **Festival Mode**: Special recipes for Sankranti, Ugadi, Dasara, and Deepavali

## Architecture

### Backend
- **AWS Bedrock**: Claude 3 Sonnet (vision), Claude 3 Haiku (recipes, orchestration)
- **DynamoDB**: Session management, market prices, reminders
- **S3**: Image storage with 24-hour lifecycle
- **Lambda**: Reminder execution
- **API Gateway**: REST API with Cognito authentication and rate limiting

### Frontend
- **Streamlit**: Interactive web interface
- **Web Speech API**: Voice input support
- **Responsive Design**: Mobile-friendly (min-width 360px)

## Prerequisites

- Python 3.11+
- AWS Account with Bedrock access
- AWS CLI configured
- Node.js (for infrastructure deployment)
- Cognito User Pool and App Client for Streamlit sign-in

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd andhra-kitchen-agent
```

### 2. Set Up Python Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

```bash
aws configure
```

### 4. Set Up Environment Variables

Copy `.env.template` to `.env` and configure:

```bash
cp .env.template .env
```

Edit `.env` with your AWS settings:

```env
AWS_REGION=ap-south-1
AWS_ACCOUNT_ID=your-account-id
COGNITO_REGION=ap-south-1
COGNITO_USER_POOL_ID=ap-south-1_example
COGNITO_APP_CLIENT_ID=exampleclientid
IMAGE_BUCKET=kitchen-agent-images-{account-id}
SESSIONS_TABLE=kitchen-agent-sessions-dev
MARKET_PRICES_TABLE=kitchen-agent-market-prices-dev
REMINDERS_TABLE=kitchen-agent-reminders-dev
BEDROCK_MODEL_VISION=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_MODEL_RECIPE=anthropic.claude-3-haiku-20240307-v1:0
```

Validate the security-sensitive settings before deployment:

```bash
python scripts/validate_security_config.py
```

After image uploads are live, run the orphan cleanup utility in dry-run mode:

```bash
python scripts/cleanup_orphan_images.py --json
```

### 5. Deploy AWS Infrastructure

```bash
python scripts/validate_security_config.py
bash infrastructure/scripts/deploy-api-gateway.sh
```

WARNING: `infrastructure/scripts/deploy.sh` still references the deprecated legacy stack flow.
Secure alternative: use `infrastructure/scripts/deploy-api-gateway.sh` with
`infrastructure/cloudformation/api-gateway-fixed.yaml` for the authenticated API
surface, and keep the old split-stack templates deprecated.

This secure deployment path creates:
- Cognito user pool and app client
- API Gateway endpoints with Cognito auth and route-level CORS preflight
- CloudWatch alarms for API 5XX and latency
- Optional log-based alarms for rate limiter and image cleanup failures

### 6. Seed Market Price Data

```bash
./scripts/populate-market-prices.sh
```

## Running the Application

### Start the Streamlit Frontend

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`. Sign in with your Cognito credentials before creating a backend session or using any API-backed feature.

### Run the Backend API (Development)

```bash
python -m uvicorn app:app --reload
```

## Usage

### Chat Interface
1. Sign in with your Cognito username and password
2. Type your message or click the microphone for voice input
2. Ask questions like:
   - "What can I cook with tomatoes and rice?"
   - "Show me low-oil recipes"
   - "Generate a shopping list for biryani"

### Image Analysis
1. Click "📷 Upload Image"
2. Select a photo of your kitchen ingredients
3. Review detected ingredients with confidence scores
4. Confirm medium-confidence items
5. Generate recipes based on detected ingredients

### Recipe Generation
1. View generated recipe cards with:
   - Ingredients and quantities
   - Step-by-step cooking instructions
   - Nutrition information
   - Estimated cost per serving
2. Select a recipe to generate a shopping list

### Shopping List
1. Review items grouped by market section
2. Check off items as you purchase them
3. View total estimated cost
4. Get reminders for price-sensitive items

### Language Toggle
- Switch between English and Telugu using the sidebar
- All UI text and responses update automatically

## Project Structure

```
andhra-kitchen-agent/
├── app.py                          # Streamlit frontend
├── src/
│   ├── kitchen_agent_core.py      # Main orchestrator
│   ├── agentcore_orchestrator.py  # Bedrock AgentCore integration
│   ├── vision_analyzer.py         # Image analysis
│   ├── recipe_generator.py        # Recipe generation
│   ├── shopping_optimizer.py      # Shopping list optimization
│   ├── reminder_service.py        # Reminder scheduling
│   └── validators.py              # JSON schema validation
├── schemas/                        # JSON schemas
├── tests/                          # Test suite
├── infrastructure/                 # AWS CloudFormation templates
└── docs/                          # Additional documentation
```

## API Endpoints

All application endpoints require `Authorization: Bearer <Cognito ID token>`.

### Session Management
- `POST /session` - Create new session
- `GET /session/{session_id}` - Get session data

### Chat & Interaction
- `POST /chat` - Send chat message
- `POST /upload-image` - Upload kitchen image
- `POST /analyze-image` - Analyze uploaded image

### Recipe & Shopping
- `POST /generate-recipes` - Generate recipe suggestions
- `POST /generate-shopping-list` - Create shopping list

### Reminders
- `GET /reminders/{session_id}` - Get pending reminders
- `POST /reminders/{reminder_id}/dismiss` - Dismiss reminder
- `POST /reminders/{reminder_id}/snooze` - Snooze reminder

## Testing

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Suites

```bash
# Vision analyzer tests
pytest tests/test_vision_analyzer.py

# Recipe generator tests
pytest tests/test_recipe_generator.py

# Shopping optimizer tests
pytest tests/test_shopping_optimizer_*.py

# API endpoint tests
pytest tests/test_*_endpoint.py
```

### Run Integration Tests

```bash
pytest tests/test_*_integration.py
```

## Development

### Code Style

The project follows PEP 8 guidelines. Format code with:

```bash
black src/ tests/
```

### Adding New Features

1. Update the spec in `.kiro/specs/andhra-kitchen-agent/`
2. Implement the feature
3. Add tests
4. Update documentation

## AWS Free Tier Compliance

The system is designed to stay within AWS Free Tier limits:
- **S3**: < 5GB storage (24-hour lifecycle)
- **DynamoDB**: On-demand billing with 7-day TTL
- **Lambda**: < 1M invocations/month
- **API Gateway**: < 1M calls/month
- **Bedrock**: Pay-per-use (monitor usage)

## Performance

- Chat responses: < 3 seconds
- Image analysis: < 10 seconds
- Recipe generation: < 15 seconds
- Supports 10 concurrent users

## Security

- HTTPS-only API endpoints
- Cognito bearer-token authentication on all application routes
- Session, reminder, and image ownership enforced by Cognito `sub`
- Session data isolation
- File upload validation (type, size)
- Image analysis resolves S3 objects server-side from stored metadata only
- Successful authenticated responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`
- Orphaned image detection utility available via `scripts/cleanup_orphan_images.py`
- No credentials in code

## Troubleshooting

### Common Issues

**Bedrock Access Denied**
- Ensure your AWS account has Bedrock access enabled
- Check IAM permissions for Bedrock API calls

**DynamoDB Table Not Found**
- Run infrastructure deployment: `./infrastructure/scripts/deploy.sh`
- Verify table names in `.env` match deployed tables

**Image Upload Fails**
- Check S3 bucket exists and is accessible
- Verify file size < 10MB
- Ensure file format is JPEG, PNG, or HEIC

**Voice Input Not Working**
- Use Chrome, Edge, or Safari (Firefox not supported)
- Grant microphone permissions in browser
- Check browser console for errors

## Security

The Andhra Kitchen Agent implements enterprise-grade security controls:

- ✅ **HTTPS Enforcement** - All remote connections secured
- ✅ **Authentication** - Cognito-based user authentication
- ✅ **Input Validation** - Comprehensive validation framework
- ✅ **Rate Limiting** - Per-session abuse prevention
- ✅ **Encryption** - Data protected at rest and in transit
- ✅ **Security Headers** - Protection against common web attacks

**Security Status**: ✅ Production Ready | **Risk Level**: 🟢 Low Risk

For detailed security information, see **[docs/security/](docs/security/)** folder:
- **[README.md](docs/security/README.md)** - Complete security documentation
- **[QUICK_REFERENCE.md](docs/security/QUICK_REFERENCE.md)** - Developer guidelines
- **[DEPLOYMENT.md](docs/security/DEPLOYMENT.md)** - Production deployment

**Reporting Security Issues**: Please email security concerns directly to the security team. Do not create public issues for security vulnerabilities.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Your License Here]

## Acknowledgments

- Amazon Bedrock for AI capabilities
- Streamlit for the frontend framework
- USDA/IFCT for nutrition data
- Vijayawada market data contributors

## Documentation

### Getting Started
- [README.md](README.md) - Project overview and setup
- [QUICKSTART.md](QUICKSTART.md) - 5-minute quick start guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Developer contribution guidelines

### Security
- [docs/security/](docs/security/) - Complete security documentation
  - [README.md](docs/security/README.md) - Main security guide
  - [QUICK_REFERENCE.md](docs/security/QUICK_REFERENCE.md) - Developer reference
  - [DEPLOYMENT.md](docs/security/DEPLOYMENT.md) - Production deployment
  - [INDEX.md](docs/security/INDEX.md) - Documentation index

### Technical Documentation
- [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) - Project architecture
- [docs/agentcore_configuration.md](docs/agentcore_configuration.md) - AgentCore setup
- [docs/README.md](docs/README.md) - Documentation overview

### Deployment
- [infrastructure/DEPLOYMENT_GUIDE.md](infrastructure/DEPLOYMENT_GUIDE.md) - Complete AWS deployment guide
- [infrastructure/API_DOCUMENTATION.md](infrastructure/API_DOCUMENTATION.md) - REST API reference
- [infrastructure/QUICK_START.md](infrastructure/QUICK_START.md) - Quick deployment steps

### Project Status & Validation
- [docs/summaries/PROJECT_STATUS_SUMMARY.md](docs/summaries/PROJECT_STATUS_SUMMARY.md) - Implementation status
- [docs/summaries/MVP_COMPLETE_SUMMARY.md](docs/summaries/MVP_COMPLETE_SUMMARY.md) - MVP completion report
- [docs/validation/VALIDATION_REPORT.md](docs/validation/VALIDATION_REPORT.md) - Test results and validation
- [docs/validation/FINAL_SYSTEM_VALIDATION.md](docs/validation/FINAL_SYSTEM_VALIDATION.md) - System validation

### Technical Documentation
- [docs/agentcore_configuration.md](docs/agentcore_configuration.md) - AgentCore configuration guide
- [.kiro/specs/andhra-kitchen-agent/](./kiro/specs/andhra-kitchen-agent/) - Complete specification documents

## Project Status

✅ **MVP Complete - Ready for Deployment**

- **Test Pass Rate**: 99.7% (309/310 tests passing)
- **Core Functionality**: 100% complete
- **API Endpoints**: 100% complete (all 10 endpoints)
- **Frontend**: 100% complete (Streamlit UI with all features)
- **Deployment**: Infrastructure ready (Lambda, API Gateway, DynamoDB, S3)
- **Documentation**: Complete

See [docs/summaries/PROJECT_STATUS_SUMMARY.md](docs/summaries/PROJECT_STATUS_SUMMARY.md) for detailed status.

---

**Version**: 1.0.0  
**Last Updated**: March 2026  
**Status**: ✅ MVP Complete - Ready for Deployment  
**Test Pass Rate**: 99.7% (309/310 tests passing)
