"""
Test script for ML analysis
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.parser_factory import ParserFactory
from src.analysis.analyzer import ReviewAnalyzer


def test_full_analysis():
    """Test full analysis pipeline"""
    print("\n" + "="*60)
    print("FULL ANALYSIS TEST")
    print("="*60)
    
    # Load test data
    csv_file = Path(__file__).parent.parent / "data" / "test" / "sample_reviews.csv"
    
    print(f"\n1. Loading data from: {csv_file.name}")
    reviews = ParserFactory.parse_file(csv_file)
    print(f"   Loaded {len(reviews)} reviews")
    
    # Initialize analyzer
    print("\n2. Initializing analyzer...")
    analyzer = ReviewAnalyzer()
    
    # Run analysis
    print("\n3. Running full analysis...")
    print("   This may take a few minutes on first run (downloading models)...")
    
    results = analyzer.analyze_full(
        reviews,
        analyze_sentiment=True,
        analyze_topics=True,
        extract_keywords=True
    )
    
    # Display results
    print("\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)
    
    # Sentiment
    if 'sentiment_summary' in results:
        sentiment = results['sentiment_summary']
        print(f"\nSENTIMENT ANALYSIS:")
        print(f"  Total reviews: {sentiment['total']}")
        print(f"  Positive: {sentiment['positive']} ({sentiment['positive_percent']:.1f}%)")
        print(f"  Negative: {sentiment['negative']} ({sentiment['negative_percent']:.1f}%)")
    
    # Topics
    if 'topic_summary' in results:
        topics = results['topic_summary']
        print(f"\nTOPIC MODELING:")
        print(f"  Topics found: {topics['total_topics']}")
        if topics.get('topics'):
            print(f"\n  Top 3 topics:")
            for i, topic in enumerate(topics['topics'][:3], 1):
                print(f"    {i}. {', '.join(topic['keywords'])} ({topic['count']} reviews)")
    
    # Keywords
    if 'keyword_summary' in results:
        keywords = results['keyword_summary']
        print(f"\nKEYWORD EXTRACTION:")
        print(f"  Unique keywords: {keywords['total_unique_keywords']}")
        
        if keywords.get('positive_keywords'):
            print(f"\n  Top positive keywords:")
            for kw, count in keywords['positive_keywords'][:5]:
                print(f"    - {kw} ({count})")
        
        if keywords.get('negative_keywords'):
            print(f"\n  Top negative keywords:")
            for kw, count in keywords['negative_keywords'][:5]:
                print(f"    - {kw} ({count})")
    
    # Insights
    print("\n" + "="*60)
    print("INSIGHTS")
    print("="*60)
    insights = analyzer.get_insights(results)
    for i, insight in enumerate(insights, 1):
        print(f"{i}. {insight}")
    
    # Recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    recommendations = analyzer.get_recommendations(results)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    print("\n" + "="*60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")
    
    return results


if __name__ == "__main__":
    try:
        test_full_analysis()
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
