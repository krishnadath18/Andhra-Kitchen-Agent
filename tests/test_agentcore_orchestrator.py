"""
Unit tests for AgentCore Workflow Orchestrator

Tests workflow orchestration functionality:
- Task decomposition
- Tool execution
- Output propagation
- Response synthesis
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.agentcore_orchestrator import AgentCoreOrchestrator


class TestAgentCoreOrchestrator:
    """Test suite for AgentCoreOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        return AgentCoreOrchestrator()
    
    @pytest.fixture
    def sample_inventory(self):
        """Sample inventory JSON for testing"""
        return {
            "total_items": 3,
            "detection_timestamp": "2024-01-15T10:30:00Z",
            "session_id": "sess_test123",
            "image_id": "img_test456",
            "ingredients": [
                {
                    "ingredient_name": "brinjal",
                    "quantity": 3,
                    "unit": "pieces",
                    "confidence_score": 0.92,
                    "category": "vegetable"
                },
                {
                    "ingredient_name": "rice",
                    "quantity": 2,
                    "unit": "kg",
                    "confidence_score": 0.95,
                    "category": "grain"
                },
                {
                    "ingredient_name": "curry_leaves",
                    "quantity": 1,
                    "unit": "bunches",
                    "confidence_score": 0.88,
                    "category": "spice"
                }
            ]
        }
    
    @pytest.fixture
    def sample_recipe(self):
        """Sample recipe JSON for testing"""
        return {
            "recipe_id": "recipe_test789",
            "name": "Brinjal Curry",
            "ingredients": [
                {"name": "brinjal", "quantity": 3, "unit": "pieces"},
                {"name": "oil", "quantity": 2, "unit": "tablespoons"}
            ],
            "steps": [
                {"step_number": 1, "instruction": "Cut brinjals"}
            ],
            "servings": 4,
            "nutrition": {
                "calories": 120,
                "protein": 2.5,
                "carbohydrates": 15,
                "fat": 6,
                "fiber": 4
            }
        }
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly"""
        assert orchestrator is not None
        assert orchestrator.bedrock_agent_runtime is not None
        assert orchestrator.vision_analyzer is not None
        assert orchestrator.recipe_generator is not None
        assert len(orchestrator.tool_registry) >= 2
        assert 'vision_analyzer' in orchestrator.tool_registry
        assert 'recipe_generator' in orchestrator.tool_registry
    
    def test_decompose_task_image_and_recipe(self, orchestrator):
        """Test task decomposition for image upload + recipe request"""
        user_request = "I uploaded a photo. Can you suggest recipes?"
        session_id = "sess_test123"
        context = {
            'image_uploaded': True,
            'image_id': 'img_test456',
            'language': 'en'
        }
        
        subtasks = orchestrator.decompose_task(user_request, session_id, context)
        
        # Should have 2 subtasks: vision_analyzer and recipe_generator
        assert len(subtasks) == 2
        
        # First subtask should be vision_analyzer
        assert subtasks[0]['tool_name'] == 'vision_analyzer'
        assert subtasks[0]['parameters']['image_id'] == context['image_id']
        assert subtasks[0]['parameters']['session_id'] == session_id
        assert len(subtasks[0]['dependencies']) == 0
        
        # Second subtask should be recipe_generator
        assert subtasks[1]['tool_name'] == 'recipe_generator'
        assert subtasks[1]['parameters']['session_id'] == session_id
        assert subtasks[1]['parameters']['language'] == 'en'
        # Should depend on vision_analyzer
        assert len(subtasks[1]['dependencies']) == 1
        assert subtasks[1]['dependencies'][0] == subtasks[0]['subtask_id']
    
    def test_decompose_task_recipe_only(self, orchestrator):
        """Test task decomposition for recipe request with existing inventory"""
        user_request = "Show me some recipes"
        session_id = "sess_test123"
        context = {
            'inventory': {'total_items': 3, 'ingredients': []},
            'language': 'en'
        }
        
        subtasks = orchestrator.decompose_task(user_request, session_id, context)
        
        # Should have 1 subtask: recipe_generator
        assert len(subtasks) == 1
        assert subtasks[0]['tool_name'] == 'recipe_generator'
        assert subtasks[0]['parameters']['session_id'] == session_id
        assert len(subtasks[0]['dependencies']) == 0
    
    def test_decompose_task_no_action_needed(self, orchestrator):
        """Test task decomposition for request with no clear action"""
        user_request = "Hello, how are you?"
        session_id = "sess_test123"
        context = {}
        
        subtasks = orchestrator.decompose_task(user_request, session_id, context)
        
        # Should have 0 subtasks for greeting
        assert len(subtasks) == 0
    
    def test_call_tool_vision_analyzer(self, orchestrator, sample_inventory):
        """Test calling vision_analyzer tool"""
        with patch.object(orchestrator.kitchen_agent, 'get_image_bytes', return_value=b'fake_image_data') as mock_get_image:
            with patch.object(orchestrator.vision_analyzer, 'analyze_image', return_value=sample_inventory):
                parameters = {
                    'session_id': 'sess_test123',
                    'image_id': 'img_test456'
                }
                
                result = orchestrator.call_tool('vision_analyzer', parameters)
                
                assert 'inventory' in result
                assert result['inventory'] == sample_inventory
                assert result['tool_name'] == 'vision_analyzer'
                assert result['session_id'] == 'sess_test123'
                mock_get_image.assert_called_once_with('sess_test123', 'img_test456')
    
    def test_call_tool_recipe_generator(self, orchestrator, sample_inventory, sample_recipe):
        """Test calling recipe_generator tool"""
        with patch.object(orchestrator.recipe_generator, 'get_user_profile', return_value=({}, [])):
            with patch.object(orchestrator.recipe_generator, 'generate_recipes', return_value=[sample_recipe]):
                parameters = {
                    'inventory': sample_inventory,
                    'session_id': 'sess_test123',
                    'language': 'en',
                    'count': 3
                }
                
                result = orchestrator.call_tool('recipe_generator', parameters)
                
                assert 'recipes' in result
                assert len(result['recipes']) == 1
                assert result['recipes'][0] == sample_recipe
                assert result['tool_name'] == 'recipe_generator'
    
    def test_call_tool_invalid_tool_name(self, orchestrator):
        """Test calling non-existent tool raises error"""
        with pytest.raises(ValueError, match="Tool 'invalid_tool' not found"):
            orchestrator.call_tool('invalid_tool', {})
    
    def test_call_tool_invalid_parameters(self, orchestrator):
        """Test calling tool with invalid parameters raises error"""
        with pytest.raises(ValueError, match="Invalid parameters"):
            # Missing required parameters
            orchestrator.call_tool('vision_analyzer', {'session_id': 'sess_test123'})
    
    def test_execute_workflow_single_tool(self, orchestrator, sample_inventory):
        """Test workflow execution with single tool"""
        with patch.object(orchestrator, 'call_tool', return_value={'inventory': sample_inventory}):
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'vision_analyzer',
                    'parameters': {
                        'session_id': 'sess_test123',
                        'image_id': 'img_test456'
                    },
                    'dependencies': [],
                    'description': 'Analyze image'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            assert result['status'] == 'completed'
            assert result['session_id'] == 'sess_test123'
            assert 'workflow_id' in result
            assert 'subtask_001' in result['subtask_results']
            assert result['subtask_results']['subtask_001']['inventory'] == sample_inventory
            assert 'final_response' in result
            assert result['execution_time_ms'] >= 0
    
    def test_execute_workflow_with_dependencies(self, orchestrator, sample_inventory, sample_recipe):
        """Test workflow execution with dependent subtasks"""
        def mock_call_tool(tool_name, parameters):
            if tool_name == 'vision_analyzer':
                return {'inventory': sample_inventory}
            elif tool_name == 'recipe_generator':
                # Verify inventory was propagated
                assert 'inventory' in parameters
                assert parameters['inventory'] == sample_inventory
                return {'recipes': [sample_recipe]}
            return {}
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'vision_analyzer',
                    'parameters': {
                        'session_id': 'sess_test123',
                        'image_id': 'img_test456'
                    },
                    'dependencies': [],
                    'description': 'Analyze image'
                },
                {
                    'subtask_id': 'subtask_002',
                    'tool_name': 'recipe_generator',
                    'parameters': {
                        'session_id': 'sess_test123',
                        'language': 'en',
                        'count': 3
                    },
                    'dependencies': ['subtask_001'],
                    'description': 'Generate recipes'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            assert result['status'] == 'completed'
            assert 'subtask_001' in result['subtask_results']
            assert 'subtask_002' in result['subtask_results']
            # Verify execution order
            assert result['execution_order'][0]['subtask_id'] == 'subtask_001'
            assert result['execution_order'][1]['subtask_id'] == 'subtask_002'
    
    def test_execute_workflow_with_failure(self, orchestrator):
        """Test workflow execution handles tool failures gracefully"""
        def mock_call_tool(tool_name, parameters):
            if tool_name == 'vision_analyzer':
                raise Exception("Vision analysis failed")
            return {}
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'vision_analyzer',
                    'parameters': {
                        'session_id': 'sess_test123',
                        'image_id': 'img_test456'
                    },
                    'dependencies': [],
                    'description': 'Analyze image'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            assert result['status'] == 'failed'
            assert 'subtask_001' in result['subtask_results']
            assert 'error' in result['subtask_results']['subtask_001']
            assert 'Vision analysis failed' in result['subtask_results']['subtask_001']['error']
    
    def test_synthesize_response_vision_success(self, orchestrator, sample_inventory):
        """Test response synthesis for successful vision analysis"""
        subtask_results = {
            'subtask_001': {
                'inventory': sample_inventory,
                'tool_name': 'vision_analyzer'
            }
        }
        
        subtasks = [
            {
                'subtask_id': 'subtask_001',
                'tool_name': 'vision_analyzer',
                'description': 'Analyze image'
            }
        ]
        
        response = orchestrator.synthesize_response(subtask_results, subtasks)
        
        assert 'Found 3 ingredients' in response
        assert '✅' in response
    
    def test_synthesize_response_recipe_success(self, orchestrator, sample_recipe):
        """Test response synthesis for successful recipe generation"""
        subtask_results = {
            'subtask_001': {
                'recipes': [sample_recipe, sample_recipe],
                'tool_name': 'recipe_generator'
            }
        }
        
        subtasks = [
            {
                'subtask_id': 'subtask_001',
                'tool_name': 'recipe_generator',
                'description': 'Generate recipes'
            }
        ]
        
        response = orchestrator.synthesize_response(subtask_results, subtasks)
        
        assert 'Generated 2' in response
        assert 'recipe' in response.lower()
        assert '✅' in response
    
    def test_synthesize_response_with_error(self, orchestrator):
        """Test response synthesis handles errors"""
        subtask_results = {
            'subtask_001': {
                'error': 'Tool execution failed',
                'tool_name': 'vision_analyzer'
            }
        }
        
        subtasks = [
            {
                'subtask_id': 'subtask_001',
                'tool_name': 'vision_analyzer',
                'description': 'Analyze image'
            }
        ]
        
        response = orchestrator.synthesize_response(subtask_results, subtasks)
        
        assert 'failed' in response.lower()
        assert '⚠️' in response
    
    def test_synthesize_response_empty_results(self, orchestrator):
        """Test response synthesis with no results"""
        response = orchestrator.synthesize_response({}, [])
        
        assert 'processed successfully' in response.lower()
    
    def test_invoke_agent_complete_flow(self, orchestrator, sample_inventory, sample_recipe):
        """Test complete agent invocation flow"""
        def mock_call_tool(tool_name, parameters):
            if tool_name == 'vision_analyzer':
                return {'inventory': sample_inventory}
            elif tool_name == 'recipe_generator':
                return {'recipes': [sample_recipe]}
            return {}
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            user_request = "I uploaded a photo. Can you suggest recipes?"
            context = {
                'image_uploaded': True,
                'image_id': 'img_test456',
                'language': 'en'
            }
            
            result = orchestrator.invoke_agent(user_request, 'sess_test123', context)
            
            assert result['status'] == 'completed'
            assert result['session_id'] == 'sess_test123'
            assert 'workflow_id' in result
            assert 'final_response' in result
            assert 'Found 3 ingredients' in result['final_response']
            assert 'Generated' in result['final_response']
    
    def test_invoke_agent_no_subtasks(self, orchestrator):
        """Test agent invocation with request that generates no subtasks"""
        user_request = "Hello"
        
        result = orchestrator.invoke_agent(user_request, 'sess_test123', {})
        
        assert result['status'] == 'completed'
        assert 'not sure how to help' in result['final_response'].lower()
    
    def test_invoke_agent_with_exception(self, orchestrator):
        """Test agent invocation handles exceptions"""
        with patch.object(orchestrator, 'decompose_task', side_effect=Exception("Decomposition failed")):
            result = orchestrator.invoke_agent("Test request", 'sess_test123', {})
            
            assert result['status'] == 'failed'
            assert 'error' in result
            assert 'Decomposition failed' in result['error']
    
    def test_execute_workflow_parallel_independent_subtasks(self, orchestrator, sample_inventory, sample_recipe):
        """Test parallel execution of independent subtasks"""
        # Create two independent subtasks (no dependencies between them)
        subtasks = [
            {
                'subtask_id': 'subtask_1',
                'tool_name': 'vision_analyzer',
                'parameters': {
                    'session_id': 'sess_test123',
                    'image_id': 'img_test_1'
                },
                'dependencies': []
            },
            {
                'subtask_id': 'subtask_2',
                'tool_name': 'recipe_generator',
                'parameters': {
                    'inventory': sample_inventory,
                    'session_id': 'sess_test123',
                    'language': 'en',
                    'count': 3
                },
                'dependencies': []
            }
        ]
        
        # Mock tool execution
        with patch.object(orchestrator, 'call_tool') as mock_call_tool:
            def call_tool_side_effect(tool_name, params):
                if tool_name == 'vision_analyzer':
                    return {'inventory': sample_inventory}
                elif tool_name == 'recipe_generator':
                    return {'recipes': [sample_recipe]}
                return {}
            
            mock_call_tool.side_effect = call_tool_side_effect
            
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            # Verify parallel execution occurred
            assert result['status'] == 'completed'
            assert result['parallel_execution_count'] == 2
            assert len(result['subtask_results']) == 2
            assert 'subtask_1' in result['subtask_results']
            assert 'subtask_2' in result['subtask_results']
            
            # Verify both tools were called
            assert mock_call_tool.call_count == 2
    
    def test_execute_workflow_parallel_with_sequential_dependency(self, orchestrator, sample_inventory, sample_recipe):
        """Test mixed parallel and sequential execution with dependencies"""
        # Create subtasks: subtask_1 and subtask_2 are independent, subtask_3 depends on subtask_1
        subtasks = [
            {
                'subtask_id': 'subtask_1',
                'tool_name': 'vision_analyzer',
                'parameters': {
                    'session_id': 'sess_test123',
                    'image_id': 'img_test_1'
                },
                'dependencies': []
            },
            {
                'subtask_id': 'subtask_2',
                'tool_name': 'recipe_generator',
                'parameters': {
                    'inventory': sample_inventory,
                    'session_id': 'sess_test123',
                    'language': 'en',
                    'count': 3
                },
                'dependencies': []
            },
            {
                'subtask_id': 'subtask_3',
                'tool_name': 'recipe_generator',
                'parameters': {
                    'session_id': 'sess_test123',
                    'language': 'en',
                    'count': 2
                },
                'dependencies': ['subtask_1']  # Depends on subtask_1
            }
        ]
        
        # Mock tool execution
        with patch.object(orchestrator, 'call_tool') as mock_call_tool:
            def call_tool_side_effect(tool_name, params):
                if tool_name == 'vision_analyzer':
                    return {'inventory': sample_inventory}
                elif tool_name == 'recipe_generator':
                    return {'recipes': [sample_recipe]}
                return {}
            
            mock_call_tool.side_effect = call_tool_side_effect
            
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            # Verify execution
            assert result['status'] == 'completed'
            assert result['parallel_execution_count'] == 2  # Only first two executed in parallel
            assert len(result['subtask_results']) == 3
            
            # Verify execution order: subtask_1 and subtask_2 should execute first (parallel),
            # then subtask_3 (sequential)
            execution_order = result['execution_order']
            assert len(execution_order) == 3
            
            # Find positions of each subtask in execution order
            positions = {item['subtask_id']: idx for idx, item in enumerate(execution_order)}
            
            # subtask_3 should execute after subtask_1
            assert positions['subtask_3'] > positions['subtask_1']
    
    def test_execute_workflow_parallel_error_handling(self, orchestrator, sample_inventory):
        """Test error handling during parallel execution"""
        # Create two independent subtasks where one will fail
        subtasks = [
            {
                'subtask_id': 'subtask_1',
                'tool_name': 'vision_analyzer',
                'parameters': {
                    'session_id': 'sess_test123',
                    'image_id': 'img_test_1'
                },
                'dependencies': []
            },
            {
                'subtask_id': 'subtask_2',
                'tool_name': 'recipe_generator',
                'parameters': {
                    'inventory': sample_inventory,
                    'session_id': 'sess_test123',
                    'language': 'en',
                    'count': 3
                },
                'dependencies': []
            }
        ]
        
        # Mock tool execution with one failure
        with patch.object(orchestrator, 'call_tool') as mock_call_tool:
            def call_tool_side_effect(tool_name, params):
                if tool_name == 'vision_analyzer':
                    raise Exception("Vision analysis failed")
                elif tool_name == 'recipe_generator':
                    return {'recipes': [{'recipe_id': 'test_recipe'}]}
                return {}
            
            mock_call_tool.side_effect = call_tool_side_effect
            
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            # Verify partial completion
            assert result['status'] == 'partial'
            assert len(result['subtask_results']) == 2
            
            # Verify one succeeded and one failed
            assert 'error' in result['subtask_results']['subtask_1']
            assert 'recipes' in result['subtask_results']['subtask_2']
            
            # Verify execution order records the failure
            failed_subtask = next(
                item for item in result['execution_order']
                if item['subtask_id'] == 'subtask_1'
            )
            assert failed_subtask['status'] == 'failed'
    
    def test_execute_workflow_single_subtask_no_parallel(self, orchestrator, sample_inventory):
        """Test that single subtask executes sequentially (no parallel overhead)"""
        subtasks = [
            {
                'subtask_id': 'subtask_1',
                'tool_name': 'vision_analyzer',
                'parameters': {
                    'session_id': 'sess_test123',
                    'image_id': 'img_test_1'
                },
                'dependencies': []
            }
        ]
        
        with patch.object(orchestrator, 'call_tool', return_value={'inventory': sample_inventory}):
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            # Verify no parallel execution for single subtask
            assert result['status'] == 'completed'
            assert result['parallel_execution_count'] == 0
            assert len(result['subtask_results']) == 1
    
    def test_execute_workflow_parallel_output_propagation(self, orchestrator, sample_inventory, sample_recipe):
        """Test that outputs are correctly propagated after parallel execution"""
        # Create workflow: parallel execution of subtask_1 and subtask_2,
        # then subtask_3 depends on both
        subtasks = [
            {
                'subtask_id': 'subtask_1',
                'tool_name': 'vision_analyzer',
                'parameters': {
                    'session_id': 'sess_test123',
                    'image_id': 'img_test_1'
                },
                'dependencies': []
            },
            {
                'subtask_id': 'subtask_2',
                'tool_name': 'vision_analyzer',
                'parameters': {
                    'session_id': 'sess_test123',
                    'image_id': 'img_test_2'
                },
                'dependencies': []
            },
            {
                'subtask_id': 'subtask_3',
                'tool_name': 'recipe_generator',
                'parameters': {
                    'session_id': 'sess_test123',
                    'language': 'en',
                    'count': 3
                },
                'dependencies': ['subtask_1', 'subtask_2']
            }
        ]
        
        with patch.object(orchestrator, 'call_tool') as mock_call_tool:
            def call_tool_side_effect(tool_name, params):
                if tool_name == 'vision_analyzer':
                    return {'inventory': sample_inventory}
                elif tool_name == 'recipe_generator':
                    # Verify inventory was propagated
                    assert 'inventory' in params
                    return {'recipes': [sample_recipe]}
                return {}
            
            mock_call_tool.side_effect = call_tool_side_effect
            
            result = orchestrator.execute_workflow(subtasks, 'sess_test123')
            
            # Verify all subtasks completed
            assert result['status'] == 'completed'
            assert len(result['subtask_results']) == 3
            
            # Verify parallel execution occurred for first two
            assert result['parallel_execution_count'] == 2

    def test_tool_error_structured_format(self, orchestrator):
        """
        Test Requirement 25.6: Tool errors are reported in structured format
        
        Verifies that when a tool fails, the error is captured with:
        - error message
        - error_type
        - tool_name
        - timestamp
        """
        def mock_call_tool(tool_name, parameters):
            raise ValueError("Invalid parameter value")
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'vision_analyzer',
                    'parameters': {'image_id': 'img_test', 'session_id': 'sess_123'},
                    'dependencies': [],
                    'description': 'Test task'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_123')
            
            # Verify structured error format
            assert result['status'] == 'failed'
            error_result = result['subtask_results']['subtask_001']
            assert 'error' in error_result
            assert 'error_type' in error_result
            assert 'tool_name' in error_result
            assert 'timestamp' in error_result
            assert error_result['error_type'] == 'ValueError'
            assert error_result['tool_name'] == 'vision_analyzer'
    
    @patch('src.agentcore_orchestrator.logger')
    def test_tool_error_cloudwatch_logging(self, mock_logger, orchestrator):
        """
        Test Requirement 25.6: Tool errors are logged to CloudWatch
        
        Verifies that tool execution failures are logged with structured details
        """
        def mock_call_tool(tool_name, parameters):
            raise RuntimeError("Tool execution failed")
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'recipe_generator',
                    'parameters': {'session_id': 'sess_123'},
                    'dependencies': [],
                    'description': 'Generate recipe'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_123')
            
            # Verify CloudWatch logging occurred
            assert mock_logger.error.called
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any('RuntimeError' in call for call in error_calls)
            assert any('recipe_generator' in call for call in error_calls)
    
    def test_workflow_continues_with_partial_results(self, orchestrator, sample_inventory, sample_recipe):
        """
        Test Requirement 25.6: Workflow continues with partial results when possible
        
        Verifies that when one tool fails, other independent tools still execute
        """
        def mock_call_tool(tool_name, parameters):
            if tool_name == 'vision_analyzer':
                raise Exception("Vision analysis failed")
            elif tool_name == 'recipe_generator':
                return {'recipes': [sample_recipe]}
            return {}
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            # Two independent subtasks - one should fail, one should succeed
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'vision_analyzer',
                    'parameters': {'image_id': 'img_test', 'session_id': 'sess_123'},
                    'dependencies': [],
                    'description': 'Analyze image'
                },
                {
                    'subtask_id': 'subtask_002',
                    'tool_name': 'recipe_generator',
                    'parameters': {'session_id': 'sess_123', 'inventory': sample_inventory},
                    'dependencies': [],
                    'description': 'Generate recipes'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_123')
            
            # Verify partial completion
            assert result['status'] == 'partial'
            assert len(result['subtask_results']) == 2
            
            # Verify one failed, one succeeded
            assert 'error' in result['subtask_results']['subtask_001']
            assert 'recipes' in result['subtask_results']['subtask_002']
            assert 'error' not in result['subtask_results']['subtask_002']
    
    def test_parallel_execution_error_structured_format(self, orchestrator):
        """
        Test Requirement 25.6: Parallel execution errors use structured format
        
        Verifies that errors in parallel execution are captured with full details
        """
        def mock_call_tool(tool_name, parameters):
            if 'fail' in parameters.get('image_id', ''):
                raise ConnectionError("Network connection failed")
            return {'inventory': {'total_items': 0, 'ingredients': []}}
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            # Two parallel tasks - one fails, one succeeds
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'vision_analyzer',
                    'parameters': {'image_id': 'img_fail', 'session_id': 'sess_123'},
                    'dependencies': [],
                    'description': 'Analyze failing image'
                },
                {
                    'subtask_id': 'subtask_002',
                    'tool_name': 'vision_analyzer',
                    'parameters': {'image_id': 'img_success', 'session_id': 'sess_123'},
                    'dependencies': [],
                    'description': 'Analyze successful image'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_123')
            
            # Verify partial completion with structured errors
            assert result['status'] == 'partial'
            
            # Check failed subtask has structured error
            failed_result = result['subtask_results']['subtask_001']
            assert 'error' in failed_result
            assert 'error_type' in failed_result
            assert failed_result['error_type'] == 'ConnectionError'
            assert 'timestamp' in failed_result
            
            # Check successful subtask has no error
            success_result = result['subtask_results']['subtask_002']
            assert 'error' not in success_result
            assert 'inventory' in success_result
    
    def test_dependent_task_continues_after_independent_failure(self, orchestrator, sample_inventory, sample_recipe):
        """
        Test Requirement 25.6: Dependent tasks continue when their dependencies succeed
        
        Verifies that if an independent task fails but another succeeds,
        tasks depending on the successful one still execute
        """
        def mock_call_tool(tool_name, parameters):
            if tool_name == 'vision_analyzer':
                if 'fail' in parameters.get('image_id', ''):
                    raise Exception("Vision failed")
                return {'inventory': sample_inventory}
            elif tool_name == 'recipe_generator':
                return {'recipes': [sample_recipe]}
            return {}
        
        with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
            subtasks = [
                {
                    'subtask_id': 'subtask_001',
                    'tool_name': 'vision_analyzer',
                    'parameters': {'image_id': 'img_fail', 'session_id': 'sess_123'},
                    'dependencies': [],
                    'description': 'Failing vision task'
                },
                {
                    'subtask_id': 'subtask_002',
                    'tool_name': 'vision_analyzer',
                    'parameters': {'image_id': 'img_success', 'session_id': 'sess_123'},
                    'dependencies': [],
                    'description': 'Successful vision task'
                },
                {
                    'subtask_id': 'subtask_003',
                    'tool_name': 'recipe_generator',
                    'parameters': {'session_id': 'sess_123'},
                    'dependencies': ['subtask_002'],  # Depends only on successful task
                    'description': 'Generate recipes'
                }
            ]
            
            result = orchestrator.execute_workflow(subtasks, 'sess_123')
            
            # Verify partial completion
            assert result['status'] == 'partial'
            assert len(result['subtask_results']) == 3
            
            # Verify subtask_001 failed
            assert 'error' in result['subtask_results']['subtask_001']
            
            # Verify subtask_002 succeeded
            assert 'inventory' in result['subtask_results']['subtask_002']
            
            # Verify subtask_003 executed and succeeded (dependency was met)
            assert 'recipes' in result['subtask_results']['subtask_003']
            assert 'error' not in result['subtask_results']['subtask_003']
    
    @patch('src.agentcore_orchestrator.logger')
    def test_multiple_error_types_logged_correctly(self, mock_logger, orchestrator):
        """
        Test Requirement 25.6: Different error types are logged with correct type information
        
        Verifies that various exception types are captured and logged correctly
        """
        error_types = [ValueError, RuntimeError, ConnectionError, KeyError]
        
        for error_type in error_types:
            mock_logger.reset_mock()
            
            def mock_call_tool(tool_name, parameters):
                raise error_type(f"Test {error_type.__name__}")
            
            with patch.object(orchestrator, 'call_tool', side_effect=mock_call_tool):
                subtasks = [
                    {
                        'subtask_id': 'subtask_001',
                        'tool_name': 'vision_analyzer',
                        'parameters': {'image_id': 'img_test', 'session_id': 'sess_123'},
                        'dependencies': [],
                        'description': 'Test task'
                    }
                ]
                
                result = orchestrator.execute_workflow(subtasks, 'sess_123')
                
                # Verify error type is captured
                error_result = result['subtask_results']['subtask_001']
                assert error_result['error_type'] == error_type.__name__
                
                # Verify CloudWatch logging includes error type
                assert mock_logger.error.called
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                assert any(error_type.__name__ in call for call in error_calls)


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
