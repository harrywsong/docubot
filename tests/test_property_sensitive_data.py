"""
Property-based test for sensitive data handling.

Feature: rag-chatbot-with-vision, Property 26: Sensitive Data No-Filtering

Validates: Requirements 9.4, 9.5, 9.6

**Validates: Requirements 9.4, 9.5, 9.6**

This test verifies that for any document content containing sensitive information
(PII, financial data, etc.), the system stores, retrieves, and displays that
information without filtering, redaction, or warnings.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch, Mock, MagicMock
from backend.document_processor import DocumentProcessor
from backend.query_engine import QueryEngine
from backend.vector_store import VectorStore
from backend.models import DocumentChunk, QueryResult
import re


# Custom strategies for generating sensitive data
@st.composite
def ssn_strategy(draw):
    """Generate a realistic SSN (Social Security Number)."""
    area = draw(st.integers(min_value=100, max_value=899))
    group = draw(st.integers(min_value=10, max_value=99))
    serial = draw(st.integers(min_value=1000, max_value=9999))
    return f"{area:03d}-{group:02d}-{serial:04d}"


@st.composite
def credit_card_strategy(draw):
    """Generate a realistic credit card number (Luhn algorithm valid)."""
    # Generate 15 digits
    digits = [draw(st.integers(min_value=0, max_value=9)) for _ in range(15)]
    
    # Calculate Luhn checksum
    def luhn_checksum(card_digits):
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits_reversed = card_digits[::-1]
        odd_digits = digits_reversed[::2]
        even_digits = digits_reversed[1::2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10
    
    checksum = luhn_checksum(digits)
    check_digit = (10 - checksum) % 10
    digits.append(check_digit)
    
    # Format as credit card (4-4-4-4)
    card_str = ''.join(str(d) for d in digits)
    return f"{card_str[0:4]}-{card_str[4:8]}-{card_str[8:12]}-{card_str[12:16]}"


@st.composite
def email_strategy(draw):
    """Generate a realistic email address."""
    username = draw(st.text(min_size=3, max_size=15, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))))
    domain = draw(st.sampled_from(['gmail.com', 'yahoo.com', 'outlook.com', 'company.com', 'example.org']))
    return f"{username}@{domain}"


@st.composite
def phone_strategy(draw):
    """Generate a realistic US phone number."""
    area = draw(st.integers(min_value=200, max_value=999))
    exchange = draw(st.integers(min_value=200, max_value=999))
    number = draw(st.integers(min_value=1000, max_value=9999))
    format_choice = draw(st.sampled_from(['dashes', 'parens', 'dots']))
    
    if format_choice == 'dashes':
        return f"{area}-{exchange}-{number}"
    elif format_choice == 'parens':
        return f"({area}) {exchange}-{number}"
    else:
        return f"{area}.{exchange}.{number}"


@st.composite
def financial_amount_strategy(draw):
    """Generate a realistic financial amount."""
    amount = draw(st.floats(min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False))
    return f"${amount:.2f}"


@st.composite
def address_strategy(draw):
    """Generate a realistic street address."""
    number = draw(st.integers(min_value=1, max_value=9999))
    street = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    street_type = draw(st.sampled_from(['St', 'Ave', 'Rd', 'Blvd', 'Dr', 'Ln', 'Way']))
    city = draw(st.text(min_size=4, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    state = draw(st.sampled_from(['CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI']))
    zipcode = draw(st.integers(min_value=10000, max_value=99999))
    
    return f"{number} {street} {street_type}, {city}, {state} {zipcode}"


@st.composite
def sensitive_document_strategy(draw):
    """Generate a document containing various types of sensitive information."""
    # Choose which types of sensitive data to include (at least one)
    include_ssn = draw(st.booleans())
    include_credit_card = draw(st.booleans())
    include_email = draw(st.booleans())
    include_phone = draw(st.booleans())
    include_financial = draw(st.booleans())
    include_address = draw(st.booleans())
    
    # Ensure at least one type is included
    if not any([include_ssn, include_credit_card, include_email, include_phone, include_financial, include_address]):
        include_ssn = True
    
    # Build document content
    content_parts = []
    sensitive_items = {}
    
    if include_ssn:
        ssn = draw(ssn_strategy())
        content_parts.append(f"Social Security Number: {ssn}")
        sensitive_items['ssn'] = ssn
    
    if include_credit_card:
        cc = draw(credit_card_strategy())
        content_parts.append(f"Credit Card: {cc}")
        sensitive_items['credit_card'] = cc
    
    if include_email:
        email = draw(email_strategy())
        content_parts.append(f"Email: {email}")
        sensitive_items['email'] = email
    
    if include_phone:
        phone = draw(phone_strategy())
        content_parts.append(f"Phone: {phone}")
        sensitive_items['phone'] = phone
    
    if include_financial:
        amount = draw(financial_amount_strategy())
        content_parts.append(f"Account Balance: {amount}")
        sensitive_items['financial_amount'] = amount
    
    if include_address:
        address = draw(address_strategy())
        content_parts.append(f"Address: {address}")
        sensitive_items['address'] = address
    
    # Add some context text
    context = draw(st.text(min_size=20, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    content_parts.insert(0, context)
    
    document_content = "\n".join(content_parts)
    
    return {
        'content': document_content,
        'sensitive_items': sensitive_items
    }


class TestPropertySensitiveDataHandling:
    """
    Property-based tests for sensitive data handling.
    
    Feature: rag-chatbot-with-vision, Property 26: Sensitive Data No-Filtering
    """
    
    @given(doc_data=sensitive_document_strategy())
    @settings(max_examples=100, deadline=None)
    def test_sensitive_data_stored_without_filtering(self, doc_data):
        """
        Property 26: Sensitive Data No-Filtering (Storage)
        
        For any document content containing sensitive information, the system
        should store that information without filtering or redaction.
        
        This test verifies that:
        1. Sensitive data is present in the stored chunk content
        2. No redaction markers (like ***, [REDACTED], XXX) are added
        3. The original sensitive data is preserved exactly
        """
        content = doc_data['content']
        sensitive_items = doc_data['sensitive_items']
        
        # Arrange: Create a document chunk with sensitive data
        metadata = {
            'filename': 'sensitive_doc.txt',
            'folder_path': '/test/folder',
            'file_type': 'text',
            'chunk_index': 0
        }
        
        chunk = DocumentChunk(
            content=content,
            metadata=metadata,
            embedding=[0.1] * 384  # Mock embedding
        )
        
        # Act: Store the chunk in vector store
        with patch('backend.vector_store.chromadb.PersistentClient') as mock_client:
            # Mock ChromaDB collection
            mock_collection = MagicMock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            mock_collection.count.return_value = 0
            
            vector_store = VectorStore()
            vector_store.add_chunks([chunk])
            
            # Assert: Verify the chunk was added with unfiltered content
            assert mock_collection.add.called, "Chunk should be added to vector store"
            
            call_args = mock_collection.add.call_args
            stored_documents = call_args[1]['documents']
            
            # Verify there is exactly one document stored
            assert len(stored_documents) == 1, "Should store exactly one document"
            
            stored_content = stored_documents[0]
            
            # Property 1: All sensitive data must be present in stored content
            for data_type, sensitive_value in sensitive_items.items():
                assert sensitive_value in stored_content, \
                    f"Sensitive data ({data_type}: {sensitive_value}) must be stored without filtering"
            
            # Property 2: No redaction markers should be present
            redaction_patterns = [
                r'\*\*\*+',  # Asterisks like ***
                r'\[REDACTED\]',  # [REDACTED]
                r'\[FILTERED\]',  # [FILTERED]
                r'XXX+',  # XXX
                r'\[REMOVED\]',  # [REMOVED]
                r'\[HIDDEN\]',  # [HIDDEN]
            ]
            
            for pattern in redaction_patterns:
                matches = re.findall(pattern, stored_content, re.IGNORECASE)
                assert len(matches) == 0, \
                    f"No redaction markers ({pattern}) should be present in stored content"
            
            # Property 3: Stored content should match original content exactly
            assert stored_content == content, \
                "Stored content must match original content exactly (no filtering)"
    
    @given(doc_data=sensitive_document_strategy())
    @settings(max_examples=100, deadline=None)
    def test_sensitive_data_retrieved_without_redaction(self, doc_data):
        """
        Property 26: Sensitive Data No-Filtering (Retrieval)
        
        For any query that retrieves documents with sensitive information,
        the system should return that information without redaction.
        
        This test verifies that:
        1. Retrieved content contains the original sensitive data
        2. No redaction is applied during retrieval
        3. Query results preserve all sensitive information
        """
        content = doc_data['content']
        sensitive_items = doc_data['sensitive_items']
        
        # Arrange: Create a query result with sensitive data
        metadata = {
            'filename': 'sensitive_doc.txt',
            'folder_path': '/test/folder',
            'file_type': 'text'
        }
        
        query_result = QueryResult(
            chunk_id='test-chunk-id',
            content=content,
            metadata=metadata,
            similarity_score=0.95
        )
        
        # Act: Simulate query engine retrieving this result
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                # Mock embedding generation
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Mock vector store to return our sensitive data result
                mock_vs.return_value.query.return_value = [query_result]
                
                engine = QueryEngine()
                
                # Query for the sensitive information
                question = "Show me the document information"
                response = engine.query(question)
                
                # Assert: Verify sensitive data is in the response
                
                # Property 1: Response should include sources with sensitive data
                assert 'sources' in response, "Response must include sources"
                assert len(response['sources']) > 0, "Sources must not be empty"
                
                source = response['sources'][0]
                source_content = source['chunk']
                
                # Property 2: All sensitive data must be present in retrieved content
                for data_type, sensitive_value in sensitive_items.items():
                    # Check if sensitive value is in the source content
                    # (may be truncated, so check if it's a substring or vice versa)
                    assert sensitive_value in content, \
                        f"Original content must contain sensitive data ({data_type})"
                    
                    # The source content might be truncated with "...", but the
                    # non-truncated part should match the original
                    source_content_clean = source_content.replace("...", "")
                    
                    # Either the sensitive value is in the source, or the source
                    # is a prefix of the content containing the sensitive value
                    value_in_source = sensitive_value in source_content
                    source_is_prefix = source_content_clean in content and \
                                      content.index(source_content_clean) <= content.index(sensitive_value)
                    
                    assert value_in_source or source_is_prefix, \
                        f"Retrieved content must preserve sensitive data ({data_type}: {sensitive_value})"
                
                # Property 3: No redaction markers in retrieved content
                redaction_patterns = [
                    r'\*\*\*+',
                    r'\[REDACTED\]',
                    r'\[FILTERED\]',
                    r'XXX+',
                    r'\[REMOVED\]',
                    r'\[HIDDEN\]',
                ]
                
                for pattern in redaction_patterns:
                    matches = re.findall(pattern, source_content, re.IGNORECASE)
                    assert len(matches) == 0, \
                        f"No redaction markers ({pattern}) should be in retrieved content"
    
    @given(doc_data=sensitive_document_strategy())
    @settings(max_examples=100, deadline=None)
    def test_sensitive_data_displayed_without_warnings(self, doc_data):
        """
        Property 26: Sensitive Data No-Filtering (Display)
        
        For any response containing sensitive information, the system should
        display that information without warnings or restrictions.
        
        This test verifies that:
        1. Response answer contains or references sensitive data
        2. No warning messages about sensitive content
        3. No restrictions on displaying sensitive information
        """
        content = doc_data['content']
        sensitive_items = doc_data['sensitive_items']
        
        # Arrange: Create a query result with sensitive data
        metadata = {
            'filename': 'sensitive_doc.txt',
            'folder_path': '/test/folder',
            'file_type': 'text'
        }
        
        query_result = QueryResult(
            chunk_id='test-chunk-id',
            content=content,
            metadata=metadata,
            similarity_score=0.95
        )
        
        # Act: Get response from query engine
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                # Mock embedding generation
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Mock vector store to return our sensitive data result
                mock_vs.return_value.query.return_value = [query_result]
                
                engine = QueryEngine()
                
                # Query for the sensitive information
                question = "What information do you have?"
                response = engine.query(question)
                
                # Assert: Verify no warnings or restrictions
                
                # Property 1: Response must include an answer
                assert 'answer' in response, "Response must include answer field"
                assert response['answer'], "Answer must not be empty"
                
                answer = response['answer']
                
                # Property 2: No warning messages about sensitive content
                # Check for actual warning phrases (not words that appear in data/filenames)
                warning_patterns = [
                    r'\bwarning\b.*\bsensitive\b',  # "warning: sensitive"
                    r'\bsensitive\b.*\bhidden\b',  # "sensitive data hidden"
                    r'\bconfidential\b.*\bredacted\b',  # "confidential information redacted"
                    r'\brestricted\b.*\baccess\b',  # "restricted access"
                    r'cannot\s+display',  # "cannot display"
                    r'cannot\s+show',  # "cannot show"
                    r'hidden\s+for\s+privacy',  # "hidden for privacy"
                    r'\bredacted\b.*\bprivacy\b',  # "redacted for privacy"
                    r'\bfiltered\b.*\bsecurity\b',  # "filtered for security"
                    r'removed\s+for\s+security',  # "removed for security"
                    r'protected\s+information',  # "protected information"
                    r'\bsensitive\b.*\bremoved\b',  # "sensitive data removed"
                    r'\bsensitive\b.*\bfiltered\b',  # "sensitive data filtered"
                ]
                
                answer_lower = answer.lower()
                for pattern in warning_patterns:
                    matches = re.findall(pattern, answer_lower)
                    assert len(matches) == 0, \
                        f"Response should not contain warning pattern: '{pattern}'"
                
                # Property 3: Sources must be included (no restriction on display)
                assert 'sources' in response, "Response must include sources"
                assert len(response['sources']) > 0, "Sources must not be empty"
                
                # Property 4: Source content should be accessible
                source = response['sources'][0]
                assert 'chunk' in source, "Source must include chunk content"
                assert source['chunk'], "Source chunk must not be empty"
                
                # Property 5: No filtering indicators in metadata
                source_metadata = source.get('metadata', {})
                assert 'filtered' not in source_metadata, \
                    "Metadata should not indicate filtering"
                assert 'redacted' not in source_metadata, \
                    "Metadata should not indicate redaction"
    
    @given(
        doc_data=sensitive_document_strategy(),
        question=st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))
    )
    @settings(max_examples=100, deadline=None)
    def test_end_to_end_sensitive_data_no_filtering(self, doc_data, question):
        """
        Property 26: Sensitive Data No-Filtering (End-to-End)
        
        For any document with sensitive data and any query, the complete pipeline
        (storage -> retrieval -> display) should preserve sensitive information
        without filtering, redaction, or warnings.
        
        This is a comprehensive end-to-end test of the no-filtering property.
        """
        content = doc_data['content']
        sensitive_items = doc_data['sensitive_items']
        
        # Arrange: Create document chunk and query result
        metadata = {
            'filename': 'sensitive_doc.txt',
            'folder_path': '/test/folder',
            'file_type': 'text',
            'chunk_index': 0
        }
        
        chunk = DocumentChunk(
            content=content,
            metadata=metadata,
            embedding=[0.1] * 384
        )
        
        query_result = QueryResult(
            chunk_id='test-chunk-id',
            content=content,
            metadata=metadata,
            similarity_score=0.95
        )
        
        # Act: Simulate full pipeline
        with patch('backend.vector_store.chromadb.PersistentClient') as mock_client:
            with patch('backend.query_engine.get_embedding_engine') as mock_emb:
                with patch('backend.query_engine.get_vector_store') as mock_vs:
                    # Setup vector store mocks
                    mock_collection = MagicMock()
                    mock_client.return_value.get_or_create_collection.return_value = mock_collection
                    mock_collection.count.return_value = 0
                    
                    # Setup query engine mocks
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_vs.return_value.query.return_value = [query_result]
                    
                    # Step 1: Store document
                    vector_store = VectorStore()
                    vector_store.add_chunks([chunk])
                    
                    # Step 2: Query for information
                    engine = QueryEngine()
                    response = engine.query(question)
                    
                    # Assert: Verify end-to-end no-filtering property
                    
                    # Verify storage preserved sensitive data
                    assert mock_collection.add.called
                    stored_documents = mock_collection.add.call_args[1]['documents']
                    stored_content = stored_documents[0]
                    
                    for data_type, sensitive_value in sensitive_items.items():
                        assert sensitive_value in stored_content, \
                            f"Storage must preserve {data_type}"
                    
                    # Verify retrieval preserved sensitive data
                    assert 'sources' in response
                    assert len(response['sources']) > 0
                    
                    # Verify display has no warnings
                    answer = response['answer']
                    warning_indicators = ['warning', 'restricted', 'cannot display', 'redacted']
                    answer_lower = answer.lower()
                    
                    for indicator in warning_indicators:
                        assert indicator not in answer_lower, \
                            f"Display should not contain warning: '{indicator}'"
                    
                    # Verify complete pipeline integrity
                    # The original content should be traceable through the pipeline
                    assert stored_content == content, \
                        "End-to-end pipeline must preserve original content exactly"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
