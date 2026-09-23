class DomainError(Exception):
    """Base class for all business-rule errors raised by the service layer."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Categories: the API layer maps these to HTTP status codes.

class NotFoundError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class RuleViolationError(DomainError):
    pass


class RateLimitError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class AuthenticationError(DomainError):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message)


# Specific errors

class MessageNotFoundError(NotFoundError):
    def __init__(self, message_id: int):
        self.message_id = message_id
        super().__init__("Message not found")


class UserNotFoundError(NotFoundError):
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"User with username '{username}' not found.")


class UsernameTakenError(ConflictError):
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Username '{username}' is already taken.")


class EmailTakenError(ConflictError):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email '{email}' is already registered.")


class MessageAccessDeniedError(PermissionDeniedError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message)


class SelfMessagingError(RuleViolationError):
    def __init__(self, message: str = "You cannot send a message to yourself."):
        super().__init__(message)


class EditWindowExpiredError(RuleViolationError):
    def __init__(self, window_minutes: int):
        self.window_minutes = window_minutes
        super().__init__(f"Messages can only be edited within {window_minutes} minutes of sending.")


class RateLimitExceededError(RateLimitError):
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        super().__init__(f"Rate limit exceeded. Maximum {max_per_minute} messages per minute.")

