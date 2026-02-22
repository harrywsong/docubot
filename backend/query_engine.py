"""
Query Engine for RAG Chatbot with Vision Processing

This module provides question answering capabilities with context retrieval.
It generates question embeddings, retrieves relevant chunks, applies metadata filtering,
and generates responses using retrieved context with LLM-based generation.

Enhanced for Pi mode with:
- Query embedding generation using conversational model
- Top-K retrieval with configurable K (default 5)
- Similarity threshold filtering
- Prompt construction with query + retrieved chunks
- 2-second timeout for retrieval operations
- Graceful degradation for query failures
- Error logging with timestamps and context
"""

import logging
import re
import time
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store
from backend.llm_generator import get_llm_generator
from backend.models import QueryResult

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Query engine for answering questions using RAG.
    
    Features:
    - Question embedding generation using conversational model
    - Top-k similarity retrieval from vector store (configurable K, default 5)
    - Similarity threshold filtering
    - Dynamic metadata filtering based on question content
    - Numerical aggregation for receipt amounts
    - Date format parsing (MMM DD YYYY, YYYY-MM-DD, Month DD YYYY)
    - Response generation using retrieved context
    - 2-second timeout for retrieval operations (Pi mode optimization)
    - Graceful degradation for query failures
    - Error logging with timestamps and context
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 14.2, 14.3, 14.4
    """
    
    def __init__(self, retrieval_timeout: float = 2.0, similarity_threshold: float = 0.3):
        """
        Initialize the query engine.
        
        Args:
            retrieval_timeout: Maximum time in seconds for retrieval operations (default: 2.0)
            similarity_threshold: Minimum similarity score for results (default: 0.3)
        """
        self.embedding_engine = get_embedding_engine()
        self.vector_store = get_vector_store()
        self.llm_generator = get_llm_generator()
        self.retrieval_timeout = retrieval_timeout
        self.similarity_threshold = similarity_threshold
        self._log_with_context(
            f"Query engine initialized (retrieval_timeout={retrieval_timeout}s, "
            f"similarity_threshold={similarity_threshold})"
        )
    
    def _log_with_context(self, message: str, level: str = "info", error: Optional[Exception] = None):
        """
        Log message with timestamp and context.
        
        Args:
            message: Log message
            level: Log level (info, warning, error, critical)
            error: Optional exception for error context
        
        Requirements: 14.4
        """
        timestamp = datetime.now().isoformat()
        context = f"[{timestamp}] [QueryEngine]"
        
        log_func = getattr(logger, level.lower(), logger.info)
        
        if error:
            log_func(f"{context} {message}: {str(error)}", exc_info=True)
        else:
            log_func(f"{context} {message}")
    
    def query(
        self,
        question: str,
        conversation_history: List[Dict[str, str]] = None,
        top_k: int = 5,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG with conversation context and graceful degradation.
        
        Implements graceful degradation:
        - If embedding generation fails, returns fallback message
        - If retrieval fails, returns fallback message
        - If LLM generation fails, uses template-based response
        - Continues serving subsequent requests after failures
        
        Args:
            question: User's current question
            conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            top_k: Number of similar chunks to retrieve (default: 5)
            timeout_seconds: Query timeout in seconds (default: 10)
            
        Returns:
            Dictionary with:
                - answer: Generated response text
                - sources: List of source documents with metadata
                - aggregated_amount: Optional total amount for spending queries
                - breakdown: Optional list of individual amounts
                - retrieval_time: Time taken for retrieval in seconds
        
        Requirements: 14.2, 14.3
        """
        try:
            self._log_with_context(f"Processing query: {question}")
            retrieval_start = time.time()
            
            # Build context-aware query by considering conversation history
            contextualized_question = self._contextualize_question(question, conversation_history or [])
            
            # Step 1: Generate question embedding with error handling
            self._log_with_context("Generating question embedding")
            try:
                question_embedding = self.embedding_engine.generate_embedding(contextualized_question)
            except Exception as e:
                self._log_with_context(
                    "Embedding generation failed, using fallback response",
                    level="error",
                    error=e
                )
                return {
                    "answer": "I'm having trouble processing your question right now. Please try again in a moment.",
                    "sources": [],
                    "aggregated_amount": None,
                    "breakdown": None,
                    "retrieval_time": 0.0
                }
            
            # Step 2: Extract metadata filters from question
            metadata_filter = self._extract_metadata_filters(question)
            self._log_with_context(f"Extracted metadata filters: {metadata_filter}")
            
            # Prepare filter for vector store (remove internal flags)
            vector_store_filter = None
            if metadata_filter:
                vector_store_filter = {k: v for k, v in metadata_filter.items() if not k.startswith('_')}
            
            # Step 3: Retrieve similar chunks from vector store with timeout and error handling
            self._log_with_context(f"Retrieving top {top_k} similar chunks (timeout: {self.retrieval_timeout}s)")
            try:
                results = self._retrieve_with_timeout(
                    question_embedding=question_embedding,
                    top_k=top_k,
                    metadata_filter=vector_store_filter
                )
            except Exception as e:
                self._log_with_context(
                    "Retrieval failed, using fallback response",
                    level="error",
                    error=e
                )
                return {
                    "answer": "I'm having trouble accessing the document database right now. Please try again in a moment.",
                    "sources": [],
                    "aggregated_amount": None,
                    "breakdown": None,
                    "retrieval_time": 0.0
                }
            
            retrieval_time = time.time() - retrieval_start
            self._log_with_context(f"Retrieval completed in {retrieval_time:.3f}s")
            
            # Step 4: Check if any results found (Requirement 6.4)
            if not results:
                self._log_with_context("No relevant chunks found", level="warning")
                return {
                    "answer": "I couldn't find any relevant information in your documents. Try rephrasing your question or processing more documents.",
                    "sources": [],
                    "aggregated_amount": None,
                    "breakdown": None,
                    "retrieval_time": retrieval_time
                }
            
            self._log_with_context(f"Retrieved {len(results)} chunks")
            
            # Generate general response (Requirement 7.1) with graceful degradation
            try:
                answer = self._generate_response(question, results, conversation_history)
            except Exception as e:
                self._log_with_context(
                    "General response generation failed, using fallback",
                    level="error",
                    error=e
                )
                answer = self._fallback_general_response(question, results, conversation_history)
            
            return {
                "answer": answer,
                "sources": self._format_sources(results, min_similarity_score=0.5),
                "aggregated_amount": None,
                "breakdown": None,
                "retrieval_time": retrieval_time
            }
        
        except Exception as e:
            self._log_with_context("Query failed with unexpected error", level="error", error=e)
            return {
                "answer": "An unexpected error occurred. Please try again.",
                "sources": [],
                "aggregated_amount": None,
                "breakdown": None,
                "retrieval_time": 0.0
            }
    
    def _retrieve_with_timeout(
        self,
        question_embedding: List[float],
        top_k: int,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[QueryResult]:
        """
        Retrieve similar chunks with timeout enforcement.
        
        Ensures retrieval completes within configured timeout (default 2 seconds for Pi mode).
        
        Args:
            question_embedding: Query embedding vector
            top_k: Number of results to retrieve
            metadata_filter: Optional metadata filters
            
        Returns:
            List of query results
            
        Raises:
            TimeoutError: If retrieval exceeds timeout
            
        Requirements: 6.2, 6.3, 6.5, 14.3
        """
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self.vector_store.query,
                query_embedding=question_embedding,
                top_k=top_k,
                metadata_filter=metadata_filter
            )
            
            try:
                results = future.result(timeout=self.retrieval_timeout)
                return results
            except FutureTimeoutError:
                self._log_with_context(
                    f"Retrieval timed out after {self.retrieval_timeout}s",
                    level="error"
                )
                # Cancel the future to free resources
                future.cancel()
                # Return empty results on timeout (Requirement 6.4)
                return []
            except Exception as e:
                self._log_with_context("Retrieval failed", level="error", error=e)
                return []
    
    def _contextualize_question(self, question: str, conversation_history: List[Dict[str, str]]) -> str:
        """
        Contextualize the current question using conversation history.
        
        Resolves pronouns and references to previous context.
        For example: "what card did i use?" becomes "what card did i use at costco?"
        
        Args:
            question: Current user question
            conversation_history: Previous messages in conversation
            
        Returns:
            Contextualized question for better retrieval
        """
        if not conversation_history or len(conversation_history) < 2:
            return question
        
        # Get last few messages for context
        recent_context = conversation_history[-4:]  # Last 2 exchanges
        
        # Build context string
        context_parts = []
        for msg in recent_context:
            if msg['role'] == 'user':
                context_parts.append(f"User asked: {msg['content']}")
            elif msg['role'] == 'assistant':
                # Only include key information from assistant responses
                content = msg['content'][:200]  # First 200 chars
                context_parts.append(f"Assistant mentioned: {content}")
        
        context_str = " ".join(context_parts)
        
        # If question has pronouns or references, add context
        has_reference = any(word in question.lower() for word in ['it', 'that', 'this', 'there', 'then'])
        
        if has_reference:
            return f"{context_str}. Now user asks: {question}"
        else:
            return question
    
    def _extract_metadata_filters(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata filters from the question.
        
        NOTE: Date filtering is NOT done via metadata filters because different documents
        use different field names (date, transaction_details_timestamp, etc.).
        Instead, we extract the date and use it for post-filtering and context.
        
        Args:
            question: User's question
            
        Returns:
            Dictionary of metadata filters or None (currently returns None as we don't use metadata filtering)
        """
        # Don't use metadata filters - they require exact field name matches
        # Different documents use different field names (date, timestamp, transaction_details_timestamp, etc.)
        # Instead, we'll do semantic search and let the LLM filter by date from the context
        return None
    
    def _extract_date(self, question: str) -> Optional[tuple]:
        """
        Extract and normalize date from question.
        
        Supports formats:
        - MMM DD, YYYY (e.g., "feb 11, 2026")
        - YYYY-MM-DD (e.g., "2026-02-11")
        - Month DD, YYYY (e.g., "February 11, 2026")
        - MMM DD (e.g., "feb 11") - defaults to current year, marked as ambiguous
        
        Args:
            question: User's question
            
        Returns:
            Tuple of (date_string, is_ambiguous) or None
            - date_string: Normalized date in YYYY-MM-DD format
            - is_ambiguous: True if year was inferred (not explicitly provided)
        """
        question_lower = question.lower()
        
        # Pattern 1: YYYY-MM-DD
        pattern1 = r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b'
        match = re.search(pattern1, question)
        if match:
            year, month, day = match.groups()
            return (f"{year}-{int(month):02d}-{int(day):02d}", False)
        
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
            # Pattern with year: "month DD, YYYY" or "month DD YYYY"
            pattern = rf'\b{month_name}\s+(\d{{1,2}}),?\s+(\d{{4}})\b'
            match = re.search(pattern, question_lower)
            if match:
                day, year = match.groups()
                return (f"{year}-{month_num:02d}-{int(day):02d}", False)
            
            # Pattern without year: "month DD" (default to current year, mark as ambiguous)
            pattern_no_year = rf'\b{month_name}\s+(\d{{1,2}})\b'
            match = re.search(pattern_no_year, question_lower)
            if match:
                day = match.group(1)
                # Default to current year (2026 based on system date)
                from datetime import datetime
                current_year = datetime.now().year
                return (f"{current_year}-{month_num:02d}-{int(day):02d}", True)
        
        return None
    
    
    def _detect_korean(self, text: str) -> bool:
        """
        Detect if text contains Korean characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains Korean characters, False otherwise
        """
        # Korean Unicode ranges: Hangul Syllables (AC00-D7AF), Hangul Jamo (1100-11FF)
        import re
        korean_pattern = re.compile(r'[\uac00-\ud7af\u1100-\u11ff]+')
        return bool(korean_pattern.search(text))
    
    def _translate_to_korean(self, english_text: str, amount: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Translate common English responses to Korean.
        
        Args:
            english_text: English response text
            amount: Optional amount value
            metadata: Optional flexible metadata dictionary
            
        Returns:
            Korean translation
        """
        # Simple template-based translation for common patterns
        if amount is not None:
            details = []
            if metadata:
                # Build details from available metadata dynamically
                for key, value in metadata.items():
                    details.append(str(value))
            
            if details:
                details_str = ' '.join(details)
                return f"{details_str}에서 ${amount:.2f}를 사용하셨습니다."
            else:
                return f"${amount:.2f}를 사용하셨습니다."
        
        # Fallback patterns
        if "couldn't find" in english_text.lower():
            return "관련 정보를 찾을 수 없습니다."
        elif "payment method" in english_text.lower():
            return "결제 수단 정보를 찾을 수 없습니다."
        
        # If no pattern matches, return English (better than nothing)
        return english_text
    
    def _is_repeated_question(
        self,
        question: str,
        conversation_history: List[Dict[str, str]]
    ) -> bool:
        """
        Check if the current question is similar to a previous question in the conversation.
        
        Args:
            question: Current user question
            conversation_history: List of previous messages
            
        Returns:
            True if question appears to be repeated, False otherwise
        """
        if not conversation_history:
            return False
        
        question_lower = question.lower().strip()
        
        # Extract key terms from current question
        key_terms = set()
        for term in ['digit', 'number', 'card', 'last 4', 'payment', 'when', 'date', 'where', 'location', 'store', 'how much', 'spend', 'spent']:
            if term in question_lower:
                key_terms.add(term)
        
        # Check if similar question was asked before
        for msg in conversation_history:
            if msg.get('role') == 'user':
                prev_question = msg.get('content', '').lower().strip()
                
                # Check for similar key terms
                matching_terms = 0
                for term in key_terms:
                    if term in prev_question:
                        matching_terms += 1
                
                # If most key terms match, consider it a repeated question
                if key_terms and matching_terms >= len(key_terms) * 0.7:
                    return True
        
        return False
    
    def _generate_response(
        self,
        question: str,
        results: List[QueryResult],
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generate a direct answer to the question using retrieved context and LLM.
        
        Uses LLM to generate natural, context-aware responses.
        
        Args:
            question: User's question
            results: Retrieved chunks
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response text
        """
        # Extract text chunks from results
        chunks = [result.content for result in results]
        
        # Use LLM to generate natural response
        try:
            return self.llm_generator.generate_general_response(
                question=question,
                retrieved_chunks=chunks,
                conversation_history=conversation_history
            )
        except Exception as e:
            logger.error(f"LLM generation failed, using fallback: {e}")
            # Fallback to template-based response
            return self._fallback_general_response(question, results, conversation_history)
    
    def _is_repeated_question(
        self,
        question: str,
        conversation_history: List[Dict[str, str]]
    ) -> bool:
        """
        Check if the current question is similar to a previous question in the conversation.

        Args:
            question: Current user question
            conversation_history: List of previous messages

        Returns:
            True if question appears to be repeated, False otherwise
        """
        if not conversation_history:
            return False

        question_lower = question.lower().strip()

        # Extract key terms from current question
        key_terms = set()
        for term in ['digit', 'number', 'card', 'last 4', 'payment', 'when', 'date', 'where', 'location', 'store', 'how much', 'spend', 'spent']:
            if term in question_lower:
                key_terms.add(term)

        # Check if similar question was asked before
        for msg in conversation_history:
            if msg.get('role') == 'user':
                prev_question = msg.get('content', '').lower().strip()

                # Check for similar key terms
                matching_terms = 0
                for term in key_terms:
                    if term in prev_question:
                        matching_terms += 1

                # If most key terms match, consider it a repeated question
                if key_terms and matching_terms >= len(key_terms) * 0.7:
                    return True

        return False

    
    def _fallback_general_response(
        self,
        question: str,
        results: List[QueryResult],
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Fallback template-based general response if LLM fails.
        
        Dynamically searches for relevant fields in metadata based on question keywords.
        
        Args:
            question: User's question
            results: Retrieved chunks
            conversation_history: Previous conversation messages
            
        Returns:
            Template-based response
        """
        question_lower = question.lower()
        is_repeated = self._is_repeated_question(question, conversation_history or [])
        
        # Dynamically search for relevant fields in metadata
        # Look for any field that might be relevant to the question
        for result in results:
            metadata = result.metadata
            
            # Payment/card questions - search for any payment-related fields
            if any(word in question_lower for word in ['card', 'payment', 'paid', 'pay', 'digit', 'number']):
                # Search for fields containing 'card', 'payment', 'digit', etc.
                relevant_fields = {}
                for key, value in metadata.items():
                    key_lower = key.lower()
                    if any(term in key_lower for term in ['card', 'payment', 'digit', 'number', 'method']):
                        relevant_fields[key] = value
                
                if relevant_fields:
                    # Format response with found fields
                    field_descriptions = []
                    for key, value in relevant_fields.items():
                        field_name = key.replace('_', ' ').title()
                        field_descriptions.append(f"{field_name}: {value}")
                    
                    return "I found: " + ", ".join(field_descriptions)
                else:
                    return "I couldn't find payment or card information in the documents."
            
            # Date/when questions - search for date-related fields
            if any(word in question_lower for word in ['when', 'date', 'time']):
                relevant_fields = {}
                for key, value in metadata.items():
                    key_lower = key.lower()
                    if any(term in key_lower for term in ['date', 'time', 'when']):
                        relevant_fields[key] = value
                
                if relevant_fields:
                    field_descriptions = []
                    for key, value in relevant_fields.items():
                        field_name = key.replace('_', ' ').title()
                        field_descriptions.append(f"{field_name}: {value}")
                    
                    return "I found: " + ", ".join(field_descriptions)
                else:
                    return "I couldn't find date information in the documents."
            
            # Location/where questions - search for location-related fields
            if any(word in question_lower for word in ['where', 'location', 'place', 'store', 'shop', 'vendor', 'seller']):
                relevant_fields = {}
                for key, value in metadata.items():
                    key_lower = key.lower()
                    if any(term in key_lower for term in ['location', 'place', 'store', 'shop', 'vendor', 'seller', 'where', 'address', 'business', 'company', 'name', 'from']):
                        relevant_fields[key] = value
                
                if relevant_fields:
                    field_descriptions = []
                    for key, value in relevant_fields.items():
                        field_name = key.replace('_', ' ').title()
                        field_descriptions.append(f"{field_name}: {value}")
                    
                    return "I found: " + ", ".join(field_descriptions)
                else:
                    return "I couldn't find location information in the documents."
        
        # General fallback - show content from best result
        if results:
            best_result = results[0]
            content = best_result.content[:300]
            return f"Based on the documents: {content}"
        
        return "I couldn't find specific information to answer that question in the documents."
    
    def _format_sources(self, results: List[QueryResult], min_similarity_score: float = 0.5) -> List[Dict[str, Any]]:
            """
            Format query results as source references.
            
            Dynamically includes all metadata fields without hardcoding specific field names.

            Args:
                results: List of query results
                min_similarity_score: Minimum similarity score threshold for filtering (default: 0.5)

            Returns:
                List of source dictionaries with similarity scores >= min_similarity_score
            """
            # Filter results by similarity score threshold
            filtered_results = [r for r in results if r.similarity_score >= min_similarity_score]

            # Log filtering for debugging
            filtered_count = len(results) - len(filtered_results)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} sources with similarity score < {min_similarity_score}")

            sources = []

            for result in filtered_results:
                source = {
                    'filename': result.metadata.get('filename', 'Unknown'),
                    'chunk': result.content[:200] + "..." if len(result.content) > 200 else result.content,
                    'score': round(result.similarity_score, 3),
                    'metadata': {}
                }

                # Dynamically add ALL metadata fields (no hardcoded field names)
                for key, value in result.metadata.items():
                    # Skip internal fields that start with underscore
                    if not key.startswith('_'):
                        source['metadata'][key] = value

                sources.append(source)

            return sources



# Singleton instance for reuse across the application
_query_engine_instance = None


def get_query_engine(retrieval_timeout: float = 2.0, similarity_threshold: float = 0.3) -> QueryEngine:
    """
    Get or create the singleton query engine instance.
    
    Args:
        retrieval_timeout: Maximum time in seconds for retrieval operations (default: 2.0)
        similarity_threshold: Minimum similarity score for results (default: 0.3)
    
    Returns:
        QueryEngine instance configured for Pi mode
    """
    global _query_engine_instance
    if _query_engine_instance is None:
        _query_engine_instance = QueryEngine(
            retrieval_timeout=retrieval_timeout,
            similarity_threshold=similarity_threshold
        )
    return _query_engine_instance
