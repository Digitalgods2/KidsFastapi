import asyncio
import database

async def test():
    # Test connection
    print("Testing database connection...")
    stats = await database.get_dashboard_stats()
    print(f"Dashboard stats: {stats}")
    
    # Get all books
    print("\nGetting all books...")
    books = await database.get_all_books()
    print(f"Found {len(books)} books:")
    for book in books:
        print(f"  - {book['title']} (ID: {book['book_id']})")
    
    # Analyze existing books
    print("\nAnalyzing existing books...")
    await database.analyze_all_books()
    
    # Get books again
    print("\nGetting books after analysis...")
    books = await database.get_all_books()
    for book in books:
        print(f"  - {book['title']}: {book['word_count']} words, {book['chapter_count']} chapters")

if __name__ == "__main__":
    asyncio.run(test())