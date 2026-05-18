# Testing Guide for Dataset Citations Project

## Quick Test Run (Recommended) 🚀
```bash
# Fast tests for all modules - runs in ~5 seconds
pytest tests/ -v
```

## Results: 21 passed, 17 skipped in 5.05s

## Test Categories

### Fast Tests (5 seconds) ✅
- **Core functionality**: DataFrame operations, data processing
- **Error handling**: Edge cases, invalid inputs
- **Unit tests**: Function validation without external dependencies  
- **Mock-based tests**: API interface validation

### Skipped Tests (for speed) ⏭️
- **Live opencite calls**: hits OpenAlex / Semantic Scholar / PubMed; gated by `RUN_INTEGRATION_TESTS=1`
- **File I/O**: JSON/pickle save/load operations
- **Real data access**: Tests using actual citation files

## Slow Integration Tests (When Needed)
```bash
# Full opencite + sources integration tests
RUN_INTEGRATION_TESTS=1 pytest tests/test_backends_opencite.py tests/test_core_opencite_pipeline.py -v
```

## Environment Setup
```bash
# Optional: raise opencite rate limits
echo "SEMANTIC_SCHOLAR_API_KEY=your_key" > .secrets
echo "OPENALEX_API_KEY=your_key" >> .secrets

# Enable integration tests
export RUN_INTEGRATION_TESTS=1
```

## Performance Improvements Made
- **Aggressive skipping**: All slow operations skipped by default
- **API call consolidation**: Multiple API tests → 1 optional integration test  
- **File I/O optimization**: Skipped save/load operations during regular testing
- **139+ seconds → 5 seconds** (28x faster!) for daily development

## Development Workflow
1. **Regular development**: `pytest tests/` (5 seconds)
2. **Before commits**: `pytest tests/` + manual integration test if needed
3. **Before releases**: Run full integration test suite
4. **Test workflows**: Use `./run_end_to_end_workflow.sh test` for pipeline validation

## End-to-End Workflow Testing
```bash
# Test the complete pipeline with mock data
./run_end_to_end_workflow.sh test

# Test GitHub Actions workflows locally with act
./run_end_to_end_workflow.sh local-ci-test    # Test workflow
./run_end_to_end_workflow.sh local-ci-update  # Update workflow

# Run full pipeline (creates branch and PR)
./run_end_to_end_workflow.sh full
```

## GitHub Actions & CI/CD
- **Automatic testing**: Tests run on every push and PR
- **CPU-only PyTorch**: Faster CI/CD without CUDA dependencies
- **Local testing**: Use `act` to test workflows before pushing
- **Branch protection**: Full and update workflows create feature branches automatically