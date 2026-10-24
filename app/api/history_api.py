"""Song history, favorites, and lyrics export APIs."""

import logging
import os

logger = logging.getLogger("HistoryAPI")


class HistoryAPIMixin:
    def toggle_favorite(self, artist, title):
        return self._app.lyrics_service.cache.toggle_favorite(artist, title)

    def get_song_history(self):
        return self._app.lyrics_service.cache.get_song_history()

    def load_history_song(self, artist, title):
        if artist and title:
            self._app.load_history_lyrics(artist, title)

    def export_lyrics(self, lrc_content, filename):
        """Exports synchronized bilingual lyrics to Desktop as .lrc."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = "".join(c for c in filename if c.isalnum() or c in " ._-").strip() or "lyrics.lrc"
            if not safe_name.endswith(".lrc"):
                safe_name += ".lrc"
            out_path = os.path.join(desktop, safe_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(lrc_content)
            return f"Exported to Desktop: {safe_name}"
        except Exception as e:
            return f"Export error: {e}"

    def export_srt(self, srt_content, filename):
        """Exports synchronized bilingual subtitles to Desktop as .srt."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = "".join(c for c in filename if c.isalnum() or c in " ._-").strip() or "lyrics.srt"
            if not safe_name.endswith(".srt"):
                safe_name += ".srt"
            out_path = os.path.join(desktop, safe_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return f"Exported Subtitles to Desktop: {safe_name}"
        except Exception as e:
            return f"Export error: {e}"

    def export_lyric_sheet(self, html_content, filename):
        """Exports poster-style printable HTML lyric sheet to Desktop."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = "".join(c for c in filename if c.isalnum() or c in " ._-").strip() or "Lyric_Sheet.html"
            if not safe_name.endswith(".html"):
                safe_name += ".html"
            out_path = os.path.join(desktop, safe_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return f"Exported Printable Sheet to Desktop: {safe_name}"
        except Exception as e:
            return f"Export error: {e}"
