#!/usr/bin/env python3

"""
Monitor configuration management for multi-directory monitoring
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from pathlib import Path


@dataclass
class MonitorConfig:
    """Configuration for a single directory monitor"""
    directory: str
    project: str
    patterns: List[str]
    recursive: bool = False
    delay: int = 5
    max_concurrent: int = 3
    exclude: Optional[List[str]] = None

    def __post_init__(self):
        """Normalize paths and set defaults"""
        self.directory = os.path.expanduser(self.directory)
        if self.exclude is None:
            self.exclude = ['*.tmp', '*.partial', '*~', '.*.swp']

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


class MonitorConfigFile:
    """Handles reading and writing monitor configuration files"""

    def __init__(self, config_path: str):
        self.config_path = os.path.expanduser(config_path)

    def load(self) -> List[MonitorConfig]:
        """Load monitor configurations from JSON file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            data = json.load(f)

        # Handle both array and object with 'monitors' key
        if isinstance(data, list):
            configs_data = data
        elif isinstance(data, dict) and 'monitors' in data:
            configs_data = data['monitors']
        else:
            raise ValueError("Config file must be array of monitors or object with 'monitors' key")

        return [MonitorConfig.from_dict(config) for config in configs_data]

    def save(self, configs: List[MonitorConfig]):
        """Save monitor configurations to JSON file"""
        # Create directory if needed
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        # Save with monitors key for extensibility
        data = {
            'monitors': [config.to_dict() for config in configs]
        }

        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def create_example(path: str):
        """Create an example configuration file"""
        example_config = {
            'monitors': [
                {
                    'directory': '~/scans/nmap',
                    'project': 'my-pentest',
                    'patterns': ['*.xml'],
                    'recursive': False,
                    'delay': 5,
                    'max_concurrent': 3,
                    'exclude': ['*.tmp', '*.partial']
                },
                {
                    'directory': '~/scans/masscan',
                    'project': 'my-pentest',
                    'patterns': ['*.json'],
                    'recursive': False,
                    'delay': 3,
                    'max_concurrent': 3
                }
            ]
        }

        os.makedirs(os.path.dirname(os.path.expanduser(path)), exist_ok=True)
        with open(os.path.expanduser(path), 'w') as f:
            json.dump(example_config, f, indent=2)
