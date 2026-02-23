"""
LLM Generator for natural language response generation.

Uses either Ollama (local) or Groq (cloud API) for generating responses.

Enhanced with:
- Groq API support for fast cloud responses
- 10-second timeout for response generation (Pi mode)
- Error logging with timestamps and context
- Graceful fallback to template-based responses
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from backend.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class LLMGenerator:
    """
    Generator for natural language responses using LLM.
    
    Features:
    - Supports both Ollama (local) and Groq (cloud API)
    - 10-second timeout for response generation (Pi mode)
    - Error logging with timestamps and context
    - Graceful fallback to template-based responses
    
    Requirements: 7.5, 14.3, 14.4
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None, groq_client=None, config=None):
        """
        Initialize LLM generator.
        
        Args:
            ollama_client: OllamaClient instance (creates new one if None)
            groq_client: GroqClient instance (creates new one if USE_GROQ=true)
            config: Config instance for model configuration (uses default if None)
        """
        from backend.config import Config
        self.config = config or Config
        self.use_groq = self.config.USE_GROQ
        
        if self.use_groq:
            # Use Groq API for responses
            if groq_client is None:
                from backend.groq_client import GroqClient
                groq_client = GroqClient(
                    api_key=self.config.GROQ_API_KEY,
                    model=self.config.GROQ_MODEL
                )
            self.client = groq_client
            self._log_with_context(f"LLM generator initialized with Groq: {self.config.GROQ_MODEL}")
        else:
            # Use Ollama for responses
            if self.config.ENABLE_DOCUMENT_PROCESSING:
                # Desktop mode - use the powerful model
                self.conversation_model = self.config.OLLAMA_MODEL
            else:
                # Pi mode - use the lightweight model
                self.conversation_model = self.config.CONVERSATIONAL_MODEL
            
            # Create client with 60-second timeout for Pi mode response generation
            self.client = ollama_client or OllamaClient(
                model=self.conversation_model,
                timeout=60
            )
            self._log_with_context(f"LLM generator initialized with Ollama: {self.conversation_model}")
    
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
        context = f"[{timestamp}] [LLMGenerator]"
        
        log_func = getattr(logger, level.lower(), logger.info)
        
        if error:
            log_func(f"{context} {message}: {str(error)}", exc_info=True)
        else:
            log_func(f"{context} {message}")
    
    def generate_spending_response(
        self,
        question: str,
        aggregated_amount: float,
        breakdown: List[Dict[str, Any]],
        is_ambiguous_date: bool = False
    ) -> str:
        """
        Generate natural response for spending queries with timeout handling.
        
        Args:
            question: User's question
            aggregated_amount: Total amount spent
            breakdown: List of individual transactions with flexible metadata
            is_ambiguous_date: Whether the date was inferred (not explicitly provided)
            
        Returns:
            Generated response text
        
        Requirements: 7.5, 14.3
        """
        # Detect language from question
        is_korean = self._detect_korean(question)
        
        # Build context from breakdown - use flexible metadata
        context_parts = []
        for item in breakdown:
            # Format each transaction dynamically based on available fields
            item_parts = []
            for key, value in item.items():
                if key not in ['amount']:  # Skip amount as we'll format it separately
                    field_name = key.replace('_', ' ').title()
                    item_parts.append(f"{field_name}: {value}")
            
            # Add amount if present
            if 'amount' in item:
                item_parts.append(f"Amount: ${item['amount']:.2f}")
            
            context_parts.append(f"- {', '.join(item_parts)}")
        context = "\n".join(context_parts)
        
        # Build prompt
        if is_korean:
            prompt = f"""당신은 한국어로 대화하는 친절한 재무 어시스턴트입니다.

사용자 질문: {question}

찾은 거래 내역:
{context}

총액: ${aggregated_amount:.2f}

지침:
- 반드시 한국어로만 답변하세요
- 자연스럽고 친근한 톤으로 답변하세요
- 총액과 관련 거래 정보를 명확하게 전달하세요
"""
            if is_ambiguous_date:
                prompt += "- 날짜가 명확하지 않으면 확인을 요청하세요\n"
            
            prompt += "\n답변:"
        else:
            prompt = f"""You are a helpful financial assistant.

User question: {question}

Found transactions:
{context}

Total: ${aggregated_amount:.2f}

Instructions:
- Answer in English only
- Use a natural, friendly tone
- Clearly communicate the total and relevant transaction details
"""
            if is_ambiguous_date:
                prompt += "- If the date is ambiguous, ask for confirmation\n"
            
            prompt += "\nResponse:"
        
        # Generate response with timeout (10 seconds for Pi mode)
        try:
            response = self.client.generate(
                prompt=prompt,
                stream=False
            )
            
            answer = response.get("response", "").strip()
            return answer if answer else self._fallback_spending_response(
                question, aggregated_amount, breakdown, is_ambiguous_date
            )
            
        except Exception as e:
            self._log_with_context("LLM generation failed for spending response", level="error", error=e)
            return self._fallback_spending_response(
                question, aggregated_amount, breakdown, is_ambiguous_date
            )
    
    def generate_general_response(
        self,
        question: str,
        retrieved_results: List = None,
        retrieved_chunks: List[str] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generate natural response for general document queries with timeout handling.
        
        Args:
            question: User's question
            retrieved_results: List of QueryResult objects with metadata (preferred)
            retrieved_chunks: List of relevant text chunks (fallback for backward compatibility)
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response text
        
        Requirements: 7.5, 14.3
        """
        # Detect language from question
        is_korean = self._detect_korean(question)
        
        # Build context from results (with filenames) or chunks (fallback)
        context_parts = []
        if retrieved_results:
            for i, result in enumerate(retrieved_results):
                filename = result.metadata.get('filename', f'Document {i+1}')
                context_parts.append(f"=== {filename} ===\n{result.content}")
        elif retrieved_chunks:
            for i, chunk in enumerate(retrieved_chunks):
                context_parts.append(f"=== Document {i+1} ===\n{chunk}")
        
        context = "\n\n".join(context_parts)
        
        # Build conversation context
        conv_context = ""
        if conversation_history:
            recent = conversation_history[-4:]  # Last 2 exchanges
            conv_parts = []
            for msg in recent:
                role = "사용자" if msg['role'] == 'user' else "어시스턴트" if is_korean else msg['role'].capitalize()
                conv_parts.append(f"{role}: {msg['content'][:150]}")
            conv_context = "\n".join(conv_parts)
        
        # Build prompt with clear instructions
        if is_korean:
            prompt = f"""당신은 한국어로 대화하는 문서 분석 어시스턴트입니다.

중요한 규칙:
- 반드시 한국어로만 답변하세요
- 아래 {len(context_parts)}개의 모든 문서를 확인하세요
- "총", "전체", "모두" 같은 단어가 있으면 관련된 모든 문서를 찾아서 합산하세요
- 실제 파일명을 사용하세요 (예: IMG_4025.jpeg)
- 문서에 없는 정보는 추측하지 마세요

합산 예시:
질문: "코스트코에서 총 얼마 썼어?"
답변: "코스트코에서 총 $411.89를 사용했습니다 (IMG_4025.jpeg: $222.18, KakaoTalk_xxx.jpg: $189.71)"

"""
            if conv_context:
                prompt += f"이전 대화:\n{conv_context}\n\n"
            
            prompt += f"""관련 문서 ({len(context_parts)}개):
{context}

질문: {question}

답변:"""
        else:
            prompt = f"""You are a helpful document analysis assistant.

Important rules:
- Answer ONLY in English
- Check ALL {len(context_parts)} documents provided below
- If the question asks for "total", "all", or "sum", find ALL related documents and aggregate
- Use actual filenames (e.g., IMG_4025.jpeg), not "Document 1"
- Don't make assumptions about information not in the documents

Aggregation example:
Question: "How much did I spend at Costco in total?"
Answer: "You spent $411.89 total at Costco (IMG_4025.jpeg: $222.18, KakaoTalk_xxx.jpg: $189.71)"

"""
            if conv_context:
                prompt += f"Previous conversation:\n{conv_context}\n\n"
            
            prompt += f"""Relevant documents ({len(context_parts)} documents):
{context}

Question: {question}

Answer:"""
        
        # Generate response with timeout (10 seconds for Pi mode)
        try:
            response = self.client.generate(
                prompt=prompt,
                stream=False
            )
            
            answer = response.get("response", "").strip()
            
            # Validate language consistency
            if is_korean and self._contains_chinese(answer):
                self._log_with_context("LLM mixed Chinese in Korean response, regenerating", level="warning")
                # Try one more time with stronger emphasis
                return self._regenerate_with_emphasis(question, context, conv_context, is_korean)
            
            # Return answer or fallback message
            if answer:
                return answer
            else:
                # Fallback message in appropriate language
                if is_korean:
                    return "응답을 생성할 수 없습니다. 질문을 다시 표현해 주세요."
                else:
                    return "I couldn't generate a response. Please try rephrasing your question."
            
        except Exception as e:
            self._log_with_context("LLM generation failed for general response", level="error", error=e)
            # Fallback message on generation failure
            if is_korean:
                return "응답 생성에 실패했습니다. 다시 시도해 주세요."
            else:
                return "Failed to generate response. Please try again."
    
    def _regenerate_with_emphasis(
        self,
        question: str,
        context: str,
        conv_context: str,
        is_korean: bool
    ) -> str:
        """
        Regenerate response with stronger language emphasis.
        
        Args:
            question: User's question
            context: Document context
            conv_context: Conversation context
            is_korean: Whether to respond in Korean
            
        Returns:
            Regenerated response
        """
        if is_korean:
            prompt = f"""당신은 한국어 전용 어시스턴트입니다.

!!! 경고: 중국어나 다른 언어를 절대 사용하지 마세요 !!!
!!! 오직 한국어로만 답변하세요 !!!

"""
            if conv_context:
                prompt += f"이전 대화:\n{conv_context}\n\n"
            
            prompt += f"""문서:
{context}

질문: {question}

한국어 답변:"""
        else:
            prompt = f"""You are an English-only assistant.

!!! WARNING: DO NOT use Chinese or other languages !!!
!!! Answer ONLY in English !!!

"""
            if conv_context:
                prompt += f"Previous conversation:\n{conv_context}\n\n"
            
            prompt += f"""Documents:
{context}

Question: {question}

English response:"""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                stream=False
            )
            return response.get("response", "").strip()
        except:
            return "Failed to generate response."
    
    def _detect_korean(self, text: str) -> bool:
        """
        Detect if text contains Korean characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains Korean, False otherwise
        """
        import re
        korean_pattern = re.compile(r'[\uac00-\ud7af\u1100-\u11ff]+')
        return bool(korean_pattern.search(text))
    
    def _contains_chinese(self, text: str) -> bool:
        """
        Detect if text contains Chinese characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains Chinese, False otherwise
        """
        import re
        # Chinese Unicode ranges
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        return bool(chinese_pattern.search(text))
    
    def _fallback_spending_response(
        self,
        question: str,
        aggregated_amount: float,
        breakdown: List[Dict[str, Any]],
        is_ambiguous_date: bool
    ) -> str:
        """
        Fallback template-based spending response.
        
        Args:
            question: User's question
            aggregated_amount: Total amount
            breakdown: Transaction breakdown with flexible metadata
            is_ambiguous_date: Whether date was ambiguous
            
        Returns:
            Template-based response
        """
        is_korean = self._detect_korean(question)
        
        if len(breakdown) == 1:
            item = breakdown[0]
            # Build description from available fields dynamically
            details = []
            for key, value in item.items():
                if key != 'amount':
                    details.append(str(value))
            
            details_str = ' '.join(details) if details else "this transaction"
            
            if is_korean:
                response = f"{details_str}에서 ${aggregated_amount:.2f}를 사용하셨습니다."
                if is_ambiguous_date:
                    response += " 찾으시던 영수증이 맞나요?"
            else:
                response = f"You spent ${aggregated_amount:.2f} for {details_str}."
                if is_ambiguous_date:
                    response += " Is this the receipt you were looking for?"
        else:
            if is_korean:
                response = f"총 ${aggregated_amount:.2f}를 사용하셨습니다."
            else:
                response = f"You spent a total of ${aggregated_amount:.2f}."
        
        return response


# Singleton instance
_llm_generator_instance = None


def get_llm_generator() -> LLMGenerator:
    """
    Get or create the singleton LLM generator instance.
    
    Returns:
        LLMGenerator instance
    """
    global _llm_generator_instance
    if _llm_generator_instance is None:
        _llm_generator_instance = LLMGenerator()
    return _llm_generator_instance
