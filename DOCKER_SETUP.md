# Docker Setup Guide

Get the Andhra Kitchen Agent running with Docker in under 2 minutes - no AWS configuration required!

## Prerequisites

- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))
- Docker Compose (included with Docker Desktop)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/krishnadath18/Andhra-Kitchen-Agent.git
cd Andhra-Kitchen-Agent
```

### 2. Start the Application

```bash
# Build and start all services
docker-compose up

# Or run in detached mode (background)
docker-compose up -d
```

### 3. Access the Application

- **Frontend (Streamlit)**: http://localhost:8501
- **Mock API Backend**: http://localhost:5001

### 4. Stop the Application

```bash
# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## What's Included

The Docker setup includes:

- **Streamlit Frontend**: Full UI with chat, recipe generation, shopping lists
- **Mock Backend Server**: Simulates AWS Bedrock responses (no AWS account needed)
- **Automatic Health Checks**: Services restart automatically if they fail
- **Hot Reload**: Code changes are reflected immediately (volumes mounted)

## Development Workflow

### Making Code Changes

The following directories are mounted as volumes, so changes are reflected immediately:

- `./src` - Backend logic
- `./config` - Configuration files
- `./app.py` - Streamlit frontend

Just edit the files and refresh your browser!

### Viewing Logs

```bash
# View logs from all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs from specific service
docker-compose logs streamlit
docker-compose logs mock-backend
```

### Rebuilding After Dependency Changes

If you modify `requirements.txt`:

```bash
# Rebuild images
docker-compose build

# Restart services
docker-compose up
```

## Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose Network          │
│                                         │
│  ┌──────────────┐    ┌──────────────┐ │
│  │  Streamlit   │───▶│ Mock Backend │ │
│  │  (Port 8501) │    │  (Port 5001) │ │
│  └──────────────┘    └──────────────┘ │
│         │                    │         │
└─────────┼────────────────────┼─────────┘
          │                    │
          ▼                    ▼
    Your Browser          Mock Responses
```

## Troubleshooting

### Port Already in Use

If port 8501 or 5001 is already in use:

```bash
# Edit docker-compose.yml and change ports:
# ports:
#   - "8502:8501"  # Use 8502 instead of 8501
```

### Services Won't Start

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs

# Restart specific service
docker-compose restart streamlit
```

### Permission Errors (Linux)

```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Or run with sudo
sudo docker-compose up
```

### Out of Disk Space

```bash
# Clean up unused Docker resources
docker system prune -a

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune -a
```

## Advanced Configuration

### Custom Environment Variables

Create a `.env.docker` file:

```bash
# .env.docker
ENVIRONMENT=dev
USE_MOCK_BACKEND=true
LOG_LEVEL=DEBUG
```

Update `docker-compose.yml`:

```yaml
services:
  streamlit:
    env_file:
      - .env.docker
```

### Using Real AWS Backend

To connect to real AWS services instead of mock:

1. Configure AWS credentials:

```bash
# Create .env.aws file
cat > .env.aws << EOF
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=ap-south-1
USE_MOCK_BACKEND=false
EOF
```

2. Update `docker-compose.yml`:

```yaml
services:
  streamlit:
    env_file:
      - .env.aws
    # Remove mock-backend dependency
```

3. Remove or comment out the mock-backend service

### Production Deployment

For production, use a proper orchestration platform:

- **AWS ECS/Fargate**: Deploy containers to AWS
- **Kubernetes**: Use Helm charts for deployment
- **Docker Swarm**: Simple multi-host deployment

See [docs/security/DEPLOYMENT.md](docs/security/DEPLOYMENT.md) for production deployment guides.

## Health Checks

Both services include health checks:

```bash
# Check Streamlit health
curl http://localhost:8501/_stcore/health

# Check Mock Backend health
curl http://localhost:5001/health
```

## Performance Tips

### Faster Builds

Use Docker BuildKit for faster builds:

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with BuildKit
docker-compose build
```

### Resource Limits

Limit resource usage in `docker-compose.yml`:

```yaml
services:
  streamlit:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Security Notes

### Development vs Production

This Docker setup is optimized for **local development**:

- ✅ Easy to use, no AWS setup required
- ✅ Hot reload for rapid development
- ✅ Mock backend for testing
- ⚠️ **NOT suitable for production** without modifications

### Production Security Checklist

Before deploying to production:

- [ ] Remove volume mounts (use COPY in Dockerfile)
- [ ] Use multi-stage builds to reduce image size
- [ ] Run as non-root user (already configured)
- [ ] Enable HTTPS/TLS
- [ ] Use secrets management (not environment variables)
- [ ] Implement proper authentication
- [ ] Set up monitoring and logging
- [ ] Use production-grade database (not mock)

## Next Steps

- 📖 Read [QUICKSTART.md](QUICKSTART.md) for AWS deployment
- 🔒 Review [docs/security/README.md](docs/security/README.md) for security best practices
- 🏗️ Explore [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) to understand the codebase
- 🤝 Check [CONTRIBUTING.md](CONTRIBUTING.md) to contribute

## Support

- **Issues**: [GitHub Issues](https://github.com/krishnadath18/Andhra-Kitchen-Agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/krishnadath18/Andhra-Kitchen-Agent/discussions)
- **Email**: krishnadath10@gmail.com

---

**Happy Cooking! 🍛**
