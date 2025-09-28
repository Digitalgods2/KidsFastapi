"""
Image Generation Service for KidsKlassiks
Handles both OpenAI DALL-E and Google Vertex AI Imagen generation
"""

import os
import asyncio
import aiohttp
import json
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

# Import existing services
# Using legacy OpenAIService only for image generation backend compatibility
from legacy.services.openai_service import OpenAIService
from services import VertexService

class ImageGenerationService:
    def __init__(self):
        self.openai_service = OpenAIService()
        
        # Initialize Vertex AI service if configured
        try:
            self.vertex_service = VertexService()
            self.vertex_available = True
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.image_generation").info("vertex_unavailable", extra={"component":"services.image_generation","error":str(e)})
            self.vertex_service = None
            self.vertex_available = False
        
        self.generation_queue = []
        self.active_generations = {}
        
        # Create root directory (per-book subdirs created on demand)
        os.makedirs("generated_images", exist_ok=True)

        # Concurrency control for outbound image calls
        self._concurrency = int(os.getenv("IMAGE_CONCURRENCY", "3"))
        self._semaphore = asyncio.Semaphore(self._concurrency)

        # Allowed image extensions for safety
        self._allowed_exts = {".png", ".jpg", ".jpeg"}
    
    def create_batch(self, adaptation_id: int, total_chapters: int) -> str:
        batch_id = str(uuid.uuid4())
        self.active_generations[batch_id] = {
            "adaptation_id": adaptation_id,
            "total": total_chapters,
            "completed": 0,
            "status": "queued",
            "started_at": datetime.now(),
            "results": {
                "batch_id": batch_id,
                "total_chapters": total_chapters,
                "completed": 0,
                "failed": 0,
                "images": [],
                "errors": []
            }
        }
        return batch_id

    async def generate_chapter_images_batch(self, adaptation_id: int, chapters: List[Dict], 
                                          image_api: str = "dall-e-3", 
                                          progress_callback=None) -> Dict[str, Any]:
        """
        Generate images for multiple chapters in batch
        """
        # If called repeatedly, allow pre-created batch entry

        try:
            total_chapters = len(chapters)
            # Reuse existing batch if created; otherwise initialize
            if not self.active_generations:
                # edge case: empty cache; initialize
                batch_id = str(uuid.uuid4())
                self.active_generations[batch_id] = {
                    "adaptation_id": adaptation_id,
                    "total": total_chapters,
                    "completed": 0,
                    "status": "processing",
                    "started_at": datetime.now(),
                    "results": {
                        "batch_id": batch_id,
                        "total_chapters": total_chapters,
                        "completed": 0,
                        "failed": 0,
                        "images": [],
                        "errors": []
                    }
                }
            # pick the most recent batch id for this adaptation
            batch_id = next((bid for bid, info in self.active_generations.items() if info.get("adaptation_id") == adaptation_id and info.get("status") in {"queued","processing"}), None)
            if not batch_id:
                batch_id = self.create_batch(adaptation_id, total_chapters)
            results = self.active_generations[batch_id]["results"]
            self.active_generations[batch_id]["status"] = "processing"

            
            for i, chapter in enumerate(chapters):
                try:
                    if progress_callback:
                        await progress_callback(batch_id, i, total_chapters, f"Generating image for Chapter {chapter.get('chapter_number', i+1)}")
                    
                    # Generate image prompt first
                    prompt = await self.generate_image_prompt(chapter, adaptation_id)
                    
                    # Generate the image
                    image_result = await self.generate_single_image(
                        prompt=prompt,
                        chapter_id=chapter.get('chapter_id'),
                        adaptation_id=adaptation_id,
                        api_type=image_api
                    )
                    from services.logger import get_logger
                    _log = get_logger("image")
                    _log.info("image_generated", extra={
                        "component": "image_batch",
                        "event": "image_generated",
                        "adaptation_id": adaptation_id,
                        "chapter_id": chapter.get('chapter_id'),
                        "success": bool(image_result.get('success')),
                        "error": image_result.get('error')
                    })

                    
                    if image_result["success"]:
                        results["images"].append(image_result)
                        results["completed"] += 1
                    else:
                        results["errors"].append({
                            "chapter_id": chapter.get('chapter_id'),
                            "error": image_result.get("error", "Unknown error")
                        })
                        results["failed"] += 1

                    # Update progress
                    self.active_generations[batch_id]["completed"] = i + 1

                except Exception as e:
                    from services.logger import get_logger
                    get_logger("image").error("image_generate_exception", extra={
                        "adaptation_id": adaptation_id,
                        "chapter_id": chapter.get('chapter_id'),
                        "error": str(e),
                    })
                    results["errors"].append({
                        "chapter_id": chapter.get('chapter_id'),
                        "error": str(e)
                    })
                    results["failed"] += 1
            
            # Mark batch as complete
            self.active_generations[batch_id]["status"] = "completed"
            self.active_generations[batch_id]["completed_at"] = datetime.now()
            
            if progress_callback:
                await progress_callback(batch_id, total_chapters, total_chapters, "Batch generation completed")
            
            return results
        except Exception as e:
            if batch_id in self.active_generations:
                self.active_generations[batch_id]["status"] = "failed"
                self.active_generations[batch_id]["error"] = str(e)
            return {
                "batch_id": batch_id,
                "success": False,
                "error": str(e)
            }
            
    async def _retry_async(self, func, *, retries=3, base_delay=0.5, max_delay=6.0, jitter=True, retry_on_status={429, 500, 502, 503, 504}):
        for attempt in range(retries + 1):
            try:
                return await func()
            except Exception as e:
                msg = str(e)
                status = None
                # crude status extraction
                for s in retry_on_status:
                    if f" {s}" in msg or f"{s}:" in msg:
                        status = s
                        break
                if attempt >= retries or (status is None and attempt > 0):
                    raise
                delay = min(max_delay, base_delay * (2 ** attempt))
                if jitter:
                    import random
                    delay = delay * (0.5 + random.random())
                await asyncio.sleep(delay)
        # Shouldn't reach here
        raise RuntimeError("retry exhausted")

    def _safe_target_path(self, directory: str, filename: str) -> str:
        # Prevent absolute or traversal
        if os.path.isabs(filename) or ".." in filename.replace("\\", "/"):
            raise ValueError("Unsafe filename")
        target = os.path.join(directory, filename)
        # Enforce allowed extension
        _, ext = os.path.splitext(target)
        ext = ext.lower()
        if ext not in self._allowed_exts:
            raise ValueError("Disallowed file extension")
        return target

    async def _safe_write_file(self, directory: str, filename: str, data: bytes) -> str:
        os.makedirs(directory, exist_ok=True)
        target = self._safe_target_path(directory, filename)
        tmp = target + ".tmp"
        with open(tmp, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        return target
    
    async def generate_single_image(self, prompt: str, chapter_id: int, 
                                  adaptation_id: int, api_type: str = "dall-e-3") -> Dict[str, Any]:
        """
        Generate a single image using the specified API
        """
        try:
            if api_type.startswith("dall-e"):
                return await self._generate_openai_image(prompt, chapter_id, adaptation_id, api_type)
            elif api_type.startswith("vertex") or api_type.startswith("imagen"):
                return await self._generate_vertex_image(prompt, chapter_id, adaptation_id, api_type)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported API type: {api_type}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_openai_image(self, prompt: str, chapter_id: int, 
                                   adaptation_id: int, model: str) -> Dict[str, Any]:
        """Generate image using OpenAI DALL-E"""
        try:
            # Configure based on model
            if model == "dall-e-3":
                size = "1024x1024"
                quality = "standard"
            elif model == "dall-e-2":
                size = "1024x1024"
                quality = "standard"
            else:
                size = "1024x1024"
                quality = "hd"
            
            async def _call_openai():
                return await self.openai_service.generate_image(
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    model=model
                )
            
            async with self._semaphore:
                gen_out = await self._retry_async(_call_openai)

            # Accept multiple return shapes:
            # - str URL (modern OpenAIService)
            # - tuple (url, error) legacy
            # - dict {image_url, error}
            upstream_url = None
            gen_error = None

            if isinstance(gen_out, tuple):
                upstream_url, gen_error = gen_out
            elif isinstance(gen_out, dict):
                upstream_url = gen_out.get("image_url") or gen_out.get("url")
                gen_error = gen_out.get("error")
            elif isinstance(gen_out, str):
                upstream_url = gen_out
            elif gen_out is None:
                upstream_url = None
            else:
                gen_error = "Unknown image generation return format"

            if gen_error or not upstream_url:
                return {
                    "success": False,
                    "chapter_id": chapter_id,
                    "error": gen_error or "OpenAI generation failed"
                }

            # Resolve book-scoped directory
            import database
            adaptation = await database.get_adaptation_details(adaptation_id)
            book_id = adaptation.get('book_id') if adaptation else None
            target_dir = os.path.join("generated_images", str(book_id)) if book_id else "generated_images"

            # Save image locally under per-book directory
            filename = f"adaptation_{adaptation_id}_chapter_{chapter_id}_{model}.png"
            # Download bytes then write under target_dir
            image_bytes_path = await self._save_image_from_url(upstream_url, filename)
            if isinstance(image_bytes_path, str) and os.path.exists(image_bytes_path):
                with open(image_bytes_path, 'rb') as _f:
                    data = _f.read()
            else:
                data = image_bytes_path
            image_path = await self._safe_write_file(target_dir, filename, data)
            served_url = f"/{target_dir}/{os.path.basename(image_path)}"

            return {
                "success": True,
                "chapter_id": chapter_id,
                "image_url": served_url,
                "local_path": image_path,
                "source_url": upstream_url,
                "prompt": prompt,
                "backend": "openai",
                "model": model,
                "generated_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "success": False,
                "chapter_id": chapter_id,
                "error": f"OpenAI generation error: {str(e)}"
            }
    
    async def _generate_vertex_image(self, prompt: str, chapter_id: int, 
                                   adaptation_id: int, model: str) -> Dict[str, Any]:
        """Generate image using Google Vertex AI Imagen"""
        try:
            if not self.vertex_available or not self.vertex_service:
                return {
                    "success": False,
                    "chapter_id": chapter_id,
                    "error": "Vertex AI service not available"
                }
            
            # Configure based on model type
            if "children" in model:
                enhanced_prompt = f"A whimsical and colorful children's book illustration of {prompt}, in a friendly cartoon style with bright colors and simple shapes"
            elif "artistic" in model:
                enhanced_prompt = f"A masterpiece painting of {prompt}, with artistic brushstrokes and rich colors"
            else:
                enhanced_prompt = prompt
            
            async def _call_vertex():
                return await self.vertex_service.generate_image(
                    prompt=enhanced_prompt,
                    aspect_ratio="1:1"
                )
            async with self._semaphore:
                result = await self._retry_async(_call_vertex)
            
            if result["success"]:
                # Resolve per-book directory
                import database
                adaptation = await database.get_adaptation_details(adaptation_id)
                book_id = adaptation.get('book_id') if adaptation else None
                target_dir = os.path.join("generated_images", str(book_id)) if book_id else "generated_images"

                # Save image from base64 into per-book directory
                filename = f"adaptation_{adaptation_id}_chapter_{chapter_id}_vertex.png"
                image_data = result.get("image_data", "")
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                import base64 as _b64
                image_bytes = _b64.b64decode(image_data)
                image_path = await self._safe_write_file(target_dir, filename, image_bytes)
                
                return {
                    "success": True,
                    "chapter_id": chapter_id,
                    "image_url": f"/{target_dir}/{os.path.basename(image_path)}",
                    "local_path": image_path,
                    "source_url": None,
                    "prompt": enhanced_prompt,
                    "backend": "vertex",
                    "model": model,
                    "generated_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "chapter_id": chapter_id,
                    "error": result.get("error", "Vertex AI generation failed")
                }
        
        except Exception as e:
            return {
                "success": False,
                "chapter_id": chapter_id,
                "error": f"Vertex AI generation error: {str(e)}"
            }
    
    async def generate_image_prompt(self, chapter: Dict, adaptation_id: int) -> str:
        """
        Generate an AI-powered image prompt based on chapter content
        """
        try:
            # Get adaptation details for context
            import database
            adaptation = await database.get_adaptation_details(adaptation_id)
            
            chapter_text = chapter.get('original_chapter_text', '')[:2000]  # Limit text length
            age_group = adaptation.get('target_age_group', 'Ages 6-8')
            style = adaptation.get('transformation_style', 'Simple & Direct')
            
            prompt_generation_text = f"""
            Create a detailed image prompt for a children's book illustration based on this chapter excerpt:
            
            Chapter Text: {chapter_text}
            
            Target Age Group: {age_group}
            Style: {style}
            
            Generate a prompt that describes a single, engaging scene from this chapter that would be perfect for a children's book illustration. Focus on:
            - Main characters and their actions
            - Setting and environment
            - Mood and atmosphere appropriate for {age_group}
            - Visual elements that support the story
            
            Keep the prompt under 200 words and make it vivid and descriptive.
            """
            
            # Use modern chat helper
            from services import chat_helper
            messages = chat_helper.build_chapter_prompt_template(
                chapter_text,
                chapter.get('chapter_number', 1),
                adaptation,
            )
            text, err = await chat_helper.generate_chat_text(messages, temperature=0.7, max_tokens=500)
            if text:
                return text.strip()
            # Fallback to basic prompt
            return f"A children's book illustration showing characters from Chapter {chapter.get('chapter_number', 1)}, colorful and engaging for {age_group}"
        
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.image_generation_service").error("generate_image_prompt_error", extra={"component":"services.image_generation_service","error":str(e),"adaptation_id":adaptation_id,"chapter_id":chapter.get('chapter_id')})
            return f"A children's book illustration for Chapter {chapter.get('chapter_number', 1)}"
    
    async def _save_image_from_url(self, image_url: str, filename: str) -> str:
        """Download and save image from URL with timeouts and size caps"""
        MAX_BYTES = int(os.getenv("IMAGE_MAX_BYTES", "10485760"))  # 10 MiB default
        REQ_TIMEOUT = float(os.getenv("IMAGE_HTTP_TIMEOUT", "15"))  # seconds
        try:
            timeout = aiohttp.ClientTimeout(total=REQ_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async def _getter():
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download image: HTTP {response.status}")
                        total = 0
                        chunks = []
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            total += len(chunk)
                            if total > MAX_BYTES:
                                raise Exception(f"Image exceeds max size: {total} > {MAX_BYTES}")
                            chunks.append(chunk)
                        return b"".join(chunks)
                image_data = await self._retry_async(_getter)
                # Determine per-book directory for this adaptation
                import database
                adaptation = await database.get_adaptation_details(self._current_adaptation_id if hasattr(self, "_current_adaptation_id") else None) if False else None
                # Fallback: caller should pass adaptation_id through context; using filename to extract as last resort is unsafe, so we rely on generate_single_image to place correctly.
                # Here, just write to root; generate_single_image reads bytes and re-writes to the per-book directory.
                file_path = await self._safe_write_file("generated_images", filename, image_data)
                return file_path
        except Exception as e:
            # No partial files remain because writes are atomic to a temp path and swap
            from services.logger import get_logger
            get_logger("services.image_generation_service").error("image_download_error", extra={"component":"services.image_generation_service","error":str(e),"url":image_url})
            raise
    
    async def _save_image_from_base64(self, image_data: str, filename: str) -> str:
        """Save image from base64 data"""
        try:
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            # Write to root; caller moves/rewrites to per-book directory as needed
            file_path = await self._safe_write_file("generated_images", filename, image_bytes)
            return file_path
        
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.image_generation_service").error("image_save_base64_error", extra={"component":"services.image_generation_service","error":str(e)})
            raise
    
    def get_batch_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get progress information for a batch generation"""
        return self.active_generations.get(batch_id)
    
    async def generate_cover_image(self, adaptation_id: int, title: str, 
                                 author: str, theme: str, api_type: str = "dall-e-3") -> Dict[str, Any]:
        """Generate a cover image for the adaptation"""
        try:
            cover_prompt = f"""
            Create a beautiful children's book cover illustration for "{title}" by {author}.
            Theme: {theme}
            
            The cover should be:
            - Colorful and engaging for children
            - Show main characters or key scenes
            - Include space for the title and author name
            - Professional book cover quality
            - Appealing to the target age group
            """
            
            result = await self.generate_single_image(
                prompt=cover_prompt,
                chapter_id=0,  # 0 for cover
                adaptation_id=adaptation_id,
                api_type=api_type
            )
            
            if result["success"]:
                # Move to per-book directory
                import database, shutil
                adaptation = await database.get_adaptation_details(adaptation_id)
                book_id = adaptation.get('book_id') if adaptation else None
                target_dir = os.path.join("generated_images", str(book_id)) if book_id else "generated_images"
                os.makedirs(target_dir, exist_ok=True)

                cover_filename = f"cover_adaptation_{adaptation_id}.png"
                cover_path = os.path.join(target_dir, cover_filename)

                shutil.copy2(result["local_path"], cover_path)

                result["cover_path"] = cover_path
                result["cover_url"] = f"/{target_dir}/{cover_filename}"

            return result
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Cover generation error: {str(e)}"
            }
