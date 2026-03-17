"""
AgentCore Configuration for Andhra Kitchen Agent

Configures AWS Bedrock AgentCore with tool registrations for:
- vision_analyzer: Analyzes images to detect Andhra ingredients
- recipe_generator: Generates Andhra-style recipes based on ingredients
- shopping_optimizer: Creates optimized shopping lists with market prices
- reminder_service: Schedules reminders for shopping and cooking

Requirements: 25.1, 25.2
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Import configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.env import Config

# Configure CloudWatch logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# Add CloudWatch handler if running in AWS environment
if Config.ENVIRONMENT != 'local':
    try:
        import watchtower
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group='/aws/andhra-kitchen-agent/agentcore-config',
            stream_name=f'{Config.ENVIRONMENT}-{datetime.now(timezone.utc).strftime("%Y-%m-%d")}'
        )
        cloudwatch_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(cloudwatch_handler)
    except ImportError:
        # watchtower not installed, use console logging only
        pass

# Add console handler for local development
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(console_handler)


class AgentCoreConfig:
    """
    Configuration class for AWS Bedrock AgentCore.
    
    Registers tools and configures the foundation model for the Andhra Kitchen Agent.
    """
    
    # Foundation model configuration
    FOUNDATION_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
    
    # Instruction prompt for the Andhra kitchen assistant
    INSTRUCTION_PROMPT = """You are an expert Andhra Pradesh kitchen assistant helping families manage their kitchen inventory, discover nutritious recipes, and optimize grocery shopping.

Your capabilities:
- Analyze images to detect Andhra ingredients from fridge/pantry photos
- Generate authentic Andhra-style recipes based on available ingredients
- Create optimized shopping lists with Vijayawada market prices
- Schedule reminders for optimal shopping times

Your personality:
- Warm, helpful, and culturally aware
- Expert in Andhra Pradesh cuisine and traditions
- Knowledgeable about local markets and ingredients
- Health-conscious and waste-reduction focused

Important guidelines:
- Always respond in the user's language (English or Telugu)
- Respect dietary preferences and allergies strictly
- Prioritize quick, nutritious recipes (under 30 minutes when possible)
- Consider festival modes for Telugu celebrations
- Provide accurate nutrition information and cost estimates
- Be proactive with helpful reminders

When users upload images, use the vision_analyzer tool to detect ingredients.
When users ask for recipes, use the recipe_generator tool with their preferences.
When users need shopping lists, use the shopping_optimizer tool.
When you identify good shopping opportunities, use the reminder_service tool."""
    
    # Tool definitions with descriptions and parameter schemas
    TOOL_DEFINITIONS = [
        {
            "name": "vision_analyzer",
            "description": "Analyzes images of kitchen inventory (fridge, pantry) to detect Andhra cuisine ingredients. Returns structured inventory with ingredient names, quantities, units, and confidence scores. Use this when users upload photos or mention they have images to share.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "User session identifier for tracking"
                    },
                    "image_id": {
                        "type": "string",
                        "description": "Unique identifier for the image"
                    }
                },
                "required": ["session_id", "image_id"]
            }
        },
        {
            "name": "recipe_generator",
            "description": "Generates authentic Andhra-style recipes based on available ingredients and user preferences. Returns 2-5 recipe options with ingredients, steps, nutrition info, and cost estimates. Respects dietary preferences (low-oil, vegetarian, spice level) and excludes allergens. Use this when users ask for recipe suggestions or what they can cook.",
            "parameters": {
                "type": "object",
                "properties": {
                    "inventory": {
                        "type": "object",
                        "description": "Inventory JSON containing detected ingredients with quantities and confidence scores"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "User session identifier to retrieve preferences and allergies"
                    },
                    "preferences": {
                        "type": "object",
                        "description": "Optional dietary preferences (low_oil, vegetarian, spice_level)",
                        "properties": {
                            "low_oil": {
                                "type": "boolean",
                                "description": "Limit oil to 2 tablespoons per serving"
                            },
                            "vegetarian": {
                                "type": "boolean",
                                "description": "Exclude meat, fish, and eggs"
                            },
                            "spice_level": {
                                "type": "string",
                                "enum": ["mild", "medium", "hot"],
                                "description": "Preferred spice level"
                            }
                        }
                    },
                    "allergies": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of allergens to exclude from recipes"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "te"],
                        "description": "Output language: 'en' for English, 'te' for Telugu"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 2,
                        "maximum": 5,
                        "description": "Number of recipe options to generate (default: 3)"
                    }
                },
                "required": ["inventory", "session_id", "language"]
            }
        },
        {
            "name": "shopping_optimizer",
            "description": "Creates optimized shopping lists by comparing recipe requirements against current inventory. Returns missing ingredients with Vijayawada market prices, optimized quantities to minimize waste, and items grouped by market section. Use this when users select a recipe or ask what they need to buy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "Unique identifier of the selected recipe"
                    },
                    "recipe": {
                        "type": "object",
                        "description": "Complete recipe object with ingredients list"
                    },
                    "inventory": {
                        "type": "object",
                        "description": "Current inventory JSON with available ingredients"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "User session identifier"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "te"],
                        "description": "Output language for shopping list"
                    }
                },
                "required": ["recipe_id", "recipe", "inventory", "session_id"]
            }
        },
        {
            "name": "reminder_service",
            "description": "Schedules proactive reminders for shopping and cooking activities. Use this when you identify price-sensitive ingredients, upcoming festivals, or optimal shopping times. Reminders are delivered when users next log in.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "User session identifier"
                    },
                    "content": {
                        "type": "string",
                        "description": "Reminder message content (e.g., 'Buy fresh curry leaves tomorrow')"
                    },
                    "trigger_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "ISO 8601 timestamp when reminder should trigger"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Explanation for the reminder (e.g., 'Prices are lower on Wednesdays at Gandhi Nagar market')"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Reminder priority level (default: medium)"
                    }
                },
                "required": ["session_id", "content", "trigger_time", "reason"]
            }
        }
    ]
    
    def __init__(self):
        """Initialize AgentCore configuration"""
        self.bedrock_agent = boto3.client(
            service_name='bedrock-agent',
            region_name=Config.BEDROCK_REGION
        )
        
        logger.info(
            f"AgentCoreConfig initialized: "
            f"model={self.FOUNDATION_MODEL}, "
            f"tools={len(self.TOOL_DEFINITIONS)}"
        )
    
    @classmethod
    def get_tool_schemas(cls) -> List[Dict[str, Any]]:
        """
        Get tool schemas in the format required by Bedrock AgentCore.
        
        Requirements: 25.2
        
        Returns:
            List of tool definition dictionaries
        """
        return cls.TOOL_DEFINITIONS
    
    @classmethod
    def get_tool_by_name(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific tool definition by name.
        
        Args:
            tool_name: Name of the tool to retrieve
        
        Returns:
            Tool definition dictionary or None if not found
        """
        for tool in cls.TOOL_DEFINITIONS:
            if tool['name'] == tool_name:
                return tool
        return None
    
    @classmethod
    def validate_tool_parameters(cls, tool_name: str, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate parameters against tool schema.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        tool = cls.get_tool_by_name(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
        
        schema = tool.get('parameters', {})
        required_params = schema.get('required', [])
        properties = schema.get('properties', {})
        
        # Check required parameters
        for param in required_params:
            if param not in parameters:
                return False, f"Missing required parameter: {param}"
        
        # Check parameter types (basic validation)
        for param_name, param_value in parameters.items():
            if param_name not in properties:
                logger.warning(f"Unknown parameter '{param_name}' for tool '{tool_name}'")
                continue
            
            expected_type = properties[param_name].get('type')
            if expected_type == 'string' and not isinstance(param_value, str):
                return False, f"Parameter '{param_name}' must be a string"
            elif expected_type == 'integer' and not isinstance(param_value, int):
                return False, f"Parameter '{param_name}' must be an integer"
            elif expected_type == 'boolean' and not isinstance(param_value, bool):
                return False, f"Parameter '{param_name}' must be a boolean"
            elif expected_type == 'object' and not isinstance(param_value, dict):
                return False, f"Parameter '{param_name}' must be an object"
            elif expected_type == 'array' and not isinstance(param_value, list):
                return False, f"Parameter '{param_name}' must be an array"
        
        return True, None
    
    def create_agent_configuration(self, agent_name: str = "andhra-kitchen-agent") -> Dict[str, Any]:
        """
        Create complete agent configuration for Bedrock AgentCore.
        
        Requirements: 25.1, 25.2
        
        Args:
            agent_name: Name for the agent
        
        Returns:
            Complete agent configuration dictionary
        """
        config = {
            "agentName": agent_name,
            "foundationModel": self.FOUNDATION_MODEL,
            "instruction": self.INSTRUCTION_PROMPT,
            "description": "Multilingual AI-powered kitchen assistant for Andhra Pradesh families",
            "idleSessionTTLInSeconds": 600,  # 10 minutes
            "agentResourceRoleArn": self._get_agent_role_arn(),
            "tools": self._format_tools_for_bedrock()
        }
        
        logger.info(
            f"Created agent configuration: "
            f"name={agent_name}, "
            f"model={self.FOUNDATION_MODEL}, "
            f"tools={len(self.TOOL_DEFINITIONS)}"
        )
        
        return config
    
    def _format_tools_for_bedrock(self) -> List[Dict[str, Any]]:
        """
        Format tool definitions for Bedrock AgentCore API.
        
        Returns:
            List of tool definitions in Bedrock format
        """
        formatted_tools = []
        
        for tool in self.TOOL_DEFINITIONS:
            formatted_tool = {
                "toolSpec": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": {
                        "json": tool["parameters"]
                    }
                }
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools
    
    def _get_agent_role_arn(self) -> str:
        """
        Get or construct the IAM role ARN for the agent.
        
        Returns:
            IAM role ARN string
        """
        # In production, this would be retrieved from environment or AWS
        # For now, construct a placeholder ARN
        account_id = Config.AWS_ACCOUNT_ID if hasattr(Config, 'AWS_ACCOUNT_ID') else "123456789012"
        role_name = "BedrockAgentRole-AndhraKitchen"
        
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    
    def register_agent(self, agent_name: str = "andhra-kitchen-agent") -> Dict[str, Any]:
        """
        Register the agent with Bedrock AgentCore service.
        
        Requirements: 25.1
        
        Args:
            agent_name: Name for the agent
        
        Returns:
            Agent registration response with agent_id and status
        
        Raises:
            ClientError: If registration fails
        """
        logger.info(f"Registering agent with Bedrock: name={agent_name}")
        
        try:
            config = self.create_agent_configuration(agent_name)
            
            # Create agent using Bedrock Agents API
            response = self.bedrock_agent.create_agent(
                agentName=config["agentName"],
                foundationModel=config["foundationModel"],
                instruction=config["instruction"],
                description=config["description"],
                idleSessionTTLInSeconds=config["idleSessionTTLInSeconds"],
                agentResourceRoleArn=config["agentResourceRoleArn"]
            )
            
            agent_id = response['agent']['agentId']
            agent_status = response['agent']['agentStatus']
            
            logger.info(
                f"Agent registered successfully: "
                f"agent_id={agent_id}, "
                f"status={agent_status}"
            )
            
            # Prepare the agent (required before use)
            self._prepare_agent(agent_id)
            
            return {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "status": agent_status,
                "foundation_model": self.FOUNDATION_MODEL,
                "tools_registered": len(self.TOOL_DEFINITIONS)
            }
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                f"Failed to register agent: "
                f"name={agent_name}, "
                f"error_code={error_code}, "
                f"error={str(e)}",
                exc_info=True
            )
            raise
    
    def _prepare_agent(self, agent_id: str) -> None:
        """
        Prepare the agent for use (required step after creation).
        
        Args:
            agent_id: Agent identifier
        
        Raises:
            ClientError: If preparation fails
        """
        logger.info(f"Preparing agent: agent_id={agent_id}")
        
        try:
            response = self.bedrock_agent.prepare_agent(agentId=agent_id)
            
            status = response['agentStatus']
            logger.info(f"Agent prepared: agent_id={agent_id}, status={status}")
        
        except ClientError as e:
            logger.error(
                f"Failed to prepare agent: agent_id={agent_id}, error={str(e)}",
                exc_info=True
            )
            raise
    
    def update_agent_tools(self, agent_id: str) -> Dict[str, Any]:
        """
        Update tool configurations for an existing agent.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Update response
        
        Raises:
            ClientError: If update fails
        """
        logger.info(f"Updating agent tools: agent_id={agent_id}")
        
        try:
            # Update agent with new tool configurations
            response = self.bedrock_agent.update_agent(
                agentId=agent_id,
                instruction=self.INSTRUCTION_PROMPT
            )
            
            # Re-prepare agent after update
            self._prepare_agent(agent_id)
            
            logger.info(f"Agent tools updated successfully: agent_id={agent_id}")
            
            return {
                "agent_id": agent_id,
                "status": response['agent']['agentStatus'],
                "tools_count": len(self.TOOL_DEFINITIONS)
            }
        
        except ClientError as e:
            logger.error(
                f"Failed to update agent tools: agent_id={agent_id}, error={str(e)}",
                exc_info=True
            )
            raise
    
    def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """
        Get information about a registered agent.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Agent information dictionary
        
        Raises:
            ClientError: If retrieval fails
        """
        try:
            response = self.bedrock_agent.get_agent(agentId=agent_id)
            
            agent = response['agent']
            return {
                "agent_id": agent['agentId'],
                "agent_name": agent['agentName'],
                "status": agent['agentStatus'],
                "foundation_model": agent.get('foundationModel'),
                "created_at": agent.get('createdAt'),
                "updated_at": agent.get('updatedAt')
            }
        
        except ClientError as e:
            logger.error(
                f"Failed to get agent info: agent_id={agent_id}, error={str(e)}",
                exc_info=True
            )
            raise
    
    @classmethod
    def print_tool_summary(cls) -> None:
        """Print a summary of all registered tools."""
        print("\n" + "=" * 80)
        print("ANDHRA KITCHEN AGENT - TOOL CONFIGURATION")
        print("=" * 80)
        print(f"\nFoundation Model: {cls.FOUNDATION_MODEL}")
        print(f"Total Tools: {len(cls.TOOL_DEFINITIONS)}")
        print("\n" + "-" * 80)
        
        for idx, tool in enumerate(cls.TOOL_DEFINITIONS, 1):
            print(f"\n{idx}. {tool['name'].upper()}")
            print(f"   Description: {tool['description'][:100]}...")
            
            params = tool['parameters']
            required = params.get('required', [])
            properties = params.get('properties', {})
            
            print(f"   Required Parameters: {', '.join(required)}")
            print(f"   Total Parameters: {len(properties)}")
            
            print("   Parameters:")
            for param_name, param_spec in properties.items():
                param_type = param_spec.get('type', 'unknown')
                is_required = param_name in required
                req_marker = "*" if is_required else " "
                print(f"     {req_marker} {param_name}: {param_type}")
        
        print("\n" + "=" * 80)


if __name__ == "__main__":
    # Example usage and testing
    print("AgentCore Configuration for Andhra Kitchen Agent")
    print("=" * 80)
    
    # Initialize configuration
    config = AgentCoreConfig()
    
    # Print tool summary
    AgentCoreConfig.print_tool_summary()
    
    # Example: Validate tool parameters
    print("\n" + "=" * 80)
    print("PARAMETER VALIDATION EXAMPLES")
    print("=" * 80)
    
    # Valid parameters for vision_analyzer
    valid_params = {
        "session_id": "sess_abc123",
        "image_id": "img_xyz789"
    }
    is_valid, error = AgentCoreConfig.validate_tool_parameters("vision_analyzer", valid_params)
    print(f"\n✓ vision_analyzer with valid params: {is_valid}")
    
    # Invalid parameters (missing required field)
    invalid_params = {
        "session_id": "sess_abc123"
    }
    is_valid, error = AgentCoreConfig.validate_tool_parameters("vision_analyzer", invalid_params)
    print(f"✗ vision_analyzer with missing params: {is_valid}")
    print(f"  Error: {error}")
    
    # Get specific tool schema
    print("\n" + "=" * 80)
    print("TOOL SCHEMA RETRIEVAL")
    print("=" * 80)
    
    recipe_tool = AgentCoreConfig.get_tool_by_name("recipe_generator")
    if recipe_tool:
        print(f"\n✓ Retrieved recipe_generator tool")
        print(f"  Description: {recipe_tool['description'][:80]}...")
        print(f"  Parameters: {len(recipe_tool['parameters']['properties'])} defined")
    
    print("\n" + "=" * 80)
    print("Configuration ready for Bedrock AgentCore integration")
    print("=" * 80)
