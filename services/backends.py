"""Centralized backend registry and validation"""
from typing import Set, Dict, List, Any

# Supported image generation backends
SUPPORTED_BACKENDS: Set[str] = {
    "gpt-image-1",     # GPT-Image-1 - Newer model with tighter GPT/multimodal integration, enhanced over previous models
    "dall-e-3",        # DALL-E 3 - good quality, various sizes
    # "dall-e-2" REMOVED - deprecated
    "vertex-imagen",   # Google Vertex AI Imagen
    "vertex-children", # Vertex optimized for children's illustrations
    "vertex-artistic", # Vertex artistic style
}

# Aspect ratios supported by each backend
BACKEND_ASPECT_RATIOS: Dict[str, List[str]] = {
    "gpt-image-1": [
        "1:1",      # Square - 1024x1024
        "16:9",     # Landscape wide - 1792x1024
        "9:16",     # Portrait tall - 1024x1792
        # GPT-Image-1 supports these aspect ratios
    ],
    "dall-e-3": [
        "1:1",      # Square - 1024x1024
        "16:9",     # Landscape wide - 1792x1024
        "9:16",     # Portrait tall - 1024x1792
    ],
    "vertex-imagen": [
        "1:1",      # Square
        "16:9",     # Landscape
        "9:16",     # Portrait
        "4:3",      # Classic landscape
        "3:4",      # Classic portrait
    ],
    "vertex-children": [
        "1:1",      # Square
        "4:3",      # Classic landscape (best for books)
        "3:4",      # Classic portrait
    ],
    "vertex-artistic": [
        "1:1",      # Square
        "16:9",     # Landscape
        "9:16",     # Portrait
    ],
}

# Map aspect ratios to actual sizes for each backend
ASPECT_RATIO_SIZES: Dict[str, Dict[str, str]] = {
    "gpt-image-1": {
        "1:1": "1024x1024",
        "16:9": "1792x1024",
        "9:16": "1024x1792",
        # GPT-Image-1 supports these sizes
    },
    "dall-e-3": {
        "1:1": "1024x1024",
        "16:9": "1792x1024",
        "9:16": "1024x1792",
    },
    "vertex-imagen": {
        "1:1": "1024x1024",
        "16:9": "1920x1080",
        "9:16": "1080x1920",
        "4:3": "1024x768",
        "3:4": "768x1024",
    },
    "vertex-children": {
        "1:1": "1024x1024",
        "4:3": "1024x768",
        "3:4": "768x1024",
    },
    "vertex-artistic": {
        "1:1": "1024x1024",
        "16:9": "1920x1080",
        "9:16": "1080x1920",
    },
}

# Backend descriptions
BACKEND_DESCRIPTIONS: Dict[str, str] = {
    "gpt-image-1": "GPT-Image-1 (Recommended) - Newer model with tighter GPT/multimodal integration, enhanced quality and instruction following",
    "dall-e-3": "DALL-E 3 - High quality, good for general illustrations",
    "vertex-imagen": "Google Vertex Imagen - Advanced Google AI model",
    "vertex-children": "Vertex Children's Mode - Optimized for whimsical children's illustrations",
    "vertex-artistic": "Vertex Artistic Mode - Generate images in artistic styles",
}

# Default aspect ratio for each backend
DEFAULT_ASPECT_RATIOS: Dict[str, str] = {
    "gpt-image-1": "16:9",        # Landscape format (supported)
    "dall-e-3": "1:1",            # Square default
    "vertex-imagen": "16:9",      # Landscape format 
    "imagen-children": "4:3",     # Book format (children's books)
    "vertex-children": "4:3",     # Book format
    "vertex-artistic": "1:1",     # Square for art
}

def validate_backend(name: str) -> bool:
    """Check if a backend is supported"""
    return name in SUPPORTED_BACKENDS

def get_backend_info(name: str) -> Dict[str, Any]:
    """Get complete information about a backend"""
    if not validate_backend(name):
        return {}
    
    return {
        "name": name,
        "description": BACKEND_DESCRIPTIONS.get(name, ""),
        "aspect_ratios": BACKEND_ASPECT_RATIOS.get(name, []),
        "default_aspect_ratio": DEFAULT_ASPECT_RATIOS.get(name, "1:1"),
        "sizes": ASPECT_RATIO_SIZES.get(name, {}),
    }

def get_all_backends() -> List[Dict[str, Any]]:
    """Get information about all available backends"""
    return [get_backend_info(name) for name in sorted(SUPPORTED_BACKENDS)]

def get_aspect_ratio_size(backend: str, aspect_ratio: str) -> str:
    """Get the actual size for a backend and aspect ratio"""
    if backend in ASPECT_RATIO_SIZES and aspect_ratio in ASPECT_RATIO_SIZES[backend]:
        return ASPECT_RATIO_SIZES[backend][aspect_ratio]
    
    # Fallback to default
    default_ratio = DEFAULT_ASPECT_RATIOS.get(backend, "1:1")
    return ASPECT_RATIO_SIZES.get(backend, {}).get(default_ratio, "1024x1024")