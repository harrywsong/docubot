"""
Query Engine for RAG Chatbot with Vision Processing

This module provides question answering capabilities with context retrieval.
It generates question embeddings, retrieves relevant chunks, applies metadata filtering,
and generates responses using retrieved context.
"""

import logging
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store
from backend.models import QueryResult

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Query engine for answering questions using RAG.
    
    Features:
    - Question embedding generation
    - Top-k similarity retrieval from vector store
    - Metadata filtering for date and merchant queries
    - Numerical aggregation for receipt amounts
    - Date format parsing (MMM DD YYYY, YYYY-MM-DD, Month DD YYYY)
    - Response generation using retrieved context
    """
    
    def __init__(self):
        """Initialize the query engine."""
        self.embedding_engine = get_embedding_engine()
        self.vector_store = get_vector_store()
        logger.info("Query engine initialized")
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG.
        
        Args:
            question: User's question
            top_k: Number of similar chunks to retrieve (default: 5)
            timeout_seconds: Query timeout in seconds (default: 10)
            
        Returns:
            Dictionary with:
                - answer: Generated response text
                - sources: List of source documents with metadata
                - aggregated_amount: Optional total amount for spending queries
                - breakdown: Optional list of individual amounts
        """
        try:
            logger.info(f"Processing query: {question}")
            
            # Step 1: Generate question embedding
            logger.info("Generating question embedding")
            question_embedding = self.embedding_engine.generate_embedding(question)
            
            # Step 2: Extract metadata filters from question
            metadata_filter = self._extract_metadata_filters(question)
            logger.info(f"Extracted metadata filters: {metadata_filter}")
            
            # Step 3: Retrieve similar chunks from vector store
            logger.info(f"Retrieving top {top_k} similar chunks")
            results = self.vector_store.query(
                query_embedding=question_embedding,
                top_k=top_k,
                metadata_filter=metadata_filter
            )
            
            # Step 4: Check if any results found
            if not results:
                logger.warning("No relevant chunks found")
                return {
                    "answer": "I couldn't find any relevant information in your documents. Try rephrasing your question or processing more documents.",
                    "sources": [],
                    "aggregated_amount": None,
                    "breakdown": None
                }
            
            logger.info(f"Retrieved {len(results)} chunks")
            
            # Step 5: Check if this is a spending/amount aggregation query
            is_spending_query = self._is_spending_query(question)
            
            if is_spending_query:
                # Aggregate amounts from receipts
                aggregated_amount, breakdown = self._aggregate_amounts(results)
                
                # Generate response for spending query
                answer = self._generate_spending_response(
                    question=question,
                    results=results,
                    aggregated_amount=aggregated_amount,
                    breakdown=breakdown,
                    metadata_filter=metadata_filter
                )
                
                return {
                    "answer": answer,
                    "sources": self._format_sources(results),
                    "aggregated_amount": aggregated_amount,
                    "breakdown": breakdown
                }
            else:
                # Generate general response
                answer = self._generate_response(question, results)
                
                return {
                    "answer": answer,
                    "sources": self._format_sources(results),
                    "aggregated_amount": None,
                    "breakdown": None
                }
        
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return {
                "answer": "Failed to generate response. Please try again.",
                "sources": [],
                "aggregated_amount": None,
                "breakdown": None
            }
    
    def _extract_metadata_filters(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata filters from the question.
        
        Supports:
        - Date filtering: "on feb 11, 2026", "on 2026-02-11", "on February 11, 2026"
        - Merchant filtering: "at costco", "from walmart", "at target"
        
        Args:
            question: User's question
            
        Returns:
            Dictionary of metadata filters or None
        """
        filters = {}
        
        # Extract date
        date = self._extract_date(question)
        if date:
            filters["date"] = date
        
        # Extract merchant
        merchant = self._extract_merchant(question)
        if merchant:
            filters["merchant"] = merchant
        
        return filters if filters else None
    
    def _extract_date(self, question: str) -> Optional[str]:
        """
        Extract and normalize date from question.
        
        Supports formats:
        - MMM DD, YYYY (e.g., "feb 11, 2026")
        - YYYY-MM-DD (e.g., "2026-02-11")
        - Month DD, YYYY (e.g., "February 11, 2026")
        
        Args:
            question: User's question
            
        Returns:
            Normalized date string in YYYY-MM-DD format or None
        """
        question_lower = question.lower()
        
        # Pattern 1: YYYY-MM-DD
        pattern1 = r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b'
        match = re.search(pattern1, question)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        # Pattern 2: MMM DD, YYYY or Month DD, YYYY
        month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        for month_name, month_num in month_names.items():
            # Pattern: "month DD, YYYY" or "month DD YYYY"
            pattern = rf'\b{month_name}\s+(\d{{1,2}}),?\s+(\d{{4}})\b'
            match = re.search(pattern, question_lower)
            if match:
                day, year = match.groups()
                return f"{year}-{month_num:02d}-{int(day):02d}"
        
        return None
    
    def _extract_merchant(self, question: str) -> Optional[str]:
        """
        Extract merchant name from question.
        
        Looks for patterns like:
        - "at [merchant]"
        - "from [merchant]"
        - "spent at [merchant]"
        
        Args:
            question: User's question
            
        Returns:
            Merchant name or None
        """
        question_lower = question.lower()
        
        # Common patterns for merchant mentions
        patterns = [
            r'\bat\s+([a-z][a-z0-9\s&\'-]+?)(?:\s+on|\s+in|\s+during|\?|$)',
            r'\bfrom\s+([a-z][a-z0-9\s&\'-]+?)(?:\s+on|\s+in|\s+during|\?|$)',
            r'\bspent\s+at\s+([a-z][a-z0-9\s&\'-]+?)(?:\s+on|\s+in|\s+during|\?|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question_lower)
            if match:
                merchant = match.group(1).strip()
                # Capitalize first letter of each word
                merchant = ' '.join(word.capitalize() for word in merchant.split())
                return merchant
        
        return None
    
    def _is_spending_query(self, question: str) -> bool:
        """
        Determine if the question is asking about spending/amounts.
        
        Args:
            question: User's question
            
        Returns:
            True if this is a spending query
        """
        question_lower = question.lower()
        spending_keywords = [
            'how much', 'spent', 'total', 'cost', 'price', 'amount',
            'expense', 'paid', 'money', 'sum', 'aggregate'
        ]
        
        return any(keyword in question_lower for keyword in spending_keywords)
    
    def _aggregate_amounts(
        self,
        results: List[QueryResult]
    ) -> Tuple[Optional[float], Optional[List[Dict[str, Any]]]]:
        """
        Aggregate amounts from receipt chunks.
        
        Args:
            results: List of query results
            
        Returns:
            Tuple of (total_amount, breakdown_list)
        """
        amounts = []
        
        for result in results:
            # Check if this chunk has amount metadata
            total_amount = result.metadata.get('total_amount')
            
            if total_amount is not None:
                try:
                    amount = float(total_amount)
                    amounts.append({
                        'amount': amount,
                        'merchant': result.metadata.get('merchant', 'Unknown'),
                        'date': result.metadata.get('date', 'Unknown'),
                        'filename': result.metadata.get('filename', 'Unknown')
                    })
                except (ValueError, TypeError):
                    logger.warning(f"Invalid amount in metadata: {total_amount}")
        
        if not amounts:
            return None, None
        
        total = sum(item['amount'] for item in amounts)
        return total, amounts
    
    def _generate_spending_response(
        self,
        question: str,
        results: List[QueryResult],
        aggregated_amount: Optional[float],
        breakdown: Optional[List[Dict[str, Any]]],
        metadata_filter: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate response for spending queries.
        
        Args:
            question: User's question
            results: Retrieved chunks
            aggregated_amount: Total amount
            breakdown: List of individual amounts
            metadata_filter: Applied filters
            
        Returns:
            Generated response text
        """
        if aggregated_amount is None or breakdown is None:
            return "I found relevant documents but couldn't extract spending information. The documents may not contain receipt data."
        
        # Build response
        response_parts = []
        
        # Add total amount
        if len(breakdown) == 1:
            response_parts.append(f"You spent ${aggregated_amount:.2f}.")
        else:
            response_parts.append(f"You spent a total of ${aggregated_amount:.2f}.")
        
        # Add breakdown if multiple receipts
        if len(breakdown) > 1:
            response_parts.append("\nBreakdown:")
            for item in breakdown:
                merchant = item['merchant']
                date = item['date']
                amount = item['amount']
                response_parts.append(f"  - {merchant} on {date}: ${amount:.2f}")
        
        # Add context about filters
        if metadata_filter:
            filter_desc = []
            if 'merchant' in metadata_filter:
                filter_desc.append(f"at {metadata_filter['merchant']}")
            if 'date' in metadata_filter:
                filter_desc.append(f"on {metadata_filter['date']}")
            
            if filter_desc:
                response_parts.append(f"\n(Filtered {' '.join(filter_desc)})")
        
        return '\n'.join(response_parts)
    
    def _generate_response(
        self,
        question: str,
        results: List[QueryResult]
    ) -> str:
        """
        Generate response for general queries using retrieved context.
        
        For MVP, uses a simple template-based approach.
        Can be enhanced with LLM-based generation in the future.
        
        Args:
            question: User's question
            results: Retrieved chunks
            
        Returns:
            Generated response text
        """
        # For MVP: Simple context-based response
        # Combine top chunks as context
        context_parts = []
        
        for i, result in enumerate(results[:3], 1):  # Use top 3 chunks
            filename = result.metadata.get('filename', 'Unknown')
            content_preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
            context_parts.append(f"From {filename}:\n{content_preview}")
        
        context = "\n\n".join(context_parts)
        
        # Simple template response
        response = f"Based on your documents, here's what I found:\n\n{context}\n\n"
        response += f"(Found {len(results)} relevant document sections)"
        
        return response
    
    def _format_sources(self, results: List[QueryResult]) -> List[Dict[str, Any]]:
        """
        Format query results as source references.
        
        Args:
            results: List of query results
            
        Returns:
            List of source dictionaries
        """
        sources = []
        
        for result in results:
            source = {
                'filename': result.metadata.get('filename', 'Unknown'),
                'chunk': result.content[:200] + "..." if len(result.content) > 200 else result.content,
                'score': round(result.similarity_score, 3),
                'metadata': {
                    'file_type': result.metadata.get('file_type'),
                    'folder_path': result.metadata.get('folder_path')
                }
            }
            
            # Add image-specific metadata if available
            if result.metadata.get('merchant'):
                source['metadata']['merchant'] = result.metadata.get('merchant')
            if result.metadata.get('date'):
                source['metadata']['date'] = result.metadata.get('date')
            if result.metadata.get('total_amount'):
                source['metadata']['total_amount'] = result.metadata.get('total_amount')
            
            # Add text-specific metadata if available
            if result.metadata.get('page_number'):
                source['metadata']['page_number'] = result.metadata.get('page_number')
            
            sources.append(source)
        
        return sources


# Singleton instance for reuse across the application
_query_engine_instance = None


def get_query_engine() -> QueryEngine:
    """
    Get or create the singleton query engine instance.
    
    Returns:
        QueryEngine instance
    """
    global _query_engine_instance
    if _query_engine_instance is None:
        _query_engine_instance = QueryEngine()
    return _query_engine_instance
