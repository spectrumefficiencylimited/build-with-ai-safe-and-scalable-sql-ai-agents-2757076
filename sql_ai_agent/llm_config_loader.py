"""
LLM Configuration Loader

This module provides utilities to load and access LLM provider configurations
from the llm_config.yaml file.

Example Usage:
    from llm_config_loader import LLMConfig

    # Load configuration
    config = LLMConfig()

    # Get provider settings
    openai_config = config.get_provider('openai')

    # Get models for a provider
    models = config.get_models('openai')

    # Get default model for a provider
    default_model = config.get_default_model('anthropic')

    # Get API credentials
    api_key = config.get_api_key('openai')
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


class LLMConfig:
    """Load and manage LLM provider configurations from YAML file."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the LLM configuration loader.

        Args:
            config_path: Path to the YAML config file. If None, looks for
                        llm_config.yaml in the project root.
        """
        if config_path is None:
            # Default to llm_config.yaml in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "llm_config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load the YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get_provider(self, provider_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider (e.g., 'openai', 'anthropic')

        Returns:
            Dictionary containing provider configuration

        Raises:
            ValueError: If provider not found or not enabled
        """
        provider = self.config.get('providers', {}).get(provider_name)

        if provider is None:
            available = list(self.config.get('providers', {}).keys())
            raise ValueError(
                f"Provider '{provider_name}' not found. "
                f"Available providers: {available}"
            )

        if not provider.get('enabled', False):
            raise ValueError(f"Provider '{provider_name}' is not enabled")

        return provider

    def get_models(self, provider_name: str) -> List[Dict[str, Any]]:
        """
        Get list of available models for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of model configurations
        """
        provider = self.get_provider(provider_name)
        return provider.get('models', [])

    def get_model_names(self, provider_name: str) -> List[str]:
        """
        Get list of model names for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of model name strings
        """
        models = self.get_models(provider_name)
        return [model['name'] for model in models]

    def get_recommended_models(self, provider_name: str) -> List[str]:
        """
        Get list of recommended model names for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of recommended model name strings
        """
        models = self.get_models(provider_name)
        return [
            model['name'] for model in models
            if model.get('recommended', False)
        ]

    def get_default_model(self, provider_name: str) -> str:
        """
        Get the default model for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Default model name
        """
        provider = self.get_provider(provider_name)
        return provider.get('default_model', '')

    def get_fallback_model(self, provider_name: str) -> str:
        """
        Get the fallback model for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Fallback model name
        """
        provider = self.get_provider(provider_name)
        return provider.get('fallback_model', '')

    def get_base_url(self, provider_name: str) -> str:
        """
        Get the base URL for a provider's API.

        Args:
            provider_name: Name of the provider

        Returns:
            Base URL string
        """
        provider = self.get_provider(provider_name)
        return provider.get('base_url', '')

    def get_api_key(self, provider_name: str) -> str:
        """
        Get the API key for a provider from environment variables.

        Args:
            provider_name: Name of the provider

        Returns:
            API key from environment variable

        Raises:
            ValueError: If API key environment variable not found
        """
        provider = self.get_provider(provider_name)

        # Docker Model Runner uses a static key
        if 'api_key' in provider:
            return provider['api_key']

        # Other providers use environment variables
        api_key_env = provider.get('api_key_env')
        if not api_key_env:
            raise ValueError(
                f"No API key configuration found for provider '{provider_name}'"
            )

        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(
                f"Environment variable '{api_key_env}' not set for "
                f"provider '{provider_name}'"
            )

        return api_key

    def get_temperature(self, provider_name: str) -> float:
        """Get temperature setting for a provider."""
        provider = self.get_provider(provider_name)
        return provider.get('temperature', self.config['defaults']['temperature'])

    def get_max_tokens(self, provider_name: str) -> int:
        """Get max tokens setting for a provider."""
        provider = self.get_provider(provider_name)
        return provider.get('max_tokens', self.config['defaults']['max_tokens'])

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self.config.get('database', {})

    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration."""
        return self.config.get('agent', {})

    def get_validation_config(self) -> Dict[str, Any]:
        """
        Get SQL validation configuration from agent config.

        Returns:
            Dictionary with validation settings (read_only, max_result_limit, enforce_limit)
        """
        agent_config = self.get_agent_config()
        return {
            'read_only': agent_config.get('read_only', True),
            'max_result_limit': agent_config.get('max_result_limit', 10000),
            'enforce_limit': agent_config.get('enforce_limit', True),
        }

    def get_read_only(self) -> bool:
        """Get read-only mode setting from agent config."""
        return self.get_agent_config().get('read_only', True)

    def get_max_result_limit(self) -> int:
        """Get maximum result limit from agent config."""
        return self.get_agent_config().get('max_result_limit', 10000)

    def get_enforce_limit(self) -> bool:
        """Get enforce limit setting from agent config."""
        return self.get_agent_config().get('enforce_limit', True)

    def get_memory_enabled(self) -> bool:
        """Get memory enabled setting from agent config."""
        return self.get_agent_config().get('memory', False)

    def get_memory_size(self) -> int:
        """Get memory size setting from agent config."""
        return self.get_agent_config().get('memory_size', 10)

    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory configuration from agent config.

        Returns:
            Dictionary with memory settings (memory, memory_size)
        """
        agent_config = self.get_agent_config()
        return {
            'memory': agent_config.get('memory', False),
            'memory_size': agent_config.get('memory_size', 10),
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.

        Returns:
            Dictionary with logging settings including enabled flag, level,
            console/file output, LangChain callbacks, and performance tracking
        """
        return self.config.get('logging', {
            'enabled': False,
            'level': 'INFO',
            'console': {'enabled': True, 'format': 'human'},
            'file': {'enabled': False},
            'langchain': {'enabled': True, 'track_tokens': True, 'track_timing': True},
            'performance': {
                'track_llm_calls': True,
                'track_db_queries': True,
                'track_validation': True,
                'slow_query_threshold_ms': 1000
            }
        })

    def get_global_defaults(self) -> Dict[str, Any]:
        """Get global default settings."""
        return self.config.get('defaults', {})

    def list_providers(self, enabled_only: bool = True) -> List[str]:
        """
        List all available providers.

        Args:
            enabled_only: If True, only return enabled providers

        Returns:
            List of provider names
        """
        providers = self.config.get('providers', {})

        if enabled_only:
            return [
                name for name, config in providers.items()
                if config.get('enabled', False)
            ]

        return list(providers.keys())

    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Dictionary with provider info including models, settings, etc.
        """
        provider = self.get_provider(provider_name)

        return {
            'name': provider_name,
            'enabled': provider.get('enabled', False),
            'base_url': provider.get('base_url', ''),
            'default_model': provider.get('default_model', ''),
            'fallback_model': provider.get('fallback_model', ''),
            'temperature': provider.get('temperature', 0),
            'max_tokens': provider.get('max_tokens', 10000),
            'models': self.get_model_names(provider_name),
            'recommended_models': self.get_recommended_models(provider_name),
        }

    def print_summary(self):
        """Print a summary of the configuration."""
        print("=" * 60)
        print("LLM Configuration Summary")
        print("=" * 60)

        # Global defaults
        defaults = self.get_global_defaults()
        print(f"\nGlobal Defaults:")
        print(f"  Default Provider: {defaults.get('default_provider')}")
        print(f"  Default Model: {defaults.get('default_model')}")
        print(f"  Temperature: {defaults.get('temperature')}")
        print(f"  Max Tokens: {defaults.get('max_tokens')}")

        # Providers
        print(f"\nEnabled Providers:")
        for provider_name in self.list_providers(enabled_only=True):
            info = self.get_provider_info(provider_name)
            print(f"\n  {provider_name.upper()}:")
            print(f"    Base URL: {info['base_url']}")
            print(f"    Default Model: {info['default_model']}")
            print(f"    Available Models: {len(info['models'])}")
            print(f"    Models: {', '.join(info['models'][:3])}{'...' if len(info['models']) > 3 else ''}")

        # Database
        db_config = self.get_database_config()
        print(f"\nDatabase Configuration:")
        print(f"  Host: {db_config.get('host')}")
        print(f"  Port: {db_config.get('port')}")
        print(f"  Database: {db_config.get('database')}")
        print(f"  Table: {db_config.get('table_name')}")

        print("\n" + "=" * 60)


# Convenience function to load config
def load_config(config_path: Optional[str] = None) -> LLMConfig:
    """
    Load LLM configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        LLMConfig instance
    """
    return LLMConfig(config_path)


if __name__ == "__main__":
    # Example usage and testing
    config = load_config()
    config.print_summary()
