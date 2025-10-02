"""
Authentication middleware for Hermes API.

Provides API key-based authentication for Epic 2 monitoring endpoints.
"""

import os
import logging
from typing import Optional

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader


logger = logging.getLogger(__name__)

# API Key header configuration
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key authentication.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        str: The validated API key

    Raises:
        HTTPException: 401 if API key is invalid or missing
    """
    expected_api_key = os.getenv("HERMES_API_KEY")

    # If no API key is configured, allow access (for development)
    if not expected_api_key:
        logger.warning(
            "HERMES_API_KEY environment variable not set - authentication disabled. "
            "Set HERMES_API_KEY in production environments."
        )
        return "development-mode"

    # Check if API key was provided
    if not api_key:
        logger.warning("API request rejected: Missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key matches
    if api_key != expected_api_key:
        logger.warning(f"API request rejected: Invalid API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Please check your credentials.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug("API key authentication successful")
    return api_key


async def optional_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Optional API key verification for public endpoints.

    This allows endpoints to be accessed without authentication but still
    validates the key if provided.

    Args:
        api_key: Optional API key from X-API-Key header

    Returns:
        Optional[str]: The API key if provided and valid, None otherwise
    """
    if not api_key:
        return None

    try:
        return await verify_api_key(api_key)
    except HTTPException:
        # For optional auth, don't raise exception
        return None