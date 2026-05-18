# Testing Guide - Dataset Citations

## Overview

This project uses a comprehensive testing strategy with **real controlled data** instead of mocks. We have multiple testing layers to ensure quality and reliability.

## Quick Start

### Run All Tests
```bash
# Fast tests only (< 5 seconds)
pytest tests/ -v

# With coverage report
pytest --cov=dataset_citations --cov-report=term-missing tests/

# Specific test module
pytest tests/test_integration_workflow.py -v
```

### Run End-to-End Workflow
```bash
# Test mode (no API calls, ~30 seconds)
./run_end_to_end_workflow.sh test

# Full production mode (requires API keys, creates branch/PR)
./run_end_to_end_workflow.sh full

# Test CI/CD locally with act (requires Docker)
./run_end_to_end_workflow.sh local-ci-test    # Test workflow
./run_end_to_end_workflow.sh local-ci-update  # Update workflow

# Analysis only (when citations already exist)
./run_full_analysis.sh
```

## Test Categories

### 1. Unit Tests
Fast, focused tests for individual components:
- `test_citation_utils.py` - Citation processing utilities
- `test_dashboard_aggregator.py` - Dashboard data aggregation
- `test_discover_datasets.py` - Dataset discovery logic

### 2. Integration Tests
Tests with controlled real data:
- `test_integration_workflow.py` - Full pipeline with test datasets
- `test_backends_opencite.py` - Live opencite lookups (gated by `RUN_INTEGRATION_TESTS=1`)
- `test_core_opencite_pipeline.py::FetchViaOpenCiteIntegration` - End-to-end orchestrator run
- `test_dashboard_aggregator.py` - Dashboard data aggregation with real citations

### 3. End-to-End Tests
Complete workflow validation:
- `run_end_to_end_workflow.sh` - Three modes for different scenarios
- GitHub Actions workflow tests

## Testing Analysis Modules

The analysis modules can be tested independently:

```bash
# Test theme analysis
python -m dataset_citations.analysis.generate_themes \
    --citations-dir test_citations/json \
    --output-dir test_output/themes

# Test network analysis
python -m dataset_citations.analysis.generate_network \
    --citations-dir test_citations/json \
    --output-dir test_output/network

# Test temporal analysis
python -m dataset_citations.analysis.generate_temporal \
    --citations-dir test_citations/json \
    --output-dir test_output/temporal
```

## Test Data Strategy

We use **controlled real data** instead of mocks:

### Test Datasets
- **ds_small**: 3 citations (2 high-confidence, 1 low)
- **ds_medium**: 8 citations (all high-confidence)
- **ds_empty**: Edge case with no citations
- **ds_lowconf**: 5 citations (all low-confidence)

### Why No Mocks?
1. Real data reveals actual edge cases
2. Validates actual data processing logic
3. Catches integration issues early
4. More maintainable than mock updates

## CI/CD Pipeline

### GitHub Actions Workflows

#### Main Test Workflow (`.github/workflows/test.yml`)
Runs on all PRs and pushes to main:

1. **Lint Stage**
   - Ruff format check
   - Ruff linting
   - Ty type checking (preview; non-failing)

2. **Test Stage**
   - Python 3.13
   - Fast tests only
   - Coverage reporting to Codecov

3. **Integration Stage**
   - Runs on PRs only
   - Tests CLI commands
   - Dashboard generation validation

4. **Security Stage**
   - Trivy security scanning
   - SARIF report generation

### Local Testing with act

Run GitHub Actions locally:
```bash
# Install act
brew install act

# Run workflow
act workflow_dispatch --secret-file .secrets
```

## Performance Benchmarks

| Test Suite | Execution Time | Coverage | API Calls |
|------------|---------------|----------|-----------|
| Unit Tests | < 5 seconds | 75%+ | None |
| Integration Tests | < 30 seconds | 60%+ | None |
| End-to-End (test) | < 1 minute | - | None |
| End-to-End (full) | 1-3 hours | - | Real |
| End-to-End (local-ci-test) | 5-10 min | - | None |
| End-to-End (local-ci-update) | 10-30 min | - | Real |
| Analysis Only | 10-30 min | - | None |

## Writing Tests

### Test Structure
```python
class TestYourFeature(TestCase):
    def setUp(self):
        # Create controlled test data
        self.test_data = create_controlled_data()

    def test_specific_behavior(self):
        # Arrange
        input_data = self.test_data["case1"]

        # Act
        result = your_function(input_data)

        # Assert
        self.assertEqual(result, expected_value)

    def tearDown(self):
        # Clean up test artifacts
        cleanup_test_data()
```

### Best Practices
1. **Use real data**: Create small, controlled datasets
2. **Test edge cases**: Empty data, Unicode, malformed input
3. **Clean up**: Always clean temporary files
4. **Be specific**: One assertion per test when possible
5. **Document intent**: Clear test names and docstrings

## Coverage Goals

- **Overall**: 75% minimum
- **Core modules**: 80%+
- **CLI commands**: 60%+
- **Utilities**: 70%+

Check current coverage:
```bash
pytest --cov=dataset_citations --cov-report=html tests/
open htmlcov/index.html
```

## Debugging Tests

### Verbose Output
```bash
# Show all output
pytest -vv tests/

# Show print statements
pytest -s tests/

# Stop on first failure
pytest -x tests/

# Run specific test
pytest tests/test_file.py::TestClass::test_method
```

### Environment Variables
```bash
# Run slow tests
RUN_SLOW_TESTS=1 pytest tests/

# Run integration tests
RUN_SLOW_INTEGRATION_TESTS=1 pytest tests/
```

## Common Issues

### 1. Test Discovery Issues
```bash
# Ensure package is installed
pip install -e .

# Check Python path
python -c "import dataset_citations; print(dataset_citations.__file__)"
```

### 2. API Key Issues
```bash
# For local testing
export GITHUB_TOKEN=your_token
# Optional, higher opencite rate limits:
# export SEMANTIC_SCHOLAR_API_KEY=your_key
# export OPENALEX_API_KEY=your_key

# For act
echo "GITHUB_TOKEN=your_token" > .secrets
```

### 3. Path Issues
Tests create temporary directories. Ensure you have write permissions:
```bash
# Check temp directory
python -c "import tempfile; print(tempfile.gettempdir())"
```

## Test Output Directories

Test runs create output directories that are gitignored:
- `test_output_*/` - Test mode outputs
- `workflow_output_*/` - Full workflow outputs
- `logs/` - Execution logs
- `.coverage` - Coverage data
- `htmlcov/` - HTML coverage reports

## Continuous Improvement

### Adding New Tests
1. Create test file: `test_<feature>.py`
2. Use controlled real data
3. Test both success and failure cases
4. Update this documentation

### Monitoring Test Health
```bash
# Check test trends
git log --oneline -- tests/

# Find slow tests
pytest --durations=10 tests/

# Check coverage trends
pytest --cov=dataset_citations --cov-report=term tests/
```

## Support

For test-related issues:
1. Check test output carefully
2. Verify environment setup
3. Check recent changes: `git diff tests/`
4. Open an issue with test logs