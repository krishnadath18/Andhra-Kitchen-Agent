# Quick Start Guide

Get the Andhra Kitchen Agent running in 5 minutes.

## Prerequisites

- Python 3.11+
- AWS Account (for production deployment)
- Git

## Local Development (No AWS Required)

### Option 1: Docker (Recommended - Easiest)

```bash
git clone https://github.com/krishnadath18/Andhra-Kitchen-Agent.git
cd Andhra-Kitchen-Agent

# Start with Docker Compose
docker-compose up

# Access at http://localhost:8501
```

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed Docker instructions.

### Option 2: Manual Setup

### 1. Clone and Setup

```bash
git clone https://github.com/krishnadath18/Andhra-Kitchen-Agent.git
cd Andhra-Kitchen-Agent

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Run Mock Server

```bash
# Terminal 1: Start mock backend
python local_server_mock.py

# Terminal 2: Start Streamlit
streamlit run app.py
```

### 3. Access Application

Open browser to: http://localhost:8501

## AWS Deployment (Production)

### 1. Configure AWS

```bash
aws configure
# Enter your AWS credentials
# Region: ap-south-1 (Mumbai)
```

### 2. Enable Bedrock Models

> ⚠️ **COST WARNING**: AWS Bedrock is **NOT included in the AWS Free Tier**. You will be charged per token for all API calls. Monitor your usage to avoid unexpected charges. See [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/).

1. Go to AWS Console → Bedrock → Model access
2. Enable: Claude 3 Haiku, Claude 3 Sonnet
3. Wait for approval (usually instant)

### 3. Deploy Infrastructure

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your AWS details
nano .env

# Deploy secure infrastructure
./infrastructure/scripts/deploy-api-gateway.sh
```

### 4. Verify Deployment

```bash
# Test API endpoint
curl -X POST https://your-api-endpoint/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"Hello","language":"en"}'
```

## Next Steps

- 📖 Read [Full Documentation](docs/README.md)
- 🔒 Review [Security Guide](docs/security/README.md)
- 🏗️ Explore [Project Structure](docs/PROJECT_STRUCTURE.md)
- 🤝 Check [Contributing Guidelines](CONTRIBUTING.md)

## Troubleshooting

**Issue**: Module not found
```bash
pip install -r requirements.txt
```

**Issue**: AWS credentials error
```bash
aws configure
# Re-enter credentials
```

**Issue**: Bedrock access denied
- Enable models in AWS Console → Bedrock → Model access

**Issue**: Port already in use
```bash
streamlit run app.py --server.port 8502
```

## Support

- GitHub Issues: [Report a bug](https://github.com/krishnadath18/Andhra-Kitchen-Agent/issues)
- Email: krishnadath10@gmail.com
