"""
Test script for data parsers
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.parser_factory import ParserFactory


def test_csv_parser():
    """Test CSV parser"""
    print("\n" + "="*60)
    print("Testing CSV Parser")
    print("="*60)
    
    csv_file = Path(__file__).parent.parent / "data" / "test" / "sample_reviews.csv"
    
    try:
        reviews = ParserFactory.parse_file(csv_file)
        
        print(f"\nSuccessfully parsed {len(reviews)} reviews from CSV")
        print("\nFirst 3 reviews:")
        for i, review in enumerate(reviews[:3], 1):
            print(f"\n{i}. Date: {review.get('date', 'N/A')}")
            print(f"   Rating: {review.get('rating', 'N/A')}")
            print(f"   Author: {review.get('author', 'N/A')}")
            print(f"   Text: {review['text'][:100]}...")
        
        # Statistics
        ratings = [r['rating'] for r in reviews if r.get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        print(f"\nStatistics:")
        print(f"  Total reviews: {len(reviews)}")
        print(f"  Reviews with ratings: {len(ratings)}")
        print(f"  Average rating: {avg_rating:.2f}")
        
        return True
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False


def test_google_parser():
    """Test Google JSON parser"""
    print("\n" + "="*60)
    print("Testing Google Takeout JSON Parser")
    print("="*60)
    
    json_file = Path(__file__).parent.parent / "data" / "test" / "sample_google_takeout.json"
    
    try:
        reviews = ParserFactory.parse_file(json_file)
        
        print(f"\nSuccessfully parsed {len(reviews)} reviews from JSON")
        print("\nAll reviews:")
        for i, review in enumerate(reviews, 1):
            print(f"\n{i}. Date: {review.get('date', 'N/A')}")
            print(f"   Rating: {review.get('rating', 'N/A')}")
            print(f"   Author: {review.get('author', 'N/A')}")
            print(f"   Text: {review['text']}")
        
        # Statistics
        ratings = [r['rating'] for r in reviews if r.get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        print(f"\nStatistics:")
        print(f"  Total reviews: {len(reviews)}")
        print(f"  Reviews with ratings: {len(ratings)}")
        print(f"  Average rating: {avg_rating:.2f}")
        
        return True
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PARSER TESTING SUITE")
    print("="*60)
    
    csv_success = test_csv_parser()
    json_success = test_google_parser()
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"CSV Parser: {'PASSED' if csv_success else 'FAILED'}")
    print(f"Google Parser: {'PASSED' if json_success else 'FAILED'}")
    print("="*60 + "\n")
