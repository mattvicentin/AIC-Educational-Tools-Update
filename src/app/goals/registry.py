"""
Goal Generator Registry
Implements the registry pattern for automatic template discovery and registration.
Eliminates the factory anti-pattern by enabling templates to auto-register themselves.
"""

from typing import Dict, Type, Optional, List
from .base import GoalGenerator
from .types import TemplateType, GeneratorInstance, RegistryStats, RegistryInfo


class GoalGeneratorRegistry:
    """Registry for goal generators with automatic template discovery."""
    
    _generators: Dict[TemplateType, Type[GoalGenerator]] = {}
    
    @classmethod
    def register(cls, template_type: TemplateType, generator_class: Type[GoalGenerator]) -> None:
        """
        Register a goal generator for a template type.
        
        Args:
            template_type: The template type identifier (e.g., "study-group")
            generator_class: The goal generator class to register
        """
        cls._generators[template_type] = generator_class
    
    @classmethod
    def get_generator(cls, template_type: TemplateType) -> Optional[Type[GoalGenerator]]:
        """
        Get generator class for template type.
        
        Args:
            template_type: The template type identifier
            
        Returns:
            The generator class if registered, None otherwise
        """
        return cls._generators.get(template_type)
    
    @classmethod
    def get_supported_templates(cls) -> List[TemplateType]:
        """
        Get list of all supported template types.
        
        Returns:
            List of registered template type identifiers
        """
        return list(cls._generators.keys())
    
    @classmethod
    def is_supported(cls, template_type: TemplateType) -> bool:
        """
        Check if template type is supported.
        
        Args:
            template_type: The template type identifier
            
        Returns:
            True if the template type is registered, False otherwise
        """
        return template_type in cls._generators
    
    @classmethod
    def create_generator(cls, template_type: TemplateType) -> GeneratorInstance:
        """
        Create a generator instance for the given template type.
        
        Args:
            template_type: The template type identifier
            
        Returns:
            A generator instance if the type is supported, None otherwise
        """
        generator_class = cls.get_generator(template_type)
        if generator_class:
            return generator_class()
        return None
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered generators (mainly for testing)."""
        cls._generators.clear()
    
    @classmethod
    def count(cls) -> int:
        """
        Get the number of registered generators.
        
        Returns:
            Number of registered template generators
        """
        return len(cls._generators)
    
    @classmethod
    def get_stats(cls) -> RegistryStats:
        """
        Get comprehensive registry statistics.
        
        Returns:
            Registry statistics including template count and health status
        """
        return {
            "total_templates": cls.count(),
            "supported_templates": cls.get_supported_templates(),
            "registry_health": "healthy" if cls.count() > 0 else "empty"
        }
    
    @classmethod
    def get_info(cls, template_type: TemplateType) -> RegistryInfo:
        """
        Get detailed information about a specific template type.
        
        Args:
            template_type: The template type identifier
            
        Returns:
            Detailed information about the template type
        """
        generator_class = cls.get_generator(template_type)
        return {
            "template_type": template_type,
            "generator_class": generator_class.__name__ if generator_class else "None",
            "is_supported": cls.is_supported(template_type)
        }
