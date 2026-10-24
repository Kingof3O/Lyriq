import sqlite3
import json
import os
import logging

logger = logging.getLogger("CacheService")

class CacheService:
    def __init__(self, db_path=None):
        if not db_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "lyrics_cache.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                
                # Lyrics cache
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS lyrics_cache (
                        cache_key TEXT PRIMARY KEY,
                        title TEXT,
                        artist TEXT,
                        data_json TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Translation & Romaji cache
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS translation_cache (
                        source_text TEXT,
                        target_lang TEXT,
                        translated_text TEXT,
                        romaji_text TEXT DEFAULT '',
                        PRIMARY KEY(source_text, target_lang)
                    );
                """)

                # Check if romaji_text exists
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(translation_cache);")
                columns = [row[1] for row in cur.fetchall()]
                if "romaji_text" not in columns:
                    conn.execute("ALTER TABLE translation_cache ADD COLUMN romaji_text TEXT DEFAULT '';")

                # Song History & Favorites
                conn.execute("""
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
                """)

                # Bilingual Vocabulary Notebook
                conn.execute("""
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
                """)

                conn.commit()
        except Exception as e:
            logger.error(f"Cache init error: {e}")

    # Lyrics Cache
    def get_lyrics(self, artist: str, title: str):
        key = f"{artist.strip().lower()}:::{title.strip().lower()}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT data_json FROM lyrics_cache WHERE cache_key = ?", (key,))
                row = cur.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None

    def save_lyrics(self, artist: str, title: str, data: dict):
        key = f"{artist.strip().lower()}:::{title.strip().lower()}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO lyrics_cache (cache_key, title, artist, data_json) VALUES (?, ?, ?, ?)",
                    (key, title, artist, json.dumps(data))
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache write error: {e}")

    # Translations Cache
    def get_translations_batch(self, texts: list, target_lang="en") -> dict:
        results = {}
        if not texts:
            return results
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                placeholders = ",".join("?" for _ in texts)
                query = f"SELECT source_text, translated_text, romaji_text FROM translation_cache WHERE target_lang = ? AND source_text IN ({placeholders})"
                cur.execute(query, [target_lang] + texts)
                for src, trans, romaji in cur.fetchall():
                    results[src] = {
                        "translation": trans or "",
                        "romaji": romaji or ""
                    }
        except Exception as e:
            logger.debug(f"Translation cache read error: {e}")
        return results

    def save_translations_batch(self, mapping: dict, target_lang="en"):
        if not mapping:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                items = [
                    (src, target_lang, val.get("translation", ""), val.get("romaji", ""))
                    for src, val in mapping.items()
                ]
                conn.executemany(
                    "INSERT OR REPLACE INTO translation_cache (source_text, target_lang, translated_text, romaji_text) VALUES (?, ?, ?, ?)",
                    items
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Translation cache write error: {e}")

    # Song History & Favorites
    def record_song_play(self, artist: str, title: str, album: str = "", thumbnail: str = ""):
        if not artist or not title:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO song_history (artist, title, album, thumbnail, played_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(artist, title) DO UPDATE SET
                        album = excluded.album,
                        thumbnail = COALESCE(NULLIF(excluded.thumbnail, ''), song_history.thumbnail),
                        played_at = CURRENT_TIMESTAMP;
                """, (artist, title, album, thumbnail or ""))
                conn.commit()
        except Exception as e:
            logger.debug(f"History record error: {e}")

    def toggle_favorite(self, artist: str, title: str) -> bool:
        new_fav = 1
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT is_favorite FROM song_history WHERE artist = ? AND title = ?", (artist, title))
                row = cur.fetchone()
                if row:
                    new_fav = 0 if row[0] == 1 else 1
                    conn.execute("UPDATE song_history SET is_favorite = ? WHERE artist = ? AND title = ?", (new_fav, artist, title))
                else:
                    conn.execute("INSERT INTO song_history (artist, title, is_favorite) VALUES (?, ?, 1)", (artist, title))
                conn.commit()
        except Exception as e:
            logger.debug(f"Favorite toggle error: {e}")
        return bool(new_fav)

    def is_favorite(self, artist: str, title: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT is_favorite FROM song_history WHERE artist = ? AND title = ?", (artist, title))
                row = cur.fetchone()
                return bool(row and row[0] == 1)
        except Exception:
            return False

    def get_song_history(self, limit: int = 30) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT artist, title, album, thumbnail, is_favorite, played_at
                    FROM song_history
                    ORDER BY played_at DESC
                    LIMIT ?
                """, (limit,))
                return [
                    {
                        "artist": row[0],
                        "title": row[1],
                        "album": row[2],
                        "thumbnail": row[3],
                        "is_favorite": bool(row[4]),
                        "played_at": row[5]
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.debug(f"Get history error: {e}")
            return []

    # Bilingual Vocabulary Notebook
    def save_vocab_word(self, word: str, romaji: str = "", meaning: str = "", lang: str = "unknown", song_title: str = "") -> bool:
        if not word:
            return False
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO vocab_notebook (word, romaji, meaning, lang, song_title, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (word.strip(), romaji.strip(), meaning.strip(), lang.strip(), song_title.strip()))
                conn.commit()
                return True
        except Exception as e:
            logger.debug(f"Vocab save error: {e}")
            return False

    def get_vocab_words(self) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, word, romaji, meaning, lang, song_title, created_at FROM vocab_notebook ORDER BY id DESC")
                return [
                    {
                        "id": row[0],
                        "word": row[1],
                        "romaji": row[2],
                        "meaning": row[3],
                        "lang": row[4],
                        "song_title": row[5],
                        "created_at": row[6]
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.debug(f"Get vocab error: {e}")
            return []

    def delete_vocab_word(self, word_id: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM vocab_notebook WHERE id = ?", (word_id,))
                conn.commit()
        except Exception:
            pass
