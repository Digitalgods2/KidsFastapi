"""
Routes package for KidsKlassiks FastAPI application
Contains all API endpoints and route handlers
"""

# Import only the routes that don't have modern OpenAI dependencies
from . import adaptations, review, settings

# Note: books and images are imported directly in main.py as legacy versions

__all__ = ['adaptations', 'review', 'settings']
