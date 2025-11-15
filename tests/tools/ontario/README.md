# Ontario Tools Tests

Comprehensive unit tests for Ontario Nature Watch tools.

## Test Coverage

### Agent Router (`tests/agent/test_ontario_router.py`)
- **46 test cases** covering:
  - Query detection logic (Ontario vs global)
  - Word boundary matching for short keywords
  - Context-aware routing
  - Agent selection with force override
  - Agent switching rules
  - Agent descriptions

### Ontario Tools (`tests/tools/ontario/`)

#### `test_pick_ontario_area.py` (6 tests)
- Not found handling
- Single result selection
- Multiple results presentation
- Area type filtering (park/conservation/treaty)
- First Nations territory handling
- Error handling

#### `test_ontario_proximity_search.py` (6 tests)
- No results handling
- Successful proximity search
- Area type filtering
- Default radius handling
- Distance rounding
- Error handling

#### `test_compare_ontario_areas.py` (8 tests)
- Too few/too many areas validation
- Not found handling
- Successful comparison
- Missing areas warning
- Null hectares handling
- Error handling

#### `test_get_ontario_statistics.py` (3 tests)
- Not implemented status
- Metric specification
- Integration next steps documentation

### Ontario Agent (`tests/agent/test_ontario_agent.py`)
- **10 test cases** covering:
  - Prompt generation with Ontario context
  - Williams Treaty cultural sensitivity
  - Current date inclusion
  - Tool usage instructions
  - Agent factory functions
  - Tool availability

## Running Tests

### Prerequisites

Tests require PostgreSQL to be running for database fixture setup:

```bash
# Start PostgreSQL
./scripts/setup-database.sh

# Or manually
sudo service postgresql start  # Linux
brew services start postgresql  # macOS
```

### Run All Ontario Tests

```bash
# All Ontario router tests
pytest tests/agent/test_ontario_router.py -v

# All Ontario tool tests
pytest tests/tools/ontario/ -v

# All Ontario agent tests
pytest tests/agent/test_ontario_agent.py -v

# Everything together
pytest tests/agent/test_ontario_router.py tests/tools/ontario/ tests/agent/test_ontario_agent.py -v
```

### Run Specific Tests

```bash
# Single test class
pytest tests/agent/test_ontario_router.py::TestDetectOntarioQuery -v

# Single test
pytest tests/tools/ontario/test_pick_ontario_area.py::TestPickOntarioArea::test_pick_area_not_found -v

# With coverage
pytest tests/tools/ontario/ --cov=src.tools.ontario --cov-report=html
```

## Test Structure

All tests follow pytest conventions:

- **Fixtures**: Defined in `conftest.py` files
- **Mocking**: Uses `unittest.mock.patch` for database queries
- **Assertions**: Standard pytest assertions
- **Async**: Uses `pytest.mark.asyncio` for async tests

## CI/CD Integration

Tests are designed to run in CI environments:

```yaml
# Example GitHub Actions
- name: Run Ontario Tests
  run: |
    pytest tests/agent/test_ontario_router.py \\
           tests/tools/ontario/ \\
           tests/agent/test_ontario_agent.py \\
           --junit-xml=test-results/ontario-tests.xml
```

## Troubleshooting

### Database Connection Errors

If you see `ConnectionRefusedError`:

1. Ensure PostgreSQL is running: `pg_isready`
2. Check database URL in `.env.local`
3. Verify test database exists: `psql -l | grep test`

### Import Errors

If modules can't be imported:

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv sync
```

## Future Enhancements

- [ ] Add integration tests with real PostGIS queries
- [ ] Add performance benchmarks for proximity searches
- [ ] Add snapshot testing for agent responses
- [ ] Add property-based tests with Hypothesis
- [ ] Add mutation testing for coverage verification
