# 🚀 How to Run Andhra Kitchen Agent

## Quick Answer

**No, the backend does NOT start automatically when you run the frontend.**

You need to run **TWO separate processes**:
1. **Backend API Server** (Port 5000)
2. **Streamlit Frontend** (Port 8501)

---

## 📋 Prerequisites

Before running, ensure you have:

1. ✅ Python 3.11+ installed
2. ✅ Virtual environment activated
3. ✅ Dependencies installed
4. ✅ AWS credentials configured (optional for testing)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS (optional - tests work without this)
aws configure
```

---

## 🎯 Option 1: Run with MOCK Server (Recommended - No AWS Needed!)

### Step 1: Start the MOCK Backend Server

Open **Terminal 1**:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Start MOCK backend server (no AWS credentials needed!)
python local_server_mock.py
```

You should see:
```
============================================================
🍛 Andhra Kitchen Agent - MOCK Development Server
============================================================
✅ Running in MOCK mode - No AWS credentials needed!
✅ Using moto to simulate AWS services
✅ DynamoDB tables created in memory
============================================================
Server starting on http://localhost:5000
```

**Note**: This uses moto to simulate AWS services in memory. AI responses will be generic since Bedrock is mocked.

### Step 2: Start the Frontend

Open **Terminal 2** (keep Terminal 1 running):

```bash
# Activate virtual environment
.venv\Scripts\activate

# Start Streamlit frontend
streamlit run app.py
```

You should see:
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

### Step 3: Open in Browser

The browser should open automatically to `http://localhost:8501`

If not, manually open: **http://localhost:8501**

---

## 🎯 Option 2: Run with Real AWS Server (Requires AWS Credentials)

### Step 1: Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter region: ap-south-1
```

### Step 2: Start the Backend Server

Open **Terminal 1**:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Start backend server with real AWS
python local_server.py
```

You should see:
```
============================================================
🍛 Andhra Kitchen Agent - Local Development Server
============================================================
Server starting on http://localhost:5000
```

**Note**: This connects to real AWS services (DynamoDB, Bedrock, S3). You need valid AWS credentials and deployed infrastructure.

### Step 3: Start the Frontend

Open **Terminal 2** (keep Terminal 1 running):

```bash
# Activate virtual environment
.venv\Scripts\activate

# Start Streamlit frontend
streamlit run app.py
```

---

## 🧪 Option 3: Run Tests Only (No AWS Required)

If you just want to test the system without AWS:

```bash
# Run all tests (uses mocked AWS services)
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_kitchen_agent_error_handling.py -v
python -m pytest tests/test_vision_analyzer.py -v
python -m pytest tests/test_recipe_generator.py -v
```

**Note**: Tests use `moto` to mock AWS services, so no real AWS credentials needed!

---

## ⚙️ Option 4: Run with AWS Lambda + API Gateway (Production)

For production deployment:

### Step 1: Deploy AWS Infrastructure

```bash
cd infrastructure
.\scripts\deploy.sh
```

This creates:
- DynamoDB tables
- S3 bucket
- Lambda functions
- API Gateway endpoints

### Step 2: Update .env File

Copy the API Gateway URL from deployment output:

```env
API_BASE_URL=https://xxxxxxxxxx.execute-api.ap-south-1.amazonaws.com/v1
```

### Step 3: Run Streamlit

```bash
streamlit run app.py
```

The frontend will now connect to your deployed AWS backend!

---

## 🔍 Troubleshooting

### Problem: "Connection refused" or "Network error"

**Cause**: Backend server is not running

**Solution**: Make sure `local_server.py` is running in a separate terminal

---

### Problem: "AWS credentials not found"

**Cause**: AWS CLI not configured

**Solution**: 
```bash
# Option 1: Configure AWS
aws configure

# Option 2: Run tests only (no AWS needed)
python -m pytest tests/ -v
```

---

### Problem: "Module not found" errors

**Cause**: Dependencies not installed

**Solution**:
```bash
pip install -r requirements.txt
```

---

### Problem: Backend starts but frontend can't connect

**Cause**: Wrong API_BASE_URL in .env

**Solution**: Check `.env` file:
```env
API_BASE_URL=http://localhost:5000
```

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                        │
│                  http://localhost:8501                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP Requests
                     ▼
┌─────────────────────────────────────────────────────────┐
│              STREAMLIT FRONTEND (app.py)                 │
│                    Port 8501                             │
│  - UI rendering                                          │
│  - User interactions                                     │
│  - Voice input                                           │
│  - Image upload                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ REST API Calls
                     │ (via api_client.py)
                     ▼
┌─────────────────────────────────────────────────────────┐
│         BACKEND API SERVER (local_server.py)             │
│                    Port 5000                             │
│  - Flask wrapper for Lambda handlers                     │
│  - Routes requests to api_handler.py                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│              CORE BACKEND (src/*.py)                     │
│  - kitchen_agent_core.py (orchestration)                 │
│  - vision_analyzer.py (image analysis)                   │
│  - recipe_generator.py (recipe generation)               │
│  - shopping_optimizer.py (shopping lists)                │
│  - reminder_service.py (reminders)                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ AWS SDK Calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   AWS SERVICES                           │
│  - Bedrock (Claude AI)                                   │
│  - DynamoDB (data storage)                               │
│  - S3 (image storage)                                    │
│  - Lambda (reminder execution)                           │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Quick Health Check

Run this to verify everything is set up correctly:

```bash
# Check Python version
python --version  # Should be 3.11+

# Check imports
python -c "from src.kitchen_agent_core import KitchenAgentCore; print('✓ Imports OK')"

# Run quick test
python -m pytest tests/test_kitchen_agent_error_handling.py -v --tb=short

# Check if Flask is installed
python -c "import flask; print('✓ Flask installed')"
```

---

## 🎯 Summary

| What | Command | Port | Required? |
|------|---------|------|-----------|
| **Backend Server (MOCK)** | `python local_server_mock.py` | 5000 | ✅ Yes (No AWS needed) |
| **Backend Server (Real AWS)** | `python local_server.py` | 5000 | ⚠️ Optional (Needs AWS) |
| **Frontend UI** | `streamlit run app.py` | 8501 | ✅ Yes |
| **AWS Services** | Deploy via `infrastructure/scripts/deploy.sh` | N/A | ⚠️ Optional* |

*AWS services are optional for local testing (tests use mocks), but required for full functionality.

---

## 🚀 Recommended Workflow

**For Development/Testing:**
```bash
# Terminal 1: Start backend
python local_server.py

# Terminal 2: Start frontend
streamlit run app.py

# Terminal 3: Run tests
python -m pytest tests/ -v
```

**For Production:**
```bash
# Deploy to AWS
cd infrastructure && .\scripts\deploy.sh

# Update .env with API Gateway URL
# Then run frontend
streamlit run app.py
```

---

## 📞 Need Help?

- Check logs in Terminal 1 (backend) and Terminal 2 (frontend)
- Run tests to verify components: `python -m pytest tests/ -v`
- Check AWS credentials: `aws sts get-caller-identity`
- Verify .env file has correct settings

---

**Version**: 1.0.0  
**Last Updated**: March 2026  
**Status**: ✅ Ready to Run
