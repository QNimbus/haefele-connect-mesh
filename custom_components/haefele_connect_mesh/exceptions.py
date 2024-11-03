from typing import Optional, Any, Dict


class HafeleAPIError(Exception):
    """Custom exception class for Häfele Connect Mesh API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the API error.

        Args:
            message: Human-readable error message
            status_code: HTTP status code from the API response
            error_code: Error code returned by the API (e.g., 'GATEWAY_UNAVAILABLE')
            response: Complete error response data from the API
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.response = response or {}

    def __str__(self) -> str:
        """Return a string representation of the error."""
        error_parts = [self.message]

        if self.status_code:
            error_parts.append(f"Status Code: {self.status_code}")
        if self.error_code:
            error_parts.append(f"Error Code: {self.error_code}")

        return " | ".join(error_parts)


class AuthenticationError(Exception):
    """Raised when there are authentication issues with the API."""

    pass


class ValidationError(Exception):
    """Raised when there are validation errors with the request parameters."""

    pass
