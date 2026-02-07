# Contributing to AI FP&A

## Development Workflow

### 1. Set Up Development Environment

```bash
# Clone repository
git clone https://github.com/escotilha/nuvini-ai-fpa.git
cd nuvini-ai-fpa

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment file
cp .env.example .env
# Edit .env with your local settings

# Set up database
createdb nuvini_fpa_dev
alembic upgrade head

# Seed test data
python -m scripts.seed_test_data
```

### 2. Development Guidelines

**Code Style:**
- Use Black for formatting: `black src/`
- Use Ruff for linting: `ruff check src/`
- Use mypy for type checking: `mypy src/`
- All code must pass pre-commit hooks

**Testing:**
- Write tests for all new code
- Maintain >80% code coverage
- Run tests: `pytest`
- Run with coverage: `pytest --cov=src --cov-report=html`

**Security:**
- NEVER commit credentials or API keys
- All ERP credentials via AWS Secrets Manager
- Run security scan: `bandit -r src/`
- Follow OWASP Top 10 guidelines

### 3. Git Workflow

```bash
# Create feature branch
git checkout -b feature/erp-connector-totvs

# Make changes and commit
git add src/connectors/totvs_connector.py
git commit -m "feat(connectors): add TOTVS Protheus connector

- Implement OAuth 2.0 authentication
- Add trial balance extraction
- Add comprehensive error handling
- Add unit tests with 95% coverage"

# Push to remote
git push origin feature/erp-connector-totvs

# Create pull request via GitHub CLI
gh pr create --title "Add TOTVS Protheus ERP Connector" \
             --body "Implements connector for TOTVS with OAuth 2.0"
```

### 4. Commit Message Convention

Format: `<type>(<scope>): <description>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Build process, dependencies

**Examples:**
```
feat(consolidation): add intercompany elimination logic
fix(database): resolve deadlock in period locking
docs(README): update installation instructions
test(connectors): add integration tests for ContaAzul
```

### 5. Pull Request Process

1. **Before submitting:**
   - [ ] All tests pass (`pytest`)
   - [ ] Code coverage >80%
   - [ ] Type checking passes (`mypy src/`)
   - [ ] Linting passes (`ruff check src/`)
   - [ ] Security scan clean (`bandit -r src/`)
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated

2. **PR description must include:**
   - Summary of changes
   - Testing performed
   - Breaking changes (if any)
   - Screenshots (for UI changes)

3. **Code review:**
   - Requires 1 approval from core team
   - All comments must be resolved
   - CI/CD must pass

4. **Merge:**
   - Squash and merge for feature branches
   - Keep commit history clean

### 6. Testing Guidelines

**Unit Tests:**
```python
# tests/connectors/test_totvs_connector.py
import pytest
from src.connectors.totvs_connector import TOTVSConnector

@pytest.mark.asyncio
async def test_totvs_authentication():
    connector = TOTVSConnector(
        api_endpoint="https://test.totvs.com.br/api",
        client_id="test_client",
        client_secret="test_secret"
    )
    result = await connector.authenticate()
    assert result == True

@pytest.mark.asyncio
async def test_totvs_extract_trial_balance():
    connector = TOTVSConnector(...)
    await connector.authenticate()

    trial_balance = await connector.extract_trial_balance(
        period_year=2026,
        period_month=1
    )

    assert trial_balance is not None
    assert len(trial_balance.rows) > 0
    assert trial_balance.is_balanced()
```

**Integration Tests:**
```python
# tests/integration/test_monthly_close_flow.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_monthly_close():
    """Test end-to-end monthly close for one company."""
    # Setup
    company = await create_test_company("test_effecti")

    # Execute monthly close
    result = await orchestrator.run_monthly_close(
        company_id=company.id,
        period_year=2026,
        period_month=1
    )

    # Verify
    assert result.status == "SUCCESS"
    assert result.consolidated_balance is not None
    assert result.accuracy >= 0.99
```

### 7. Security Review Checklist

Before committing code that handles:
- [ ] Financial data → Encrypt sensitive fields
- [ ] API credentials → Use AWS Secrets Manager
- [ ] User input → Validate and sanitize
- [ ] SQL queries → Use parameterized queries
- [ ] File uploads → Validate type and size
- [ ] External APIs → Implement retry/timeout
- [ ] Logging → Never log credentials or PII

### 8. Documentation

**Code documentation:**
- All public functions have docstrings
- Complex logic has inline comments
- Type hints on all functions

**Example:**
```python
async def extract_trial_balance(
    self,
    period_year: int,
    period_month: int
) -> TrialBalanceResult:
    """
    Extract trial balance from ERP for specified period.

    Args:
        period_year: Year (e.g., 2026)
        period_month: Month (1-12)

    Returns:
        TrialBalanceResult with rows and metadata

    Raises:
        ERPConnectionError: If API connection fails
        DataValidationError: If trial balance doesn't balance

    Example:
        >>> connector = TOTVSConnector(...)
        >>> result = await connector.extract_trial_balance(2026, 1)
        >>> print(f"Extracted {len(result.rows)} accounts")
    """
```

### 9. Performance Considerations

- Database queries should use indexes (check `EXPLAIN ANALYZE`)
- Batch operations for bulk inserts (use `COPY` or `executemany`)
- Cache frequently accessed data (use Redis)
- Profile slow operations (`cProfile` for Python)
- Target: Monthly close for 7 companies in <2 hours

### 10. Monitoring & Observability

All code should emit structured logs:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "trial_balance_extracted",
    company_id=company_id,
    period=f"{year}-{month:02d}",
    row_count=len(rows),
    duration_seconds=duration,
    success=True
)
```

### 11. Need Help?

- **Technical questions:** Open an issue on GitHub
- **Security concerns:** Email security@nuvini.ai
- **Documentation:** See `/docs` folder
- **Slack:** #fpa-automation channel

## Code of Conduct

- Be respectful and professional
- Focus on constructive feedback
- Assume good intent
- Help junior developers learn

## License

All contributions are proprietary to Nuvini Group Limited.
