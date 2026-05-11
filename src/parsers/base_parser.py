"""
Base parser class for all data parsers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd


class BaseParser(ABC):
    """Abstract base class for all parsers"""
    
    def __init__(self):
        self.data = None
        self.parsed_reviews = []
    
    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse file and return list of review dictionaries
        
        Expected format:
        {
            'date': datetime or str,
            'rating': int (1-5),
            'text': str,
            'author': str (optional)
        }
        """
        pass
    
    def validate_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean parsed reviews"""
        validated = []
        
        for review in reviews:
            # Skip reviews without text
            if not review.get('text') or not str(review['text']).strip():
                continue
            
            # Clean text
            review['text'] = str(review['text']).strip()
            
            # Validate rating
            if 'rating' in review:
                try:
                    rating = int(review['rating'])
                    if 1 <= rating <= 5:
                        review['rating'] = rating
                    else:
                        review['rating'] = None
                except (ValueError, TypeError):
                    review['rating'] = None
            
            validated.append(review)
        
        return validated
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert parsed reviews to pandas DataFrame"""
        if not self.parsed_reviews:
            return pd.DataFrame()
        
        return pd.DataFrame(self.parsed_reviews)
