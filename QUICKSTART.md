# Andhra Kitchen Agent - Quick Start Guide

Get up and running with the Andhra Kitchen Agent in 5 minutes!

## Prerequisites

- Python 3.11+
- AWS Account with Bedrock access
- AWS CLI configured

## Quick Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env with your AWS credentials
# Minimum required:
# - AWS_REGION=ap-south-1
# - AWS_ACCOUNT_ID=your-account-id
```

### 3. Deploy Infrastructure (Optional for Local Testing)

```bash
cd infrastructure
./scripts/deploy.sh
cd ..
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## First Steps

### Try the Chat Interface
1. Type: "What can I cook with tomatoes and rice?"
2. Or click the microphone icon for voice input

### Upload an Image
1. Click "📷 Upload Image"
2. Select a photo of your kitchen ingredients
3. Review detected ingredients
4. Generate recipes

### Switch Languages
- Use the sidebar to toggle between English and Telugu
- All UI text updates automatically

## What's Working

✅ **Frontend**: Complete Streamlit UI with all features
✅ **Backend**: All core tools and API endpoints
✅ **AWS**: Infrastructure templates ready

## What Needs Integration

⏳ **API Gateway**: Configure CORS and rate limiting
⏳ **Frontend-Backend**: Connect Streamlit to REST API
⏳ **Lambda**: Deploy reminder executor

## Development Mode

For local development without AWS:

```bash
# Run with mock data
export USE_MOCK_DATA=true
streamlit run app.py
```

## Troubleshooting

**Port already in use?**
```bash
streamlit run app.py --server.port 8502
```

**AWS credentials not found?**
```bash
aws configure
```

**Module not found?**
```bash
pip install -r requirements.txt
```

## Next Steps

- Read the full [README.md](README.md)
- Check [docs/summaries/PROJECT_STATUS_SUMMARY.md](docs/summaries/PROJECT_STATUS_SUMMARY.md) for implementation status
- Review [infrastructure/DEPLOYMENT_GUIDE.md](infrastructure/DEPLOYMENT_GUIDE.md) for AWS setup
- See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for project organization

## Support

- Documentation: See [docs/](docs/) directory
- AWS Setup: See [infrastructure/DEPLOYMENT_GUIDE.md](infrastructure/DEPLOYMENT_GUIDE.md)
- API Reference: See [infrastructure/API_DOCUMENTATION.md](infrastructure/API_DOCUMENTATION.md)

---

**Ready to cook? Let's go! 🍛**
