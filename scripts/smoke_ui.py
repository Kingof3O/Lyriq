#!/usr/bin/env python3
"""Headless UI smoke testing and screenshot generator for Lyriq v3.

Uses Microsoft Edge headless to test the 2026 frontend redesign without requiring Spotify,
captures reference screenshots with genuine Taemin tracks and real high-res album thumbnails.
"""

from __future__ import annotations

import base64
import http.server
import json
import os
import socketserver
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
AUDIT_DIR = ROOT / "docs" / "audit" / "v3"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# Load Taemin Guilty lines
with open(Path(__file__).resolve().parent / "taemin_sample_lines.json", "r", encoding="utf-8") as f:
    SAMPLE_LINES = json.load(f)

# Load real high-res album covers as base64
with open(WEB_DIR / "assets" / "taemin-guilty.jpg", "rb") as f:
    TAEMIN_THUMBNAIL = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

with open(WEB_DIR / "assets" / "amr-diab-tamally-maak.jpg", "rb") as f:
    AMR_DIAB_THUMBNAIL = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

ARABIC_SAMPLE_LINES = [
    {"time": 0.0, "text": "تملي معاك، ولو حتى بعيد عني", "translation": "Always with you, even if you are far from me", "romaji": ""},
    {"time": 4.0, "text": "في قلبي هواك، بتمناك ومشتريك\nوعايش ليك سنين عمري", "translation": "Your love is in my heart, I desire only you\nAnd I live all the years of my life for you", "romaji": ""},
    {"time": 9.0, "text": "تملي معاك، معاك قلبي معاك روحي يا أغلى حبيب", "translation": "Always with you, my heart is with you, my soul is with you, dearest beloved", "romaji": ""},
    {"time": 14.0, "text": "ومهما تكون بعيد عني لقلبي قريب", "translation": "And no matter how far away you are, you remain close to my heart", "romaji": ""},
]


class SmokeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        url = self.path
        if url.startswith("/?") or url == "/" or url.startswith("/index.html"):
            index_path = WEB_DIR / "index.html"
            content = index_path.read_text(encoding="utf-8")
            
            scenario = "synced"
            if "scenario=" in url:
                scenario = url.split("scenario=")[1].split("&")[0]

            harness = f"""
            <script>
            (function() {{
              var sampleLines = {json.dumps(SAMPLE_LINES)};
              var arabicLines = {json.dumps(ARABIC_SAMPLE_LINES)};
              var taeminThumb = {json.dumps(TAEMIN_THUMBNAIL)};
              var arabicThumb = {json.dumps(AMR_DIAB_THUMBNAIL)};
              var scenario = "{scenario}";

              window.pywebview = {{
                api: {{
                  get_settings: function() {{
                    return Promise.resolve({{
                      theme: 'dark',
                      target_lang: 'en',
                      romanization_enabled: true,
                      karaoke_sweep_enabled: true,
                      view_mode: scenario === 'mini' ? 'mini' : (scenario === 'square' ? 'square' : (scenario === 'split' ? 'fullscreen' : 'card')),
                      ghost_mode: false,
                      discord_rpc_enabled: true,
                      low_power_mode: false,
                      font_scale: 1.0,
                      always_on_top: false,
                      lyrics_view_mode: 'both',
                      word_lookup_enabled: true,
                      split_layout: scenario === 'split'
                    }});
                  }},
                  save_settings: function() {{ return Promise.resolve(true); }},
                  get_song_offset: function() {{ return Promise.resolve(0.0); }},
                  set_song_offset: function() {{ return Promise.resolve(0.0); }},
                  get_cache_stats: function() {{
                    return Promise.resolve({{ lyrics: 42, translations: 128, thumbnails: 15, size_bytes: 524288 }});
                  }},
                  clear_cache: function() {{
                    return Promise.resolve({{ lyrics_deleted: 42, translations_deleted: 128, thumbnails_deleted: 15 }});
                  }},
                  get_lrc_folder: function() {{
                    return Promise.resolve("C:\\\\Users\\\\User\\\\AppData\\\\Local\\\\SpotifyLyrics\\\\lrc");
                  }},
                  open_lrc_folder: function() {{ return Promise.resolve(true); }},
                  search_lyrics: function() {{
                    return Promise.resolve([
                      {{ provider: 'local', id: 'local:1', title: 'Guilty', artist: 'TAEMIN', album: 'Guilty - The 4th Mini Album', duration: 181, has_synced: true, score: 100 }},
                      {{ provider: 'lrclib', id: 'lrclib:123', title: 'Guilty', artist: 'TAEMIN', album: 'Guilty - The 4th Mini Album', duration: 181, has_synced: true, score: 99 }},
                      {{ provider: 'netease', id: 'netease:456', title: 'Criminal', artist: 'TAEMIN', album: 'Never Gonna Dance Again : Act 1', duration: 210, has_synced: true, score: 85 }}
                    ]);
                  }},
                  select_lyrics: function() {{ return Promise.resolve(true); }},
                  save_local_lyrics: function() {{ return Promise.resolve({{ ok: true, path: "C:\\\\test.lrc" }}); }},
                  lookup_word: function(w) {{
                    return Promise.resolve({{
                      word: w,
                      definition: "guilt; guilty conscience; remorse",
                      phonetic: "joechaekgam",
                      lang: "Korean",
                      pos: "noun",
                      notes: "Theme of Taemin's 4th Mini Album"
                    }});
                  }},
                  get_favorites: function() {{ return Promise.resolve([]); }},
                  get_history: function() {{ return Promise.resolve([]); }},
                  get_vocab_notebook: function() {{ return Promise.resolve([]); }},
                  set_mode: function() {{ return Promise.resolve(true); }},
                  get_saved_bounds: function() {{ return Promise.resolve(null); }},
                  save_window_bounds: function() {{ return Promise.resolve(true); }},
                  drag_window: function() {{ return Promise.resolve(true); }},
                  toggle_pin: function() {{ return Promise.resolve(true); }},
                  toggle_fullscreen: function() {{ return Promise.resolve(true); }},
                  toggle_mini_mode: function() {{ return Promise.resolve(true); }},
                  set_mini_width: function(w) {{ return Promise.resolve(w); }},
                  get_mini_width: function() {{ return Promise.resolve(560); }},
                  toggle_square_mode: function() {{ return Promise.resolve(true); }},
                  set_square_size: function(s) {{ return Promise.resolve(s); }},
                  get_square_size: function() {{ return Promise.resolve(420); }},
                  toggle_ghost_mode: function() {{ return Promise.resolve(true); }},
                  toggle_discord_rpc: function() {{ return Promise.resolve(true); }},
                  seek: function() {{ return Promise.resolve(true); }},
                  play_pause: function() {{ return Promise.resolve(true); }},
                  next_track: function() {{ return Promise.resolve(true); }},
                  prev_track: function() {{ return Promise.resolve(true); }},
                  minimize: function() {{ return Promise.resolve(true); }},
                  close: function() {{ return Promise.resolve(true); }},
                  retry_lyrics: function() {{ return Promise.resolve(true); }},
                  get_startup_state: function() {{ return Promise.resolve(false); }},
                  set_start_with_windows: function() {{ return Promise.resolve(false); }},
                  set_close_to_tray: function() {{ return Promise.resolve(true); }}
                }}
              }};

              // Dispatch ready
              window.dispatchEvent(new Event('pywebviewready'));

              // Feed scenario data after init
              setTimeout(function() {{
                if (scenario === 'synced' || scenario === 'split' || scenario === 'mini' || scenario === 'square' || scenario === 'palette' || scenario === 'settings' || scenario === 'search' || scenario === 'trans_only') {{
                  window.updateTrack({{
                    title: 'Guilty',
                    artist: 'TAEMIN',
                    album: 'Guilty - The 4th Mini Album',
                    thumbnail: taeminThumb,
                    duration: 181.0,
                    status: 4,
                    position_ms: 42600,
                    is_playing: true,
                    is_favorite: true
                  }});
                  window.updateLyrics({{
                    title: 'Guilty',
                    artist: 'TAEMIN',
                    is_synced: true,
                    lang: 'ko',
                    provider: 'LRCLIB',
                    lines: sampleLines.map(function(l) {{ return {{ time: l.time, text: l.text }}; }})
                  }});
                  window.updateTranslations({{
                    lang: 'ko',
                    provider: 'LRCLIB',
                    lines: sampleLines.map(function(l) {{ return {{ translation: l.translation, romaji: l.romaji }}; }})
                  }});
                  window.updatePosition(42.6, true);

                  if (scenario === 'split') {{
                    document.body.classList.add('mode-fullscreen', 'layout-split');
                  }} else if (scenario === 'mini') {{
                    document.body.classList.add('mode-mini');
                  }} else if (scenario === 'square') {{
                    document.body.classList.add('mode-square', 'square-art-bg');
                  }} else if (scenario === 'trans_only') {{
                    document.body.classList.remove('view-both', 'view-orig-only');
                    document.body.classList.add('view-trans-only');
                  }} else if (scenario === 'palette') {{
                    var cp = document.getElementById('commandPalette');
                    if (cp) {{
                      cp.classList.add('open');
                      var inp = document.getElementById('paletteInput');
                      if (inp) inp.value = 'theme';
                      var list = document.getElementById('paletteList');
                      if (list) {{
                        list.innerHTML = '<div class=\"palette-item active\"><span class=\"palette-title\">Appearance: Switch theme</span></div>';
                      }}
                    }}
                  }} else if (scenario === 'settings') {{
                    if (window.openSettings) window.openSettings('lyrics');
                  }} else if (scenario === 'search') {{
                    var modal = document.getElementById('modalSearchLyrics');
                    if (modal) {{
                      modal.classList.add('open');
                      var inp = document.getElementById('inputSearchLyrics');
                      if (inp) inp.value = 'Guilty TAEMIN';
                      var res = document.getElementById('searchResults');
                      if (res) {{
                        res.innerHTML = `
                          <div class="search-item is-selected">
                            <span class="search-provider-badge">LRCLIB</span>
                            <div class="search-meta">
                              <span class="search-title">Guilty</span>
                              <span class="search-artist">TAEMIN • Guilty - The 4th Mini Album • 3:01</span>
                            </div>
                            <span class="badge badge-accent">100% Match</span>
                          </div>
                          <div class="search-item">
                            <span class="search-provider-badge">NETEASE</span>
                            <div class="search-meta">
                              <span class="search-title">Criminal</span>
                              <span class="search-artist">TAEMIN • Never Gonna Dance Again : Act 1 • 3:30</span>
                            </div>
                            <span class="badge">98% Match</span>
                          </div>
                          <div class="search-item">
                            <span class="search-provider-badge">LRCLIB</span>
                            <div class="search-meta">
                              <span class="search-title">MOVE</span>
                              <span class="search-artist">TAEMIN • MOVE - The 2nd Album • 3:31</span>
                            </div>
                            <span class="badge">95% Match</span>
                          </div>
                        `;
                      }}
                    }}
                  }}
                }} else if (scenario === 'arabic') {{
                  window.updateTrack({{
                    title: 'تملي معاك',
                    artist: 'عمرو دياب',
                    album: 'تملي معاك',
                    thumbnail: arabicThumb,
                    duration: 269.0,
                    status: 4,
                    position_ms: 5000,
                    is_playing: true,
                    is_favorite: true
                  }});
                  window.updateLyrics({{
                    title: 'تملي معاك',
                    artist: 'عمرو دياب',
                    is_synced: true,
                    lang: 'ar',
                    provider: 'LRCLIB',
                    lines: arabicLines.map(function(l) {{ return {{ time: l.time, text: l.text }}; }})
                  }});
                  window.updateTranslations({{
                    lang: 'ar',
                    provider: 'LRCLIB',
                    lines: arabicLines.map(function(l) {{ return {{ translation: l.translation, romaji: l.romaji }}; }})
                  }});
                  window.updatePosition(5.0, true);
                }} else if (scenario === 'unsynced') {{
                  window.updateTrack({{
                    title: 'Guilty (Unsynced)',
                    artist: 'TAEMIN',
                    album: 'Guilty - The 4th Mini Album',
                    thumbnail: taeminThumb,
                    duration: 181.0,
                    status: 4,
                    position_ms: 42600,
                    is_playing: true,
                    is_favorite: false
                  }});
                  window.updateLyrics({{
                    title: 'Guilty (Unsynced)',
                    artist: 'TAEMIN',
                    is_synced: false,
                    lang: 'ko',
                    provider: 'UNSYNCED',
                    lines: sampleLines.map(function(l) {{ return {{ time: -1, text: l.text }}; }})
                  }});
                  window.updateTranslations({{
                    lang: 'ko',
                    provider: 'UNSYNCED',
                    lines: sampleLines.map(function(l) {{ return {{ translation: l.translation, romaji: l.romaji }}; }})
                  }});
                  window.updatePosition(42.6, true);
                }}
              }}, 120);
            }})();
            </script>
            """

            modified = content.replace("</body>", f"{harness}</body>")
            raw = modified.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        else:
            super().do_GET()


def run_smoke():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    port = 8991
    server = socketserver.TCPServer(("127.0.0.1", port), SmokeRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Smoke HTTP server running at http://127.0.0.1:{port}/")

    scenarios = [
        ("synced", 1120, 760, AUDIT_DIR / "00_reader_desktop_1120x760.png"),
        ("synced", 480, 720, AUDIT_DIR / "01_card_synced.png"),
        ("unsynced", 480, 720, AUDIT_DIR / "02_card_unsynced.png"),
        ("split", 1280, 800, AUDIT_DIR / "03_fullscreen_split.png"),
        ("mini", 560, 95, AUDIT_DIR / "04_mini_mode.png"),
        ("palette", 480, 720, AUDIT_DIR / "05_command_palette.png"),
        ("settings", 480, 720, AUDIT_DIR / "06_settings.png"),
        ("search", 480, 720, AUDIT_DIR / "07_manual_search.png"),
        ("trans_only", 480, 720, AUDIT_DIR / "08_view_trans_only.png"),
        ("arabic", 480, 720, AUDIT_DIR / "09_arabic_lyrics.png"),
        ("square", 520, 520, AUDIT_DIR / "10_square_mode.png"),
    ]

    for name, w, h, out_path in scenarios:
        url = f"http://127.0.0.1:{port}/index.html?scenario={name}"
        cmd = [
            EDGE_EXE,
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=1200",
            f"--window-size={w},{h}",
            f"--screenshot={out_path}",
            url,
        ]
        print(f"Capturing [{name}] ({w}x{h}) -> {out_path.name}...")
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if p.returncode != 0:
            print(f"  Warning: Edge exited with {p.returncode}: {p.stderr}")
        else:
            size = out_path.stat().st_size if out_path.exists() else 0
            print(f"  Success: {out_path.name} ({size:,} bytes)")

    server.shutdown()
    print("Smoke testing complete.")


if __name__ == "__main__":
    run_smoke()
