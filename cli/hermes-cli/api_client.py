#!/usr/bin/env python3

import requests
from typing import Optional, Dict, Any, BinaryIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os


class HermesAPIError(Exception):
    """Custom exception for Hermes API errors"""
    pass


class HermesConnectionError(Exception):
    """Custom exception for connection errors"""
    pass


class HermesAPIClient:
    """API client for Hermes backend with retry logic and error handling"""

    def __init__(self, base_url: str, timeout: int = 30, api_key: Optional[str] = None):
        """
        Initialize the Hermes API client

        Args:
            base_url: Base URL of the Hermes backend API
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication (future use)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.api_key = api_key
        self.session = self._create_session()
        self.debug = os.getenv('DEBUG', '').lower() in ('true', '1', 'yes')

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update({
            'User-Agent': 'Hermes-CLI/1.0.0'
        })

        # Add API key if provided
        if self.api_key:
            session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

        return session

    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details if debug is enabled"""
        if self.debug:
            print(f"[DEBUG] {method} {url}")
            if 'data' in kwargs:
                print(f"[DEBUG] Data: {kwargs['data']}")
            if 'json' in kwargs:
                print(f"[DEBUG] JSON: {kwargs['json']}")

    def _log_response(self, response: requests.Response):
        """Log response details if debug is enabled"""
        if self.debug:
            print(f"[DEBUG] Response: {response.status_code}")
            try:
                print(f"[DEBUG] Body: {response.json()}")
            except:
                print(f"[DEBUG] Body: {response.text[:200]}")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate exceptions"""
        self._log_response(response)

        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise HermesAPIError(f"Resource not found: {response.url}")
            elif response.status_code == 400:
                try:
                    error_detail = response.json().get('detail', 'Bad request')
                except:
                    error_detail = 'Bad request'
                raise HermesAPIError(f"Bad request: {error_detail}")
            elif response.status_code >= 500:
                raise HermesAPIError(f"Server error: {response.status_code}")
            else:
                raise HermesAPIError(f"HTTP {response.status_code}: {str(e)}")
        except requests.exceptions.JSONDecodeError:
            raise HermesAPIError("Invalid JSON response from server")

    def import_scan(self, project_id: str, file_path: str, format: str = 'auto') -> Dict[str, Any]:
        """
        Import a scan file into a project

        Args:
            project_id: UUID of the project
            file_path: Path to the scan file
            format: Scan format (auto, nmap, masscan, dirb, gobuster)

        Returns:
            Response dictionary with scan_id and status
        """
        url = f"{self.base_url}/api/v1/projects/{project_id}/scans/import"

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                data = {'tool_type': format}

                self._log_request('POST', url, data=data)
                response = self.session.post(
                    url,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )

            return self._handle_response(response)
        except FileNotFoundError:
            raise HermesAPIError(f"File not found: {file_path}")
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after {self.timeout}s")

    def import_scan_from_stdin(self, project_id: str, content: str, format: str = 'auto') -> Dict[str, Any]:
        """
        Import scan data from stdin

        Args:
            project_id: UUID of the project
            content: Scan content from stdin
            format: Scan format (auto, nmap, masscan, dirb, gobuster)

        Returns:
            Response dictionary with scan_id and status
        """
        url = f"{self.base_url}/api/v1/projects/{project_id}/scans/import"

        try:
            files = {'file': ('stdin.txt', content.encode())}
            data = {'tool_type': format}

            self._log_request('POST', url, data=data)
            response = self.session.post(
                url,
                files=files,
                data=data,
                timeout=self.timeout
            )

            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after {self.timeout}s")

    def export_project(self, project_id: str, format: str = 'markdown',
                      include_graph: bool = True, include_attack_chains: bool = True) -> Dict[str, Any]:
        """
        Export project documentation

        Args:
            project_id: UUID of the project
            format: Export format (markdown, pdf, json, csv)
            include_graph: Include network graph in export
            include_attack_chains: Include attack chains in export

        Returns:
            Response dictionary with job_id and status
        """
        url = f"{self.base_url}/api/v1/projects/{project_id}/export"

        payload = {
            'format': format,
            'include_graph': include_graph,
            'include_attack_chains': include_attack_chains
        }

        try:
            self._log_request('POST', url, json=payload)
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after {self.timeout}s")

    def get_export_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of an export job

        Args:
            job_id: UUID of the export job

        Returns:
            Job status dictionary
        """
        url = f"{self.base_url}/api/v1/export-jobs/{job_id}"

        try:
            self._log_request('GET', url)
            response = self.session.get(url, timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after {self.timeout}s")

    def download_export(self, job_id: str, output_path: str):
        """
        Download completed export file

        Args:
            job_id: UUID of the export job
            output_path: Path to save the downloaded file
        """
        url = f"{self.base_url}/api/v1/export-jobs/{job_id}/download"

        try:
            self._log_request('GET', url)
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after {self.timeout}s")

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status including database, Redis, Celery workers

        Returns:
            System status dictionary
        """
        url = f"{self.base_url}/api/v1/status"

        try:
            self._log_request('GET', url)
            response = self.session.get(url, timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after {self.timeout}s")

    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """
        Get project-specific status and statistics

        Args:
            project_id: UUID of the project

        Returns:
            Project status dictionary with metadata
        """
        url = f"{self.base_url}/api/v1/projects/{project_id}"

        try:
            self._log_request('GET', url)
            response = self.session.get(url, timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after {self.timeout}s")

    def health_check(self) -> Dict[str, Any]:
        """
        Check backend health

        Returns:
            Health status dictionary
        """
        url = f"{self.base_url}/health"

        try:
            self._log_request('GET', url)
            response = self.session.get(url, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            raise HermesConnectionError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise HermesConnectionError(f"Request timed out after 5s")
