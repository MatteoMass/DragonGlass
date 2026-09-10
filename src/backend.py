"""Assembles the application, and does nothing else.

It opens the hollow connector and the renderer for the life of the process,
registers the routers, installs CORS when it is configured, and translates
connector errors into status codes -- so no endpoint has to.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api import ROUTERS, frontend
from config import Settings, settings
from connectors.hollow_connector import (
    EntryAlreadyExists,
    EntryNotFound,
    InvalidMove,
    InvalidName,
    InvalidPath,
    NotANote,
    HollowConfig,
    HollowConnector,
    HollowError,
)
from connectors.settings_connector import SettingsConnector
from connectors.tutor_connector import (
    ImportNotFound as TutorImportNotFound,
    InvalidAttempt,
    InvalidImage,
    InvalidMapping,
    InvalidNote,
    NoteNotFound,
    QuestionNotFound,
    QuizNotFound,
    TutorConnector,
    TutorError,
    UnsupportedFile,
)
from core import MarkdownRenderer, TitleSynchroniser

logger = logging.getLogger(__name__)

HOLLOW_ROUTE = "/hollow"
TUTOR_IMAGES_ROUTE = "/tutor-images"

STATUS_BY_ERROR: tuple[tuple[type[HollowError], int], ...] = (
    (EntryNotFound, 404),
    (NotANote, 404),
    (EntryAlreadyExists, 409),
    (InvalidName, 400),
    (InvalidPath, 400),
    (InvalidMove, 400),
)

TUTOR_STATUS_BY_ERROR: tuple[tuple[type[TutorError], int], ...] = (
    (TutorImportNotFound, 404),
    (QuizNotFound, 404),
    (QuestionNotFound, 404),
    (NoteNotFound, 404),
    (InvalidMapping, 400),
    (UnsupportedFile, 400),
    (InvalidAttempt, 400),
    (InvalidNote, 400),
    (InvalidImage, 400),
)


def _configure_logging(level: str) -> None:
    """Set the root logger up once, at the configured level."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def _status_for(error: HollowError) -> int:
    """The status code that answers one connector error.

    Anything the table does not name is a fault of the server rather than of the
    request, and is answered ``500``.
    """
    for kind, code in STATUS_BY_ERROR:
        if isinstance(error, kind):
            return code
    return 500


def _status_for_tutor(error: TutorError) -> int:
    """The status code that answers one tutor connector error."""
    for kind, code in TUTOR_STATUS_BY_ERROR:
        if isinstance(error, kind):
            return code
    return 500


def create_app(config: Settings = settings) -> FastAPI:
    """Build the application.

    Args:
        config: The settings to run on. Defaults to the ones assembled at import.

    Returns:
        The application, with the hollow, the renderer and the title sync opened
        on its state, every router registered, the hollow's files mounted
        read-only at ``/hollow``, the tutor's question images at
        ``/tutor-images``, and the built frontend at ``/``.
    """
    _configure_logging(config.logging.level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Open the hollow and the renderer for the life of the process."""
        logger.info("Dragon Glass starting on the hollow at %s", app.state.hollow.root)
        yield
        logger.info("Dragon Glass stopped")

    app = FastAPI(
        title="Dragon Glass",
        description="A browser for a folder of Markdown files.",
        version="2.0.0",
        lifespan=lifespan,
    )

    hollow = HollowConnector(
        config.paths.hollow_root,
        HollowConfig(
            note_extension=config.hollow.note_extension,
            images_suffix=config.hollow.images_suffix,
            image_extensions=config.hollow.image_extensions,
        ),
    )
    app.state.hollow = hollow
    app.state.renderer = MarkdownRenderer(
        config.markdown.extensions,
        wikilinks=config.markdown.wikilinks,
        image_paths=config.markdown.image_paths,
        tasklists=config.markdown.tasklists,
        hollow_route=HOLLOW_ROUTE,
    )
    app.state.titles = TitleSynchroniser(
        note_extension=config.hollow.note_extension,
        images_suffix=config.hollow.images_suffix,
        enabled=config.hollow.sync_title,
    )
    app.state.max_image_bytes = config.server.max_image_bytes
    app.state.max_import_bytes = config.server.max_import_bytes
    app.state.settings_store = SettingsConnector(config.paths.settings_file)
    config.paths.tutor_images_root.mkdir(parents=True, exist_ok=True)
    app.state.tutor_store = TutorConnector(config.paths.tutor_file, config.paths.tutor_images_root)

    @app.exception_handler(HollowError)
    async def hollow_error_handler(_: Request, error: HollowError) -> JSONResponse:
        """Answer every connector error with its status code and its reason."""
        status_code = _status_for(error)
        if status_code >= 500:
            logger.exception("The hollow failed to answer", exc_info=error)
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    @app.exception_handler(TutorError)
    async def tutor_error_handler(_: Request, error: TutorError) -> JSONResponse:
        """Answer every tutor connector error with its status code and its reason."""
        status_code = _status_for_tutor(error)
        if status_code >= 500:
            logger.exception("The tutor failed to answer", exc_info=error)
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    if config.server.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.server.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS allowed for %s", ", ".join(config.server.cors_origins))

    for router in ROUTERS:
        app.include_router(router)

    app.mount(HOLLOW_ROUTE, StaticFiles(directory=hollow.root), name="hollow")
    app.mount(
        TUTOR_IMAGES_ROUTE, StaticFiles(directory=config.paths.tutor_images_root), name="tutor-images"
    )
    frontend.mount(app, config.paths.frontend_dist)

    return app


app = create_app()
