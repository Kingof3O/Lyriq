import json
import logging
import sqlite3
import threading
from pathlib import Path

import app_paths

logger = logging.getLogger("CacheService")

SCHEMA_VERSION = 1
CACHE_TABLES = ("lyrics_cache", "translation_cache", "thumbnails")
DEFAULT_THUMBNAIL_MAX_BYTES = 50 * 1024 * 1024
TRANSLATION_PRUNE_EVERY = 100

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS lyrics_cache (
        cache_key TEXT PRIMARY KEY,
        title TEXT,
        artist TEXT,
        data_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS translation_cache (
        source_text TEXT,
        target_lang TEXT,
        translated_text TEXT,
        romaji_text TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(source_text, target_lang)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS song_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist TEXT,
        title TEXT,
        album TEXT DEFAULT '',
        thumbnail TEXT DEFAULT '',
        is_favorite INTEGER DEFAULT 0,
        played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(artist, title)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS vocab_notebook (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT,
        romaji TEXT DEFAULT '',
        meaning TEXT DEFAULT '',
        lang TEXT DEFAULT 'unknown',
        song_title TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(word, lang)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS song_offsets (
        track_key TEXT PRIMARY KEY,
        offset REAL NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS thumbnails (
        track_key TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        bytes INTEGER NOT NULL,
        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
)

_INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_song_history_played_at ON song_history(played_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_vocab_notebook_created_at ON vocab_notebook(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_translation_cache_target_lang ON translation_cache(target_lang);",
    "CREATE INDEX IF NOT EXISTS idx_translation_cache_created_at ON translation_cache(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_thumbnails_last_used ON thumbnails(last_used);",
)

_instance = None
_instance_lock = threading.Lock()
_schema_lock = threading.RLock()


def get_cache() -> "CacheService":
    """Return the process-wide cache singleton, creating it on first use."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = CacheService()
    return _instance


class CacheService:
    """Thread-safe SQLite cache.

    Each thread gets one persistent connection (connections are not shared
    across threads).  Schema setup and writes are serialised with a re-entrant
    lock so concurrent writers do not trip over SQLite's single-writer rule.
    """

    def __init__(self, db_path=None):
        if db_path is None:
            self.db_path = str(app_paths.get_db_path())
        else:
            raw_path = str(db_path)
            if raw_path == ":memory:":
                raise ValueError(
                    "CacheService does not support ':memory:' because each thread "
                    "uses its own connection; pass a temporary database file instead."
                )
            path = Path(raw_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(path.resolve())

        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._translation_writes_since_prune = 0
        self._init_db()

    # ------------------------------------------------------------------
    # Connection / schema management
    # ------------------------------------------------------------------
    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.connection = conn
        return conn

    def _init_db(self):
        with _schema_lock, self._write_lock:
            conn = self._get_connection()
            try:
                version = int(conn.execute("PRAGMA user_version;").fetchone()[0])
                if version < SCHEMA_VERSION:
                    with conn:
                        self._apply_migrations(conn, version)
                        conn.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)};")
            except Exception as exc:
                logger.error("Cache init error for %s: %s", self.db_path, exc)
                raise

    def _apply_migrations(self, conn: sqlite3.Connection, from_version: int):
        if from_version >= 1:
            return

        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)

        # Databases created by older releases may miss columns added later.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(translation_cache);").fetchall()}
        if "romaji_text" not in columns:
            conn.execute("ALTER TABLE translation_cache ADD COLUMN romaji_text TEXT DEFAULT '';")
        if "created_at" not in columns:
            # SQLite rejects ALTER TABLE ... DEFAULT CURRENT_TIMESTAMP, so add
            # the column first and backfill existing rows afterwards.
            conn.execute("ALTER TABLE translation_cache ADD COLUMN created_at TIMESTAMP;")
            conn.execute("UPDATE translation_cache SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;")

        for statement in _INDEX_STATEMENTS:
            conn.execute(statement)

    def close(self):
        """Close this thread's connection. Safe to call more than once."""
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            try:
                conn.close()
            except Exception as exc:
                logger.debug("Cache close error: %s", exc)
            finally:
                self._local.connection = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _lyrics_key(artist: str, title: str) -> str:
        # Keep the historical key format so existing cached lyrics still match.
        return f"{str(artist or '').strip().lower()}:::{str(title or '').strip().lower()}"

    @staticmethod
    def _encode_setting(value) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _decode_setting(value):
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            # Tolerate values written by older builds or external tools.
            return value

    @staticmethod
    def normalize_track_key(artist: str, title: str) -> str:
        """Canonical per-song key: lower-case, whitespace-collapsed."""
        def _clean(value) -> str:
            return " ".join(str(value or "").split()).strip().lower()

        return f"{_clean(artist)}::{_clean(title)}"

    # ------------------------------------------------------------------
    # Lyrics cache
    # ------------------------------------------------------------------
    def get_lyrics(self, artist: str, title: str):
        key = self._lyrics_key(artist, title)
        try:
            row = self._get_connection().execute(
                "SELECT data_json FROM lyrics_cache WHERE cache_key = ?", (key,)
            ).fetchone()
            if row and row["data_json"]:
                return json.loads(row["data_json"])
        except Exception as exc:
            logger.debug("Cache read error: %s", exc)
        return None

    def save_lyrics(self, artist: str, title: str, data: dict):
        key = self._lyrics_key(artist, title)
        try:
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO lyrics_cache "
                        "(cache_key, title, artist, data_json, updated_at) "
                        "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                        (key, title, artist, self._encode_setting(data)),
                    )
        except Exception as exc:
            logger.error("Cache write error: %s", exc)

    # ------------------------------------------------------------------
    # Translation cache
    # ------------------------------------------------------------------
    def get_translations_batch(self, texts: list, target_lang="en") -> dict:
        results = {}
        if not texts:
            return results
        try:
            conn = self._get_connection()
            placeholders = ",".join("?" for _ in texts)
            query = (
                "SELECT source_text, translated_text, romaji_text "
                "FROM translation_cache "
                f"WHERE target_lang = ? AND source_text IN ({placeholders})"
            )
            for row in conn.execute(query, [target_lang] + list(texts)).fetchall():
                results[row["source_text"]] = {
                    "translation": row["translated_text"] or "",
                    "romaji": row["romaji_text"] or "",
                }
        except Exception as exc:
            logger.debug("Translation cache read error: %s", exc)
        return results

    def save_translations_batch(self, mapping: dict, target_lang="en"):
        if not mapping:
            return
        try:
            items = [
                (src, target_lang, val.get("translation", ""), val.get("romaji", ""))
                for src, val in mapping.items()
            ]
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.executemany(
                        "INSERT OR REPLACE INTO translation_cache "
                        "(source_text, target_lang, translated_text, romaji_text, created_at) "
                        "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                        items,
                    )
                self._translation_writes_since_prune += 1
                should_prune = self._translation_writes_since_prune >= TRANSLATION_PRUNE_EVERY
                if should_prune:
                    self._translation_writes_since_prune = 0
            if should_prune:
                self.prune_translations()
        except Exception as exc:
            logger.error("Translation cache write error: %s", exc)

    def prune_translations(self, max_rows: int = 20000) -> int:
        """Delete the oldest translation rows beyond ``max_rows``."""
        try:
            max_rows = max(0, int(max_rows))
            with self._write_lock:
                conn = self._get_connection()
                before = conn.execute("SELECT COUNT(*) FROM translation_cache;").fetchone()[0]
                if before <= max_rows:
                    return 0
                with conn:
                    conn.execute(
                        "DELETE FROM translation_cache WHERE rowid NOT IN ("
                        "  SELECT rowid FROM translation_cache "
                        "  ORDER BY created_at DESC, rowid DESC LIMIT ?"
                        ")",
                        (max_rows,),
                    )
                after = conn.execute("SELECT COUNT(*) FROM translation_cache;").fetchone()[0]
                return max(0, before - after)
        except Exception as exc:
            logger.error("Translation cache prune error: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # History / favourites / vocabulary
    # ------------------------------------------------------------------
    def record_song_play(self, artist: str, title: str, album: str = "", thumbnail: str = ""):
        if not artist or not title:
            return
        try:
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.execute(
                        """
                        INSERT INTO song_history (artist, title, album, thumbnail, played_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(artist, title) DO UPDATE SET
                            album = excluded.album,
                            thumbnail = COALESCE(NULLIF(excluded.thumbnail, ''), song_history.thumbnail),
                            played_at = CURRENT_TIMESTAMP;
                        """,
                        (artist, title, album, thumbnail or ""),
                    )
        except Exception as exc:
            logger.error("History record error: %s", exc)

    def toggle_favorite(self, artist: str, title: str) -> bool:
        new_fav = 1
        try:
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    row = conn.execute(
                        "SELECT is_favorite FROM song_history WHERE artist = ? AND title = ?",
                        (artist, title),
                    ).fetchone()
                    if row:
                        new_fav = 0 if row["is_favorite"] == 1 else 1
                        conn.execute(
                            "UPDATE song_history SET is_favorite = ? WHERE artist = ? AND title = ?",
                            (new_fav, artist, title),
                        )
                    else:
                        conn.execute(
                            "INSERT INTO song_history (artist, title, is_favorite) VALUES (?, ?, 1)",
                            (artist, title),
                        )
        except Exception as exc:
            logger.error("Favorite toggle error: %s", exc)
        return bool(new_fav)

    def is_favorite(self, artist: str, title: str) -> bool:
        try:
            row = self._get_connection().execute(
                "SELECT is_favorite FROM song_history WHERE artist = ? AND title = ?",
                (artist, title),
            ).fetchone()
            return bool(row and row["is_favorite"] == 1)
        except Exception as exc:
            logger.debug("Favorite read error: %s", exc)
            return False

    def get_song_history(self, limit: int = 30) -> list:
        try:
            rows = self._get_connection().execute(
                """
                SELECT artist, title, album, thumbnail, is_favorite, played_at
                FROM song_history
                ORDER BY played_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "artist": row["artist"],
                    "title": row["title"],
                    "album": row["album"],
                    "thumbnail": row["thumbnail"],
                    "is_favorite": bool(row["is_favorite"]),
                    "played_at": row["played_at"],
                }
                for row in rows
            ]
        except Exception as exc:
            logger.debug("Get history error: %s", exc)
            return []

    def save_vocab_word(
        self,
        word: str,
        romaji: str = "",
        meaning: str = "",
        lang: str = "unknown",
        song_title: str = "",
    ) -> bool:
        if not word:
            return False
        try:
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO vocab_notebook
                        (word, romaji, meaning, lang, song_title, created_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (
                            word.strip(),
                            (romaji or "").strip(),
                            (meaning or "").strip(),
                            (lang or "").strip(),
                            (song_title or "").strip(),
                        ),
                    )
            return True
        except Exception as exc:
            logger.error("Vocab save error: %s", exc)
            return False

    def get_vocab_words(self) -> list:
        try:
            rows = self._get_connection().execute(
                "SELECT id, word, romaji, meaning, lang, song_title, created_at "
                "FROM vocab_notebook ORDER BY id DESC"
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "word": row["word"],
                    "romaji": row["romaji"],
                    "meaning": row["meaning"],
                    "lang": row["lang"],
                    "song_title": row["song_title"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        except Exception as exc:
            logger.debug("Get vocab error: %s", exc)
            return []

    def delete_vocab_word(self, word_id: int):
        try:
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.execute("DELETE FROM vocab_notebook WHERE id = ?", (word_id,))
        except Exception as exc:
            logger.error("Vocab delete error: %s", exc)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_setting(self, key, default=None):
        try:
            row = self._get_connection().execute(
                "SELECT value FROM settings WHERE key = ?", (str(key),)
            ).fetchone()
            if row is None:
                return default
            return self._decode_setting(row["value"])
        except Exception as exc:
            logger.debug("Setting read error: %s", exc)
            return default

    def set_setting(self, key, value) -> bool:
        return self.set_settings({key: value})

    def get_settings(self) -> dict:
        try:
            rows = self._get_connection().execute("SELECT key, value FROM settings;").fetchall()
            return {row["key"]: self._decode_setting(row["value"]) for row in rows}
        except Exception as exc:
            logger.debug("Settings read error: %s", exc)
            return {}

    def set_settings(self, mapping: dict) -> bool:
        if not mapping:
            return True
        try:
            rows = [(str(key), self._encode_setting(value)) for key, value in mapping.items()]
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.executemany(
                        "INSERT INTO settings (key, value, updated_at) "
                        "VALUES (?, ?, CURRENT_TIMESTAMP) "
                        "ON CONFLICT(key) DO UPDATE SET "
                        "value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                        rows,
                    )
            return True
        except Exception as exc:
            logger.error("Settings write error: %s", exc)
            return False

    save_setting = set_setting
    save_settings = set_settings

    # ------------------------------------------------------------------
    # Per-song offsets
    # ------------------------------------------------------------------
    def get_song_offset(self, artist: str, title: str) -> float:
        track_key = self.normalize_track_key(artist, title)
        try:
            row = self._get_connection().execute(
                "SELECT offset FROM song_offsets WHERE track_key = ?", (track_key,)
            ).fetchone()
            return float(row["offset"]) if row else 0.0
        except Exception as exc:
            logger.debug("Song offset read error: %s", exc)
            return 0.0

    def set_song_offset(self, artist: str, title: str, offset) -> float:
        try:
            value = float(offset or 0.0)
        except (TypeError, ValueError):
            logger.error("Invalid song offset %r for %s / %s", offset, artist, title)
            return 0.0
        track_key = self.normalize_track_key(artist, title)
        try:
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.execute(
                        "INSERT INTO song_offsets (track_key, offset, updated_at) "
                        "VALUES (?, ?, CURRENT_TIMESTAMP) "
                        "ON CONFLICT(track_key) DO UPDATE SET "
                        "offset = excluded.offset, updated_at = CURRENT_TIMESTAMP",
                        (track_key, value),
                    )
        except Exception as exc:
            logger.error("Song offset write error: %s", exc)
        return value

    # ------------------------------------------------------------------
    # Thumbnail LRU cache
    # ------------------------------------------------------------------
    def get_thumbnail(self, track_key) -> str | None:
        key = str(track_key or "").strip()
        if not key:
            return None
        try:
            conn = self._get_connection()
            row = conn.execute(
                "SELECT data FROM thumbnails WHERE track_key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            try:
                with self._write_lock:
                    with conn:
                        conn.execute(
                            "UPDATE thumbnails SET last_used = CURRENT_TIMESTAMP WHERE track_key = ?",
                            (key,),
                        )
            except Exception as exc:
                # A failed LRU touch must not hide a valid thumbnail.
                logger.debug("Thumbnail touch error: %s", exc)
            return row["data"]
        except Exception as exc:
            logger.debug("Thumbnail read error: %s", exc)
            return None

    def save_thumbnail(self, track_key, data, max_bytes: int = DEFAULT_THUMBNAIL_MAX_BYTES) -> bool:
        key = str(track_key or "").strip()
        if not key or not data:
            return False
        payload = data if isinstance(data, str) else str(data)
        size = len(payload.encode("utf-8"))
        try:
            with self._write_lock:
                conn = self._get_connection()
                with conn:
                    conn.execute(
                        "INSERT INTO thumbnails (track_key, data, bytes, last_used) "
                        "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                        "ON CONFLICT(track_key) DO UPDATE SET "
                        "data = excluded.data, bytes = excluded.bytes, "
                        "last_used = CURRENT_TIMESTAMP",
                        (key, payload, size),
                    )
            self._evict_thumbnails(max_bytes)
            return True
        except Exception as exc:
            logger.error("Thumbnail write error: %s", exc)
            return False

    def _evict_thumbnails(self, max_bytes: int) -> int:
        try:
            max_bytes = max(0, int(max_bytes))
        except (TypeError, ValueError):
            max_bytes = DEFAULT_THUMBNAIL_MAX_BYTES
        try:
            with self._write_lock:
                conn = self._get_connection()
                rows = conn.execute(
                    "SELECT track_key, bytes FROM thumbnails ORDER BY last_used ASC, rowid ASC"
                ).fetchall()
                total = sum(int(row["bytes"] or 0) for row in rows)
                if total <= max_bytes:
                    return 0

                doomed = []
                for row in rows:
                    if total <= max_bytes:
                        break
                    doomed.append(row["track_key"])
                    total -= int(row["bytes"] or 0)
                if doomed:
                    with conn:
                        conn.executemany(
                            "DELETE FROM thumbnails WHERE track_key = ?",
                            [(key,) for key in doomed],
                        )
                return len(doomed)
        except Exception as exc:
            logger.error("Thumbnail eviction error: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def clear_cache(self) -> dict:
        """Clear disposable caches; favourites, history, vocabulary, settings
        and offsets are intentionally preserved."""
        deleted = {}
        try:
            with self._write_lock:
                conn = self._get_connection()
                counts = {}
                with conn:
                    for table in CACHE_TABLES:
                        cursor = conn.execute(f"DELETE FROM {table};")
                        counts[table] = max(0, cursor.rowcount)
                # Only report counts after the transaction committed. If any
                # DELETE failed, the context manager rolled everything back.
                deleted = counts
                self._translation_writes_since_prune = 0
                try:
                    conn.execute("VACUUM;")
                except Exception as exc:
                    logger.debug("VACUUM after cache clear failed (non-fatal): %s", exc)
        except Exception as exc:
            logger.error("Cache clear error: %s", exc)
            deleted = {}
        return deleted

    def get_cache_stats(self) -> dict:
        db_path = Path(self.db_path)
        try:
            db_size = db_path.stat().st_size
        except OSError:
            db_size = 0

        counts = {}
        settings_count = 0
        try:
            conn = self._get_connection()
            for table in CACHE_TABLES:
                counts[table] = int(
                    conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
                )
            settings_count = int(
                conn.execute("SELECT COUNT(*) FROM settings;").fetchone()[0]
            )
        except Exception as exc:
            logger.debug("Cache stats error: %s", exc)
            for table in CACHE_TABLES:
                counts.setdefault(table, 0)

        return {
            "data_dir": str(db_path.parent),
            "db_path": self.db_path,
            "db_size": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "lyrics_cache": counts.get("lyrics_cache", 0),
            "translation_cache": counts.get("translation_cache", 0),
            "thumbnails": counts.get("thumbnails", 0),
            "settings": settings_count,
            "row_counts": {
                "lyrics_cache": counts.get("lyrics_cache", 0),
                "translation_cache": counts.get("translation_cache", 0),
                "thumbnails": counts.get("thumbnails", 0),
            },
        }
