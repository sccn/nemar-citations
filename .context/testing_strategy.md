# Testing Strategy (Revised)

## Core Principle: Test As We Build
Fix the automation first, then test each component as it's implemented. No testing of hypothetical code.

## Test Dataset Approach

### Controlled Test Dataset
- **Dataset:** Use a real dataset with ~10 citations (e.g., a smaller dataset from OpenNeuro)
- **Purpose:** Rapid testing without expensive API calls
- **Method:**
  1. Create snapshot with known citations
  2. Manually reduce by 1-2 citations
  3. Run pipeline - should find missing citations
  4. Verify all outputs (JSON, dashboard, etc.)

### Test Data Structure

```text
tests/
├── test_data/
│   ├── controlled_dataset/
│   │   ├── ds_test_001_citations.json  # Modified with fewer citations
│   │   └── ds_test_001_expected.json   # Expected after fetch
│   └── snapshots/
│       └── dashboard_snapshot.html     # Expected dashboard output
├── integration/
│   └── test_full_pipeline.py
└── unit/
    ├── test_citation_fetch.py
    ├── test_dashboard_generation.py
    └── test_confidence_scoring.py
```

## Phased Testing Approach

### Phase 1: Test Automation Fix
- Create minimal test for dashboard generation
- Validate workflow runs end-to-end
- Use single controlled dataset

### Phase 2: Test Each Module
- As we modularize, add unit tests
- Test extraction doesn't break functionality
- Incremental coverage growth

### Phase 3: Comprehensive Test Suite
- Multiple test datasets (edge cases)
- Full integration tests
- CI/CD pipeline activation
- 75%+ code coverage target

## Key Testing Rules
- **No Mocks:** Real data only
- **Test Working Code:** Fix first, test second
- **Incremental:** Add tests as we build
- **Fast Feedback:** <2 minutes for basic tests
- **Atomic:** Test one thing per test
