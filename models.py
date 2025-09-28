"""
Pydantic models for KidsKlassiks FastAPI application
Data validation and API response models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ==================== ENUMS ====================

class SourceType(str, Enum):
    """Book source types"""
    UPLOAD = "upload"
    URL = "url"
    GUTENBERG = "gutenberg"

class AgeGroup(str, Enum):
    """Target age groups for adaptations"""
    AGES_3_5 = "3-5"
    AGES_6_8 = "6-8"
    AGES_9_12 = "9-12"

class TransformationStyle(str, Enum):
    """Transformation styles"""
    SIMPLE_DIRECT = "Simple & Direct"
    PLAYFUL_WHIMSICAL = "Playful & Whimsical"
    ADVENTUROUS_EXCITING = "Adventurous & Exciting"
    GENTLE_POETIC = "Gentle & Poetic"

class ChapterStructure(str, Enum):
    """Chapter structure options"""
    AUTO = "auto"
    ORIGINAL = "original"
    CUSTOM = "custom"

class AdaptationStatus(str, Enum):
    """Adaptation processing status"""
    CREATED = "created"
    PROCESSING = "processing"
    SEGMENTING = "segmenting"
    TRANSFORMING = "transforming"
    GENERATING_IMAGES = "generating_images"
    COMPLETE = "complete"
    ERROR = "error"

class ChapterStatus(str, Enum):
    """Chapter processing status"""
    CREATED = "created"
    PROCESSED = "processed"
    IMAGE_GENERATED = "image_generated"
    COMPLETE = "complete"

class ImageModel(str, Enum):
    """Available image generation models"""
    DALLE_2 = "dall-e-2"
    DALLE_3 = "dall-e-3"
    GPT_IMAGE_1 = "gpt-image-1"
    VERTEX_IMAGEN = "vertex-imagen"
    IMAGEN_CHILDREN = "imagen-children"
    IMAGEN_ARTISTIC = "imagen-artistic"
    IMAGEN_TEXT = "imagen-text"

# ==================== REQUEST MODELS ====================

class BookImportRequest(BaseModel):
    """Request model for importing a book"""
    title: str = Field(..., min_length=1, max_length=255)
    author: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = None
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

class AdaptationCreateRequest(BaseModel):
    """Request model for creating an adaptation"""
    book_id: int = Field(..., gt=0)
    target_age_group: AgeGroup
    transformation_style: TransformationStyle
    overall_theme_tone: str = Field(..., min_length=1, max_length=500)
    key_characters_to_preserve: Optional[str] = Field(None, max_length=1000)
    chapter_structure: ChapterStructure = ChapterStructure.AUTO

class ChapterUpdateRequest(BaseModel):
    """Request model for updating chapter content"""
    transformed_text: Optional[str] = None
    image_prompt: Optional[str] = None

class ImageGenerationRequest(BaseModel):
    """Request model for image generation"""
    prompt: str = Field(..., min_length=1, max_length=4000)
    model: ImageModel = ImageModel.DALLE_3
    size: Optional[str] = "1024x1024"
    quality: Optional[str] = "standard"

class SettingUpdateRequest(BaseModel):
    """Request model for updating settings"""
    setting_key: str = Field(..., min_length=1, max_length=255)
    setting_value: str = Field(..., max_length=1000)
    description: Optional[str] = Field(None, max_length=500)

# ==================== RESPONSE MODELS ====================

class BookResponse(BaseModel):
    """Response model for book data"""
    book_id: int
    title: str
    author: Optional[str]
    source_type: Optional[SourceType]
    imported_at: Optional[str]
    adaptation_count: Optional[int] = 0

class BookDetailResponse(BookResponse):
    """Detailed response model for book data"""
    source_url: Optional[str]
    original_content_path: Optional[str]
    character_reference: Optional[Dict[str, Any]]
    content: Optional[str]

class AdaptationResponse(BaseModel):
    """Response model for adaptation data"""
    adaptation_id: int
    book_id: int
    target_age_group: AgeGroup
    transformation_style: TransformationStyle
    overall_theme_tone: Optional[str]
    key_characters_to_preserve: Optional[str]
    chapter_structure: ChapterStructure
    status: AdaptationStatus
    created_at_formatted: Optional[str]
    chapter_count: Optional[int] = 0

class AdaptationDetailResponse(AdaptationResponse):
    """Detailed response model for adaptation data"""
    book_title: Optional[str]
    book_author: Optional[str]
    cover_image_prompt: Optional[str]
    cover_image_url: Optional[str]

class ChapterResponse(BaseModel):
    """Response model for chapter data"""
    chapter_id: int
    chapter_number: int
    original_chapter_text: Optional[str]
    transformed_chapter_text: Optional[str]
    ai_generated_image_prompt: Optional[str]
    user_edited_image_prompt: Optional[str]
    image_url: Optional[str]
    status: ChapterStatus

class CharacterReference(BaseModel):
    """Model for character reference data"""
    role: str
    age: Optional[str]
    physical_appearance: Optional[Dict[str, str]]
    clothing: Optional[Dict[str, str]]
    personality: Optional[Dict[str, Any]]
    special_attributes: Optional[Dict[str, str]]

class SettingResponse(BaseModel):
    """Response model for settings"""
    setting_key: str
    setting_value: str
    description: Optional[str]
    updated_at: Optional[datetime]

class DashboardStatsResponse(BaseModel):
    """Response model for dashboard statistics"""
    books: int
    adaptations: int
    chapters: int
    images: int

class PipelineProgressResponse(BaseModel):
    """Response model for pipeline progress updates"""
    status: AdaptationStatus
    current_step: str
    current_chapter: Optional[int] = None
    total_chapters: Optional[int] = None
    cover_prompt: Optional[str] = None
    error: Optional[str] = None
    progress_percentage: Optional[float] = None

class ImageGenerationProgressResponse(BaseModel):
    """Response model for image generation progress"""
    status: str
    image_url: Optional[str] = None
    error: Optional[str] = None
    progress_percentage: Optional[float] = None

# ==================== UTILITY MODELS ====================

class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    """Response model for validation errors"""
    detail: List[Dict[str, Any]]

class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    detail: Optional[str] = None
    status_code: int

# ==================== CONFIGURATION MODELS ====================

class ImageModelConfig(BaseModel):
    """Configuration for image generation models"""
    name: str
    description: str
    prompt_prefix: Optional[str] = ""
    prompt_suffix: Optional[str] = ""
    vertex_config: Optional[Dict[str, Any]] = {}
    openai_config: Optional[Dict[str, Any]] = {}

class AppConfig(BaseModel):
    """Application configuration model"""
    app_env: str
    app_debug: bool
    openai_configured: bool
    vertex_configured: bool
    database_configured: bool
    default_gpt_model: str
    default_image_model: str
    features: Dict[str, bool]

# ==================== SCENE AND CHARACTER MODELS ====================

class SceneCharacter(BaseModel):
    """Model for character in a scene"""
    ref: str
    expression: str
    action: str
    position: str

class SceneVisuals(BaseModel):
    """Model for scene visual elements"""
    setting: str
    time_of_day: str
    actions: List[str]
    mood: str
    lighting: str
    style: str
    focus_elements: List[str]

class ChapterScene(BaseModel):
    """Model for chapter scene description"""
    chapter: int
    title: str
    scene: str
    characters: Dict[str, SceneCharacter]
    visuals: SceneVisuals

class CompleteScene(BaseModel):
    """Model for complete scene with character references"""
    characters_reference: Dict[str, CharacterReference]
    settings_reference: Optional[Dict[str, Any]] = {}
    story_metadata: Optional[Dict[str, Any]] = {}
    chapter: int
    title: str
    scene: str
    characters: Dict[str, SceneCharacter]
    visuals: SceneVisuals

# ==================== EXPORT MODELS ====================

class ExportRequest(BaseModel):
    """Request model for exporting adaptations"""
    adaptation_id: int
    format: str = Field(..., pattern="^(pdf|txt|json)$")
    include_images: bool = True

class ExportResponse(BaseModel):
    """Response model for export operations"""
    file_path: str
    file_size: int
    format: str
    created_at: datetime

# ==================== VALIDATION HELPERS ====================

def validate_image_prompt_length(prompt: str, model: ImageModel) -> bool:
    """Validate image prompt length for specific model"""
    from config import MODEL_LIMITS
    
    limit = MODEL_LIMITS.get(model.value, 4000)
    return len(prompt) <= limit

def validate_age_appropriate_content(text: str, age_group: AgeGroup) -> bool:
    """Basic validation for age-appropriate content"""
    # This is a simplified validation - in production, you'd want more sophisticated checks
    inappropriate_words = ["violence", "death", "scary", "frightening"]
    
    if age_group == AgeGroup.AGES_3_5:
        return not any(word in text.lower() for word in inappropriate_words)
    
    return True  # Less restrictive for older age groups
