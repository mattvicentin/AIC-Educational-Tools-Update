#!/usr/bin/env python3
"""
helpers.py
Purpose: General utility functions for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

General utility functions for validation, sanitization, and common operations
"""

import re
import html
from typing import Optional, Any, Dict, List
from flask import current_app, request, g
import logging


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS attacks."""
    if not text:
        return ""
    
    # HTML escape
    text = html.escape(text)
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    
    return text.strip()


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """Validate username format."""
    if not username:
        return False
    
    # Username should be 3-20 characters, alphanumeric and underscores only
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength and return detailed feedback."""
    if not password:
        return {"valid": False, "errors": ["Password cannot be empty"]}
    
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": "strong" if len(errors) == 0 else "weak"
    }


def log_security_event(event_type: str, details: Dict[str, Any], user_id: Optional[int] = None) -> None:
    """Log security-related events for monitoring."""
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": get_client_ip(),
        "details": details,
        "timestamp": get_current_timestamp()
    }
    
    logging.warning(f"Security event: {log_data}")


def get_client_ip() -> str:
    """Get client IP address, handling proxies."""
    if 'X-Forwarded-For' in request.headers:
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def rate_limit_key() -> str:
    """Generate rate limiting key based on user and endpoint."""
    user_id = getattr(g, 'user_id', None)
    endpoint = request.endpoint or 'unknown'
    return f"{user_id}:{endpoint}:{get_client_ip()}"


def validate_json_payload(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """Validate JSON payload and return validation result."""
    if not isinstance(data, dict):
        return {"valid": False, "errors": ["Invalid JSON payload"]}
    
    errors = []
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None or data[field] == "":
            errors.append(f"Field cannot be empty: {field}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    if not filename:
        return ""
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename.strip()


def validate_url(url: str) -> bool:
    """Validate URL format."""
    if not url:
        return False
    
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
    return bool(re.match(pattern, url))


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."
