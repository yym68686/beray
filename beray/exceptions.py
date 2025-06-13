class BeRayException(Exception):
    """Base exception for the BeRay SDK."""
    pass

class AuthenticationError(BeRayException):
    """Raised for authentication failures."""
    pass

class APIError(BeRayException):
    """Raised for general API errors."""
    def __init__(self, status_code, error_detail):
        self.status_code = status_code
        self.error_detail = error_detail
        super().__init__(f"API request failed with status {status_code}: {error_detail}")

class NotFoundError(APIError):
    """Raised when a resource is not found (404)."""
    pass

class ConflictError(APIError):
    """Raised for conflicts (409)."""
    pass

class UnprocessableEntityError(APIError):
    """Raised for validation errors (422)."""
    pass
