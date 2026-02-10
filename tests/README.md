# Speecher Testing Documentation

## 🎯 Testing Strategy Overview

The Speecher project employs a **hybrid testing strategy** that delivers the best of both worlds:

- **🐳 Docker-first locally**: Fast, consistent, zero-configuration development experience
- **☸️ Kubernetes-native in CI**: Production-like environment for maximum confidence

This approach ensures developers can work efficiently locally while CI/CD validates in a true production-like environment.

### Why This Hybrid Approach?

| Environment | Tool | Benefits |
|------------|------|----------|
| **Local Development** | Docker Compose | • Instant startup<br>• Simple debugging<br>• Familiar tooling<br>• Resource efficient |
| **CI/CD Pipeline** | Kubernetes (K3s) | • Production parity<br>• Real service mesh<br>• True isolation<br>• Scale testing |

## 📊 Database Isolation Strategy

Every environment has complete database isolation to prevent data corruption and ensure test reliability:

| Environment | Database | Collection | Connection String | Cleanup |
|------------|----------|------------|-------------------|---------|
| **Development** | `speecher` | `transcriptions` | `mongodb://...@mongodb:27017/speecher` | Manual |
| **Local Tests** | `speecher_test` | `transcriptions_test` | `mongodb://...@mongodb:27017/speecher_test` | Auto before each run |
| **CI/CD Tests** | `speecher_ci_${RUN_ID}` | `transcriptions_ci` | Dynamic per workflow | Auto after run |
| **Production** | `speecher_prod` | `transcriptions` | Managed by K8s secrets | Never |

### Key Principles:
- **Never share databases** between environments
- **Always clean test data** before running tests
- **Use unique namespaces** in CI for parallel runs
- **Isolate by convention** (suffix patterns: `_test`, `_ci`, `_prod`)

## 🚀 Local Testing Commands

### Quick Start

```bash
# Run all tests (recommended)
npm test
# or
make test

# Run tests and watch for changes
make test-watch

# Run specific test file
make test-specific FILE=test_api.py

# Clean up test resources
make test-cleanup
```

### NPM Scripts

```bash
npm test              # Run tests in Docker (alias for test:local)
npm run test:local    # Explicitly run Docker-based tests
npm run test:watch    # Auto-rerun tests on file changes
npm run test:build    # Rebuild test container
npm run test:cleanup  # Remove test containers and volumes
```

### Make Commands (with pretty output)

```bash
make test           # 🧪 Run tests in Docker
make test-watch     # 👁️ Watch mode for development
make test-specific  # 🎯 Run single test file
make test-cleanup   # 🧹 Clean test resources
make test-build     # 🔨 Rebuild test container
```

## 🏗️ CI/CD Testing Explanation

### How CI/CD Tests Work

1. **Trigger**: Push to main/develop or PR creation
2. **Environment**: K3s Kubernetes cluster on self-hosted runners
3. **Isolation**: Each workflow gets a unique namespace
4. **Services**: Real MongoDB, Redis, etc. deployed as pods
5. **Cleanup**: Automatic namespace deletion after completion

### CI Workflow Example

```yaml
# .github/workflows/ci-k3s.yml
jobs:
  test:
    runs-on: self-hosted  # K3s runner with containerd
    services:
      mongodb:
        image: mongo:6.0   # Runs as a Kubernetes pod
    steps:
      - Run tests directly against K8s services
      - No Docker Compose needed
      - Real production-like networking
```

### Key Differences from Local

| Aspect | Local (Docker) | CI/CD (Kubernetes) |
|--------|---------------|--------------------|
| **Container Runtime** | Docker Engine | containerd |
| **Networking** | Bridge network | K8s Service mesh |
| **Image Building** | `docker build` | `nerdctl build` |
| **Service Discovery** | Container names | DNS/Services |
| **Resource Limits** | Optional | Enforced |

## 📁 Test Structure and Organization

```
tests/
├── unit/                 # Fast, isolated unit tests
│   ├── test_models.py   # Data model tests
│   ├── test_utils.py    # Utility function tests
│   └── test_services.py # Business logic tests
│
├── integration/          # Component interaction tests
│   ├── test_api.py      # API endpoint tests
│   ├── test_database.py # Database operations
│   └── test_auth.py     # Authentication flows
│
├── e2e/                  # End-to-end workflows
│   ├── test_user_flow.py    # Complete user journeys
│   └── test_transcription.py # Full transcription pipeline
│
├── fixtures/             # Shared test data
│   ├── audio_samples/   # Test audio files
│   └── mock_data.py     # Reusable test data
│
├── conftest.py          # Pytest configuration and fixtures
└── README.md            # This file
```

### Test Categories

1. **Unit Tests** (`unit/`)
   - Test individual functions/methods
   - No external dependencies
   - Mock external services
   - Run in < 1 second each

2. **Integration Tests** (`integration/`)
   - Test component interactions
   - Use real database connections
   - Test API endpoints
   - May use test doubles for external APIs

3. **E2E Tests** (`e2e/`)
   - Test complete user workflows
   - Use real services
   - Simulate user behavior
   - Longer running (OK to take 10+ seconds)

## ✍️ Writing New Tests Guidelines

### Test File Naming

```python
# Good
test_user_authentication.py
test_audio_processing.py
test_database_operations.py

# Bad
tests.py
user_tests.py
test_stuff.py
```

### Test Structure Template

```python
"""Test module for [component name].

This module tests [brief description of what's being tested].
"""

import pytest
from unittest.mock import Mock, patch

# Import the code you're testing
from src.backend.services import UserService


class TestUserService:
    """Test cases for UserService."""
    
    @pytest.fixture
    def service(self):
        """Create a UserService instance for testing."""
        return UserService()
    
    @pytest.fixture
    def mock_database(self):
        """Create a mock database connection."""
        with patch('src.backend.services.database') as mock_db:
            yield mock_db
    
    def test_create_user_success(self, service, mock_database):
        """Test successful user creation."""
        # Arrange
        user_data = {"email": "test@example.com", "name": "Test User"}
        mock_database.insert_one.return_value = {"_id": "123"}
        
        # Act
        result = service.create_user(user_data)
        
        # Assert
        assert result["_id"] == "123"
        mock_database.insert_one.assert_called_once_with(user_data)
    
    def test_create_user_duplicate_email(self, service, mock_database):
        """Test user creation with duplicate email."""
        # Arrange
        mock_database.insert_one.side_effect = DuplicateKeyError("email")
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            service.create_user({"email": "existing@example.com"})
        assert "already exists" in str(exc.value)
```

### Best Practices

1. **Use descriptive test names**: `test_should_reject_invalid_email_format`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion per test** (when possible)
4. **Use fixtures** for common setup
5. **Mock external dependencies** in unit tests
6. **Use real services** in integration tests
7. **Clean up after tests** (databases, files, etc.)

## 🐛 Debugging Failed Tests

### Local Debugging

```bash
# Run tests with verbose output
docker compose --profile test run --rm test-runner pytest -vvs

# Run with debugger
docker compose --profile test run --rm test-runner pytest --pdb

# Run specific test with full traceback
docker compose --profile test run --rm test-runner \
  pytest tests/unit/test_api.py::TestAPI::test_endpoint -vvs --tb=long

# Check test logs
docker compose --profile test logs test-runner

# Interactive debugging session
docker compose --profile test run --rm test-runner bash
# Then inside container:
python -m pytest tests/unit/test_api.py --pdb
```

### CI/CD Debugging

```bash
# Check workflow logs in GitHub Actions
# Navigate to Actions tab → Select failed workflow → View logs

# Download artifacts
# CI saves test results as artifacts
# Download from Actions → Workflow run → Artifacts

# Re-run with debug logging
# Re-run failed jobs with debug logging enabled
# Click "Re-run jobs" → "Enable debug logging"
```

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Database Connection** | `ConnectionError` | Check MongoDB is running: `docker compose ps` |
| **Port Conflicts** | `Address already in use` | Stop other services: `make dev-stop` |
| **Stale Test Data** | Unexpected test results | Clean database: `make test-cleanup` |
| **Import Errors** | `ModuleNotFoundError` | Rebuild container: `make test-build` |
| **Timeout Errors** | Tests hang | Increase timeout: `pytest --timeout=60` |

## ⚡ Performance Tips

### Speed Up Local Tests

1. **Use test profiles**
   ```bash
   # Run only unit tests (fastest)
   pytest tests/unit -v
   
   # Skip slow tests
   pytest -m "not slow"
   ```

2. **Parallel execution**
   ```bash
   # Run tests in parallel (requires pytest-xdist)
   pytest -n auto
   ```

3. **Reuse containers**
   ```bash
   # Keep containers running between test runs
   make test-watch
   ```

4. **Cache dependencies**
   ```dockerfile
   # Docker layer caching for faster builds
   COPY requirements/test.txt .
   RUN pip install -r test.txt
   COPY . .  # Source code changes don't invalidate pip cache
   ```

### CI/CD Optimization

1. **Matrix testing**: Run tests in parallel across Python versions
2. **Cache dependencies**: Use GitHub Actions cache
3. **Fail fast**: Stop on first failure in CI
4. **Selective testing**: Only run affected tests on PRs

## 🔧 Common Issues and Solutions

### Issue: Tests Pass Locally but Fail in CI

**Symptoms**: Green tests locally, red in GitHub Actions

**Common Causes**:
- Environment variables differences
- Timezone differences
- File path separators (Windows vs Linux)
- Missing dependencies in CI

**Solutions**:
```bash
# Match CI environment locally
docker compose --profile test run --rm \
  -e CI=true \
  -e TZ=UTC \
  test-runner pytest

# Check for hardcoded paths
grep -r "/home/" tests/
grep -r "C:\\" tests/

# Verify all dependencies are in requirements/test.txt
pip freeze > current_deps.txt
diff requirements/test.txt current_deps.txt
```

### Issue: Database Tests Interfering

**Symptoms**: Tests fail when run together but pass individually

**Solutions**:
```python
# Use unique collection names per test
@pytest.fixture
def collection_name():
    return f"test_{uuid.uuid4().hex}"

# Clean up after each test
@pytest.fixture(autouse=True)
def cleanup_database(mongodb_client):
    yield
    mongodb_client.drop_database("speecher_test")

# Use transactions for isolation (MongoDB 4.0+)
@pytest.fixture
def transaction():
    with mongodb_client.start_session() as session:
        with session.start_transaction():
            yield session
            session.abort_transaction()
```

### Issue: Slow Test Suite

**Symptoms**: Tests take > 5 minutes to run

**Solutions**:
```bash
# Profile slow tests
pytest --durations=10

# Mark slow tests
@pytest.mark.slow
def test_heavy_processing():
    pass

# Run without slow tests by default
pytest -m "not slow"

# Use mocks for external services
@patch('requests.post')
def test_api_call(mock_post):
    mock_post.return_value.json.return_value = {"status": "ok"}
```

### Issue: Flaky Tests

**Symptoms**: Tests randomly fail/pass

**Common Causes**:
- Race conditions
- Unordered assertions
- External service dependencies
- Time-dependent code

**Solutions**:
```python
# Fix race conditions with proper waits
from selenium.webdriver.support.wait import WebDriverWait

WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "myElement"))
)

# Use sorted() for order-independent comparisons
assert sorted(result) == sorted(expected)

# Mock time-dependent code
@freeze_time("2024-01-01")
def test_date_logic():
    assert get_current_year() == 2024

# Retry flaky external service tests
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_external_api():
    response = requests.get("https://api.example.com")
    assert response.status_code == 200
```

## 📚 Additional Resources

### Documentation Links

- [Pytest Documentation](https://docs.pytest.org/)
- [Docker Compose Testing](https://docs.docker.com/compose/gettingstarted/)
- [GitHub Actions Testing](https://docs.github.com/en/actions/automating-builds-and-tests)
- [MongoDB Testing Best Practices](https://www.mongodb.com/docs/manual/tutorial/write-scripts-for-the-mongo-shell/)

### Project-Specific Docs

- [Development Workflow](.claude/rules/development-workflow.md)
- [CI/CD Strategy](.claude/rules/ci-cd-kubernetes-strategy.md)
- [Database Management](.claude/rules/database-management-strategy.md)
- [Golden Rules](.claude/rules/golden-rules.md)

### Testing Philosophy

Our testing approach follows these principles:

1. **Tests are Documentation**: Tests show how code should be used
2. **Fast Feedback**: Unit tests run in seconds, integration in minutes
3. **Isolation**: Tests never affect each other
4. **Deterministic**: Same input always produces same output
5. **Meaningful**: Test behavior, not implementation
6. **Maintained**: Broken tests are fixed immediately

Remember: **A test that doesn't run is worse than no test at all.**

## 🎓 Quick Reference Card

```bash
# Daily Testing Workflow
make test              # Run before committing
make test-specific FILE=changed_file.py  # Test your changes
git commit            # Commit when green
git push             # CI runs automatically

# Debugging Workflow
make test            # See failure
make test-watch      # Fix and auto-rerun
docker compose --profile test logs  # Check logs
make test-cleanup    # Clean and retry

# Performance Testing
pytest --durations=10  # Find slow tests
pytest -n auto        # Run in parallel
pytest -m "not slow"  # Skip slow tests
```

---

*Last Updated: 2025-01-11*
*Maintained by: Speecher Development Team*