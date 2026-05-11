"""
Google Takeout JSON parser
"""
import json
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import logging

from .base_parser import BaseParser
from config.config import GOOGLE_TAKEOUT_STRUCTURE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleParser(BaseParser):
    """Parser for Google Takeout JSON files"""
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse Google Takeout JSON file"""
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded JSON from {file_path.name}")
            
            # Extract reviews based on Google structure
            reviews_key = GOOGLE_TAKEOUT_STRUCTURE['reviews_key']
            
            if reviews_key not in data:
                # Try to find reviews in different locations
                if isinstance(data, list):
                    reviews_data = data
                else:
                    # Look for reviews in nested structure
                    reviews_data = self._find_reviews_recursive(data)
                    if not reviews_data:
                        raise ValueError(f"Could not find '{reviews_key}' key in JSON")
            else:
                reviews_data = data[reviews_key]
            
            # Parse each review
            reviews = []
            for item in reviews_data:
                review = self._parse_review_item(item)
                if review:
                    reviews.append(review)
            
            self.parsed_reviews = self.validate_reviews(reviews)
            logger.info(f"Successfully parsed {len(self.parsed_reviews)} valid reviews")
            
            return self.parsed_reviews
            
        except Exception as e:
            logger.error(f"Error parsing Google Takeout file {file_path}: {str(e)}")
            raise
    
    def _parse_review_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single review item from Google format"""
        config = GOOGLE_TAKEOUT_STRUCTURE
        review = {}
        
        try:
            # Extract text
            text_key = config['text_key']
            if text_key in item:
                review['text'] = item[text_key]
            elif 'review' in item:
                review['text'] = item['review']
            elif 'comment' in item:
                review['text'] = item['comment']
            else:
                return None
            
            # Extract rating
            rating_key = config['rating_key']
            if rating_key in item:
                rating_str = item[rating_key]
                rating_mapping = config['rating_mapping']
                review['rating'] = rating_mapping.get(rating_str, None)
            elif 'rating' in item:
                review['rating'] = int(item['rating'])
            
            # Extract date
            date_key = config['date_key']
            if date_key in item:
                review['date'] = item[date_key]
            elif 'date' in item:
                review['date'] = item['date']
            
            # Extract author
            if 'reviewer' in item:
                review['author'] = item['reviewer'].get('displayName', '')
            elif 'author' in item:
                review['author'] = item['author']
            
            return review
            
        except Exception as e:
            logger.warning(f"Error parsing review item: {str(e)}")
            return None
    
    def _find_reviews_recursive(self, data: Any, depth: int = 0, max_depth: int = 5) -> List:
        """Recursively search for reviews in nested JSON structure"""
        if depth > max_depth:
            return []
        
        if isinstance(data, list):
            # Check if this looks like a list of reviews
            if data and isinstance(data[0], dict):
                # Check if first item has review-like keys
                first_item = data[0]
                review_keys = ['comment', 'review', 'text', 'starRating', 'rating']
                if any(key in first_item for key in review_keys):
                    return data
        
        if isinstance(data, dict):
            # Search in dict values
            for value in data.values():
                result = self._find_reviews_recursive(value, depth + 1, max_depth)
                if result:
                    return result
        
        return []
