import logging

from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


class BusinessException(APIException):
    """Exceção base para regras de negócio violadas (HTTP 422)."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "business_error"

    def __init__(self, detail=None, code=None):
        super().__init__(detail=detail, code=code)


class ConflictException(BusinessException):
    """Recurso já existe ou conflito de estado (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


class NotFoundException(APIException):
    """Recurso não encontrado (HTTP 404)."""

    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
