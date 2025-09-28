"""
PDF generator service for KidsKlassiks FastAPI application
Creates PDF publications from adaptations with images
"""

import os
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from PIL import Image as PILImage
import io
import requests

class PDFGenerator:
    """Service class for PDF generation operations"""
    
    def __init__(self):
        """Initialize PDF generator"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for children's books"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='BookTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        ))
        
        # Author style
        self.styles.add(ParagraphStyle(
            name='Author',
            parent=self.styles['Normal'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkgreen,
            fontName='Helvetica-Oblique'
        ))
        
        # Chapter title style
        self.styles.add(ParagraphStyle(
            name='ChapterTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            spaceBefore=30,
            alignment=TA_CENTER,
            textColor=colors.darkred,
            fontName='Helvetica-Bold'
        ))
        
        # Story text style
        self.styles.add(ParagraphStyle(
            name='StoryText',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            leading=16
        ))
        
        # Age-specific styles
        self.styles.add(ParagraphStyle(
            name='StoryText_3_5',
            parent=self.styles['StoryText'],
            fontSize=14,
            leading=18,
            spaceAfter=15
        ))
        
        self.styles.add(ParagraphStyle(
            name='StoryText_6_8',
            parent=self.styles['StoryText'],
            fontSize=12,
            leading=16,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='StoryText_9_12',
            parent=self.styles['StoryText'],
            fontSize=11,
            leading=14,
            spaceAfter=10
        ))
    
    # ==================== MAIN PDF GENERATION ====================
    
    async def generate_adaptation_pdf(
        self, 
        adaptation: Dict[str, Any], 
        book: Dict[str, Any], 
        chapters: List[Dict[str, Any]],
        include_images: bool = True
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate PDF for a complete adaptation"""
        try:
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self._sanitize_filename(book['title'])
            safe_style = self._sanitize_filename(adaptation['transformation_style'])
            age_group = adaptation['target_age_group'].replace('-', '_')
            
            filename = f"{safe_title}_{safe_style}_{age_group}_{timestamp}.pdf"
            
            # Ensure publications directory exists
            os.makedirs("publications", exist_ok=True)
            file_path = os.path.join("publications", filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build content
            story = []
            
            # Add title page
            story.extend(self._create_title_page(book, adaptation))
            
            # Add cover image if available
            if include_images and adaptation.get('cover_image_url'):
                cover_image = await self._add_image_to_story(adaptation['cover_image_url'])
                if cover_image:
                    story.append(cover_image)
                    story.append(PageBreak())
            
            # Add chapters
            for chapter in chapters:
                story.extend(await self._create_chapter_content(
                    chapter, 
                    adaptation['target_age_group'], 
                    include_images
                ))
            
            # Build PDF
            doc.build(story)
            
            return file_path, None
            
        except Exception as e:
            return None, f"Error generating PDF: {e}"
    
    def _create_title_page(self, book: Dict[str, Any], adaptation: Dict[str, Any]) -> List[Any]:
        """Create title page content"""
        content = []
        
        # Title
        title = book['title']
        content.append(Paragraph(title, self.styles['BookTitle']))
        content.append(Spacer(1, 20))
        
        # Author
        author = book.get('author', 'Unknown Author')
        content.append(Paragraph(f"by {author}", self.styles['Author']))
        content.append(Spacer(1, 30))
        
        # Adaptation info
        adaptation_info = f"""
        <b>A KidsKlassiks Adaptation</b><br/>
        Target Age: {adaptation['target_age_group']} years<br/>
        Style: {adaptation['transformation_style']}<br/>
        Created: {datetime.now().strftime('%B %d, %Y')}
        """
        
        content.append(Paragraph(adaptation_info, self.styles['Normal']))
        content.append(Spacer(1, 40))
        
        # Theme/tone if available
        if adaptation.get('overall_theme_tone'):
            theme_text = f"<i>Theme: {adaptation['overall_theme_tone']}</i>"
            content.append(Paragraph(theme_text, self.styles['Normal']))
        
        content.append(PageBreak())
        
        return content
    
    async def _create_chapter_content(
        self, 
        chapter: Dict[str, Any], 
        age_group: str, 
        include_images: bool
    ) -> List[Any]:
        """Create content for a single chapter"""
        content = []
        
        # Chapter title
        chapter_title = f"Chapter {chapter['chapter_number']}"
        content.append(Paragraph(chapter_title, self.styles['ChapterTitle']))
        content.append(Spacer(1, 20))
        
        # Chapter image
        if include_images and chapter.get('image_url'):
            chapter_image = await self._add_image_to_story(chapter['image_url'])
            if chapter_image:
                content.append(chapter_image)
                content.append(Spacer(1, 20))
        
        # Chapter text
        text = chapter.get('transformed_chapter_text', chapter.get('original_chapter_text', ''))
        if text:
            # Choose appropriate style based on age group
            style_name = f"StoryText_{age_group.replace('-', '_')}"
            if style_name not in self.styles:
                style_name = 'StoryText'
            
            # Split text into paragraphs
            paragraphs = text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    content.append(Paragraph(para.strip(), self.styles[style_name]))
                    content.append(Spacer(1, 12))
        
        content.append(PageBreak())
        
        return content
    
    async def _add_image_to_story(self, image_url: str) -> Optional[RLImage]:
        """Add image to PDF story"""
        try:
            # Handle local file paths
            if image_url.startswith('/'):
                image_path = image_url[1:]  # Remove leading slash
            elif image_url.startswith('http'):
                # Download image
                image_path = await self._download_image(image_url)
                if not image_path:
                    return None
            else:
                image_path = image_url
            
            # Check if file exists
            if not os.path.exists(image_path):
                return None
            
            # Open and resize image if needed
            with PILImage.open(image_path) as img:
                # Calculate size to fit on page
                max_width = 4.5 * inch
                max_height = 6 * inch
                
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
                
                if img_width > max_width or img_height > max_height:
                    if aspect_ratio > 1:  # Wider than tall
                        new_width = max_width
                        new_height = max_width / aspect_ratio
                    else:  # Taller than wide
                        new_height = max_height
                        new_width = max_height * aspect_ratio
                else:
                    new_width = img_width
                    new_height = img_height
                
                # Create ReportLab image
                return RLImage(image_path, width=new_width, height=new_height)
        
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.pdf_generator").error("pdf_add_image_error", extra={"component":"services.pdf_generator","error":str(e),"image_url":image_url})
            return None
    
    async def _download_image(self, url: str) -> Optional[str]:
        """Download image from URL and return local path"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"temp_image_{timestamp}.png"
            temp_path = os.path.join("generated_images", filename)
            
            # Save image
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            return temp_path
            
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.pdf_generator").error("pdf_download_image_error", extra={"component":"services.pdf_generator","error":str(e),"url":url})
            return None
    
    # ==================== EXPORT FORMATS ====================
    
    async def export_text_only(
        self, 
        adaptation: Dict[str, Any], 
        book: Dict[str, Any], 
        chapters: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Export adaptation as plain text"""
        try:
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self._sanitize_filename(book['title'])
            filename = f"{safe_title}_text_export_{timestamp}.txt"
            
            # Ensure exports directory exists
            os.makedirs("exports", exist_ok=True)
            file_path = os.path.join("exports", filename)
            
            # Build content
            content = []
            
            # Header
            content.append(f"{book['title']}")
            content.append(f"by {book.get('author', 'Unknown Author')}")
            content.append("")
            content.append("A KidsKlassiks Adaptation")
            content.append(f"Target Age: {adaptation['target_age_group']} years")
            content.append(f"Style: {adaptation['transformation_style']}")
            content.append(f"Created: {datetime.now().strftime('%B %d, %Y')}")
            content.append("")
            content.append("=" * 50)
            content.append("")
            
            # Chapters
            for chapter in chapters:
                content.append(f"Chapter {chapter['chapter_number']}")
                content.append("-" * 20)
                content.append("")
                
                text = chapter.get('transformed_chapter_text', chapter.get('original_chapter_text', ''))
                if text:
                    content.append(text)
                
                content.append("")
                content.append("")
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            return file_path, None
            
        except Exception as e:
            return None, f"Error exporting text: {e}"
    
    async def export_json(
        self, 
        adaptation: Dict[str, Any], 
        book: Dict[str, Any], 
        chapters: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Export adaptation as JSON"""
        try:
            import json
            
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self._sanitize_filename(book['title'])
            filename = f"{safe_title}_json_export_{timestamp}.json"
            
            # Ensure exports directory exists
            os.makedirs("exports", exist_ok=True)
            file_path = os.path.join("exports", filename)
            
            # Build JSON structure
            export_data = {
                "book": {
                    "title": book['title'],
                    "author": book.get('author'),
                    "source_type": book.get('source_type')
                },
                "adaptation": {
                    "target_age_group": adaptation['target_age_group'],
                    "transformation_style": adaptation['transformation_style'],
                    "overall_theme_tone": adaptation.get('overall_theme_tone'),
                    "key_characters_to_preserve": adaptation.get('key_characters_to_preserve'),
                    "cover_image_prompt": adaptation.get('cover_image_prompt'),
                    "cover_image_url": adaptation.get('cover_image_url')
                },
                "chapters": [
                    {
                        "chapter_number": ch['chapter_number'],
                        "original_text": ch.get('original_chapter_text'),
                        "transformed_text": ch.get('transformed_chapter_text'),
                        "image_prompt": ch.get('ai_generated_image_prompt') or ch.get('user_edited_image_prompt'),
                        "image_url": ch.get('image_url')
                    }
                    for ch in chapters
                ],
                "export_metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "2.0.0",
                    "format": "KidsKlassiks JSON Export"
                }
            }
            
            # Write JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return file_path, None
            
        except Exception as e:
            return None, f"Error exporting JSON: {e}"
    
    # ==================== UTILITY METHODS ====================
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage"""
        # Remove or replace problematic characters
        import re
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Remove special characters
        filename = re.sub(r'[^\w\-_.]', '', filename)
        
        # Limit length
        if len(filename) > 50:
            filename = filename[:50]
        
        return filename
    
    async def get_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a generated PDF"""
        try:
            if not os.path.exists(file_path):
                return {"error": "File not found"}
            
            file_size = os.path.getsize(file_path)
            created_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            return {
                "file_path": file_path,
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "created_at": created_time.isoformat(),
                "format": "PDF"
            }
            
        except Exception as e:
            return {"error": f"Error getting PDF info: {e}"}
    
    def estimate_pdf_size(self, chapters: List[Dict[str, Any]], include_images: bool = True) -> Dict[str, Any]:
        """Estimate PDF file size"""
        # Base size for PDF structure
        base_size = 50000  # 50KB
        
        # Text size estimation
        total_text_length = sum(
            len(ch.get('transformed_chapter_text', ch.get('original_chapter_text', '')))
            for ch in chapters
        )
        text_size = total_text_length * 2  # Rough estimate
        
        # Image size estimation
        image_size = 0
        if include_images:
            image_count = sum(1 for ch in chapters if ch.get('image_url'))
            if image_count > 0:
                image_size = image_count * 200000  # 200KB per image estimate
        
        total_estimated_size = base_size + text_size + image_size
        
        return {
            "estimated_size_bytes": total_estimated_size,
            "estimated_size_mb": round(total_estimated_size / (1024 * 1024), 2),
            "text_contribution": text_size,
            "image_contribution": image_size,
            "base_contribution": base_size,
            "chapter_count": len(chapters),
            "estimated_image_count": sum(1 for ch in chapters if ch.get('image_url'))
        }
