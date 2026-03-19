# Andhra Kitchen Agent

> AI-powered kitchen assistant for Andhra Pradesh cuisine with intelligent recipe generation, shopping optimization, and meal planning.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20DynamoDB-orange.svg)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-audited-brightgreen.svg)](docs/security/)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue.svg)](.github/workflows/ci.yml)

## Overview

Andhra Kitchen Agent is an intelligent culinary assistant that leverages AWS Bedrock's Claude 3 models to provide personalized cooking guidance for Andhra Pradesh cuisine. The system combines computer vision, natural language processing, and real-time market data to deliver comprehensive meal planning solutions.

## Screenshots

> 📸 **Visual Documentation Coming Soon**: Screenshots and demo video will be added to showcase the UI and key features. For now, you can run the application locally using Docker (see Quick Start below) to explore the interface.

### Key Features

- **🍳 Intelligent Recipe Generation** - Context-aware recipes based on available ingredients, dietary preferences, and allergies
- **📸 Visual Ingredient Detection** - Computer vision analysis of fridge/pantry images using Claude 3 Sonnet
- **🛒 Smart Shopping Lists** - Optimized shopping recommendations with real-time Vijayawada market prices
- **⏰ Meal Reminders** - Automated cooking reminders with EventBridge scheduling
- **🌐 Bilingual Support** - Full Telugu and English language support
- **🔒 Enterprise Security** - Comprehensive security controls with encryption, rate limiting, and input validation

## Architecture

```
┌─────────────────────────────────────┐
│   Streamlit UI (Modular Frontend)   │
│   ├── components.py (UI rendering)  │
│   ├── handlers.py (API integration) │
│   ├── state.py (session mgmt)       │
│   ├── styles.py (Andhra aesthetic)  │
│   └── translations.py (EN/TE)       │
└────────────────┬────────────────────┘
                 │
                 ▼
         ┌─────────────────┐
         │  API Gateway    │
         │  + Lambda       │
         └────────┬────────┘
                  │
         ├────────┴────────┬──────────────┬──────────────┐
         ▼                 ▼              ▼              ▼
    ┌────────┐        ┌─────────┐   ┌──────────┐   ┌──────────┐
    │Bedrock │        │DynamoDB │   │    S3    │   │EventBridge│
    │Claude 3│        │Sessions │   │  Images  │   │ Reminders │
    └────────┘        └─────────┘   └──────────┘   └──────────┘
```

### Technology Stack

- **AI/ML**: AWS Bedrock (Claude 3 Haiku, Claude 3 Sonnet)
- **Backend**: Python 3.11+, AWS Lambda
- **Frontend**: Streamlit (modular architecture with warm Andhra aesthetic)
- **Database**: Amazon DynamoDB
- **Storage**: Amazon S3
- **Scheduling**: Amazon EventBridge
- **Infrastructure**: AWS CloudFormation

## Quick Start

### Prerequisites

- Python 3.11 or higher
- AWS Account with Bedrock access
- AWS CLI configured
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/krishnadath18/Andhra-Kitchen-Agent.git
cd Andhra-Kitchen-Agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your AWS credentials and configuration
```

### Local Development

```bash
# Run Streamlit app locally
streamlit run app.py

# Run with mock backend (no AWS required)
python local_server_mock.py
streamlit run app.py
```

### Docker Development (Recommended)

The easiest way to get started without configuring AWS:

```bash
# Build and start all services
docker-compose up

# Access the application
# Frontend: http://localhost:8501
# Mock API: http://localhost:5001
```

This starts both the Streamlit frontend and mock backend in isolated containers.

### AWS Deployment

For production deployment with all security features:

```bash
# Deploy secure infrastructure
./infrastructure/scripts/deploy-api-gateway.sh

# See complete deployment guide
```

> ⚠️ **Note**: The legacy `infrastructure/scripts/deploy.sh` script is deprecated. Use `deploy-api-gateway.sh` for secure Cognito-authenticated API deployment.

📖 **Full deployment instructions**: [docs/security/DEPLOYMENT.md](docs/security/DEPLOYMENT.md)

## Documentation

### Getting Started
- [Quick Start Guide](QUICKSTART.md) - Get running in 5 minutes
- [Project Structure](docs/PROJECT_STRUCTURE.md) - Codebase organization
- [UI Refactoring Summary](REFACTORING_SUMMARY.md) - Modular frontend architecture
- [Docker Setup Guide](DOCKER_SETUP.md) - Docker development environment
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute

### Security
- [Security Overview](docs/security/README.md) - Security architecture and controls
- [Deployment Guide](docs/security/DEPLOYMENT.md) - Secure production deployment
- [Security Audit](docs/security/AUDIT.md) - Vulnerability assessment
- [Security Fixes](docs/security/FIXES.md) - Implemented security controls
- [Quick Reference](docs/security/QUICK_REFERENCE.md) - Developer security guidelines

### Technical
- [AgentCore Configuration](docs/agentcore_configuration.md) - Bedrock AgentCore setup
- [API Documentation](infrastructure/API_DOCUMENTATION.md) - REST API reference
- [Infrastructure Guide](infrastructure/README.md) - AWS infrastructure details

## Features in Detail

### Modern UI Design

Beautiful, culturally-authentic interface featuring:
- **Warm Andhra Aesthetic** - Traditional color palette (cream, tamarind, turmeric, saffron)
- **Custom Typography** - Playfair Display, Lora, and Noto Sans Telugu fonts
- **Bilingual Support** - Seamless English ↔ Telugu switching
- **Responsive Design** - Mobile-optimized layouts
- **Modular Architecture** - Clean separation of concerns for maintainability

### Recipe Generation

Generate authentic Andhra recipes with:
- Ingredient-based recommendations
- Dietary restriction compliance (vegetarian, vegan, allergies)
- Cooking time and difficulty levels
- Step-by-step instructions in Telugu or English
- Nutritional information

### Visual Ingredient Detection

Upload fridge/pantry images to:
- Automatically detect ingredients
- Identify quantities and freshness
- Get recipe suggestions based on available items
- Track inventory over time

### Shopping Optimization

Smart shopping lists with:
- Real-time Vijayawada market prices
- Cost optimization across multiple markets
- Quantity calculations based on recipes
- Ingredient substitution suggestions

### Meal Planning

Comprehensive meal planning:
- Weekly meal schedules
- Cooking time reminders
- Ingredient preparation alerts
- Leftover management

## Security

This project implements enterprise-grade security controls:

- ✅ **Authentication** - AWS Cognito user authentication
- ✅ **Encryption** - Data encrypted at rest (KMS) and in transit (TLS)
- ✅ **Input Validation** - Comprehensive validation against injection attacks
- ✅ **Rate Limiting** - Per-user rate limiting with DynamoDB
- ✅ **Security Headers** - Strict CSP, HSTS, and other security headers
- ✅ **PII Protection** - Automatic PII redaction in logs
- ✅ **HTTPS Enforcement** - TLS required for all connections
- ✅ **Access Control** - Least-privilege IAM policies

**Security Status**: 🚧 Beta / Work in Progress | 🟡 Active Development | 12/12 Known Vulnerabilities Addressed

See [Security Documentation](docs/security/) for details.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test suite
pytest tests/test_recipe_generator.py

# Run integration tests (requires AWS credentials)
pytest tests/test_*_integration.py
```

**Note on Test Coverage**: The test suite includes both unit tests (no AWS required) and integration tests (require AWS credentials). The CI pipeline runs unit tests automatically on every push. Some integration tests may require manual setup of AWS resources and are excluded from automated CI runs.

## Performance

- **Response Time**: < 2s for recipe generation
- **Image Analysis**: < 3s for ingredient detection
- **Concurrent Users**: Supports 100+ concurrent users
- **Availability**: 99.9% uptime with AWS infrastructure

## Cost Optimization

Designed for AWS Free Tier compliance:
- Lambda: ~10K requests/month (well within 1M free tier)
- DynamoDB: < 1GB storage (within 25GB free tier)
- S3: < 100MB with 24-hour lifecycle (within 5GB free tier)
- Bedrock: Pay-per-use (Claude 3 Haiku optimized for cost)

> ⚠️ **IMPORTANT**: AWS Bedrock is **NOT included in the AWS Free Tier**. Bedrock charges per token (input/output) and can incur significant costs depending on usage. Claude 3 Haiku is the most cost-effective model, but monitor your usage carefully. See [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) for details.

**Estimated Monthly Cost**: $5-10 beyond free tier (primarily Bedrock usage)

## Recent Updates

### December 2024 - UI Refactoring
- ✅ Refactored monolithic `app.py` (1375 lines → 150 lines, 89% reduction)
- ✅ Created modular UI architecture with 5 specialized modules
- ✅ Implemented warm Andhra aesthetic design system
- ✅ Enhanced bilingual support (English/Telugu)
- ✅ Improved code maintainability and testability
- ✅ Preserved all security features and functionality

See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for details.

## Roadmap

- [ ] Mobile app (React Native)
- [ ] Voice commands (Alexa integration)
- [ ] Meal prep video tutorials
- [ ] Community recipe sharing
- [ ] Nutritionist consultation integration
- [ ] Grocery delivery integration

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 src/ tests/

# Run type checking
mypy src/

# Format code
black src/ tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/krishnadath18/Andhra-Kitchen-Agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/krishnadath18/Andhra-Kitchen-Agent/discussions)
- **Email**: krishnadath10@gmail.com

## Acknowledgments

- AWS Bedrock team for Claude 3 models
- Andhra Pradesh culinary community
- Open source contributors

---

**Built with ❤️ for Andhra Pradesh cuisine lovers**
