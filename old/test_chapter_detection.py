'''
Test script for the TransformationService chapter detection.
'''

import asyncio
from services.transformation_service import TransformationService

async def main():
    # Initialize the service
    transformation_service = TransformationService()

    # Load a sample book
    book_path = "uploads/Peter Pan.txt"
    try:
        with open(book_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Successfully loaded book: {book_path}")
    except FileNotFoundError:
        print(f"Error: Book not found at {book_path}")
        return

    # Detect chapters
    print("\nDetecting chapters...")
    chapters = transformation_service.detect_chapters_in_text(content)

    # Print the results
    if chapters:
        print(f"\nSuccessfully detected {len(chapters)} chapters.")
        for i, chapter in enumerate(chapters[:3]): # Print first 3 chapters for brevity
            print(f"\n--- Chapter {i+1} ---")
            print(chapter.get("title", "No Title"))
            print(f"Content length: {len(chapter.get('content', ''))} characters")
            print(f"Content preview: {chapter.get('content', '')[:200]}...")
    else:
        print("\nNo chapters detected.")

if __name__ == "__main__":
    asyncio.run(main())

