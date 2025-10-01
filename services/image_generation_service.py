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
# Using new database-aware OpenAI service for image generation
from services.openai_service_new import OpenAIService
from services import VertexService
from services.logger import get_logger

# Initialize logger for this module
logger = get_logger("services.image_generation_service")

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
                # Convert string model to ImageModel enum
                from models import ImageModel
                model_enum = ImageModel.DALLE_3 if model == "dall-e-3" else ImageModel.DALLE_3  # Default to DALLE_3
                return await self.openai_service.generate_image(
                    prompt=prompt,
                    model=model_enum,
                    size=size,
                    quality=quality
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

            # Resolve book-scoped directory and get chapter number
            import database_fixed as database
            adaptation = await database.get_adaptation_details(adaptation_id)
            chapter = await database.get_chapter_details(chapter_id)
            book_id = adaptation.get('book_id') if adaptation else None
            chapter_number = chapter.get('chapter_number') if chapter else chapter_id
            target_dir = os.path.join("generated_images", str(book_id)) if book_id else "generated_images"

            # Save image locally under per-book directory (use chapter_number for filename)
            filename = f"adaptation_{adaptation_id}_chapter_{chapter_number}_{model}.png"
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
    
    def _size_to_aspect_ratio(self, size_str: str) -> str:
        """Convert image size (e.g., '1792x1024') to Vertex AI aspect ratio (e.g., '16:9')"""
        try:
            if 'x' not in size_str:
                return "1:1"
            
            width, height = map(int, size_str.lower().split('x'))
            
            # Calculate GCD to simplify ratio
            from math import gcd
            divisor = gcd(width, height)
            ratio_w = width // divisor
            ratio_h = height // divisor
            
            # Map to closest Vertex AI supported aspect ratio
            # Vertex AI supports: 1:1, 4:3, 3:4, 16:9, 9:16
            ratio = ratio_w / ratio_h
            
            if ratio >= 1.7:  # 16:9 = 1.78
                return "16:9"
            elif ratio >= 1.2:  # 4:3 = 1.33
                return "4:3"
            elif ratio >= 0.9:  # Close to square
                return "1:1"
            elif ratio >= 0.7:  # 3:4 = 0.75
                return "3:4"
            else:  # 9:16 = 0.56
                return "9:16"
        except Exception as e:
            logger.warning(f"Failed to parse size '{size_str}': {e}, using 1:1")
            return "1:1"
    
    async def _generate_vertex_image(self, prompt: str, chapter_id: int, 
                                   adaptation_id: int, model: str) -> Dict[str, Any]:
        """Generate image using Google Vertex AI Imagen"""
        try:
            logger.info(f"🎨 Vertex AI generation starting for chapter_id={chapter_id}, adaptation_id={adaptation_id}, model={model}")
            
            if not self.vertex_available or not self.vertex_service:
                logger.error(f"❌ Vertex AI not available: vertex_available={self.vertex_available}, vertex_service={self.vertex_service is not None}")
                return {
                    "success": False,
                    "chapter_id": chapter_id,
                    "error": "Vertex AI service not available"
                }
            
            # Get image settings from database
            import database_fixed as database
            size_setting = await database.get_setting("default_image_size", "1024x1024")
            logger.info(f"📐 Using image size: {size_setting}")
            
            # Convert string model to ImageModel enum
            from models import ImageModel
            model_enum = ImageModel.VERTEX_IMAGEN
            
            async def _call_vertex():
                logger.info(f"🔧 Calling vertex_service.generate_image with size={size_setting}")
                return await self.vertex_service.generate_image(
                    prompt=prompt,
                    model=model_enum,
                    size=size_setting,
                    style="children_illustration"
                )
            async with self._semaphore:
                logger.info("🔄 Calling Vertex AI service...")
                result = await self._retry_async(_call_vertex)
                logger.info(f"✅ Vertex AI service returned: type={type(result)}, result={str(result)[:200]}")
            
            # Handle tuple return (image_url, error) from vertex_service
            if isinstance(result, tuple):
                image_url, error = result
                logger.info(f"📦 Tuple unpacked: image_url={image_url}, error={error}")
            else:
                # Fallback for unexpected format
                image_url, error = None, "Unexpected result format"
                logger.error(f"❌ Unexpected result format: {type(result)}")
            
            if image_url and not error:
                logger.info(f"✨ Image URL received: {image_url}")
                
                # Resolve per-book directory and get chapter number
                import database_fixed as database
                adaptation = await database.get_adaptation_details(adaptation_id)
                chapter = await database.get_chapter_details(chapter_id)
                book_id = adaptation.get('book_id') if adaptation else None
                chapter_number = chapter.get('chapter_number') if chapter else chapter_id
                target_dir = os.path.join("generated_images", str(book_id)) if book_id else "generated_images"
                logger.info(f"📁 Target directory: {target_dir}, book_id={book_id}")

                # Vertex AI already saved the image locally - image_url is a local path like /generated_images/filename.png
                # We need to move it to the per-book directory (use chapter_number for filename)
                filename = f"adaptation_{adaptation_id}_chapter_{chapter_number}_vertex.png"
                
                # Convert URL path to filesystem path
                source_path = image_url.lstrip('/')  # Remove leading slash to get relative path
                logger.info(f"🔍 Looking for source file: {source_path}")
                
                if not os.path.exists(source_path):
                    logger.error(f"❌ Source file not found: {source_path}")
                    return {
                        "success": False,
                        "chapter_id": chapter_id,
                        "error": f"Vertex AI image file not found: {source_path}"
                    }
                
                logger.info(f"✅ Source file exists, size: {os.path.getsize(source_path)} bytes")
                
                # Read and move to target directory
                with open(source_path, 'rb') as f:
                    image_bytes = f.read()
                image_path = await self._safe_write_file(target_dir, filename, image_bytes)
                logger.info(f"💾 Image saved to: {image_path}")
                
                # Clean up original file
                try:
                    os.remove(source_path)
                    logger.info(f"🗑️  Removed temporary file: {source_path}")
                except Exception as e:
                    logger.warning(f"Could not remove temporary Vertex image: {e}")
                
                logger.info(f"🎉 Vertex AI image generation complete!")
                
                return {
                    "success": True,
                    "chapter_id": chapter_id,
                    "image_url": f"/{target_dir}/{os.path.basename(image_path)}",
                    "local_path": image_path,
                    "source_url": image_url,
                    "prompt": enhanced_prompt,
                    "backend": "vertex",
                    "model": model,
                    "generated_at": datetime.now().isoformat()
                }
            else:
                logger.error(f"❌ Vertex generation failed: {error}")
                return {
                    "success": False,
                    "chapter_id": chapter_id,
                    "error": error or "Vertex AI generation failed"
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
        Uses the new OpenAI service for prompt generation
        """
        try:
            # Get adaptation and book details for context
            import database_fixed as database
            adaptation = await database.get_adaptation_details(adaptation_id)
            
            if not adaptation:
                logger.warning(f"No adaptation found for ID {adaptation_id}")
                return f"A children's book illustration for Chapter {chapter.get('chapter_number', 1)}"
            
            book_id = adaptation.get('book_id')
            book = await database.get_book_details(book_id) if book_id else None
            book_title = book.get('title', 'Unknown Book') if book else 'Unknown Book'
            
            chapter_text = chapter.get('transformed_text') or chapter.get('original_text_segment', '')
            chapter_number = chapter.get('chapter_number', 1)
            target_age_group = adaptation.get('target_age_group', 'ages_6_8')
            
            # Convert string age group to enum
            from models import AgeGroup
            age_group_map = {
                'ages_3_5': AgeGroup.AGES_3_5,
                'ages_6_8': AgeGroup.AGES_6_8,
                'ages_9_12': AgeGroup.AGES_9_12
            }
            age_group = age_group_map.get(target_age_group, AgeGroup.AGES_6_8)
            
            # Use new OpenAI service for prompt generation
            prompt, error = await self.openai_service.generate_image_prompt(
                chapter_text=chapter_text,
                chapter_number=chapter_number,
                book_context=f"Book: {book_title}, Theme: {adaptation.get('overall_theme_tone', 'Adventure')}",
                age_group=age_group
            )
            
            if error:
                logger.error(f"OpenAI prompt generation error: {error}")
            
            if prompt:
                return prompt.strip()
            
            # Fallback to basic prompt
            age_group = adaptation.get('target_age_group', 'Ages 6-8')
            return f"A children's book illustration showing characters from Chapter {chapter_number}, colorful and engaging for {age_group}"
        
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
                import database_fixed as database
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
                import database_fixed as database, shutil
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
