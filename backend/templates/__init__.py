"""Template engine configuration for markdown generation."""

import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, Any

# Get the templates directory path
TEMPLATES_DIR = Path(__file__).parent


def create_template_environment() -> Environment:
    """Create and configure Jinja2 environment for markdown templates.

    Returns:
        Environment: Configured Jinja2 environment
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True
    )

    # Add custom filters if needed
    env.filters['markdown_escape'] = markdown_escape

    return env


def markdown_escape(text: str) -> str:
    """Escape special characters for markdown.

    Args:
        text: Text to escape

    Returns:
        str: Escaped text safe for markdown
    """
    if not text:
        return text

    # Escape markdown special characters
    special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '|']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def validate_markdown_syntax(content: str) -> bool:
    """Basic validation to ensure markdown syntax is correct.

    Args:
        content: Markdown content to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Basic validation checks
    checks = [
        # Tables should have matching column counts
        _validate_tables(content),
        # Code blocks should be properly closed
        _validate_code_blocks(content),
        # Headers should have proper formatting
        _validate_headers(content)
    ]

    return all(checks)


def _validate_tables(content: str) -> bool:
    """Validate markdown table structure."""
    lines = content.split('\n')
    in_table = False
    column_count = 0

    for line in lines:
        if '|' in line:
            if not in_table:
                # Start of table
                column_count = line.count('|') - 1
                in_table = True
            else:
                # Check column count consistency
                current_count = line.count('|') - 1
                if current_count != column_count and '---' not in line:
                    return False
        elif in_table and line.strip() and '---' not in line:
            # Table ended
            in_table = False
            column_count = 0

    return True


def _validate_code_blocks(content: str) -> bool:
    """Validate code blocks are properly closed."""
    return content.count('```') % 2 == 0


def _validate_headers(content: str) -> bool:
    """Validate header formatting."""
    lines = content.split('\n')
    for line in lines:
        if line.startswith('#'):
            # Check for space after hash
            if len(line) > 1 and line[1] not in [' ', '#']:
                return False
    return True


# Create default environment instance
default_env = create_template_environment()


def get_template(name: str) -> Any:
    """Get a template by name.

    Args:
        name: Template filename

    Returns:
        Template object
    """
    return default_env.get_template(name)