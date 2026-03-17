# Contributing to Andhra Kitchen Agent

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/andhra-kitchen-agent.git
   cd andhra-kitchen-agent
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to all functions and classes
- Format code with Black:
  ```bash
  black src/ tests/
  ```

## Testing

### Run All Tests
```bash
pytest tests/
```

### Run Specific Tests
```bash
pytest tests/test_vision_analyzer.py
pytest tests/test_recipe_generator.py
```

### Check Coverage
```bash
pytest --cov=src tests/
```

Target: 80% code coverage

## Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code style

3. Add tests for new functionality

4. Run tests to ensure nothing breaks:
   ```bash
   pytest tests/
   ```

5. Commit your changes:
   ```bash
   git commit -m "Add: Brief description of changes"
   ```

## Commit Message Guidelines

Use conventional commit format:

- `Add:` New feature or functionality
- `Fix:` Bug fix
- `Update:` Changes to existing functionality
- `Docs:` Documentation changes
- `Test:` Adding or updating tests
- `Refactor:` Code refactoring
- `Style:` Code style changes (formatting, etc.)

Examples:
```
Add: Voice input support for Telugu language
Fix: Image upload validation for HEIC format
Update: Recipe card UI with nutrition display
Docs: Add API endpoint documentation
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update PROJECT_STATUS_SUMMARY.md if completing tasks
5. Submit pull request with clear description

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] Added new tests
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

## Adding New Features

### Backend Features

1. Update the spec in `.kiro/specs/andhra-kitchen-agent/`
2. Implement in appropriate module (`src/`)
3. Add JSON schema if needed (`schemas/`)
4. Create tests (`tests/`)
5. Update API endpoints if needed (`app.py`)

### Frontend Features

1. Update `app.py` with new UI components
2. Add translations to `UI_TEXT` dictionary
3. Test in both English and Telugu
4. Verify mobile responsiveness
5. Add error handling

## Security Guidelines

⚠️ **CRITICAL**: Always follow security best practices

- Never commit AWS credentials or API keys
- Validate all user inputs
- Sanitize file uploads (type, size, content)
- Use parameterized queries for database operations
- Follow principle of least privilege for IAM roles
- Add WARNING comments for security-critical code

Example:
```python
# WARNING: File upload validation is critical for security
# We validate file type and size to prevent malicious uploads
if file_size_mb > 10:
    raise ValueError("File size exceeds 10MB limit")
```

## Documentation

Update documentation when:
- Adding new features
- Changing API endpoints
- Modifying configuration
- Adding dependencies

Files to update:
- `README.md` - Main documentation
- `QUICKSTART.md` - Quick start guide
- `PROJECT_STATUS_SUMMARY.md` - Task completion status
- Inline code comments

## Questions?

- Check existing documentation
- Review closed issues
- Open a new issue for discussion

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Andhra Kitchen Agent! 🍛
