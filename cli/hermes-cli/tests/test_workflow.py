"""Unit tests for workflow execution engine."""

import pytest
import yaml
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from jsonschema import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow import WorkflowEngine, WORKFLOW_SCHEMA


class TestWorkflowEngineInit:
    """Tests for WorkflowEngine initialization."""

    def test_init(self):
        """Test workflow engine initialization."""
        mock_client = Mock()
        engine = WorkflowEngine(api_client=mock_client)

        assert engine.api_client == mock_client
        assert engine.step_outputs == {}
        assert engine.completed_steps == set()


class TestLoadWorkflow:
    """Tests for workflow template loading and validation."""

    def test_load_valid_workflow(self, tmp_path):
        """Test loading a valid workflow template."""
        # Create valid workflow YAML
        workflow_content = """
name: Test Workflow
description: A test workflow
version: "1.0"
steps:
  - name: step1
    tool: nmap
    args: ["-sV", "target"]
"""
        workflow_file = tmp_path / "test-workflow.yml"
        workflow_file.write_text(workflow_content)

        engine = WorkflowEngine(api_client=Mock())
        workflow = engine.load_workflow(workflow_file)

        assert workflow['name'] == 'Test Workflow'
        assert workflow['description'] == 'A test workflow'
        assert workflow['version'] == '1.0'
        assert len(workflow['steps']) == 1
        assert workflow['steps'][0]['name'] == 'step1'

    def test_load_workflow_missing_required_field(self, tmp_path):
        """Test loading workflow missing required field."""
        # Missing 'steps' field
        workflow_content = """
name: Test Workflow
description: A test workflow
version: 1.0
"""
        workflow_file = tmp_path / "invalid-workflow.yml"
        workflow_file.write_text(workflow_content)

        engine = WorkflowEngine(api_client=Mock())

        with pytest.raises(ValueError, match="Invalid workflow schema"):
            engine.load_workflow(workflow_file)

    def test_load_workflow_invalid_step_structure(self, tmp_path):
        """Test loading workflow with invalid step structure."""
        # Step missing 'tool' field
        workflow_content = """
name: Test Workflow
description: A test workflow
version: 1.0
steps:
  - name: step1
    args: ["-sV"]
"""
        workflow_file = tmp_path / "invalid-step.yml"
        workflow_file.write_text(workflow_content)

        engine = WorkflowEngine(api_client=Mock())

        with pytest.raises(ValueError, match="Invalid workflow schema"):
            engine.load_workflow(workflow_file)

    def test_load_workflow_with_optional_fields(self, tmp_path):
        """Test loading workflow with all optional fields."""
        workflow_content = """
name: Complete Workflow
description: Workflow with all fields
version: "2.0"
variables:
  target: "{{target}}"
  rate: "{{rate|default:1000}}"
steps:
  - name: scan
    tool: masscan
    args: ["-p80", "{{target}}"]
    depends_on: []
    condition: "true"
    timeout: 3600
    on_error: continue
"""
        workflow_file = tmp_path / "complete-workflow.yml"
        workflow_file.write_text(workflow_content)

        engine = WorkflowEngine(api_client=Mock())
        workflow = engine.load_workflow(workflow_file)

        assert 'variables' in workflow
        assert workflow['steps'][0]['timeout'] == 3600
        assert workflow['steps'][0]['on_error'] == 'continue'

    def test_load_workflow_file_not_found(self):
        """Test loading non-existent workflow file."""
        engine = WorkflowEngine(api_client=Mock())

        with pytest.raises(FileNotFoundError):
            engine.load_workflow(Path("/nonexistent/workflow.yml"))


class TestRenderVariables:
    """Tests for Jinja2 variable rendering."""

    def test_render_simple_variables(self):
        """Test rendering simple variable substitution."""
        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test {{env}}',
            'description': 'Scan {{target}}',
            'steps': [
                {
                    'name': 'scan',
                    'tool': 'nmap',
                    'args': ['-sV', '{{target}}']
                }
            ]
        }

        variables = {'env': 'production', 'target': '192.168.1.1'}
        rendered = engine.render_variables(workflow, variables)

        assert rendered['name'] == 'Test production'
        assert rendered['description'] == 'Scan 192.168.1.1'
        assert rendered['steps'][0]['args'][1] == '192.168.1.1'

    def test_render_with_default_filter(self):
        """Test rendering with Jinja2 default filter."""
        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test',
            'steps': [
                {
                    'name': 'scan',
                    'tool': 'masscan',
                    'args': ['--rate', '{{rate|default("10000")}}']
                }
            ]
        }

        # Don't provide 'rate' variable
        variables = {}
        rendered = engine.render_variables(workflow, variables)

        # Should use default value
        assert rendered['steps'][0]['args'][1] == '10000'

    def test_render_multiple_variables_in_string(self):
        """Test rendering multiple variables in single string."""
        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': '{{type}} scan of {{target}}',
            'steps': []
        }

        variables = {'type': 'Full', 'target': 'example.com'}
        rendered = engine.render_variables(workflow, variables)

        assert rendered['name'] == 'Full scan of example.com'

    def test_render_preserves_non_string_types(self):
        """Test that rendering preserves integers and booleans."""
        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test',
            'steps': [
                {
                    'name': 'step1',
                    'tool': 'nmap',
                    'args': ['-p', '{{port}}'],
                    'timeout': 3600
                }
            ]
        }

        variables = {'port': '80'}
        rendered = engine.render_variables(workflow, variables)

        # Timeout should remain integer
        assert rendered['steps'][0]['timeout'] == 3600
        assert isinstance(rendered['steps'][0]['timeout'], int)


class TestCheckDependencies:
    """Tests for dependency checking."""

    def test_check_dependencies_all_met(self):
        """Test dependency check when all dependencies are met."""
        engine = WorkflowEngine(api_client=Mock())
        engine.completed_steps = {'step1', 'step2'}

        step = {'name': 'step3', 'depends_on': ['step1', 'step2']}

        assert engine.check_dependencies(step) is True

    def test_check_dependencies_not_met(self):
        """Test dependency check when dependencies not met."""
        engine = WorkflowEngine(api_client=Mock())
        engine.completed_steps = {'step1'}

        step = {'name': 'step3', 'depends_on': ['step1', 'step2']}

        assert engine.check_dependencies(step) is False

    def test_check_dependencies_no_dependencies(self):
        """Test dependency check with no dependencies."""
        engine = WorkflowEngine(api_client=Mock())

        step = {'name': 'step1'}

        assert engine.check_dependencies(step) is True

    def test_check_dependencies_empty_list(self):
        """Test dependency check with empty dependency list."""
        engine = WorkflowEngine(api_client=Mock())

        step = {'name': 'step1', 'depends_on': []}

        assert engine.check_dependencies(step) is True


class TestEvaluateCondition:
    """Tests for condition evaluation."""

    def test_evaluate_condition_none(self):
        """Test condition evaluation with None."""
        engine = WorkflowEngine(api_client=Mock())

        assert engine.evaluate_condition(None) is True

    def test_evaluate_condition_empty_string(self):
        """Test condition evaluation with empty string."""
        engine = WorkflowEngine(api_client=Mock())

        assert engine.evaluate_condition("") is True

    def test_evaluate_condition_any_string(self):
        """Test condition evaluation with any string (simplified implementation)."""
        engine = WorkflowEngine(api_client=Mock())

        # Current implementation always returns True for non-empty conditions
        assert engine.evaluate_condition("some_condition") is True


class TestExecuteWorkflow:
    """Tests for workflow execution."""

    def test_execute_workflow_dry_run(self):
        """Test workflow execution in dry-run mode."""
        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test Workflow',
            'description': 'Test description',
            'version': '1.0',
            'steps': [
                {
                    'name': 'scan',
                    'tool': 'nmap',
                    'args': ['-sV', 'target']
                }
            ]
        }

        # Execute in dry run mode
        engine.execute_workflow(
            workflow=workflow,
            variables={},
            project_id='test-project',
            dry_run=True
        )

        # In dry run, step should be marked complete
        assert 'scan' in engine.completed_steps

    def test_execute_workflow_skip_unmet_dependency(self):
        """Test workflow skips step with unmet dependencies."""
        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test Workflow',
            'description': 'Test',
            'version': '1.0',
            'steps': [
                {
                    'name': 'step2',
                    'tool': 'nmap',
                    'args': ['-sV', 'target'],
                    'depends_on': ['step1']  # Dependency not satisfied
                }
            ]
        }

        engine.execute_workflow(
            workflow=workflow,
            variables={},
            project_id='test-project',
            dry_run=True
        )

        # Step should not be completed due to unmet dependency
        assert 'step2' not in engine.completed_steps

    def test_execute_workflow_with_variable_rendering(self):
        """Test workflow execution renders variables correctly."""
        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Scan {{target}}',
            'description': 'Test',
            'version': '1.0',
            'steps': [
                {
                    'name': 'scan',
                    'tool': 'nmap',
                    'args': ['-sV', '{{target}}']
                }
            ]
        }

        engine.execute_workflow(
            workflow=workflow,
            variables={'target': '192.168.1.1'},
            project_id='test-project',
            dry_run=True
        )

        assert 'scan' in engine.completed_steps

    @patch('wrappers.registry.get_wrapper_registry')
    def test_execute_workflow_unknown_tool_fail(self, mock_get_registry):
        """Test workflow execution fails on unknown tool with on_error=fail."""
        mock_registry = Mock()
        mock_registry.get_wrapper_class.return_value = None
        mock_get_registry.return_value = mock_registry

        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test',
            'description': 'Test',
            'version': '1.0',
            'steps': [
                {
                    'name': 'scan',
                    'tool': 'unknown-tool',
                    'args': ['-x'],
                    'on_error': 'fail'
                }
            ]
        }

        with pytest.raises(ValueError, match="Unknown tool: unknown-tool"):
            engine.execute_workflow(
                workflow=workflow,
                variables={},
                project_id='test-project',
                dry_run=False
            )

    @patch('wrappers.registry.get_wrapper_registry')
    def test_execute_workflow_unknown_tool_continue(self, mock_get_registry):
        """Test workflow execution continues on unknown tool with on_error=continue."""
        mock_registry = Mock()
        mock_registry.get_wrapper_class.return_value = None
        mock_get_registry.return_value = mock_registry

        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test',
            'description': 'Test',
            'version': '1.0',
            'steps': [
                {
                    'name': 'scan',
                    'tool': 'unknown-tool',
                    'args': ['-x'],
                    'on_error': 'continue'
                }
            ]
        }

        # Should not raise exception
        engine.execute_workflow(
            workflow=workflow,
            variables={},
            project_id='test-project',
            dry_run=False
        )

        # Step should not be in completed_steps
        assert 'scan' not in engine.completed_steps

    @patch('wrappers.registry.get_wrapper_registry')
    def test_execute_workflow_step_execution(self, mock_get_registry):
        """Test workflow step execution with mocked wrapper."""
        # Mock wrapper and registry
        mock_wrapper = Mock()
        mock_wrapper.execute_tool.return_value = {'status': 'success'}
        mock_wrapper_class = Mock(return_value=mock_wrapper)

        mock_registry = Mock()
        mock_registry.get_wrapper_class.return_value = mock_wrapper_class
        mock_get_registry.return_value = mock_registry

        engine = WorkflowEngine(api_client=Mock())

        workflow = {
            'name': 'Test',
            'description': 'Test',
            'version': '1.0',
            'steps': [
                {
                    'name': 'scan',
                    'tool': 'nmap',
                    'args': ['-sV', 'target']
                }
            ]
        }

        engine.execute_workflow(
            workflow=workflow,
            variables={},
            project_id='test-project',
            dry_run=False
        )

        # Verify wrapper was called
        mock_wrapper.execute_tool.assert_called_once_with(
            args=['-sV', 'target'],
            auto_import=True,
            dry_run=False
        )

        # Verify step completed
        assert 'scan' in engine.completed_steps
        assert 'scan' in engine.step_outputs


class TestListTemplates:
    """Tests for template listing."""

    def test_list_templates_empty_directory(self, tmp_path):
        """Test listing templates from empty directory."""
        templates = WorkflowEngine.list_templates(tmp_path)

        assert templates == []

    def test_list_templates_nonexistent_directory(self):
        """Test listing templates from non-existent directory."""
        templates = WorkflowEngine.list_templates(Path("/nonexistent"))

        assert templates == []

    def test_list_templates_valid_workflows(self, tmp_path):
        """Test listing valid workflow templates."""
        # Create test workflow files
        workflow1 = tmp_path / "workflow1.yml"
        workflow1.write_text("""
name: Workflow One
description: First workflow
version: 1.0
steps: []
""")

        workflow2 = tmp_path / "workflow2.yml"
        workflow2.write_text("""
name: Workflow Two
description: Second workflow
version: 2.0
steps: []
""")

        templates = WorkflowEngine.list_templates(tmp_path)

        assert len(templates) == 2

        template_names = [t['name'] for t in templates]
        assert 'Workflow One' in template_names
        assert 'Workflow Two' in template_names

        # Check structure
        for template in templates:
            assert 'file' in template
            assert 'name' in template
            assert 'description' in template
            assert 'version' in template

    def test_list_templates_ignores_invalid_yaml(self, tmp_path):
        """Test that invalid YAML files are skipped."""
        # Create valid workflow
        valid = tmp_path / "valid.yml"
        valid.write_text("""
name: Valid Workflow
description: Test
version: 1.0
steps: []
""")

        # Create invalid YAML
        invalid = tmp_path / "invalid.yml"
        invalid.write_text("invalid: yaml: content: [unclosed")

        templates = WorkflowEngine.list_templates(tmp_path)

        # Should only return valid workflow
        assert len(templates) == 1
        assert templates[0]['name'] == 'Valid Workflow'

    def test_list_templates_handles_missing_fields(self, tmp_path):
        """Test listing templates with missing optional fields."""
        workflow = tmp_path / "minimal.yml"
        workflow.write_text("""
name: Minimal
steps: []
""")

        templates = WorkflowEngine.list_templates(tmp_path)

        assert len(templates) == 1
        assert templates[0]['name'] == 'Minimal'
        assert templates[0]['description'] == ''
        assert templates[0]['version'] == 'unknown'


class TestWorkflowSchema:
    """Tests for workflow schema validation."""

    def test_schema_structure(self):
        """Test that WORKFLOW_SCHEMA is properly structured."""
        assert WORKFLOW_SCHEMA['type'] == 'object'
        assert 'name' in WORKFLOW_SCHEMA['required']
        assert 'description' in WORKFLOW_SCHEMA['required']
        assert 'version' in WORKFLOW_SCHEMA['required']
        assert 'steps' in WORKFLOW_SCHEMA['required']

    def test_schema_validates_minimal_workflow(self):
        """Test schema validates minimal valid workflow."""
        from jsonschema import validate

        minimal_workflow = {
            'name': 'Test',
            'description': 'Test workflow',
            'version': '1.0',
            'steps': [
                {
                    'name': 'step1',
                    'tool': 'nmap',
                    'args': ['-sV']
                }
            ]
        }

        # Should not raise exception
        validate(minimal_workflow, WORKFLOW_SCHEMA)

    def test_schema_rejects_invalid_on_error(self):
        """Test schema rejects invalid on_error value."""
        from jsonschema import validate, ValidationError

        invalid_workflow = {
            'name': 'Test',
            'description': 'Test',
            'version': '1.0',
            'steps': [
                {
                    'name': 'step1',
                    'tool': 'nmap',
                    'args': ['-sV'],
                    'on_error': 'invalid'  # Only 'fail' or 'continue' allowed
                }
            ]
        }

        with pytest.raises(ValidationError):
            validate(invalid_workflow, WORKFLOW_SCHEMA)
