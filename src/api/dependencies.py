"""What every router asks for, and the only place the application state is reached."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from connectors.hollow_connector import HollowConnector
from core import MarkdownRenderer, TitleSynchroniser


def get_hollow(request: Request) -> HollowConnector:
    """The hollow connector opened for the life of the process."""
    return request.app.state.hollow


def get_renderer(request: Request) -> MarkdownRenderer:
    """The Markdown renderer built for the life of the process."""
    return request.app.state.renderer


def get_titles(request: Request) -> TitleSynchroniser:
    """The title-to-filename sync configured for this hollow."""
    return request.app.state.titles


Hollow = Annotated[HollowConnector, Depends(get_hollow)]
Renderer = Annotated[MarkdownRenderer, Depends(get_renderer)]
Titles = Annotated[TitleSynchroniser, Depends(get_titles)]
