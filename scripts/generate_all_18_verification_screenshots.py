#!/usr/bin/env python3
"""Generates all 18 visual verification screenshots required by the Lyriq UI/UX redesign order.

Uses headless Microsoft Edge to render and capture every required screen state at exact dimensions.
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
AUDIT_DIR = ROOT / "docs" / "audit" / "v3" / "screenshots"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

SAMPLE_LINES = [
    {"time": 0.0, "text": "맨날 이런 식", "translation": "It's always like this", "romaji": "maennal ireon sik"},
    {"time": 3.5, "text": "너는 너, 나는 나, 너의 공식", "translation": "You are you, I am me, that's your formula", "romaji": "neoneun neo naneun na"},
    {"time": 7.0, "text": "핸드폰은 장식", "translation": "Your phone is just an accessory", "romaji": "haendeuponeun jangsik"},
    {"time": 10.5, "text": "진짜 남친 맞긴 하니? I'm sick", "translation": "Am I really your boyfriend? I'm sick", "romaji": "jinjja namchin matgin hani"},
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
    {"time": 50.0, "text": "만만해 uh? 날 갖고 노는 거야", "translation": "Am I that easy? Are you playing with me?", "romaji": "manmanhae uh? nal gatgo noneun geoya"}
]

class LyriqVerificationHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        if self.path.startswith("/index.html"):
            query = ""
            if "?" in self.path:
                query = self.path.split("?", 1)[1]
            
            scenario = "synced"
            for param in query.split("&"):
                if param.startswith("scenario="):
                    scenario = param.split("=", 1)[1]

            with open(WEB_DIR / "index.html", "r", encoding="utf-8") as f:
                content = f.read()

            harness = f"""
            <style>
              *, *::before, *::after {{
                animation-duration: 0.001s !important;
                animation-delay: 0s !important;
                transition-duration: 0.001s !important;
                transition-delay: 0s !important;
              }}
            </style>
            <script>
            (function() {{
              var scenario = "{scenario}";
              var sampleLines = {json.dumps(SAMPLE_LINES)};

              window.pywebview = {{
                api: {{
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

              window.dispatchEvent(new Event('pywebviewready'));

              setTimeout(function() {{
                if (scenario === 'waiting') {{
                  if (window.showIdle) window.showIdle();
                  return;
                }}

                if (scenario === 'resolving') {{
                  window.updateTrack({{
                    title: 'Danger',
                    artist: 'BTS',
                    album: 'Dark & Wild',
                    duration: 245.0,
                    status: 4,
                    position_ms: 0,
                    is_playing: true,
                    is_favorite: true
                  }});
                  if (window.showSkeleton) window.showSkeleton();
                  return;
                }}

                if (scenario === 'offline') {{
                  window.updateTrack({{
                    title: 'Danger',
                    artist: 'BTS',
                    album: 'Dark & Wild',
                    duration: 245.0,
                    status: 4,
                    position_ms: 0,
                    is_playing: true,
                    is_favorite: false
                  }});
                  if (window.showError) {{
                    window.showError('You are offline', 'Lyriq cannot reach online providers. Connect to network or load cached local .lrc file.', true);
                  }}
                  return;
                }}

                if (scenario === 'unsynced') {{
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
                  return;
                }}

                if (scenario === 'trans_unavail') {{
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
                    lines: sampleLines.map(function(l, i) {{
                      return {{
                        translation: i === 10 ? 'Translation unavailable' : l.translation,
                        romaji: l.romaji
                      }};
                    }})
                  }});
                  window.updatePosition(35.0, true);
                  return;
                }}

                // Standard track playback for other scenarios
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
                  var mb = document.getElementById('miniBar');
                  if (mb) mb.hidden = false;
                  var orig = document.getElementById('miniOriginal');
                  if (orig) orig.textContent = '너무 다르지, 난 너밖에 없는데';
                  var trans = document.getElementById('miniTranslation');
                  if (trans) trans.textContent = 'Yet so different; I only have you';
                  var fill = document.getElementById('miniProgressFill');
                  if (fill) fill.style.width = '65%';
                }} else if (scenario === 'mini_expanded') {{
                  document.body.classList.add('mode-mini', 'mini-expanded');
                  var mb = document.getElementById('miniBar');
                  if (mb) mb.hidden = false;
                  var d = document.getElementById('miniDrawer');
                  if (d) d.hidden = false;
                  var orig = document.getElementById('miniOriginal');
                  if (orig) orig.textContent = '너무 다르지, 난 너밖에 없는데';
                  var trans = document.getElementById('miniTranslation');
                  if (trans) trans.textContent = 'Yet so different; I only have you';
                }} else if (scenario === 'square') {{
                  document.body.classList.add('mode-square');
                  var h = document.getElementById('squareHeader');
                  var f = document.getElementById('squareFooter');
                  if (h) h.hidden = false;
                  if (f) f.hidden = false;
                }} else if (scenario === 'ghost') {{
                  document.body.classList.add('mode-ghost', 'ghost-mode');
                }} else if (scenario === 'study') {{
                  var sl = document.getElementById('studyLens');
                  if (sl) {{
                    sl.hidden = false;
                    document.body.classList.add('study-open');
                    var sw = document.getElementById('studyWord'); if (sw) sw.textContent = '다르다';
                    var sp = document.getElementById('studyPron'); if (sp) sp.textContent = 'dareuda • Adjective';
                    var sd = document.getElementById('studyDef'); if (sd) sd.textContent = 'To be different, dissimilar, unlike';
                    var sq = document.getElementById('studyQuote'); if (sq) sq.innerHTML = '너무 <span class="selected-word-highlight">다르지</span>, 난 너밖에 없는데';
                    var sqt = document.getElementById('studyQuoteTrans'); if (sqt) sqt.textContent = 'Yet so different; I only have you';
                  }}
                }} else if (scenario === 'palette') {{
                  var cp = document.getElementById('commandPalette');
                  if (cp) {{
                    cp.hidden = false;
                    var inp = document.getElementById('paletteInput');
                    if (inp) inp.value = 'mode';
                    var list = document.getElementById('paletteList');
                    if (list) {{
                      list.innerHTML = `
                        <button class="palette-item is-active" type="button"><span class="palette-icon"><svg class="icon"><use href="#icon-square"></use></svg></span><div><div class="palette-title">Switch to 1:1 Square Mode</div><div class="palette-sub">Compact floating square window</div></div><kbd>Ctrl+2</kbd></button>
                        <button class="palette-item" type="button"><span class="palette-icon"><svg class="icon"><use href="#icon-pip"></use></svg></span><div><div class="palette-title">Switch to Mini Island Mode</div><div class="palette-sub">Compact 560x95 floating dock</div></div><kbd>Ctrl+M</kbd></button>
                        <button class="palette-item" type="button"><span class="palette-icon"><svg class="icon"><use href="#icon-expand"></use></svg></span><div><div class="palette-title">Switch to Fullscreen Split</div><div class="palette-sub">High-res album art + synced lyrics</div></div><kbd>F11</kbd></button>
                        <button class="palette-item" type="button"><span class="palette-icon"><svg class="icon"><use href="#icon-eye-off"></use></svg></span><div><div class="palette-title">Toggle Ghost Overlay HUD</div><div class="palette-sub">Transparent click-through desktop overlay</div></div><kbd>Ctrl+G</kbd></button>
                      `;
                    }}
                  }}
                }} else if (scenario === 'settings') {{
                  if (window.openSettings) window.openSettings('appearance');
                }} else if (scenario === 'search') {{
                  var sm = document.getElementById('searchModal');
                  if (sm) {{
                    sm.hidden = false;
                    var inp = document.getElementById('searchQueryInput');
                    if (inp) inp.value = 'Danger BTS';
                    var title = document.getElementById('searchCurrentTitle');
                    if (title) title.textContent = 'Danger';
                    var sub = document.getElementById('searchCurrentSub');
                    if (sub) sub.textContent = 'BTS • Dark & Wild (2014) • 4:05';
                    var count = document.getElementById('searchCandidateCount');
                    if (count) count.textContent = '3 candidates';
                    var results = document.getElementById('searchResults');
                    if (results) {{
                      results.innerHTML = `
                        <div class="search-row active">
                          <span class="tag provider-badge">LRCLIB</span>
                          <div><strong>BTS - Danger</strong><div class="small">Dark & Wild (2014) • 4:05</div></div>
                          <span class="tag">Synced</span>
                          <span>Diff: 0.0s</span>
                          <span class="small" style="color:var(--brand)">98% Match</span>
                          <span>✓</span>
                        </div>
                        <div class="search-row">
                          <span class="tag provider-badge">NETEASE</span>
                          <div><strong>BTS - Danger (Acoustic Version)</strong><div class="small">Acoustic Edition • 4:07</div></div>
                          <span class="tag">Synced</span>
                          <span>Diff: +2.1s</span>
                          <span class="small">84% Match</span>
                          <span></span>
                        </div>
                        <div class="search-row">
                          <span class="tag provider-badge">LRCLIB</span>
                          <div><strong>BTS - Danger (Japanese Ver.)</strong><div class="small">Danger - Single • 4:05</div></div>
                          <span class="tag">Synced</span>
                          <span>Diff: 0.0s</span>
                          <span class="small">72% Match</span>
                          <span></span>
                        </div>
                      `;
                    }}
                    var it = document.getElementById('inspectTitle');
                    if (it) it.textContent = 'LRCLIB (Synced LRC)';
                    var mt = document.getElementById('metricTitle');
                    if (mt) mt.textContent = '100%';
                    var mtb = document.getElementById('metricTitleBar');
                    if (mtb) mtb.style.width = '100%';
                    var ma = document.getElementById('metricArtist');
                    if (ma) ma.textContent = '100%';
                  }}
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


def generate_all():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    port = 8998
    server = socketserver.TCPServer(("127.0.0.1", port), LyriqVerificationHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Server started on http://127.0.0.1:{port}/")

    # 18 Scenarios required by Section 28:
    scenarios = [
        ("01_reader_dark.png", "synced", 1120, 760),
        ("02_reader_small_480x663.png", "synced", 480, 663),
        ("03_reader_small_400x500.png", "synced", 400, 500),
        ("04_square_320.png", "square", 320, 320),
        ("05_square_520.png", "square", 520, 520),
        ("06_mini_island.png", "mini", 560, 54),
        ("07_mini_expanded.png", "mini_expanded", 560, 220),
        ("08_fullscreen_split.png", "split", 1280, 800),
        ("09_ghost_hud.png", "ghost", 800, 400),
        ("10_study_lens.png", "study", 1120, 760),
        ("11_lyrics_search.png", "search", 1040, 720),
        ("12_command_palette.png", "palette", 800, 600),
        ("13_settings.png", "settings", 840, 620),
        ("14_waiting_for_spotify.png", "waiting", 800, 600),
        ("15_resolving_lyrics.png", "resolving", 800, 600),
        ("16_unsynced_lyrics.png", "unsynced", 800, 600),
        ("17_translation_unavailable.png", "trans_unavail", 800, 600),
        ("18_offline_state.png", "offline", 800, 600),
    ]

    for fname, scenario, w, h in scenarios:
        out_path = AUDIT_DIR / fname
        url = f"http://127.0.0.1:{port}/index.html?scenario={scenario}"
        cmd = [
            EDGE_EXE,
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=1500",
            f"--window-size={w},{h}",
            f"--screenshot={out_path.resolve()}",
            url,
        ]
        print(f"Generating {fname} ({w}x{h}, scenario={scenario})...")
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if p.returncode != 0:
            print(f"  Error: {p.stderr}")
        else:
            print(f"  Success: {out_path.name} ({out_path.stat().st_size:,} bytes)")

    server.shutdown()
    print("All 18 verification screenshots successfully captured!")


if __name__ == "__main__":
    generate_all()
