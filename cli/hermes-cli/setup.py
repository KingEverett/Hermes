from setuptools import setup, find_packages

setup(
    name="hermes-cli",
    version="1.0.0",
    py_modules=['hermes', 'api_client'],
    packages=find_packages(),
    install_requires=[
        'click==8.1.7',
        'requests==2.31.0',
        'python-dotenv==1.0.0',
        'urllib3>=1.26.0',
        'watchdog>=4.0.0',
        'python-daemon>=3.0.1',
        'pyyaml>=6.0',
        'jinja2>=3.1.0',
        'jsonschema>=4.0.0',
        'chardet>=5.0.0'
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-mock>=3.11.0',
            'pytest-cov>=4.1.0'
        ]
    },
    entry_points={
        'console_scripts': [
            'hermes=hermes:cli',
        ],
        'hermes_cli.wrappers': [
            # Built-in wrappers (can be extended by plugins)
        ],
        'hermes_cli.parsers': [
            # Built-in parsers (can be extended by plugins)
        ],
    },
    author="Hermes Team",
    description="CLI tool for Hermes Security Research Platform",
    long_description=open('README.md').read() if __import__('os').path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    python_requires='>=3.8',
)