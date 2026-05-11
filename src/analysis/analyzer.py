"""
Main analyzer that combines all analysis components
"""
from typing import List, Dict, Any
import copy
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.models.sentiment_analyzer import SentimentAnalyzer
from src.models.topic_extractor import TopicExtractor
from src.models.keyword_extractor import KeywordExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReviewAnalyzer:
    """Main analyzer combining sentiment, topic, and keyword analysis"""
    
    def __init__(self):
        """Initialize all analysis components"""
        logger.info("Initializing Review Analyzer...")
        
        self.sentiment_analyzer = None
        self.topic_extractor = None
        self.keyword_extractor = None
        
        logger.info("Review Analyzer initialized (models will load on first use)")
    
    def analyze_full(self, reviews: List[Dict[str, Any]], 
                    analyze_sentiment: bool = True,
                    analyze_topics: bool = True,
                    extract_keywords: bool = True) -> Dict[str, Any]:
        """
        Perform full analysis on reviews
        
        Args:
            reviews: List of review dictionaries
            analyze_sentiment: Whether to perform sentiment analysis
            analyze_topics: Whether to perform topic modeling
            extract_keywords: Whether to extract keywords
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting full analysis of {len(reviews)} reviews")
        
        results = {
            'total_reviews': len(reviews),
            'reviews': copy.deepcopy(reviews),
            'analysis_performed': []
        }
        
        # Sentiment Analysis
        if analyze_sentiment:
            logger.info("Performing sentiment analysis...")
            try:
                if not self.sentiment_analyzer:
                    self.sentiment_analyzer = SentimentAnalyzer()
                
                results['reviews'] = self.sentiment_analyzer.analyze_reviews(results['reviews'])
                results['sentiment_summary'] = self.sentiment_analyzer.get_summary(results['reviews'])
                results['analysis_performed'].append('sentiment')
                logger.info("Sentiment analysis completed")
            except Exception as e:
                logger.error(f"Sentiment analysis failed: {str(e)}")
                results['sentiment_error'] = str(e)
        
        # Topic Extraction
        if analyze_topics:
            logger.info("Performing topic extraction...")
            try:
                if not self.topic_extractor:
                    self.topic_extractor = TopicExtractor()
                
                results['reviews'] = self.topic_extractor.analyze_reviews(results['reviews'])
                results['topic_summary'] = self.topic_extractor.get_summary()
                results['analysis_performed'].append('topics')
                logger.info("Topic extraction completed")
            except Exception as e:
                logger.error(f"Topic extraction failed: {str(e)}")
                results['topic_error'] = str(e)
        
        # Keyword Extraction
        if extract_keywords:
            logger.info("Performing keyword extraction...")
            try:
                if not self.keyword_extractor:
                    self.keyword_extractor = KeywordExtractor()
                
                results['reviews'] = self.keyword_extractor.analyze_reviews(results['reviews'], top_n=5)
                results['keyword_summary'] = self.keyword_extractor.get_summary(results['reviews'])
                results['analysis_performed'].append('keywords')
                logger.info("Keyword extraction completed")
            except Exception as e:
                logger.error(f"Keyword extraction failed: {str(e)}")
                results['keyword_error'] = str(e)
        
        logger.info("Full analysis completed")
        return results
    
    def get_insights(self, analysis_results: Dict[str, Any]) -> List[str]:
        """
        Generate actionable insights from analysis
        
        Args:
            analysis_results: Results from analyze_full
            
        Returns:
            List of insight strings
        """
        insights = []
        
        # Sentiment insights
        if 'sentiment_summary' in analysis_results:
            sentiment = analysis_results['sentiment_summary']
            positive_pct = sentiment.get('positive_percent', 0)
            negative_pct = sentiment.get('negative_percent', 0)
            
            if positive_pct > 70:
                insights.append(f"Strong positive sentiment ({positive_pct:.1f}%) - customers are very satisfied")
            elif positive_pct > 50:
                insights.append(f"Mostly positive feedback ({positive_pct:.1f}%) with room for improvement")
            elif negative_pct > 50:
                insights.append(f"Concerning negative feedback ({negative_pct:.1f}%) - immediate action needed")
            
            if negative_pct > 30:
                insights.append(f"High negative sentiment ({negative_pct:.1f}%) requires attention")
        
        # Topic insights
        if 'topic_summary' in analysis_results:
            topics = analysis_results['topic_summary'].get('topics', [])
            if topics:
                top_topic = max(topics, key=lambda x: x['count'])
                insights.append(f"Most discussed topic: {', '.join(top_topic['keywords'][:3])} ({top_topic['count']} reviews)")
        
        # Keyword insights
        if 'keyword_summary' in analysis_results:
            keywords = analysis_results['keyword_summary']
            
            if keywords.get('positive_keywords'):
                top_positive = keywords['positive_keywords'][:3]
                insights.append(f"Key strengths: {', '.join(kw for kw, _ in top_positive)}")
            
            if keywords.get('negative_keywords'):
                top_negative = keywords['negative_keywords'][:3]
                insights.append(f"Main concerns: {', '.join(kw for kw, _ in top_negative)}")
        
        if not insights:
            insights.append("Analysis completed - review detailed results for more information")
        
        return insights
    
    def get_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """
        Generate actionable recommendations
        
        Args:
            analysis_results: Results from analyze_full
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Based on sentiment
        if 'sentiment_summary' in analysis_results:
            sentiment = analysis_results['sentiment_summary']
            negative_pct = sentiment.get('negative_percent', 0)
            
            if negative_pct > 40:
                recommendations.append("Priority: Address negative feedback immediately")
                recommendations.append("Action: Contact dissatisfied customers to resolve issues")
            elif negative_pct > 20:
                recommendations.append("Monitor: Keep track of negative feedback trends")
        
        # Based on keywords
        if 'keyword_summary' in analysis_results:
            keywords = analysis_results['keyword_summary']
            
            if keywords.get('negative_keywords'):
                top_issues = [kw for kw, _ in keywords['negative_keywords'][:3]]
                recommendations.append(f"Focus on improving: {', '.join(top_issues)}")
            
            if keywords.get('positive_keywords'):
                strengths = [kw for kw, _ in keywords['positive_keywords'][:2]]
                recommendations.append(f"Leverage your strengths in marketing: {', '.join(strengths)}")
        
        # Based on topics
        if 'topic_summary' in analysis_results:
            total_topics = analysis_results['topic_summary'].get('total_topics', 0)
            if total_topics > 5:
                recommendations.append("Consider: Reviews cover many topics - prioritize based on frequency")
        
        if not recommendations:
            recommendations.append("Continue monitoring customer feedback regularly")
            recommendations.append("Maintain current quality standards")
        
        return recommendations
