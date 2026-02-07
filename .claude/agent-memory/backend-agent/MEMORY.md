# Backend Agent Memory

## ERP Connector Framework

**Implementation Date**: 2026-02-07

Successfully built a comprehensive ERP Connector Framework for Brazilian ERP systems.

### Key Components

1. **Base Framework** (`/Volumes/AI/Code/FPA/src/connectors/`)
   - Abstract base class with standard interface
   - Support for 4 authentication types (OAuth2, API Key, Basic Auth, Bearer Token)
   - Automatic retry with exponential backoff
   - Circuit breaker pattern
   - Token bucket rate limiting
   - Comprehensive data validation

2. **ERP Implementations**
   - TOTVS Protheus (Effecti, OnClick) - 100 req/min
   - ContaAzul (Mercos, Munddi) - 60 req/min
   - Omie (Datahub) - 300 req/min
   - Bling (Ipê Digital, Leadlovers) - 100 req/min

3. **Standard Data Models**
   - TrialBalance with AccountBalance list
   - SubledgerEntry with full transaction details
   - HealthCheckResult for monitoring
   - All amounts use Decimal for precision

4. **Test Coverage**
   - 46 unit tests, 100% passing
   - Comprehensive validation tests
   - Mocked integration tests
   - Test file: `/Volumes/AI/Code/FPA/tests/test_connectors.py`

### Important Patterns

1. **Always use async context manager**
   ```python
   async with connector:
       data = await connector.get_trial_balance(...)
   ```

2. **Factory pattern for creation**
   ```python
   connector = create_connector(erp_type, auth_type, credentials, config)
   ```

3. **Data validation is automatic**
   - All responses validated and normalized
   - Portuguese account types converted to English
   - Decimal precision for amounts
   - Multiple date formats supported

4. **Rate limiting is built-in**
   - No need to manually throttle requests
   - Automatic token bucket implementation

5. **Retry logic is automatic**
   - Use `@with_retry` decorator
   - Exponential backoff with jitter
   - Respects HTTP status codes

### Common Issues & Solutions

1. **datetime.utcnow() deprecation**
   - Use `datetime.now(timezone.utc)` instead
   - Must import `timezone` from datetime

2. **Account objects vs dicts**
   - TrialBalanceValidator returns dict with validated accounts
   - Must convert to AccountBalance objects before creating TrialBalance
   - Pattern: `[AccountBalance(**acc) for acc in validated_data["accounts"]]`

3. **Import paths in tests**
   - Tests need `sys.path.insert(0, str(Path(__file__).parent.parent / "src"))`
   - Or set PYTHONPATH environment variable

### Portfolio Company Mapping

Use `get_erp_for_company(company_name)` to look up ERP type:
- effecti → TOTVS Protheus
- onclick → TOTVS Protheus
- mercos → ContaAzul
- munddi → ContaAzul
- datahub → Omie
- ipe_digital / ipedigital → Bling
- leadlovers → Bling

### Documentation

- README: `/Volumes/AI/Code/FPA/src/connectors/README.md`
- Examples: `/Volumes/AI/Code/FPA/src/connectors/examples.py`
- Summary: `/Volumes/AI/Code/FPA/src/connectors/IMPLEMENTATION_SUMMARY.md`

### Future Enhancements

- Add caching layer (Redis)
- Implement bulk operations
- Add webhook support
- Monitoring & alerting (Prometheus)
- Additional ERPs (SAP, Sankhya, Senior)
