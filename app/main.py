import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from api.routes import router
from core.errors import ExternalServiceError, NotFoundError, RepositoryError, ValidationError
from core.log_config import setup_logging

load_dotenv()
logger = logging.getLogger(__name__)

_ERROR_STATUS: dict[type[Exception], int] = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    RepositoryError: status.HTTP_502_BAD_GATEWAY,
    ExternalServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _register_exception_handlers(app: FastAPI) -> None:
    def handler(request: Request, exc: Exception) -> JSONResponse:
        status_code = _ERROR_STATUS.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    for exc_type in _ERROR_STATUS:
        add_exception_handler(exc_type, handler)

    def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})

    add_exception_handler(Exception, unhandled_handler)


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="AI Support Co-Pilot API", version="1.0.0")
    _register_exception_handlers(app)

    # Mount router with dependency injection
    include_router(
        router,
        prefix="",
        dependencies=[],
    )

    return app


app = create_app()
