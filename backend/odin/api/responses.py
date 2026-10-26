"""Credential-safe JSON responses; canonical source files remain access controlled."""
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from odin.core.privacy import redact


class RedactedJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return super().render(redact(content))


class PrivateAPIRoute(APIRoute):
    """FastAPI's default exception responses otherwise bypass the JSON response policy."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request):
            try:
                return await handler(request)
            except HTTPException as exc:
                exc.detail = redact(exc.detail)
                raise
            except RequestValidationError as exc:
                return RedactedJSONResponse(status_code=422, content={"detail": jsonable_encoder(redact(exc.errors()))})
        return guarded
