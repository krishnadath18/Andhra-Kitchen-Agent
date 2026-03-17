# AgentCore Configuration Guide

## Overview

The `agentcore_config.py` module provides configuration for AWS Bedrock AgentCore integration with the Andhra Kitchen Agent. It registers four specialized tools and configures the Claude 3 Haiku foundation model.

**Requirements Implemented**: 25.1, 25.2

## Architecture

### Foundation Model
- **Model**: `anthropic.claude-3-haiku-20240307-v1:0`
- **Purpose**: Fast, cost-effective chat and orchestration
- **Temperature**: Default (configured by Bedrock)
- **Max Tokens**: Default (configured by Bedrock)

### Registered Tools

#### 1. vision_analyzer
Analyzes kitchen images to detect Andhra ingredients.

**Parameters**:
- `session_id` (required): User session identifier
- `image_id` (required): Unique image identifier

The image bytes are resolved server-side from stored image metadata. Clients must not send `s3_url` or `s3_key` to this tool.

**Returns**: Inventory JSON with detected ingredients, quantities, and confidence scores

**Use Cases**:
- User uploads fridge/pantry photo
- User mentions they have images to share
- System needs to identify available ingredients

#### 2. recipe_generator
Generates Andhra-style recipes based on available ingredients.

**Parameters**:
- `inventory` (required): Inventory JSON with detected ingredients
- `session_id` (required): User session identifier for preferences/allergies
- `language` (required): Output language ('en' or 'te')
- `preferences` (optional): Dietary preferences object
  - `low_oil`: Boolean for low-oil recipes
  - `vegetarian`: Boolean for vegetarian-only
  - `spice_level`: String enum ('mild', 'medium', 'hot')
- `allergies` (optional): Array of allergen strings to exclude
- `count` (optional): Number of recipes (2-5, default: 3)

**Returns**: Array of Recipe JSON objects with ingredients, steps, nutrition, and cost

**Use Cases**:
- User asks "What can I cook?"
- User requests recipe suggestions
- System generates meal options

#### 3. shopping_optimizer
Creates optimized shopping lists with market prices.

**Parameters**:
- `recipe_id` (required): Selected recipe identifier
- `recipe` (required): Complete recipe object
- `inventory` (required): Current inventory JSON
- `session_id` (required): User session identifier
- `language` (optional): Output language

**Returns**: Shopping List JSON with missing ingredients, prices, and market sections

**Use Cases**:
- User selects a recipe
- User asks "What do I need to buy?"
- System generates shopping list

#### 4. reminder_service
Schedules proactive reminders for shopping and cooking.

**Parameters**:
- `session_id` (required): User session identifier
- `content` (required): Reminder message
- `trigger_time` (required): ISO 8601 timestamp
- `reason` (required): Explanation for reminder
- `priority` (optional): String enum ('low', 'medium', 'high')

**Returns**: Reminder confirmation with reminder_id

**Use Cases**:
- Price-sensitive ingredients detected
- Upcoming festival preparation
- Optimal shopping time identified

## Usage

### Basic Configuration

```python
from src.agentcore_config import AgentCoreConfig

# Initialize configuration
config = AgentCoreConfig()

# Get all tool schemas
tools = AgentCoreConfig.get_tool_schemas()
print(f"Registered {len(tools)} tools")

# Get specific tool
vision_tool = AgentCoreConfig.get_tool_by_name('vision_analyzer')
print(f"Tool: {vision_tool['name']}")
print(f"Description: {vision_tool['description']}")
```

### Parameter Validation

```python
# Validate tool parameters before calling
params = {
    'session_id': 'sess_abc123',
    'image_id': 'img_xyz789'
}

is_valid, error = AgentCoreConfig.validate_tool_parameters(
    'vision_analyzer',
    params
)

if is_valid:
    # Call tool with validated parameters
    result = call_tool('vision_analyzer', params)
else:
    print(f"Validation error: {error}")
```

### Agent Registration

```python
# Register agent with Bedrock (requires AWS credentials)
config = AgentCoreConfig()

try:
    result = config.register_agent('andhra-kitchen-agent')
    print(f"Agent registered: {result['agent_id']}")
    print(f"Status: {result['status']}")
    print(f"Tools: {result['tools_registered']}")
except Exception as e:
    print(f"Registration failed: {e}")
```

### Creating Agent Configuration

```python
# Create complete agent configuration
config = AgentCoreConfig()
agent_config = config.create_agent_configuration('my-agent')

print(f"Agent Name: {agent_config['agentName']}")
print(f"Model: {agent_config['foundationModel']}")
print(f"Tools: {len(agent_config['tools'])}")
```

## Tool Schema Format

Each tool follows this JSON Schema format:

```json
{
  "name": "tool_name",
  "description": "What the tool does and when to use it",
  "parameters": {
    "type": "object",
    "properties": {
      "param_name": {
        "type": "string|integer|boolean|object|array",
        "description": "Parameter description",
        "enum": ["value1", "value2"],  // Optional
        "minimum": 1,  // Optional for integers
        "maximum": 10  // Optional for integers
      }
    },
    "required": ["param1", "param2"]
  }
}
```

## Instruction Prompt

The agent uses a comprehensive instruction prompt that defines:

1. **Role**: Expert Andhra Pradesh kitchen assistant
2. **Capabilities**: Image analysis, recipe generation, shopping optimization, reminders
3. **Personality**: Warm, helpful, culturally aware
4. **Guidelines**:
   - Respond in user's language (English/Telugu)
   - Respect dietary preferences and allergies
   - Prioritize quick, nutritious recipes
   - Consider festival modes
   - Provide accurate information

## Error Handling

### Parameter Validation Errors

```python
is_valid, error = AgentCoreConfig.validate_tool_parameters(tool_name, params)

if not is_valid:
    # Handle validation error
    if "Missing required parameter" in error:
        # Add missing parameter
        pass
    elif "must be a" in error:
        # Fix parameter type
        pass
```

### Tool Not Found

```python
tool = AgentCoreConfig.get_tool_by_name('unknown_tool')

if tool is None:
    print("Tool not found")
    # List available tools
    available = [t['name'] for t in AgentCoreConfig.TOOL_DEFINITIONS]
    print(f"Available tools: {', '.join(available)}")
```

## Testing

Run the test suite to verify configuration:

```bash
python -m pytest tests/test_agentcore_config.py -v
```

Or using unittest:

```bash
python tests/test_agentcore_config.py
```

### Test Coverage

The test suite covers:
- Foundation model configuration
- Instruction prompt validation
- Tool count and names
- Tool schema validation for all 4 tools
- Parameter validation (valid/invalid cases)
- Agent configuration generation
- Bedrock API format conversion
- Complete workflow tests for each tool

## Integration with Kitchen Agent Core

The AgentCore configuration integrates with `KitchenAgentCore`:

```python
from src.kitchen_agent_core import KitchenAgentCore
from src.agentcore_config import AgentCoreConfig

# Initialize components
agent_core = KitchenAgentCore()
agentcore_config = AgentCoreConfig()

# Get tool schemas for AgentCore
tools = agentcore_config.get_tool_schemas()

# Use in agent invocation
# (Actual invocation handled by Bedrock AgentCore runtime)
```

## CloudWatch Logging

The module logs to CloudWatch when running in AWS:

- **Log Group**: `/aws/andhra-kitchen-agent/agentcore-config`
- **Stream Name**: `{environment}-{date}`
- **Log Level**: Configured via `Config.LOG_LEVEL`

**Logged Events**:
- Configuration initialization
- Agent registration attempts
- Tool validation results
- Parameter validation errors
- Agent preparation status

## Configuration Validation

Validate the configuration before deployment:

```python
from src.agentcore_config import AgentCoreConfig

# Print tool summary
AgentCoreConfig.print_tool_summary()

# Verify all tools have required fields
for tool in AgentCoreConfig.TOOL_DEFINITIONS:
    assert 'name' in tool
    assert 'description' in tool
    assert 'parameters' in tool
    assert 'required' in tool['parameters']
    print(f"✓ {tool['name']} validated")
```

## Best Practices

1. **Always validate parameters** before calling tools
2. **Use type hints** when working with tool parameters
3. **Handle validation errors** gracefully with user-friendly messages
4. **Log tool invocations** for debugging and monitoring
5. **Test tool schemas** after any modifications
6. **Keep descriptions clear** and actionable for the LLM
7. **Document parameter constraints** in descriptions

## Troubleshooting

### Issue: Tool not found
**Solution**: Check tool name spelling, use `get_tool_schemas()` to list available tools

### Issue: Parameter validation fails
**Solution**: Check required parameters, verify parameter types match schema

### Issue: Agent registration fails
**Solution**: Verify AWS credentials, check IAM role permissions, ensure Bedrock access

### Issue: CloudWatch logs not appearing
**Solution**: Check `ENVIRONMENT` config, verify CloudWatch permissions, install `watchtower`

## Future Enhancements

Potential improvements for future iterations:

1. **Dynamic tool registration**: Add/remove tools at runtime
2. **Tool versioning**: Support multiple versions of tools
3. **Tool dependencies**: Define dependencies between tools
4. **Custom validators**: Add custom validation logic per tool
5. **Tool metrics**: Track tool usage and performance
6. **Tool caching**: Cache tool results for common queries
7. **Tool fallbacks**: Define fallback tools when primary fails

## References

- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Claude 3 Model Documentation](https://docs.anthropic.com/claude/docs/models-overview)
- [JSON Schema Specification](https://json-schema.org/)
- [Andhra Kitchen Agent Design Document](../design.md)

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Run test suite to verify configuration
3. Review tool schemas for parameter requirements
4. Consult design document for requirements
