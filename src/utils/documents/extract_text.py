"""
Document text extraction module.
Supports PDF, DOCX, and TXT files with AI summarization.
"""

import os
from typing import Dict, Any
from werkzeug.datastructures import FileStorage
from anthropic import Anthropic

PREVIEW_CHAR_LIMIT = 1500
SUMMARY_CHAR_LIMIT = 12000
SUMMARY_PROMPT = 'Summarize this document in 3 sentences.'


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return filename.lower().split('.')[-1] if '.' in filename else ''


def is_pdf(file: FileStorage) -> bool:
    """Check if file is a PDF."""
    ext = get_file_extension(file.filename or '')
    return file.content_type == 'application/pdf' or ext == 'pdf'


def is_docx(file: FileStorage) -> bool:
    """Check if file is a DOCX."""
    ext = get_file_extension(file.filename or '')
    return (
        file.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        or ext == 'docx'
    )


def is_plain_text(file: FileStorage) -> bool:
    """Check if file is plain text."""
    ext = get_file_extension(file.filename or '')
    content_type = file.content_type or ''
    return content_type.startswith('text/') or ext in ('txt', 'md', 'csv', 'log')


def extract_pdf_text(file_data: bytes) -> str:
    """Extract text from PDF using pypdf."""
    try:
        from pypdf import PdfReader
        from io import BytesIO
        
        pdf_file = BytesIO(file_data)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return '\n'.join(text_parts)
    except Exception as e:
        raise Exception(f"Failed to parse PDF file: {str(e)}")


def extract_docx_text(file_data: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
        from io import BytesIO
        
        docx_file = BytesIO(file_data)
        doc = Document(docx_file)
        
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text:
                text_parts.append(paragraph.text)
        
        return '\n'.join(text_parts)
    except Exception as e:
        raise Exception(f"Failed to parse DOCX file: {str(e)}")


def extract_plain_text(file_data: bytes) -> str:
    """Extract text from plain text file."""
    try:
        return file_data.decode('utf-8')
    except UnicodeDecodeError:
        # Try with latin-1 as fallback
        return file_data.decode('latin-1')


def convert_file_to_text(file: FileStorage) -> str:
    """Convert uploaded file to text based on type."""
    file_data = file.read()
    file.seek(0)  # Reset file pointer
    
    if is_pdf(file):
        return extract_pdf_text(file_data)
    elif is_docx(file):
        return extract_docx_text(file_data)
    elif is_plain_text(file):
        return extract_plain_text(file_data)
    else:
        raise ValueError(f"Unsupported file type: {file.content_type}")


def truncate(text: str, limit: int) -> str:
    """Truncate text to specified character limit."""
    return text[:limit] if len(text) > limit else text


def summarize_text(text: str) -> str:
    """Summarize text using Anthropic Claude."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or 'placeholder' in api_key.lower():
        # Gracefully handle missing/invalid API key for local testing
        return f"[Summary unavailable - document processed successfully. {len(text)} characters extracted.]"
    
    try:
        truncated = truncate(text, SUMMARY_CHAR_LIMIT)
        prompt = f"{SUMMARY_PROMPT}\n\n{truncated}"
        
        client = Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
            max_tokens=400,
            system='You are a helpful assistant that summarizes documents.',
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        # Extract text from response
        for block in response.content:
            if block.type == 'text':
                return block.text.strip()
        
        return ''
    except Exception as e:
        # Fallback if API call fails
        return f"[Summary unavailable - {str(e)[:50]}... Document processed successfully.]"


def extract_text(file: FileStorage) -> Dict[str, str]:
    """
    Extract and process text from uploaded file.
    
    Returns:
        Dict with fullText, firstChunks, and summary
    """
    full_text = convert_file_to_text(file)
    first_chunks = truncate(full_text, PREVIEW_CHAR_LIMIT)
    summary = summarize_text(full_text)
    
    return {
        'fullText': full_text,
        'firstChunks': first_chunks,
        'summary': summary
    }

