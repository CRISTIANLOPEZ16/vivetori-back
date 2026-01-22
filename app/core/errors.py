class AppError(Exception):
    """Base app exception."""


class ValidationError(AppError):
    pass


class ExternalServiceError(AppError):
    pass


class NotFoundError(AppError):
    pass


class RepositoryError(AppError):
    pass
