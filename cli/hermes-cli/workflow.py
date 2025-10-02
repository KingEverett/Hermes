"""Workflow execution engine for Hermes."""

import yaml
import click
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Template, Environment
from jsonschema import validate, ValidationError
import logging

logger = logging.getLogger(__name__)

# Workflow YAML schema
WORKFLOW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "description", "version", "steps"],
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "variables": {"type": "object"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "tool", "args"],
                "properties": {
                    "name": {"type": "string"},
                    "tool": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                    "condition": {"type": "string"},
                    "timeout": {"type": "integer"},
                    "on_error": {"type": "string", "enum": ["fail", "continue"]}
                }
            }
        }
    }
}


class WorkflowEngine:
    """Engine for executing workflow templates."""

    def __init__(self, api_client):
        """Initialize the workflow engine.

        Args:
            api_client: HermesAPIClient instance
        """
        self.api_client = api_client
        self.step_outputs = {}
        self.completed_steps = set()

    def load_workflow(self, template_path: Path) -> Dict[str, Any]:
        """Load and validate workflow template.

        Args:
            template_path: Path to YAML workflow file

        Returns:
            Validated workflow dictionary

        Raises:
            ValidationError: If workflow schema is invalid
        """
        with open(template_path, 'r') as f:
            workflow = yaml.safe_load(f)

        # Validate schema
        try:
            validate(workflow, WORKFLOW_SCHEMA)
        except ValidationError as e:
            raise ValueError(f"Invalid workflow schema: {e.message}")

        return workflow

    def render_variables(self, workflow: Dict[str, Any], variables: Dict[str, str]) -> Dict[str, Any]:
        """Render Jinja2 variables in workflow.

        Args:
            workflow: Workflow dictionary
            variables: User-provided variables

        Returns:
            Workflow with rendered variables
        """
        # Create Jinja2 environment
        env = Environment()

        # Convert workflow to YAML string
        workflow_str = yaml.dump(workflow)

        # Create template with default filters
        template = env.from_string(workflow_str)

        # Render with variables
        rendered_str = template.render(**variables)

        # Parse back to dict
        return yaml.safe_load(rendered_str)

    def check_dependencies(self, step: Dict[str, Any]) -> bool:
        """Check if step dependencies are met.

        Args:
            step: Step dictionary

        Returns:
            True if all dependencies are met
        """
        depends_on = step.get('depends_on', [])
        for dep in depends_on:
            if dep not in self.completed_steps:
                return False
        return True

    def evaluate_condition(self, condition: Optional[str]) -> bool:
        """Evaluate step condition.

        Args:
            condition: Condition string (currently simplified)

        Returns:
            True if condition is met
        """
        if not condition:
            return True

        # Simplified condition evaluation
        # In a full implementation, this would parse and evaluate expressions
        # For now, just return True
        return True

    def execute_workflow(
        self,
        workflow: Dict[str, Any],
        variables: Dict[str, str],
        project_id: str,
        dry_run: bool = False
    ):
        """Execute workflow steps.

        Args:
            workflow: Workflow dictionary
            variables: User-provided variables
            project_id: Project ID for imports
            dry_run: If True, show steps without executing
        """
        # Render variables
        rendered = self.render_variables(workflow, variables)

        click.echo(f"Workflow: {rendered['name']}")
        click.echo(f"Description: {rendered['description']}")
        click.echo(f"Steps: {len(rendered['steps'])}")
        click.echo("=" * 80)

        if dry_run:
            click.echo("\n[DRY RUN MODE - No commands will be executed]\n")

        # Execute steps
        for idx, step in enumerate(rendered['steps'], 1):
            step_name = step['name']
            tool_name = step['tool']

            click.echo(f"\n[{idx}/{len(rendered['steps'])}] {step_name}")
            click.echo("-" * 80)

            # Check dependencies
            if not self.check_dependencies(step):
                click.echo(f"⏭️  Skipping: dependencies not met")
                continue

            # Check condition
            if not self.evaluate_condition(step.get('condition')):
                click.echo(f"⏭️  Skipping: condition not met")
                continue

            # Get wrapper
            from wrappers.registry import get_wrapper_registry
            registry = get_wrapper_registry()
            wrapper_class = registry.get_wrapper_class(tool_name)

            if not wrapper_class:
                click.echo(f"❌ Unknown tool: {tool_name}", err=True)
                on_error = step.get('on_error', 'fail')
                if on_error == 'fail':
                    raise ValueError(f"Unknown tool: {tool_name}")
                continue

            # Execute step
            if not dry_run:
                try:
                    wrapper = wrapper_class(project_id=project_id, api_client=self.api_client)
                    result = wrapper.execute_tool(
                        args=step['args'],
                        auto_import=True,
                        dry_run=False
                    )

                    self.step_outputs[step_name] = result
                    self.completed_steps.add(step_name)
                    click.echo(f"✓ {step_name} completed")

                except Exception as e:
                    click.echo(f"❌ {step_name} failed: {e}", err=True)
                    on_error = step.get('on_error', 'fail')
                    if on_error == 'fail':
                        raise
                    else:
                        click.echo(f"⚠️  Continuing despite error...")
            else:
                # Dry run - just show what would be executed
                click.echo(f"Would execute: {tool_name} {' '.join(step['args'])}")
                self.completed_steps.add(step_name)

        click.echo("\n" + "=" * 80)
        click.echo(f"✓ Workflow completed: {len(self.completed_steps)}/{len(rendered['steps'])} steps")

    @staticmethod
    def list_templates(templates_dir: Path) -> List[Dict[str, str]]:
        """List available workflow templates.

        Args:
            templates_dir: Directory containing templates

        Returns:
            List of template info dictionaries
        """
        templates = []
        if not templates_dir.exists():
            return templates

        for yaml_file in templates_dir.glob('*.yml'):
            try:
                with open(yaml_file, 'r') as f:
                    workflow = yaml.safe_load(f)
                templates.append({
                    'file': yaml_file.name,
                    'name': workflow.get('name', 'Unknown'),
                    'description': workflow.get('description', ''),
                    'version': workflow.get('version', 'unknown')
                })
            except Exception as e:
                logger.warning(f"Failed to load template {yaml_file}: {e}")

        return templates
