"""
FastAPI application factory.

Creates and configures the FastAPI app with CORS, routers, and startup events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.engine import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="Job Hunt Agent API",
        description="AI-powered job matching and application tracking",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from api.routers import profiles, jobs, matches, applications

    app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
    app.include_router(applications.router, prefix="/api/applications", tags=["applications"])

    @app.on_event("startup")
    def startup():
        init_db()

    @app.get("/api/health")
    def health_check():
        return {"status": "ok"}

    return app
