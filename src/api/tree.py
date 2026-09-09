"""``GET /tree`` -- the whole hollow in one response.

Folders are few and human-made, so nesting them on the client costs less than
one request per level.
"""

from __future__ import annotations

from fastapi import APIRouter

from .dependencies import Hollow
from .schemas import TreeNode

router = APIRouter(tags=["tree"])


@router.get("/tree", response_model=list[TreeNode], summary="The whole hollow tree")
def read_tree(hollow: Hollow, path: str = "") -> list[TreeNode]:
    """Return the tree below a folder of the hollow.

    Args:
        hollow: The hollow connector.
        path: The hollow-relative folder to walk. Empty is the root.

    Returns:
        The nodes below the folder, folders first and then files by name, each
        folder carrying its own children.
    """
    return [TreeNode.model_validate(entry) for entry in hollow.tree(path)]
