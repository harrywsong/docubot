"""
Hybrid Query Engine that supports both ChromaDB and FAISS modes.

This engine automatically selects the appropriate backend:
- ChromaDB mode: Full embedding model + vector store (Desktop)
- FAISS mode: Pre-computed embeddings + FAISS index (Pi)
- Remote mode: Desktop API for embeddings + local FAISS (Pi with desktop online)
"""

import logging
from typing import List, Dict, Optional, Any
from backend.config import Config

logger = logging.getLogger(__name__)


def get_query_backend():
    """
    Get the appropriate query backend based on configuration.
    
    Returns:
        Query backend instance (ChromaDB or FAISS)
    """
    if Config.USE_FAISS:
        logger.info("Using FAISS mode (no embedding model needed)")
        from backend.faiss_store import get_faiss_store
        from backend.llm_generator import get_llm_generator
        return FAISSQueryBackend(
            faiss_store=get_faiss_store(Config.FAISS_INDEX_PATH),
            llm_generator=get_llm_generator()
        )
    else:
        logger.info("Using ChromaDB mode (with embedding model)")
        from backend.query_engine import get_query_engine
        return get_query_engine()


class FAISSQueryBackend:
    """
    Query backend using FAISS with keyword extraction from LLM.
    
    This backend doesn't require an embedding model - it uses the LLM
    to extract keywords and performs keyword-based search.
    """
    
    def __init__(self, faiss_store, llm_generator):
        """
        Initialize FAISS query backend.
        
        Args:
            faiss_store: FAISSVectorStore instance
            llm_generator: LLMGenerator instance
        """
        self.faiss_store = faiss_store
        self.llm_generator = llm_generator
        self.retrieval_timeout = 10.0
        self.similarity_threshold = 0.3
        
        logger.info("FAISS query backend initialized")
    
    def query(
        self,
        question: str,
        user_id: int,
        conversation_history: List[Dict[str, str]] = None,
        top_k: int = 5,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Answer a question using FAISS + keyword extraction.
        
        Since we don't have an embedding model, we use the LLM to extract
        keywords and perform a simple keyword-based search.
        
        Args:
            question: User's question
            user_id: User ID for filtering
            conversation_history: Previous conversation messages
            top_k: Number of results to return
            timeout_seconds: Query timeout
            
        Returns:
            Query response dictionary
        """
        import time
        retrieval_start = time.time()
        
        logger.info(f"Processing FAISS query for user {user_id}: {question}")
        
        # Extract keywords using LLM
        keywords = self._extract_keywords(question)
        logger.info(f"Extracted keywords: {keywords}")
        
        # Perform keyword-based search
        # For now, we'll use a simple approach: search all chunks and rank by keyword matches
        results = self._keyword_search(keywords, user_id, top_k)
        
        retrieval_time = time.time() - retrieval_start
        logger.info(f"Retrieved {len(results)} chunks in {retrieval_time:.3f}s")
        
        if not results:
            return {
                "answer": "I couldn't find any relevant information in your documents.",
                "sources": [],
                "aggregated_amount": None,
                "breakdown": None,
                "retrieval_time": retrieval_time
            }
        
        # Generate response using LLM
        answer = self.llm_generator.generate_general_response(
            question=question,
            retrieved_results=results,
            conversation_history=conversation_history
        )
        
        return {
            "answer": answer,
            "sources": self._format_sources(results, top_k=3),
            "aggregated_amount": None,
            "breakdown": None,
            "retrieval_time": retrieval_time
        }
    
    def _extract_keywords(self, question: str) -> List[str]:
        """
        Extract keywords from question using LLM.
        
        Args:
            question: User's question
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction - just split and filter
        # In production, you'd use the LLM for better extraction
        import re
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but'}
        
        # Extract words
        words = re.findall(r'\w+', question.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords[:10]  # Limit to 10 keywords
    
    def _keyword_search(
        self,
        keywords: List[str],
        user_id: int,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search on FAISS store.
        
        Args:
            keywords: List of keywords to search for
            user_id: User ID for filtering
            top_k: Number of results to return
            
        Returns:
            List of matching chunks with scores
        """
        # Score each chunk by keyword matches
        scores = []
        for i, (chunk, metadata) in enumerate(zip(self.faiss_store.chunks, self.faiss_store.metadata)):
            # Filter by user_id
            if metadata.get('user_id') != user_id:
                continue
            
            # Count keyword matches
            chunk_lower = chunk.lower()
            score = sum(1 for kw in keywords if kw in chunk_lower)
            
            if score > 0:
                scores.append((score, i))
        
        # Sort by score and take top_k
        scores.sort(reverse=True)
        top_indices = [idx for _, idx in scores[:top_k]]
        
        # Build results
        results = []
        for idx in top_indices:
            results.append({
                'content': self.faiss_store.chunks[idx],
                'metadata': self.faiss_store.metadata[idx],
                'similarity_score': scores[idx][0] / len(keywords) if keywords else 0.0
            })
        
        return results
    
    def _format_sources(self, results: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """Format results as sources."""
        sources = []
        for result in results[:top_k]:
            source = {
                'filename': result['metadata'].get('filename', 'Unknown'),
                'chunk': result['content'][:200] + "..." if len(result['content']) > 200 else result['content'],
                'score': round(result['similarity_score'], 3),
                'metadata': {}
            }
            
            # Add metadata
            for key, value in result['metadata'].items():
                if not key.startswith('_'):
                    source['metadata'][key] = value
            
            sources.append(source)
        
        return sources
