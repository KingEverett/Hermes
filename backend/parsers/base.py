from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedService:
    """Represents a parsed service from scan output"""
    port: int
    protocol: str  # 'tcp' or 'udp'
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    banner: Optional[str] = None
    cpe: Optional[str] = None
    confidence: str = 'medium'  # 'high', 'medium', 'low'


@dataclass
class ParsedHost:
    """Represents a parsed host from scan output"""
    ip_address: str
    hostname: Optional[str] = None
    os_family: Optional[str] = None
    os_details: Optional[str] = None
    mac_address: Optional[str] = None
    status: str = 'up'  # 'up', 'down', 'filtered'
    confidence_score: Optional[float] = None
    services: List[ParsedService] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.services is None:
            self.services = []
        if self.metadata is None:
            self.metadata = {}


class ScanParsingError(Exception):
    """Base exception for scan parsing errors"""
    pass


class CorruptedScanError(ScanParsingError):
    """Raised when scan file is corrupted or malformed"""
    pass


class UnsupportedScanError(ScanParsingError):
    """Raised when scan format is not supported"""
    pass


class ScanParser(ABC):
    """Abstract base class for scan parsers"""

    @abstractmethod
    def can_parse(self, content: str, filename: str) -> bool:
        """
        Determine if this parser can handle the given file content and filename.

        Args:
            content: The file content as string
            filename: The original filename

        Returns:
            True if this parser can handle the file, False otherwise
        """
        pass

    @abstractmethod
    def parse(self, content: str) -> List[ParsedHost]:
        """
        Parse scan output into structured data.

        Args:
            content: The file content as string

        Returns:
            List of ParsedHost objects

        Raises:
            CorruptedScanError: If the file is corrupted or malformed
            ScanParsingError: For other parsing errors
        """
        pass

    def validate_content(self, content: str) -> None:
        """
        Validate that the content is not corrupted.
        Should be called before parsing.

        Args:
            content: The file content as string

        Raises:
            CorruptedScanError: If content appears corrupted
        """
        if not content or not content.strip():
            raise CorruptedScanError("File content is empty")