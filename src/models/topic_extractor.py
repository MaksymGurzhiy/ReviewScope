"""
Topic Extraction using BERTopic
"""
import logging
import re
import time
from typing import Any, Dict, List, Tuple

import torch
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS as _SKLEARN_STOP

logger = logging.getLogger(__name__)

# Domain-AGNOSTIC stop-word list: only generic English + tiny conversational
# fillers. We deliberately do NOT hard-code domain words ("hotel", "pizza",
# "ice", etc.) — those would silently break topic modelling on any other
# dataset. Domain-defining tokens are filtered adaptively below via the
# CountVectorizer's `max_df` cutoff.
_CONVO_STOP = {'not', 'no', 'yes', 'ok', 'okay', 'oh', 'really'}
_TOPIC_STOP_WORDS = list(_SKLEARN_STOP | _CONVO_STOP)


class TopicExtractor:
    """Topic extraction using BERTopic"""
    
    def __init__(self, 
                 embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 min_topic_size: int = 5,
                 nr_topics: int = 10,
                 extra_blocklist: List[str] | None = None):
        """
        Initialize topic extractor

        Args:
            embedding_model: Sentence transformer model name
            min_topic_size: Minimum size for a topic
            nr_topics: Target number of topics (None for automatic)
            extra_blocklist: domain-specific words (e.g. parsed from the
                uploaded file name) that should never appear as topic
                keywords - filtered post-hoc from c-TF-IDF results.
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading topic embedding model %s on %s", embedding_model, device)
        t0 = time.perf_counter()
        self.embedding_model = SentenceTransformer(embedding_model, device=device)

        self.min_topic_size = min_topic_size
        self.nr_topics = nr_topics
        self.topic_model = None
        # Canonical (whitespace-stripped, plural-stripped) blocklist so
        # blocking "airpods" also blocks "airpod", "airpods", "AirPod".
        self._blocklist_canon: set[str] = {
            re.sub(r"\s+", "", w.lower()).rstrip("s")
            for w in (extra_blocklist or []) if w and len(w) >= 4
        }

        logger.info(
            "Topic extractor ready in %.1fs (device=%s)",
            time.perf_counter() - t0, device,
        )

    def _blocked(self, word: str) -> bool:
        if not self._blocklist_canon:
            return False
        canon = re.sub(r"\s+", "", word.lower()).rstrip("s")
        return canon in self._blocklist_canon
    
    def extract_topics(self, texts: List[str]) -> Tuple[List[int], List[float]]:
        """
        Extract topics from texts
        
        Args:
            texts: List of review texts
            
        Returns:
            Tuple of (topic assignments, probabilities)
        """
        logger.info(f"Extracting topics from {len(texts)} texts")
        
        if len(texts) < self.min_topic_size:
            logger.warning(f"Too few texts ({len(texts)}) for topic modeling. Minimum: {self.min_topic_size}")
            return [-1] * len(texts), [0.0] * len(texts)
        
        try:
            # Create embeddings
            logger.info("Creating embeddings...")
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            # Vectorizer fed to BERTopic for the c-TF-IDF representation:
            # stop_words = generic English only,
            # max_df = 0.6  → drops tokens that appear in >60% of all
            #                 reviews (the domain-defining word, e.g.
            #                 "hotel" on a hotel dataset, "pizza" on a
            #                 pizzeria dataset). c-TF-IDF still highlights
            #                 what makes each cluster *unique* without us
            #                 hard-coding any domain vocabulary.
            # min_df = 2    → drops one-off typos and proper nouns.
            # We only enable max_df when the corpus is big enough for the
            # cutoff to be meaningful.
            max_df = 0.6 if len(texts) >= 50 else 1.0
            vectorizer = CountVectorizer(
                stop_words=_TOPIC_STOP_WORDS,
                min_df=2,
                max_df=max_df,
                ngram_range=(1, 1),
                token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
            )

            # Create topic model
            self.topic_model = BERTopic(
                embedding_model=self.embedding_model,
                min_topic_size=self.min_topic_size,
                nr_topics=self.nr_topics,
                vectorizer_model=vectorizer,
                verbose=True
            )
            
            # Fit and transform
            logger.info("Fitting topic model...")
            topics, probs = self.topic_model.fit_transform(texts, embeddings)
            
            logger.info(f"Found {len(set(topics))} topics")
            return topics, probs
            
        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}")
            return [-1] * len(texts), [0.0] * len(texts)
    
    def get_topic_info(self) -> List[Dict[str, Any]]:
        """Get information about discovered topics"""
        if not self.topic_model:
            return []
        
        try:
            topic_info = self.topic_model.get_topic_info()
            
            topics = []
            for _, row in topic_info.iterrows():
                if row['Topic'] == -1:  # Skip outlier topic
                    continue
                
                topic_id = int(row['Topic'])
                topic_words = self.topic_model.get_topic(topic_id)
                # Filter domain-name tokens (e.g. product name from the
                # uploaded file) so c-TF-IDF doesn't surface them.
                filtered_words = [
                    (word, score) for word, score in topic_words
                    if not self._blocked(word)
                ]

                topics.append({
                    'id': topic_id,
                    'count': int(row['Count']),
                    'name': row.get('Name', f'Topic {topic_id}'),
                    'keywords': [word for word, _ in filtered_words[:5]],
                    'keywords_scores': [[word, float(score)] for word, score in filtered_words[:10]]
                })
            
            return topics
            
        except Exception as e:
            logger.error(f"Error getting topic info: {str(e)}")
            return []
    
    def analyze_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add topic information to reviews
        
        Args:
            reviews: List of review dictionaries
            
        Returns:
            Reviews with added topic information
        """
        texts = [r['text'] for r in reviews]
        topics, probs = self.extract_topics(texts)
        
        for review, topic, prob in zip(reviews, topics, probs):
            review['topic_id'] = int(topic)
            review['topic_probability'] = float(prob)
        
        return reviews
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of topics"""
        topics = self.get_topic_info()
        
        if not topics:
            return {'total_topics': 0, 'topics': []}
        
        return {
            'total_topics': len(topics),
            'topics': topics,
            'total_reviews_categorized': sum(t['count'] for t in topics)
        }
