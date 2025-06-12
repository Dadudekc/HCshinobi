# HCshinobi Test Suite Documentation

## 🏗️ Test Architecture

### Core Components

1. **InteractionTrace** (`tests/utils/interaction_trace.py`)
   - Tracks Discord interaction history
   - Validates response sequences
   - Handles embed and content matching
   - Supports async operation verification

2. **Mock Services**
   - `character_system`: Character data management
   - `mission_system`: Mission state and progression
   - `training_system`: Training cooldowns and rewards

3. **Test Categories**
   - `e2e/`: End-to-end command flows
   - `unit/`: Individual component tests
   - `integration/`: Service interaction tests

## 🎯 Testing Patterns

### 1. Async Command Testing

```python
@pytest.mark.asyncio
async def test_command_example(mock_bot, mock_interaction):
    # Setup
    mock_bot.services.character_system.get_character = AsyncMock(return_value=character)
    
    # Execute
    await command.callback(command, mock_interaction)
    
    # Verify
    mock_interaction.response.defer.assert_awaited_once()
    mock_interaction.followup.send.assert_awaited_once()
```

### 2. Response Validation

```python
# Text Response
assert "Expected message" in sent_message
assert kwargs.get('ephemeral') is True

# Embed Response
assert sent_embed.title == "Expected Title"
assert "Expected description" in sent_embed.description
assert "Expected value" in sent_embed.fields[0].value
```

### 3. Service Mocking

```python
@pytest.fixture
def mock_service():
    service = Mock(spec=ServiceClass)
    service.method = AsyncMock(return_value=expected_value)
    return service
```

## 🔄 Command Response Flow

### Standard Flow
1. Defer response (ephemeral + thinking)
2. Process command logic
3. Send followup with result

### Error Flow
1. Send immediate error response
2. No defer needed
3. Ephemeral error message

## 📝 Response Format Conventions

### 1. Text Responses
- Error messages: Plain text, ephemeral
- Success confirmations: Plain text, ephemeral
- Status updates: Plain text, ephemeral

### 2. Embed Responses
- Character info: Rich embed with fields
- Mission board: Embed with mission list
- Training status: Embed with progress
- Rewards: Embed with reward breakdown

## 🛠️ Fixture Construction

### 1. Bot Fixture
```python
@pytest.fixture
def mock_bot():
    bot = Mock(spec=Bot)
    bot.services = Mock()
    return bot
```

### 2. Interaction Fixture
```python
@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.user = AsyncMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction
```

## ⚠️ Common Pitfalls

1. **Async/Await**
   - Always await async mocks
   - Use `@pytest.mark.asyncio`
   - Mock with `AsyncMock`

2. **Service Injection**
   - Inject services into `bot.services`
   - Mock all required methods
   - Use proper return types

3. **Response Validation**
   - Check both content and embed
   - Verify ephemeral flag
   - Validate field structure

## 🧪 Test Categories

### 1. Command Tests
- Basic command execution
- Parameter validation
- Error handling
- Success paths

### 2. Service Tests
- Data persistence
- State management
- Business logic
- Edge cases

### 3. Integration Tests
- Service interactions
- Command chains
- State transitions
- Error propagation

## 🔍 Best Practices

1. **Test Organization**
   - Group related tests
   - Use descriptive names
   - Follow AAA pattern (Arrange, Act, Assert)

2. **Mock Management**
   - Reset mocks between tests
   - Use appropriate mock types
   - Verify mock calls

3. **Response Validation**
   - Check complete response structure
   - Validate all fields
   - Test error cases

4. **Async Testing**
   - Use proper async fixtures
   - Await all async calls
   - Handle async errors

## 📈 Test Coverage

### Required Coverage Areas
1. Command execution paths
2. Error handling
3. State transitions
4. Service interactions
5. Response formatting

### Coverage Goals
- Line coverage: >90%
- Branch coverage: >85%
- Function coverage: >95%

## 🔄 Continuous Integration

### Test Execution
```bash
# Run all tests
python -m pytest tests/

# Run specific category
python -m pytest tests/e2e/
python -m pytest tests/unit/

# Run with coverage
python -m pytest --cov=HCshinobi tests/
```

### CI Pipeline
1. Run unit tests
2. Run integration tests
3. Run e2e tests
4. Generate coverage report
5. Validate coverage thresholds

## 🚀 Future Improvements

1. **Test Automation**
   - Auto-generate test cases
   - Parameterized test data
   - Test case management

2. **Coverage Enhancement**
   - Edge case coverage
   - Error path coverage
   - Performance testing

3. **Documentation**
   - Auto-document test cases
   - Generate test reports
   - Track test metrics 