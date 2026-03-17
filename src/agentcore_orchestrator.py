"""
AgentCore Workflow Orchestrator for Andhra Kitchen Agent

Implements workflow orchestration using AWS Bedrock Agents Runtime API:
- Decomposes user requests into subtasks
- Executes tools in sequence with parameter passing
- Propagates outputs between subtasks
- Synthesizes final responses from all subtask outputs

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import json
import time
import uuid
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Import configuration and tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.env import Config
from src.agentcore_config import AgentCoreConfig
from src.kitchen_agent_core import KitchenAgentCore
from src.vision_analyzer import VisionAnalyzer
from src.recipe_generator import RecipeGenerator

# Configure CloudWatch logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# Add CloudWatch handler if running in AWS environment
if Config.ENVIRONMENT != 'local':
    try:
        import watchtower
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group='/aws/andhra-kitchen-agent/agentcore-orchestrator',
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


class AgentCoreOrchestrator:
    """
    Orchestrates workflows using Bedrock AgentCore.
    
    Responsibilities:
    - Decompose user requests into subtasks
    - Execute tools in optimal order
    - Pass outputs between subtasks
    - Synthesize final responses
    """
    
    def __init__(self, agent_id: Optional[str] = None, agent_alias_id: Optional[str] = None):
        """
        Initialize AgentCore orchestrator.
        
        Args:
            agent_id: Bedrock Agent ID (optional, will use from config if not provided)
            agent_alias_id: Bedrock Agent Alias ID (optional, will use from config if not provided)
        """
        self.bedrock_agent_runtime = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name=Config.BEDROCK_REGION
        )
        
        # Initialize DynamoDB for memory management
        self.dynamodb = boto3.resource('dynamodb', region_name=Config.AWS_REGION)
        self.sessions_table = self.dynamodb.Table(Config.SESSIONS_TABLE)
        
        self.agent_id = agent_id or getattr(Config, 'BEDROCK_AGENT_ID', None)
        self.agent_alias_id = agent_alias_id or getattr(Config, 'BEDROCK_AGENT_ALIAS_ID', 'TSTALIASID')
        
        # Configuration for memory management
        self.session_ttl_days = Config.SESSION_TTL_DAYS  # 7 days
        
        # Initialize tool implementations
        self.kitchen_agent = KitchenAgentCore()
        self.vision_analyzer = VisionAnalyzer()
        self.recipe_generator = RecipeGenerator()
        # Note: shopping_optimizer and reminder_service will be added in later tasks
        
        # Tool registry maps tool names to implementation functions
        self.tool_registry = {
            'vision_analyzer': self._execute_vision_analyzer,
            'recipe_generator': self._execute_recipe_generator,
            # 'shopping_optimizer': self._execute_shopping_optimizer,  # Task 7
            # 'reminder_service': self._execute_reminder_service,  # Task 8
        }
        
        logger.info(
            f"AgentCoreOrchestrator initialized: "
            f"agent_id={self.agent_id}, "
            f"agent_alias_id={self.agent_alias_id}, "
            f"registered_tools={len(self.tool_registry)}, "
            f"sessions_table={Config.SESSIONS_TABLE}"
        )
    def __init__(self, agent_id: Optional[str] = None, agent_alias_id: Optional[str] = None):
        """
        Initialize AgentCore orchestrator.

        Args:
            agent_id: Bedrock Agent ID (optional, will use from config if not provided)
            agent_alias_id: Bedrock Agent Alias ID (optional, will use from config if not provided)
        """
        self.bedrock_agent_runtime = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name=Config.BEDROCK_REGION
        )

        # Initialize DynamoDB for memory management
        self.dynamodb = boto3.resource('dynamodb', region_name=Config.AWS_REGION)
        self.sessions_table = self.dynamodb.Table(Config.SESSIONS_TABLE)

        self.agent_id = agent_id or getattr(Config, 'BEDROCK_AGENT_ID', None)
        self.agent_alias_id = agent_alias_id or getattr(Config, 'BEDROCK_AGENT_ALIAS_ID', 'TSTALIASID')

        # Configuration for memory management
        self.session_ttl_days = Config.SESSION_TTL_DAYS  # 7 days

        # Initialize tool implementations
        self.kitchen_agent = KitchenAgentCore()
        self.vision_analyzer = VisionAnalyzer()
        self.recipe_generator = RecipeGenerator()
        # Note: shopping_optimizer and reminder_service will be added in later tasks

        # Tool registry maps tool names to implementation functions
        self.tool_registry = {
            'vision_analyzer': self._execute_vision_analyzer,
            'recipe_generator': self._execute_recipe_generator,
            # 'shopping_optimizer': self._execute_shopping_optimizer,  # Task 7
            # 'reminder_service': self._execute_reminder_service,  # Task 8
        }

        logger.info(
            f"AgentCoreOrchestrator initialized: "
            f"agent_id={self.agent_id}, "
            f"agent_alias_id={self.agent_alias_id}, "
            f"registered_tools={len(self.tool_registry)}, "
            f"sessions_table={Config.SESSIONS_TABLE}"
        )
    
    def decompose_task(self, user_request: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Decompose user request into subtasks using Bedrock AgentCore.
        
        Requirements: 6.1, 6.2
        
        Args:
            user_request: User's natural language request
            session_id: User session identifier
            context: Optional context (inventory, preferences, etc.)
        
        Returns:
            List of subtask dictionaries with:
                - subtask_id: Unique identifier
                - tool_name: Tool to execute
                - parameters: Tool parameters
                - dependencies: List of subtask_ids this depends on
                - description: Human-readable description
        
        Note:
            In a full AgentCore implementation, Bedrock would automatically decompose
            the task. For this implementation, we use a simplified approach where
            we analyze the request and context to determine required tools.
        """
        start_time = time.time()
        
        logger.info(
            f"Decomposing task: session_id={session_id}, "
            f"request_length={len(user_request)}, "
            f"has_context={context is not None}"
        )
        
        subtasks = []
        context = context or {}
        
        # Analyze request to determine required tools
        request_lower = user_request.lower()
        
        # Check if image analysis is needed
        if context.get('image_uploaded') or 'image' in request_lower or 'photo' in request_lower:
            if context.get('image_id'):
                subtasks.append({
                    'subtask_id': f"subtask_{uuid.uuid4().hex[:8]}",
                    'tool_name': 'vision_analyzer',
                    'parameters': {
                        'session_id': session_id,
                        'image_id': context['image_id']
                    },
                    'dependencies': [],
                    'description': 'Analyze uploaded image to detect ingredients'
                })
        
        # Check if recipe generation is needed
        if any(keyword in request_lower for keyword in ['recipe', 'cook', 'make', 'prepare', 'dish']):
            # Recipe generation depends on having inventory
            vision_subtask_id = subtasks[0]['subtask_id'] if subtasks else None
            
            recipe_params = {
                'session_id': session_id,
                'language': context.get('language', 'en'),
                'count': context.get('recipe_count', 3)
            }
            
            # If we have inventory from context or will get it from vision analysis
            if context.get('inventory'):
                recipe_params['inventory'] = context['inventory']
            
            subtasks.append({
                'subtask_id': f"subtask_{uuid.uuid4().hex[:8]}",
                'tool_name': 'recipe_generator',
                'parameters': recipe_params,
                'dependencies': [vision_subtask_id] if vision_subtask_id else [],
                'description': 'Generate Andhra-style recipes based on available ingredients'
            })
        
        # Check if shopping list is needed
        if any(keyword in request_lower for keyword in ['shop', 'buy', 'purchase', 'need', 'missing']):
            # Shopping depends on having a recipe
            recipe_subtask_id = next((s['subtask_id'] for s in subtasks if s['tool_name'] == 'recipe_generator'), None)
            
            if recipe_subtask_id or context.get('recipe_id'):
                subtasks.append({
                    'subtask_id': f"subtask_{uuid.uuid4().hex[:8]}",
                    'tool_name': 'shopping_optimizer',
                    'parameters': {
                        'session_id': session_id,
                        'recipe_id': context.get('recipe_id'),
                        'language': context.get('language', 'en')
                    },
                    'dependencies': [recipe_subtask_id] if recipe_subtask_id else [],
                    'description': 'Generate optimized shopping list with market prices'
                })
        
        elapsed_time = time.time() - start_time
        logger.info(
            f"Task decomposition complete: session_id={session_id}, "
            f"subtasks={len(subtasks)}, "
            f"elapsed_time={elapsed_time:.2f}s"
        )
        
        return subtasks
    
    async def _execute_subtask_async(
        self,
        subtask: Dict[str, Any],
        subtask_results: Dict[str, Any],
        workflow_id: str
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """
        Execute a single subtask asynchronously.
        
        Args:
            subtask: Subtask dictionary
            subtask_results: Dictionary of completed subtask results
            workflow_id: Workflow identifier for logging
        
        Returns:
            Tuple of (subtask_id, tool_output, execution_info)
        """
        subtask_id = subtask['subtask_id']
        tool_name = subtask['tool_name']
        parameters = subtask['parameters'].copy()
        
        logger.info(
            f"Executing subtask (async): workflow_id={workflow_id}, "
            f"subtask_id={subtask_id}, tool={tool_name}"
        )
        
        # Propagate outputs from dependencies
        for dep_id in subtask['dependencies']:
            if dep_id and dep_id in subtask_results:
                dep_output = subtask_results[dep_id]
                
                # Propagate inventory from vision_analyzer to recipe_generator
                if tool_name == 'recipe_generator' and 'inventory' in dep_output:
                    parameters['inventory'] = dep_output['inventory']
                
                # Propagate recipe from recipe_generator to shopping_optimizer
                if tool_name == 'shopping_optimizer' and 'recipes' in dep_output:
                    # Use first recipe if not specified
                    if not parameters.get('recipe_id') and dep_output['recipes']:
                        parameters['recipe'] = dep_output['recipes'][0]
                        parameters['recipe_id'] = dep_output['recipes'][0].get('recipe_id')
                
                # Propagate inventory to shopping_optimizer
                if tool_name == 'shopping_optimizer' and 'inventory' in dep_output:
                    parameters['inventory'] = dep_output['inventory']
        
        # Execute the tool (run in thread pool since call_tool is synchronous)
        try:
            loop = asyncio.get_running_loop()
            tool_output = await loop.run_in_executor(
                None,
                self.call_tool,
                tool_name,
                parameters
            )
            
            execution_info = {
                'subtask_id': subtask_id,
                'tool_name': tool_name,
                'status': 'completed'
            }
            
            logger.info(
                f"Subtask completed (async): workflow_id={workflow_id}, "
                f"subtask_id={subtask_id}, tool={tool_name}"
            )
            
            return subtask_id, tool_output, execution_info
        
        except Exception as e:
            # Structured error reporting for Bedrock (Requirement 25.6)
            error_type = type(e).__name__
            error_timestamp = datetime.now(timezone.utc).isoformat() + "Z"
            
            error_details = {
                'error': str(e),
                'error_type': error_type,
                'tool_name': tool_name,
                'subtask_id': subtask_id,
                'workflow_id': workflow_id,
                'timestamp': error_timestamp,
                'parameters': list(parameters.keys())
            }
            
            logger.error(
                f"Subtask failed (async): workflow_id={workflow_id}, "
                f"subtask_id={subtask_id}, tool={tool_name}, "
                f"error_type={error_type}, error={str(e)}",
                exc_info=True,
                extra={'error_details': error_details}
            )
            
            # Return structured error output for Bedrock
            tool_output = {
                'error': str(e),
                'error_type': error_type,
                'tool_name': tool_name,
                'timestamp': error_timestamp
            }
            
            execution_info = {
                'subtask_id': subtask_id,
                'tool_name': tool_name,
                'status': 'failed',
                'error': str(e),
                'error_type': error_type,
                'timestamp': error_timestamp
            }
            
            return subtask_id, tool_output, execution_info

    def execute_workflow(
        self,
        subtasks: List[Dict[str, Any]],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute workflow by running subtasks in dependency order with parallel execution.
        
        Independent subtasks (no dependencies between them) are executed in parallel
        using asyncio for improved performance.
        
        Requirements: 6.3, 6.4, 6.5, 25.5
        
        Args:
            subtasks: List of subtask dictionaries from decompose_task()
            session_id: User session identifier
        
        Returns:
            WorkflowResult dictionary with:
                - workflow_id: Unique workflow identifier
                - session_id: User session identifier
                - subtask_results: Dict mapping subtask_id to tool output
                - final_response: Synthesized response from all outputs
                - execution_time_ms: Total execution time
                - status: 'completed', 'partial', or 'failed'
                - parallel_execution_count: Number of subtasks executed in parallel
        """
        start_time = time.time()
        workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
        
        logger.info(
            f"Starting workflow execution: workflow_id={workflow_id}, "
            f"session_id={session_id}, subtasks={len(subtasks)}"
        )
        
        # Track subtask results for output propagation
        subtask_results = {}
        execution_order = []
        parallel_execution_count = 0
        
        try:
            # Execute subtasks in dependency order with parallel execution
            executed = set()
            
            while len(executed) < len(subtasks):
                # Find subtasks whose dependencies are satisfied
                ready_subtasks = [
                    st for st in subtasks
                    if st['subtask_id'] not in executed
                    and all(dep in executed or dep is None for dep in st['dependencies'])
                ]
                
                if not ready_subtasks:
                    # Circular dependency or error
                    logger.error(
                        f"No ready subtasks found: workflow_id={workflow_id}, "
                        f"executed={len(executed)}, total={len(subtasks)}"
                    )
                    break
                
                # Execute ready subtasks in parallel if there are multiple
                if len(ready_subtasks) > 1:
                    logger.info(
                        f"Executing {len(ready_subtasks)} independent subtasks in parallel: "
                        f"workflow_id={workflow_id}"
                    )
                    parallel_execution_count += len(ready_subtasks)
                    
                    # Create async tasks for all ready subtasks
                    async def execute_parallel_subtasks():
                        tasks = [
                            self._execute_subtask_async(subtask, subtask_results, workflow_id)
                            for subtask in ready_subtasks
                        ]
                        return await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Run the async tasks
                    try:
                        loop = asyncio.new_event_loop()
                        try:
                            asyncio.set_event_loop(loop)
                            results = loop.run_until_complete(execute_parallel_subtasks())
                        finally:
                            asyncio.set_event_loop(None)
                            loop.close()
                        
                        # Process results
                        for result in results:
                            if isinstance(result, Exception):
                                logger.error(
                                    f"Parallel execution exception: workflow_id={workflow_id}, "
                                    f"error={str(result)}",
                                    exc_info=result
                                )
                                continue
                            
                            subtask_id, tool_output, execution_info = result
                            subtask_results[subtask_id] = tool_output
                            execution_order.append(execution_info)
                            executed.add(subtask_id)
                    
                    except Exception as e:
                        logger.error(
                            f"Parallel execution failed: workflow_id={workflow_id}, "
                            f"error={str(e)}",
                            exc_info=True
                        )
                        # Fall back to sequential execution for these subtasks
                        for subtask in ready_subtasks:
                            if subtask['subtask_id'] not in executed:
                                subtask_id = subtask['subtask_id']
                                tool_name = subtask['tool_name']
                                parameters = subtask['parameters'].copy()
                                
                                try:
                                    tool_output = self.call_tool(tool_name, parameters)
                                    subtask_results[subtask_id] = tool_output
                                    execution_order.append({
                                        'subtask_id': subtask_id,
                                        'tool_name': tool_name,
                                        'status': 'completed'
                                    })
                                    executed.add(subtask_id)
                                except Exception as tool_error:
                                    # Structured error reporting for fallback execution (Requirement 25.6)
                                    error_type = type(tool_error).__name__
                                    error_timestamp = datetime.now(timezone.utc).isoformat() + "Z"
                                    
                                    error_details = {
                                        'error': str(tool_error),
                                        'error_type': error_type,
                                        'tool_name': tool_name,
                                        'subtask_id': subtask_id,
                                        'workflow_id': workflow_id,
                                        'timestamp': error_timestamp,
                                        'context': 'fallback_sequential_execution'
                                    }
                                    
                                    logger.error(
                                        f"Fallback execution failed: workflow_id={workflow_id}, "
                                        f"subtask_id={subtask_id}, tool={tool_name}, "
                                        f"error_type={error_type}, error={str(tool_error)}",
                                        exc_info=True,
                                        extra={'error_details': error_details}
                                    )
                                    
                                    subtask_results[subtask_id] = {
                                        'error': str(tool_error),
                                        'error_type': error_type,
                                        'tool_name': tool_name,
                                        'timestamp': error_timestamp
                                    }
                                    execution_order.append({
                                        'subtask_id': subtask_id,
                                        'tool_name': tool_name,
                                        'status': 'failed',
                                        'error': str(tool_error),
                                        'error_type': error_type,
                                        'timestamp': error_timestamp
                                    })
                                    executed.add(subtask_id)
                
                else:
                    # Single subtask - execute sequentially
                    subtask = ready_subtasks[0]
                    subtask_id = subtask['subtask_id']
                    tool_name = subtask['tool_name']
                    parameters = subtask['parameters'].copy()
                    
                    logger.info(
                        f"Executing subtask: workflow_id={workflow_id}, "
                        f"subtask_id={subtask_id}, tool={tool_name}"
                    )
                    
                    # Propagate outputs from dependencies
                    for dep_id in subtask['dependencies']:
                        if dep_id and dep_id in subtask_results:
                            dep_output = subtask_results[dep_id]
                            
                            # Propagate inventory from vision_analyzer to recipe_generator
                            if tool_name == 'recipe_generator' and 'inventory' in dep_output:
                                parameters['inventory'] = dep_output['inventory']
                            
                            # Propagate recipe from recipe_generator to shopping_optimizer
                            if tool_name == 'shopping_optimizer' and 'recipes' in dep_output:
                                # Use first recipe if not specified
                                if not parameters.get('recipe_id') and dep_output['recipes']:
                                    parameters['recipe'] = dep_output['recipes'][0]
                                    parameters['recipe_id'] = dep_output['recipes'][0].get('recipe_id')
                            
                            # Propagate inventory to shopping_optimizer
                            if tool_name == 'shopping_optimizer' and 'inventory' in dep_output:
                                parameters['inventory'] = dep_output['inventory']
                    
                    # Execute the tool
                    try:
                        tool_output = self.call_tool(tool_name, parameters)
                        subtask_results[subtask_id] = tool_output
                        execution_order.append({
                            'subtask_id': subtask_id,
                            'tool_name': tool_name,
                            'status': 'completed'
                        })
                        executed.add(subtask_id)
                        
                        logger.info(
                            f"Subtask completed: workflow_id={workflow_id}, "
                            f"subtask_id={subtask_id}, tool={tool_name}"
                        )
                    
                    except Exception as e:
                        # Structured error reporting for Bedrock (Requirement 25.6)
                        error_type = type(e).__name__
                        error_timestamp = datetime.now(timezone.utc).isoformat() + "Z"
                        
                        error_details = {
                            'error': str(e),
                            'error_type': error_type,
                            'tool_name': tool_name,
                            'subtask_id': subtask_id,
                            'workflow_id': workflow_id,
                            'timestamp': error_timestamp,
                            'parameters': list(parameters.keys())
                        }
                        
                        logger.error(
                            f"Subtask failed: workflow_id={workflow_id}, "
                            f"subtask_id={subtask_id}, tool={tool_name}, "
                            f"error_type={error_type}, error={str(e)}",
                            exc_info=True,
                            extra={'error_details': error_details}
                        )
                        
                        # Store structured error for Bedrock
                        subtask_results[subtask_id] = {
                            'error': str(e),
                            'error_type': error_type,
                            'tool_name': tool_name,
                            'timestamp': error_timestamp
                        }
                        execution_order.append({
                            'subtask_id': subtask_id,
                            'tool_name': tool_name,
                            'status': 'failed',
                            'error': str(e),
                            'error_type': error_type,
                            'timestamp': error_timestamp
                        })
                        executed.add(subtask_id)
            
            # Synthesize final response
            final_response = self.synthesize_response(subtask_results, subtasks)
            
            # Determine overall status
            failed_count = sum(1 for result in subtask_results.values() if 'error' in result)
            if failed_count == 0:
                status = 'completed'
            elif failed_count < len(subtasks):
                status = 'partial'
            else:
                status = 'failed'
            
            elapsed_time = time.time() - start_time
            
            logger.info(
                f"Workflow execution complete: workflow_id={workflow_id}, "
                f"session_id={session_id}, status={status}, "
                f"execution_time_ms={int(elapsed_time * 1000)}, "
                f"parallel_execution_count={parallel_execution_count}"
            )
            
            return {
                'workflow_id': workflow_id,
                'session_id': session_id,
                'subtask_results': subtask_results,
                'execution_order': execution_order,
                'final_response': final_response,
                'execution_time_ms': int(elapsed_time * 1000),
                'status': status,
                'parallel_execution_count': parallel_execution_count,
                'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
            }
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Workflow execution failed: workflow_id={workflow_id}, "
                f"session_id={session_id}, error={str(e)}",
                exc_info=True
            )
            
            return {
                'workflow_id': workflow_id,
                'session_id': session_id,
                'subtask_results': subtask_results,
                'execution_order': execution_order,
                'final_response': f"Workflow execution failed: {str(e)}",
                'execution_time_ms': int(elapsed_time * 1000),
                'status': 'failed',
                'error': str(e),
                'parallel_execution_count': parallel_execution_count,
                'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
            }
    
    def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.

        Requirements: 6.3, 25.6

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters

        Returns:
            Tool output dictionary

        Raises:
            ValueError: If tool not found or parameters invalid
            Exception: If tool execution fails
        """
        logger.info(
            f"Calling tool: tool_name={tool_name}, "
            f"parameters={list(parameters.keys())}"
        )

        # Validate tool exists
        if tool_name not in self.tool_registry:
            error_msg = f"Tool '{tool_name}' not found in registry"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate parameters against schema
        is_valid, error = AgentCoreConfig.validate_tool_parameters(tool_name, parameters)
        if not is_valid:
            logger.error(
                f"Invalid parameters for tool '{tool_name}': {error}"
            )
            raise ValueError(f"Invalid parameters: {error}")

        # Execute tool with comprehensive error handling (Requirement 25.6)
        try:
            tool_function = self.tool_registry[tool_name]
            result = tool_function(parameters)

            logger.info(
                f"Tool execution successful: tool_name={tool_name}"
            )

            return result

        except ValueError as e:
            # Parameter validation errors
            error_details = {
                'error': str(e),
                'error_type': 'validation_error',
                'tool_name': tool_name,
                'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
            }
            logger.error(
                f"Tool validation error: tool_name={tool_name}, "
                f"error={str(e)}",
                exc_info=True
            )
            raise ValueError(str(e))

        except Exception as e:
            # All other execution errors - log to CloudWatch with structured format
            error_type = type(e).__name__
            error_details = {
                'error': str(e),
                'error_type': error_type,
                'tool_name': tool_name,
                'timestamp': datetime.now(timezone.utc).isoformat() + "Z",
                'parameters': list(parameters.keys())  # Log parameter keys only for privacy
            }

            logger.error(
                f"Tool execution failed: tool_name={tool_name}, "
                f"error_type={error_type}, error={str(e)}, "
                f"parameters={list(parameters.keys())}",
                exc_info=True,
                extra={'error_details': error_details}
            )
            raise


    
    def synthesize_response(
        self,
        subtask_results: Dict[str, Dict[str, Any]],
        subtasks: List[Dict[str, Any]]
    ) -> str:
        """
        Synthesize final response from all subtask outputs.
        
        Requirements: 6.5
        
        Args:
            subtask_results: Dict mapping subtask_id to tool output
            subtasks: Original subtask list for context
        
        Returns:
            Synthesized natural language response
        """
        logger.info(
            f"Synthesizing response from {len(subtask_results)} subtask results"
        )
        
        response_parts = []
        
        # Process results in execution order
        for subtask in subtasks:
            subtask_id = subtask['subtask_id']
            tool_name = subtask['tool_name']
            
            if subtask_id not in subtask_results:
                continue
            
            result = subtask_results[subtask_id]
            
            # Handle errors
            if 'error' in result:
                description = subtask.get('description', tool_name)
                response_parts.append(
                    f"⚠️ {description} failed: {result['error']}"
                )
                continue
            
            # Synthesize based on tool type
            if tool_name == 'vision_analyzer':
                inventory = result.get('inventory', {})
                total_items = inventory.get('total_items', 0)
                if total_items > 0:
                    response_parts.append(
                        f"✅ Found {total_items} ingredients in your image!"
                    )
                else:
                    response_parts.append(
                        "ℹ️ No ingredients detected in the image. Please ensure the photo is clear and well-lit."
                    )
            
            elif tool_name == 'recipe_generator':
                recipes = result.get('recipes', [])
                if recipes:
                    recipe_count = len(recipes)
                    response_parts.append(
                        f"✅ Generated {recipe_count} delicious Andhra-style recipe{'s' if recipe_count > 1 else ''}!"
                    )
                    
                    # Add recipe names
                    recipe_names = [r.get('name', 'Unnamed Recipe') for r in recipes[:3]]
                    response_parts.append(
                        f"Recipes: {', '.join(recipe_names)}"
                    )
                else:
                    response_parts.append(
                        "ℹ️ Could not generate recipes with the available ingredients."
                    )
            
            elif tool_name == 'shopping_optimizer':
                shopping_list = result.get('shopping_list', {})
                items = shopping_list.get('items', [])
                total_cost = shopping_list.get('total_cost', 0)
                if items:
                    response_parts.append(
                        f"✅ Shopping list ready! {len(items)} items needed (₹{total_cost:.2f} estimated)"
                    )
                else:
                    response_parts.append(
                        "✅ You have all ingredients needed!"
                    )
            
            elif tool_name == 'reminder_service':
                reminder = result.get('reminder', {})
                if reminder:
                    response_parts.append(
                        f"⏰ Reminder scheduled: {reminder.get('content', 'Reminder set')}"
                    )
        
        # Combine all parts
        if response_parts:
            final_response = "\n\n".join(response_parts)
        else:
            final_response = "Request processed successfully."
        
        logger.info(
            f"Response synthesis complete: length={len(final_response)}"
        )
        
        return final_response
    
    # Tool implementation methods
    
    def _execute_vision_analyzer(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute vision_analyzer tool.
        
        Args:
            parameters: Tool parameters (session_id, image_id)
        
        Returns:
            Dictionary with 'inventory' key containing Inventory JSON
        """
        session_id = parameters['session_id']
        image_id = parameters['image_id']
        
        logger.info(
            f"Executing vision_analyzer: session_id={session_id}, "
            f"image_id={image_id}"
        )
        
        image_data = self.kitchen_agent.get_image_bytes(session_id, image_id)
        
        # Analyze image
        inventory = self.vision_analyzer.analyze_image(
            image_data=image_data,
            session_id=session_id,
            image_id=image_id
        )
        
        return {
            'inventory': inventory,
            'tool_name': 'vision_analyzer',
            'session_id': session_id,
            'image_id': image_id
        }
    
    def _execute_recipe_generator(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute recipe_generator tool.
        
        Args:
            parameters: Tool parameters (inventory, session_id, language, etc.)
        
        Returns:
            Dictionary with 'recipes' key containing list of Recipe JSON objects
        """
        inventory = parameters.get('inventory')
        session_id = parameters['session_id']
        language = parameters.get('language', 'en')
        count = parameters.get('count', 3)
        
        logger.info(
            f"Executing recipe_generator: session_id={session_id}, "
            f"language={language}, count={count}"
        )
        
        # Get user preferences and allergies from session
        preferences, allergies = self.recipe_generator.get_user_profile(session_id)
        
        # Override with explicit parameters if provided
        if 'preferences' in parameters:
            preferences.update(parameters['preferences'])
        if 'allergies' in parameters:
            allergies = parameters['allergies']
        
        # Generate recipes
        recipes = self.recipe_generator.generate_recipes(
            inventory=inventory,
            preferences=preferences,
            allergies=allergies,
            language=language,
            count=count
        )
        
        return {
            'recipes': recipes,
            'tool_name': 'recipe_generator',
            'session_id': session_id,
            'language': language,
            'count': len(recipes)
        }
    
    def invoke_agent(
        self,
        user_request: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        High-level method to invoke the agent with a user request.
        
        This method:
        1. Decomposes the request into subtasks
        2. Executes the workflow
        3. Returns the complete workflow result
        
        Args:
            user_request: User's natural language request
            session_id: User session identifier
            context: Optional context (image URLs, preferences, etc.)
        
        Returns:
            Complete workflow result dictionary
        """
        logger.info(
            f"Invoking agent: session_id={session_id}, "
            f"request_length={len(user_request)}"
        )
        
        try:
            # Decompose task
            subtasks = self.decompose_task(user_request, session_id, context)
            
            if not subtasks:
                logger.warning(
                    f"No subtasks generated: session_id={session_id}"
                )
                return {
                    'workflow_id': f"workflow_{uuid.uuid4().hex[:12]}",
                    'session_id': session_id,
                    'subtask_results': {},
                    'execution_order': [],
                    'final_response': "I'm not sure how to help with that. Could you please rephrase your request?",
                    'execution_time_ms': 0,
                    'status': 'completed',
                    'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
                }
            
            # Execute workflow
            workflow_result = self.execute_workflow(subtasks, session_id)
            
            return workflow_result
        
        except Exception as e:
            logger.error(
                f"Agent invocation failed: session_id={session_id}, "
                f"error={str(e)}",
                exc_info=True
            )
            
            return {
                'workflow_id': f"workflow_{uuid.uuid4().hex[:12]}",
                'session_id': session_id,
                'subtask_results': {},
                'execution_order': [],
                'final_response': f"I encountered an error: {str(e)}. Please try again.",
                'execution_time_ms': 0,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
            }
    
    # Memory Management Methods
    
    def store_memory(
        self,
        session_id: str,
        key: str,
        value: Any,
        data_type: str = 'preferences',
        high_priority: bool = False
    ) -> bool:
        """
        Store data in DynamoDB memory store with session association.
        
        Requirements: 7.1, 7.2, 7.3, 7.7, 16.3
        
        Args:
            session_id: User session identifier
            key: Memory key (e.g., 'low_oil', 'peanuts')
            value: Value to store (can be any JSON-serializable type)
            data_type: Type of data ('preferences' or 'allergies')
            high_priority: Flag for high priority items (used for allergies)
        
        Returns:
            True if storage successful, False otherwise
        
        Note:
            - Preferences are stored with data_type='preferences'
            - Allergies are stored with data_type='allergies' and high_priority=True
            - TTL is set to 7 days from current time
        """
        start_time = time.time()
        
        logger.info(
            f"Storing memory: session_id={session_id}, "
            f"key={key}, data_type={data_type}, "
            f"high_priority={high_priority}"
        )
        
        try:
            # Calculate TTL (7 days from now)
            ttl = int((datetime.now(timezone.utc) + timedelta(days=self.session_ttl_days)).timestamp())
            
            # Prepare item for storage
            item = {
                'session_id': session_id,
                'data_type': data_type,
                'key': key,
                'value': value,
                'high_priority': high_priority,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'expiry_timestamp': ttl
            }
            
            # Store in DynamoDB
            self.sessions_table.put_item(Item=item)
            
            elapsed_time = time.time() - start_time
            logger.info(
                f"Memory stored successfully: session_id={session_id}, "
                f"key={key}, data_type={data_type}, "
                f"ttl={ttl}, elapsed_time={elapsed_time:.3f}s"
            )
            
            return True
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                f"DynamoDB error storing memory: session_id={session_id}, "
                f"key={key}, error_code={error_code}",
                exc_info=True
            )
            return False
        
        except Exception as e:
            logger.error(
                f"Unexpected error storing memory: session_id={session_id}, "
                f"key={key}, error={str(e)}",
                exc_info=True
            )
            return False
    
    def retrieve_memory(
        self,
        session_id: str,
        key: Optional[str] = None,
        data_type: Optional[str] = None
    ) -> Any:
        """
        Retrieve data from DynamoDB memory store.
        
        Requirements: 7.1, 7.2, 7.3, 7.7, 16.3
        
        Args:
            session_id: User session identifier
            key: Optional specific key to retrieve
            data_type: Optional data type filter ('preferences' or 'allergies')
        
        Returns:
            - If key is specified: Returns the value for that key, or None if not found
            - If key is None: Returns dict of all items for the data_type
            - If both key and data_type are None: Returns all memory items for session
        
        Examples:
            retrieve_memory('sess_123', 'low_oil', 'preferences')  # Returns True/False
            retrieve_memory('sess_123', data_type='allergies')     # Returns list of allergies
            retrieve_memory('sess_123')                            # Returns all memory items
        """
        start_time = time.time()
        
        logger.info(
            f"Retrieving memory: session_id={session_id}, "
            f"key={key}, data_type={data_type}"
        )
        
        try:
            if key and data_type:
                # Retrieve specific item
                response = self.sessions_table.get_item(
                    Key={
                        'session_id': session_id,
                        'data_type': data_type
                    }
                )
                
                item = response.get('Item')
                if item and item.get('key') == key:
                    value = item.get('value')
                    logger.info(
                        f"Memory retrieved: session_id={session_id}, "
                        f"key={key}, found={value is not None}"
                    )
                    return value
                else:
                    logger.info(
                        f"Memory not found: session_id={session_id}, "
                        f"key={key}, data_type={data_type}"
                    )
                    return None
            
            elif data_type:
                # Query all items of a specific data_type
                response = self.sessions_table.query(
                    KeyConditionExpression='session_id = :sid AND begins_with(data_type, :dtype)',
                    ExpressionAttributeValues={
                        ':sid': session_id,
                        ':dtype': data_type
                    }
                )
                
                items = response.get('Items', [])
                
                # Build result dict
                result = {}
                for item in items:
                    item_key = item.get('key')
                    if item_key:
                        result[item_key] = item.get('value')
                
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Memory retrieved: session_id={session_id}, "
                    f"data_type={data_type}, count={len(result)}, "
                    f"elapsed_time={elapsed_time:.3f}s"
                )
                
                return result
            
            else:
                # Query all memory items for session
                response = self.sessions_table.query(
                    KeyConditionExpression='session_id = :sid',
                    ExpressionAttributeValues={
                        ':sid': session_id
                    }
                )
                
                items = response.get('Items', [])
                
                # Organize by data_type
                result = {}
                for item in items:
                    dtype = item.get('data_type')
                    item_key = item.get('key')
                    
                    if dtype and item_key:
                        if dtype not in result:
                            result[dtype] = {}
                        result[dtype][item_key] = item.get('value')
                
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Memory retrieved: session_id={session_id}, "
                    f"data_types={list(result.keys())}, "
                    f"elapsed_time={elapsed_time:.3f}s"
                )
                
                return result
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                f"DynamoDB error retrieving memory: session_id={session_id}, "
                f"key={key}, data_type={data_type}, error_code={error_code}",
                exc_info=True
            )
            return None
        
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving memory: session_id={session_id}, "
                f"key={key}, data_type={data_type}, error={str(e)}",
                exc_info=True
            )
            return None


if __name__ == "__main__":
    # Example usage and testing
    print("AgentCore Workflow Orchestrator for Andhra Kitchen Agent")
    print("=" * 80)
    
    # Initialize orchestrator
    orchestrator = AgentCoreOrchestrator()
    
    print(f"\n✅ Orchestrator initialized")
    print(f"   Registered tools: {list(orchestrator.tool_registry.keys())}")
    
    # Example 1: Decompose a recipe request
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Task Decomposition")
    print("=" * 80)
    
    user_request = "I uploaded a photo of my fridge. Can you suggest some recipes?"
    context = {
        'image_uploaded': True,
        'image_id': 'img_test123',
        'language': 'en'
    }
    
    subtasks = orchestrator.decompose_task(user_request, 'sess_test123', context)
    
    print(f"\nUser Request: {user_request}")
    print(f"Decomposed into {len(subtasks)} subtasks:")
    for idx, subtask in enumerate(subtasks, 1):
        print(f"\n{idx}. {subtask['description']}")
        print(f"   Tool: {subtask['tool_name']}")
        print(f"   Dependencies: {subtask['dependencies']}")
        print(f"   Parameters: {list(subtask['parameters'].keys())}")
    
    # Example 2: Tool validation
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Tool Parameter Validation")
    print("=" * 80)
    
    valid_params = {
        'session_id': 'sess_test123',
        'image_id': 'img_test123'
    }
    
    is_valid, error = AgentCoreConfig.validate_tool_parameters('vision_analyzer', valid_params)
    print(f"\n✓ vision_analyzer with valid params: {is_valid}")
    
    invalid_params = {
        'image_id': 'img_test123'
        # Missing required parameters
    }
    
    is_valid, error = AgentCoreConfig.validate_tool_parameters('vision_analyzer', invalid_params)
    print(f"✗ vision_analyzer with invalid params: {is_valid}")
    print(f"  Error: {error}")
    
    print("\n" + "=" * 80)
    print("Orchestrator ready for workflow execution")
    print("=" * 80)
