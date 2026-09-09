"""The business logic: from a note on disk to what a reader sees.

It knows nothing of HTTP and nothing of where the bytes came from.
"""

from .blocks import split_blocks
from .features import FEATURES, FeatureDescriptor
from .renderer import MarkdownRenderer
from .titles import TitleSync, TitleSynchroniser, extract_title
from .types import LinkTarget, RenderedBlock, RenderedNote, SourceBlock

__all__ = [
    "FEATURES",
    "FeatureDescriptor",
    "LinkTarget",
    "MarkdownRenderer",
    "RenderedBlock",
    "RenderedNote",
    "SourceBlock",
    "TitleSync",
    "TitleSynchroniser",
    "extract_title",
    "split_blocks",
]
