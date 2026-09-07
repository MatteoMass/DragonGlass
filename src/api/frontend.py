"""Mounting the built Vue app at ``/``.

The mount goes last, after every router, because a mount at ``/`` catches
whatever the routes above it did not. A checkout that has never been built
starts all the same and answers the API alone.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


class SinglePageApp(StaticFiles):
    """Static files, with ``index.html`` answering anything that is not a file.

    The app routes on the client, so a URL the build has no file for is a view
    of the app rather than a missing page.
    """

    async def get_response(self, path: str, scope):
        """Serve the file, falling back to ``index.html`` for unknown paths."""
        response = await super().get_response(path, scope)
        if response.status_code == 404:
            index = Path(self.directory) / "index.html"
            if index.is_file():
                return FileResponse(index)
        return response


def mount(app: FastAPI, dist: Path) -> bool:
    """Mount the built frontend at ``/`` when there is one.

    Args:
        app: The application to mount it on.
        dist: The directory ``vite build`` wrote into.

    Returns:
        Whether anything was mounted. A missing build is reported and the API
        goes on answering on its own.
    """
    if not (dist / "index.html").is_file():
        logger.warning("No frontend build at %s; serving the API alone", dist)
        return False
    app.mount("/", SinglePageApp(directory=dist, html=True), name="frontend")
    logger.info("Frontend mounted from %s", dist)
    return True
