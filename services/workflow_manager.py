"""
Workflow Manager for KidsKlassiks
Manages the complete workflow from book import to publication
Ensures proper sequencing: Import → Character Analysis → Text Transformation → Prompt Generation → Review → Publish
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from enum import Enum

import database_fixed as database
from services.logger import get_logger
from services.character_analyzer import CharacterAnalyzer
from services.chat_helper import transform_chapter_text, generate_image_prompt_for_chapter
from services.gutenberg_cleaner import clean_gutenberg_text

logger = get_logger("workflow_manager")


class WorkflowStage(Enum):
    """Workflow stages for adaptation processing"""
    IMPORT = "import"
    CHARACTER_ANALYSIS = "character_analysis"
    TEXT_TRANSFORMATION = "text_transformation"
    PROMPT_GENERATION = "prompt_generation"
    REVIEW_EDITING = "review_editing"
    IMAGE_GENERATION = "image_generation"
    PUBLISHING = "publishing"
    COMPLETED = "completed"


class WorkflowStatus(Enum):
    """Status of workflow execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowManager:
    """
    Manages the complete book adaptation workflow with proper sequencing
    and progress notifications
    """
    
    def __init__(self):
        self.active_workflows = {}
        self.logger = logger
        
    async def start_adaptation_workflow(
        self,
        book_id: int,
        adaptation_id: int,
        progress_callback: Optional[Callable] = None,
        background: bool = True
    ) -> str:
        """
        Start the complete adaptation workflow
        
        Args:
            book_id: ID of the imported book
            adaptation_id: ID of the created adaptation
            progress_callback: Optional callback for progress updates
            background: Whether to run in background (default True)
            
        Returns:
            workflow_id: Unique identifier for this workflow
        """
        workflow_id = str(uuid.uuid4())
        
        # Initialize workflow state
        self.active_workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "book_id": book_id,
            "adaptation_id": adaptation_id,
            "stage": WorkflowStage.CHARACTER_ANALYSIS,
            "status": WorkflowStatus.PENDING,
            "started_at": datetime.now(timezone.utc),
            "progress": 0,
            "stages_completed": [],
            "current_stage_progress": 0,
            "errors": [],
            "notifications": []
        }
        
        if background:
            # Run workflow in background
            asyncio.create_task(
                self._run_workflow(workflow_id, progress_callback)
            )
        else:
            # Run workflow synchronously
            await self._run_workflow(workflow_id, progress_callback)
            
        return workflow_id
    
    async def _run_workflow(
        self,
        workflow_id: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Execute the complete workflow with proper sequencing
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
            
        try:
            workflow["status"] = WorkflowStatus.IN_PROGRESS
            
            # Stage 1: Character Analysis
            await self._notify_progress(
                workflow_id, 
                "Starting character analysis...",
                WorkflowStage.CHARACTER_ANALYSIS,
                0,
                progress_callback
            )
            
            await self._analyze_characters(workflow_id, progress_callback)
            workflow["stages_completed"].append(WorkflowStage.CHARACTER_ANALYSIS)
            
            # Stage 2: Text Transformation (CRITICAL - Must complete before proceeding)
            await self._notify_progress(
                workflow_id,
                "Transforming text to age-appropriate content...",
                WorkflowStage.TEXT_TRANSFORMATION,
                20,
                progress_callback
            )
            
            await self._transform_all_text(workflow_id, progress_callback)
            workflow["stages_completed"].append(WorkflowStage.TEXT_TRANSFORMATION)
            
            # Stage 3: Generate Image Prompts (Batch process, but don't create images)
            await self._notify_progress(
                workflow_id,
                "Generating image prompts for all chapters...",
                WorkflowStage.PROMPT_GENERATION,
                60,
                progress_callback
            )
            
            await self._generate_all_prompts(workflow_id, progress_callback)
            workflow["stages_completed"].append(WorkflowStage.PROMPT_GENERATION)
            
            # Stage 4: Mark as ready for review
            await self._notify_progress(
                workflow_id,
                "Ready for review and editing...",
                WorkflowStage.REVIEW_EDITING,
                90,
                progress_callback
            )
            
            workflow["status"] = WorkflowStatus.COMPLETED
            workflow["stage"] = WorkflowStage.REVIEW_EDITING
            workflow["progress"] = 100
            workflow["completed_at"] = datetime.now(timezone.utc)
            
            # Update adaptation status in database
            await database.update_adaptation_status(
                workflow["adaptation_id"],
                "ready_for_review"
            )
            
            await self._notify_progress(
                workflow_id,
                "Workflow completed! Ready for review and image generation.",
                WorkflowStage.REVIEW_EDITING,
                100,
                progress_callback
            )
            
        except Exception as e:
            workflow["status"] = WorkflowStatus.FAILED
            workflow["errors"].append(str(e))
            self.logger.error("workflow_failed", extra={
                "workflow_id": workflow_id,
                "error": str(e),
                "stage": workflow.get("stage").value if workflow.get("stage") else "unknown"
            })
            
            if progress_callback:
                await progress_callback({
                    "workflow_id": workflow_id,
                    "status": "error",
                    "message": f"Workflow failed: {str(e)}",
                    "stage": workflow.get("stage").value if workflow.get("stage") else "unknown"
                })
    
    async def _analyze_characters(
        self,
        workflow_id: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Analyze characters in the book using AI
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
            
        try:
            book_id = workflow["book_id"]
            adaptation_id = workflow["adaptation_id"]
            
            # Get book details
            book = await database.get_book_details(book_id)
            if not book:
                raise ValueError(f"Book {book_id} not found")
            
            # Get book text content
            book_text = book.get("path", "")
            if not book_text:
                self.logger.warning("no_book_text_for_analysis", extra={
                    "book_id": book_id,
                    "workflow_id": workflow_id
                })
                return
            
            # Analyze characters
            self.logger.info("character_analysis_start", extra={
                "workflow_id": workflow_id,
                "book_id": book_id
            })
            
            analyzer = CharacterAnalyzer()
            character_data = await analyzer.analyze_book_characters(
                book_text,
                book.get("title", "Unknown"),
                book.get("author", "Unknown")
            )
            
            if character_data:
                # Save character reference to database
                await database.save_character_reference(
                    book_id,
                    character_data
                )
                
                # Extract top characters for adaptation
                top_characters = analyzer.get_top_characters(character_data, limit=5)
                character_names = ", ".join([c["name"] for c in top_characters])
                
                # Update adaptation with key characters
                await database.update_adaptation_key_characters(
                    adaptation_id,
                    character_names
                )
                
                self.logger.info("character_analysis_complete", extra={
                    "workflow_id": workflow_id,
                    "character_count": len(top_characters),
                    "characters": character_names
                })
            
        except Exception as e:
            self.logger.error("character_analysis_error", extra={
                "workflow_id": workflow_id,
                "error": str(e)
            })
            # Don't fail workflow, character analysis is optional
    
    async def _transform_all_text(
        self,
        workflow_id: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Transform all chapter text to age-appropriate content
        This is CRITICAL and must complete before proceeding
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
            
        adaptation_id = workflow["adaptation_id"]
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise ValueError(f"Adaptation {adaptation_id} not found")
        
        # Get all chapters
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        if not chapters:
            raise ValueError(f"No chapters found for adaptation {adaptation_id}")
        
        total_chapters = len(chapters)
        age_group = adaptation.get("target_age_group", "6-8")
        
        self.logger.info("text_transformation_start", extra={
            "workflow_id": workflow_id,
            "adaptation_id": adaptation_id,
            "total_chapters": total_chapters,
            "age_group": age_group
        })
        
        transformed_count = 0
        error_count = 0
        total_original_chars = 0
        total_transformed_chars = 0
        
        for i, chapter in enumerate(chapters):
            chapter_id = chapter.get("chapter_id")
            chapter_number = chapter.get("chapter_number", i + 1)
            
            try:
                # Update progress
                progress = 20 + int((i / total_chapters) * 40)  # 20-60% range
                await self._notify_progress(
                    workflow_id,
                    f"Transforming Chapter {chapter_number} of {total_chapters}...",
                    WorkflowStage.TEXT_TRANSFORMATION,
                    progress,
                    progress_callback
                )
                
                # Skip if already transformed
                if chapter.get("transformed_text") and chapter.get("transformed_text").strip():
                    self.logger.info("chapter_already_transformed", extra={
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number
                    })
                    transformed_count += 1
                    continue
                
                # Get original text
                original_text = chapter.get("original_text_segment", "")
                if not original_text:
                    self.logger.warning("no_original_text", extra={
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number
                    })
                    continue
                
                # Transform the text
                book = await database.get_book_details(adaptation["book_id"])
                transformed_text, error = await transform_chapter_text(
                    original_text=original_text,
                    age_group=age_group,
                    book_title=book.get("title", "Unknown"),
                    chapter_number=chapter_number,
                    preserve_names=adaptation.get("key_characters_to_preserve", "")
                )
                
                if error:
                    self.logger.error("chapter_transform_error", extra={
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "error": error
                    })
                    error_count += 1
                    continue
                
                if transformed_text:
                    # Save transformed text
                    await database.update_chapter_text_and_prompt(
                        chapter_id=chapter_id,
                        transformed_text=transformed_text,
                        user_prompt=""  # Empty for now, will be generated next
                    )
                    
                    transformed_count += 1
                    total_original_chars += len(original_text)
                    total_transformed_chars += len(transformed_text)
                    
                    self.logger.info("chapter_transformed", extra={
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "original_length": len(original_text),
                        "transformed_length": len(transformed_text),
                        "reduction_percent": round((1 - len(transformed_text) / len(original_text)) * 100, 1)
                    })
                
            except Exception as e:
                self.logger.error("chapter_transform_exception", extra={
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "error": str(e)
                })
                error_count += 1
        
        # Log summary
        self.logger.info("text_transformation_complete", extra={
            "workflow_id": workflow_id,
            "adaptation_id": adaptation_id,
            "total_chapters": total_chapters,
            "transformed_count": transformed_count,
            "error_count": error_count,
            "total_original_chars": total_original_chars,
            "total_transformed_chars": total_transformed_chars,
            "overall_reduction": round((1 - total_transformed_chars / total_original_chars) * 100, 1) if total_original_chars > 0 else 0
        })
        
        if error_count == total_chapters:
            raise ValueError(f"Failed to transform any chapters for adaptation {adaptation_id}")
    
    async def _generate_all_prompts(
        self,
        workflow_id: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Generate image prompts for all chapters (but don't generate images)
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
            
        adaptation_id = workflow["adaptation_id"]
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise ValueError(f"Adaptation {adaptation_id} not found")
        
        # Get all chapters
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        if not chapters:
            raise ValueError(f"No chapters found for adaptation {adaptation_id}")
        
        total_chapters = len(chapters)
        
        self.logger.info("prompt_generation_start", extra={
            "workflow_id": workflow_id,
            "adaptation_id": adaptation_id,
            "total_chapters": total_chapters
        })
        
        generated_count = 0
        error_count = 0
        
        for i, chapter in enumerate(chapters):
            chapter_id = chapter.get("chapter_id")
            chapter_number = chapter.get("chapter_number", i + 1)
            
            try:
                # Update progress
                progress = 60 + int((i / total_chapters) * 30)  # 60-90% range
                await self._notify_progress(
                    workflow_id,
                    f"Generating prompt for Chapter {chapter_number} of {total_chapters}...",
                    WorkflowStage.PROMPT_GENERATION,
                    progress,
                    progress_callback
                )
                
                # Skip if already has prompt
                if chapter.get("ai_prompt") and chapter.get("ai_prompt").strip():
                    self.logger.info("prompt_already_exists", extra={
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number
                    })
                    generated_count += 1
                    continue
                
                # Use transformed text if available, otherwise original
                chapter_text = chapter.get("transformed_text") or chapter.get("original_text_segment", "")
                if not chapter_text:
                    self.logger.warning("no_chapter_text_for_prompt", extra={
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number
                    })
                    continue
                
                # Generate image prompt
                prompt = await generate_image_prompt_for_chapter(
                    chapter_text=chapter_text[:2000],  # Limit text for prompt generation
                    chapter_number=chapter_number,
                    adaptation=adaptation,
                    include_character_consistency=True
                )
                
                if prompt:
                    # Save prompt to database
                    await database.update_chapter_prompt(
                        chapter_id=chapter_id,
                        ai_prompt=prompt
                    )
                    
                    generated_count += 1
                    
                    self.logger.info("prompt_generated", extra={
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "prompt_length": len(prompt)
                    })
                else:
                    error_count += 1
                    
            except Exception as e:
                self.logger.error("prompt_generation_exception", extra={
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "error": str(e)
                })
                error_count += 1
        
        # Log summary
        self.logger.info("prompt_generation_complete", extra={
            "workflow_id": workflow_id,
            "adaptation_id": adaptation_id,
            "total_chapters": total_chapters,
            "generated_count": generated_count,
            "error_count": error_count
        })
    
    async def _notify_progress(
        self,
        workflow_id: str,
        message: str,
        stage: WorkflowStage,
        progress: int,
        callback: Optional[Callable] = None
    ):
        """
        Send progress notification
        """
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow["stage"] = stage
            workflow["progress"] = progress
            workflow["notifications"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": message,
                "stage": stage.value,
                "progress": progress
            })
        
        if callback:
            await callback({
                "workflow_id": workflow_id,
                "status": "progress",
                "message": message,
                "stage": stage.value,
                "progress": progress,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        self.logger.info("workflow_progress", extra={
            "workflow_id": workflow_id,
            "stage": stage.value,
            "progress": progress,
            "message": message
        })
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a workflow
        """
        return self.active_workflows.get(workflow_id)
    
    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """
        Get all active workflows
        """
        return list(self.active_workflows.values())
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause a running workflow
        """
        workflow = self.active_workflows.get(workflow_id)
        if workflow and workflow["status"] == WorkflowStatus.IN_PROGRESS:
            workflow["status"] = WorkflowStatus.PAUSED
            self.logger.info("workflow_paused", extra={"workflow_id": workflow_id})
            return True
        return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused workflow
        """
        workflow = self.active_workflows.get(workflow_id)
        if workflow and workflow["status"] == WorkflowStatus.PAUSED:
            workflow["status"] = WorkflowStatus.IN_PROGRESS
            self.logger.info("workflow_resumed", extra={"workflow_id": workflow_id})
            # Continue from where it left off
            asyncio.create_task(self._run_workflow(workflow_id))
            return True
        return False


# Global instance
workflow_manager = WorkflowManager()