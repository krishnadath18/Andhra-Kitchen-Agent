# Contributing to Andhra Kitchen Agent

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/krishnadath18/Andhra-Kitchen-Agent/issues) first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, AWS region)
   - Screenshots if applicable

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its benefits
3. Provide use cases and examples
4. Discuss implementation approach

### Submitting Code

#### 1. Fork and Clone

```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/Andhra-Kitchen-Agent.git
cd Andhra-Kitchen-Agent
```

#### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

#### 3. Make Changes

Follow these guidelines:

**Code Style**
- Follow PEP 8 for Python code
- Use type hints for function signatures
- Write docstrings for all functions/classes
- Keep functions focused and under 50 lines
- Use meaningful variable names

**Testing**
- Write tests for new features
- Ensure all tests pass: `pytest`
- Maintain test coverage above 80%
- Include integration tests for API changes

**Documentation**
- Update relevant documentation
- Add docstrings to new functions
- Update README.md if needed
- Include code examples

**Security**
- Never commit credentials or secrets
- Follow security guidelines in `AGENTS.md`
- Validate all user inputs
- Use parameterized queries for databases

#### 4. Commit Changes

```bash
git add .
git commit -m "feat: add recipe filtering by cooking time"
```

Commit message format:
```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions/updates
- `chore`: Build/tooling changes

Examples:
```
feat: add Telugu language support for recipes
fix: resolve session expiry validation bug
docs: update deployment guide with CloudFormation steps
```

#### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference related issues (#123)
- List of changes made
- Screenshots/videos if UI changes
- Test results

## Development Setup

### Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_recipe_generator.py

# Run tests matching pattern
pytest -k "test_recipe"
```

### Code Quality

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/

# Run all checks
black src/ tests/ && flake8 src/ tests/ && mypy src/ && pytest
```

### Local Testing

```bash
# Run mock server
python local_server_mock.py

# Run Streamlit app
streamlit run app.py

# Test API endpoints
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"Hello","language":"en"}'
```

## Project Structure

```
src/                    # Source code
├── api_handler.py      # API request handlers
├── kitchen_agent_core.py  # Main orchestrator
├── recipe_generator.py    # Recipe generation
├── security_utils.py      # Security utilities
└── ...

tests/                  # Test suite
├── test_*.py          # Unit tests
└── fixtures/          # Test data

docs/                   # Documentation
├── security/          # Security documentation
└── ...

infrastructure/         # AWS deployment
├── cloudformation/    # CloudFormation templates
└── scripts/           # Deployment scripts
```

## Security Guidelines

**CRITICAL**: Follow these security rules:

1. **Never commit secrets**
   - Use `.env` for local secrets (gitignored)
   - Use AWS Secrets Manager for production
   - Check with `git diff` before committing

2. **Validate all inputs**
   - Use `security_utils.py` validation functions
   - Sanitize user inputs before processing
   - Validate file uploads (type, size, content)

3. **Follow secure coding practices**
   - Use parameterized queries
   - Implement rate limiting
   - Add security headers
   - Log security events

4. **Test security**
   - Write tests for validation logic
   - Test error handling
   - Verify authentication/authorization

See [Security Documentation](docs/security/) for details.

## Documentation Guidelines

- Use clear, concise language
- Include code examples
- Add diagrams for complex concepts
- Keep documentation up-to-date with code
- Use proper Markdown formatting

## Review Process

1. **Automated Checks**
   - Tests must pass
   - Code coverage must be maintained
   - Linting must pass
   - No security vulnerabilities

2. **Code Review**
   - At least one maintainer approval required
   - Address all review comments
   - Keep discussions professional

3. **Merge**
   - Squash commits for clean history
   - Update changelog if applicable
   - Delete branch after merge

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/krishnadath18/Andhra-Kitchen-Agent/discussions)
- **Bugs**: Create an [Issue](https://github.com/krishnadath18/Andhra-Kitchen-Agent/issues)
- **Chat**: Email krishnadath10@gmail.com

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for contributing to Andhra Kitchen Agent! 🙏
