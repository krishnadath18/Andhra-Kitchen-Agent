# Andhra Kitchen Agent

> AI-powered kitchen assistant for Andhra Pradesh cuisine with intelligent recipe generation, shopping optimization, and meal planning.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20DynamoDB-orange.svg)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-audited-brightgreen.svg)](docs/security/)

## Overview

Andhra Kitchen Agent is an intelligent culinary assistant that leverages AWS Bedrock's Claude 3 models to provide personalized cooking guidance for Andhra Pradesh cuisine. The system combines computer vision, natural language processing, and real-time market data to deliver comprehensive meal planning solutions.

### Key Features

- **🍳 Intelligent Recipe Generation** - Context-aware recipes based on available ingredients, dietary preferences, and allergies
- **📸 Visual Ingredient Detection** - Computer vision analysis of fridge/pantry images using Claude 3 Sonnet
- **🛒 Smart Shopping Lists** - Optimized shopping recommendations with real-time Vijayawada market prices
- **⏰ Meal Reminders** - Automated cooking reminders with EventBridge scheduling
- **🌐 Bilingual Support** - Full Telugu and English language support
- **🔒 Enterprise Security** - Comprehensive security controls with encryption, rate limiting, and input validation

## Architecture

```
┌─────────────────┐
│   Streamlit UI  │
│  (Frontend)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Gateway    │
│  + Lambda       │
└────────┬────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
    ┌────────┐    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │Bedrock │    │DynamoDB │   │    S3    │   │EventBridge│
    │Claude 3│    │Sessions │   │  Images  │   │ Reminders │
    └────────┘    └─────────┘   └──────────┘   └──────────┘
```

### Technology Stack

- **AI/ML**: AWS Bedrock (Claude 3 Haiku, Claude 3 Sonnet)
- **Backend**: Python 3.11+, AWS Lambda
- **Frontend**: Streamlit
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

### AWS Deployment

For production deployment with all security features:

```bash
# Deploy secure infrastructure
./infrastructure/scripts/deploy-api-gateway.sh

# See complete deployment guide
```

📖 **Full deployment instructions**: [docs/security/DEPLOYMENT.md](docs/security/DEPLOYMENT.md)

## Documentation

### Getting Started
- [Quick Start Guide](QUICKSTART.md) - Get running in 5 minutes
- [Project Structure](docs/PROJECT_STRUCTURE.md) - Codebase organization
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

**Security Status**: ✅ Production Ready | 🟢 Low Risk | 12/12 Vulnerabilities Resolved

See [Security Documentation](docs/security/) for details.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test suite
pytest tests/test_recipe_generator.py

# Run integration tests
pytest tests/test_*_integration.py
```

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

**Estimated Monthly Cost**: $5-10 beyond free tier

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
