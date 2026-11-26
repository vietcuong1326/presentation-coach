from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.api.routes import health, auth, projects, files, evaluations, chat

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Include routes
# Root /health according to API.md section 2
app.include_router(health.router)
# Also include health under /api for consistency
app.include_router(health.router, prefix=settings.API_V1_STR)

# Auth router
app.include_router(auth.router, prefix=settings.API_V1_STR)

# Projects router
app.include_router(projects.router, prefix=settings.API_V1_STR)

# Files router
app.include_router(files.router, prefix=settings.API_V1_STR)

# Evaluations router
app.include_router(evaluations.router, prefix=settings.API_V1_STR)

# Chatbot router
app.include_router(chat.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "docs": f"{settings.API_V1_STR}/docs",
    }
