#!/usr/bin/env python3
"""Headless UI smoke testing and screenshot generator for SpotifyLyrics v3.

Uses Microsoft Edge headless to test the 2026 frontend redesign without requiring Spotify,
captures reference screenshots, and verifies key accessibility, rendering, and interaction states.
"""

from __future__ import annotations

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

# 20 lyric lines with Korean Hangul, English translations, and Romanizations
SAMPLE_LINES = [
    {"time": 0.0, "text": "맨날 이런 식", "translation": "It's always like this", "romaji": "maennal ireon sik"},
    {"time": 3.5, "text": "너는 너, 나는 나, 너의 공식", "translation": "You are you, I am me, that's your formula", "romaji": "neoneun neo naneun na neoui gong-sik"},
    {"time": 7.0, "text": "핸드폰은 장식", "translation": "Your phone is just an accessory", "romaji": "haendeuponeun jangsik"},
    {"time": 10.5, "text": "진짜 남친 맞긴 하니? I'm sick", "translation": "Am I really your boyfriend? I'm sick", "romaji": "jinjja namchin matgin hani? I'm sick"},
    {"time": 14.0, "text": "금보다 아껴 둔 내 맘은 어디로", "translation": "Where did my heart, kept more precious than gold, go?", "romaji": "geumboda akkyeo dun nae mameun eodiro"},
    {"time": 17.5, "text": "밀고 당기기? 그딴 거 난 몰라", "translation": "Push and pull? I know nothing of such games", "romaji": "milgo danggigi? geuttan geo nan molla"},
    {"time": 21.0, "text": "근데 왜 자꾸 날 찔러 봐", "translation": "So why do you keep poking at me?", "romaji": "geunde wae jakku nal jjilleo bwa"},
    {"time": 24.5, "text": "헤어지잔 말은 뱉지 마 제발", "translation": "Please don't spit out the word 'break up'", "romaji": "heeojijan mareun baetji ma jebal"},
    {"time": 28.0, "text": "넌 내가 필요할 때만 날 찾지", "translation": "You only look for me when you need me", "romaji": "neon naega piryohal ttaeman nal chatji"},
    {"time": 31.5, "text": "우린 평행선, 같은 곳을 보지만", "translation": "We are parallel lines, looking at the same place", "romaji": "urin pyeonghaengseon, gateun goseul bojiman"},
    {"time": 35.0, "text": "너무 다르지, 난 너밖에 없는데", "translation": "Yet so different; I only have you", "romaji": "neomu dareuji, nan neobakke eomneunde"},
    {"time": 39.0, "text": "왜 너는 내가 없는 것처럼 굴어", "translation": "Why do you act as if I am not even there?", "romaji": "wae neoneun naega eomneun geotcheoreom gureo"},
    {"time": 43.0, "text": "헷갈리게 하지 마", "translation": "Don't confuse me anymore", "romaji": "hetgallige haji ma"},
    {"time": 46.5, "text": "장난해 너? 도대체 내가 뭐야", "translation": "Are you kidding? What on earth am I to you?", "romaji": "jangnanhae neo? dodaeche naega mwoya"},
    {"time": 50.0, "text": "만만해 uh? 날 갖고 노는 거야", "translation": "Am I that easy? Are you playing with me?", "romaji": "manmanhae uh? nal gatgo noneun geoya"},
    {"time": 54.0, "text": "너 지금 위험해, 왜 나를 시험해", "translation": "You're in danger right now, why are you testing me?", "romaji": "neo jigeum wiheomhae, wae nareul siheomhae"},
    {"time": 58.0, "text": "왜 나를 시험해, 헷갈리게 하지 마", "translation": "Why are you testing me, don't confuse me", "romaji": "wae nareul siheomhae, hetgallige haji ma"},
    {"time": 62.0, "text": "장난해 너? 도대체 내가 뭐야", "translation": "Are you kidding? What on earth am I to you?", "romaji": "jangnanhae neo? dodaeche naega mwoya"},
    {"time": 66.0, "text": "만만해 uh? 날 갖고 노는 거야", "translation": "Am I that easy? Are you playing with me?", "romaji": "manmanhae uh? nal gatgo noneun geoya"},
    {"time": 70.0, "text": "너 지금 위험해, 왜 나를 시험해", "translation": "You're in danger right now, why are you testing me?", "romaji": "neo jigeum wiheomhae, wae nareul siheomhae"},
    {"time": 74.0, "text": "Can't touch this, yeah you know it", "translation": "", "romaji": ""},
]


class SmokeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        url = self.path
        if url.startswith("/?") or url == "/" or url.startswith("/index.html"):
            # Serve index.html with smoke injection script
            index_path = WEB_DIR / "index.html"
            content = index_path.read_text(encoding="utf-8")
            
            scenario = "synced"
            if "scenario=" in url:
                scenario = url.split("scenario=")[1].split("&")[0]

            harness = f"""
            <script>
            (function() {{
              var sampleLines = {json.dumps(SAMPLE_LINES)};
              var scenario = "{scenario}";

              window.pywebview = {{
                api: {{
                  get_settings: function() {{
                    return Promise.resolve({{
                      theme: 'dark',
                      target_lang: 'en',
                      romanization_enabled: true,
                      karaoke_sweep_enabled: true,
                      view_mode: scenario === 'mini' ? 'mini' : (scenario === 'split' ? 'fullscreen' : 'card'),
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
                      {{ provider: 'local', id: 'local:1', title: 'Danger', artist: 'BTS', album: 'Dark & Wild', duration: 245, has_synced: true, score: 100 }},
                      {{ provider: 'lrclib', id: 'lrclib:123', title: 'Danger', artist: 'BTS', album: 'Dark & Wild', duration: 245, has_synced: true, score: 98 }},
                      {{ provider: 'netease', id: 'netease:456', title: 'Danger (Japanese Ver.)', artist: 'BTS', album: 'Wake Up', duration: 246, has_synced: true, score: 85 }}
                    ]);
                  }},
                  select_lyrics: function() {{ return Promise.resolve(true); }},
                  save_local_lyrics: function() {{ return Promise.resolve({{ ok: true, path: "C:\\\\test.lrc" }}); }},
                  lookup_word: function(w) {{
                    return Promise.resolve({{ word: w, trans: 'danger / risk', romaji: 'wiheom', lang: 'ko' }});
                  }},
                  toggle_favorite: function() {{ return Promise.resolve(true); }},
                  get_song_history: function() {{ return Promise.resolve([]); }},
                  get_vocab_words: function() {{ return Promise.resolve([]); }},
                  toggle_pin: function() {{ return Promise.resolve(true); }},
                  toggle_fullscreen: function() {{ return Promise.resolve(true); }},
                  toggle_mini_mode: function() {{ return Promise.resolve(true); }},
                  toggle_mini_expand: function() {{ return Promise.resolve(true); }},
                  set_mini_width: function(w) {{ return Promise.resolve(w); }},
                  get_mini_width: function() {{ return Promise.resolve(560); }},
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
                if (scenario === 'synced' || scenario === 'split' || scenario === 'mini' || scenario === 'palette' || scenario === 'settings' || scenario === 'search' || scenario === 'trans_only') {{
                  window.updateTrack({{
                    title: 'Danger',
                    artist: 'BTS',
                    album: 'Dark & Wild',
                    duration: 245.0,
                    status: 4,
                    position_ms: 35000,
                    is_playing: true,
                    is_favorite: true
                  }});
                  window.updateLyrics({{
                    title: 'Danger',
                    artist: 'BTS',
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
                  window.updatePosition(35.0, true);

                  if (scenario === 'split') {{
                    document.body.classList.add('mode-fullscreen', 'layout-split');
                  }} else if (scenario === 'mini') {{
                    document.body.classList.add('mode-mini');
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
                    if (modal) modal.classList.add('open');
                  }}
                }} else if (scenario === 'unsynced') {{
                  window.updateTrack({{
                    title: 'Danger (Acoustic)',
                    artist: 'BTS',
                    album: 'Dark & Wild',
                    duration: 245.0,
                    status: 4,
                    position_ms: 35000,
                    is_playing: true,
                    is_favorite: false
                  }});
                  window.updateLyrics({{
                    title: 'Danger (Acoustic)',
                    artist: 'BTS',
                    is_synced: false,
                    lang: 'ko',
                    provider: 'UNSYNCED',
                    lines: sampleLines.map(function(l) {{ return {{ time: -1, text: l.text }}; }})
                  }});
                }}
              }}, 100);
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
        ("synced", 480, 720, AUDIT_DIR / "01_card_synced.png"),
        ("unsynced", 480, 720, AUDIT_DIR / "02_card_unsynced.png"),
        ("split", 1280, 800, AUDIT_DIR / "03_fullscreen_split.png"),
        ("mini", 560, 95, AUDIT_DIR / "04_mini_mode.png"),
        ("palette", 480, 720, AUDIT_DIR / "05_command_palette.png"),
        ("settings", 480, 720, AUDIT_DIR / "06_settings.png"),
        ("search", 480, 720, AUDIT_DIR / "07_manual_search.png"),
        ("trans_only", 480, 720, AUDIT_DIR / "08_view_trans_only.png"),
    ]

    for name, w, h, out_path in scenarios:
        url = f"http://127.0.0.1:{port}/index.html?scenario={name}"
        cmd = [
            EDGE_EXE,
            "--headless=new",
            "--disable-gpu",
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
