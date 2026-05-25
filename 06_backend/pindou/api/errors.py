"""Unified API error responses."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ADMIN_REQUIRED = "ADMIN_REQUIRED"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    INVALID_UPLOAD = "INVALID_UPLOAD"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    PATTERN_BUILD_FAILED = "PATTERN_BUILD_FAILED"
    PREVIEW_FAILED = "PREVIEW_FAILED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    ARTWORK_NOT_FOUND = "ARTWORK_NOT_FOUND"
    INVALID_CDK = "INVALID_CDK"
    CDK_REDEEMED = "CDK_REDEEMED"
    CDK_RATE_LIMITED = "CDK_RATE_LIMITED"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_PAID_TIMEOUT = "ORDER_PAID_TIMEOUT"
    INVALID_ORDER_STATUS = "INVALID_ORDER_STATUS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiException(Exception):
    def __init__(
        self,
        status_code: int,
        error: ErrorCode | str,
        message_cn: str,
        details: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = str(error)
        self.message_cn = message_cn
        self.details = details


def error_payload(error: str, message_cn: str, details: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": error, "message_cn": message_cn}
    if details is not None:
        payload["details"] = details
    return payload


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def api_exception_handler(_: Request, exc: ApiException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.error, exc.message_cn, exc.details),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail and "message_cn" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(str(exc.status_code), str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                ErrorCode.VALIDATION_ERROR,
                "请求参数不完整或格式不正确，请检查后再试。",
                exc.errors(),
            ),
        )
