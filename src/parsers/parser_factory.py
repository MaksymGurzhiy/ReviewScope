"""
Factory for creating appropriate parser based on file type
"""
from pathlib import Path
from typing import Union
import logging

from .csv_parser import CSVParser
from .google_parser import GoogleParser
from .base_parser import BaseParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory to create appropriate parser based on file type"""
    
    @staticmethod
    def create_parser(file_path: Union[str, Path]) -> BaseParser:
        """
        Create appropriate parser based on file extension
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Appropriate parser instance
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension in ['.csv', '.xlsx', '.xls']:
            logger.info(f"Creating CSV/Excel parser for {file_path.name}")
            return CSVParser()
        elif extension == '.json':
            logger.info(f"Creating Google JSON parser for {file_path.name}")
            return GoogleParser()
        else:
            raise ValueError(f"Unsupported file format: {extension}")
    
    @staticmethod
    def parse_file(file_path: Union[str, Path]):
        """
        Convenience method to parse file in one call
        
        Args:
            file_path: Path to file
            
        Returns:
            List of parsed review dictionaries
        """
        parser = ParserFactory.create_parser(file_path)
        return parser.parse(file_path)
