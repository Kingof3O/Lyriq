"""Backwards compatibility shim for api_bridge."""

from app.api import AppAPI
from app.api.lyrics_api import _make_track_key

__all__ = ["AppAPI", "_make_track_key"]
