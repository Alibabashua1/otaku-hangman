# --- standard imports
import sys
import os
import time
import subprocess
import threading
import queue
import tkinter as tk
import tkinter.font as tkfont
import re
import traceback
import codecs
import json
# Needed for in-process runner
import runpy
import builtins
# fcntl is Unix-only (not available on Windows)
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    fcntl = None
    HAS_FCNTL = False
import select
try:
    import winsound  # Windows-only
    HAS_WINSOUND = True
except Exception:
    winsound = None
    HAS_WINSOUND = False

LOG_PATH = "otaku_gui.log"

def log(*args):
    msg = " ".join(str(a) for a in args)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    print(msg, flush=True)

def log_exc(prefix: str, exc: Exception):
    try:
        log(prefix, repr(exc))
    except Exception:
        pass

log("[otaku_gui] RUNNING:", sys.executable)
log("[otaku_gui] cwd:", os.getcwd())
# macOS: Tk uses Cocoa; forking a child process can crash unless fork safety is disabled.
# This must be set in the parent before spawning the child.
if sys.platform == "darwin":
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

# =====================
#  UI THEME CONSTANTS
# =====================
# Retro handheld vibe: dark berry shell + kawaii pink neon
BG_TOP = "#120913"       # outer background (berry)
BG_BOTTOM = "#24102a"    # subtle gradient bottom (plum)
PANEL_BORDER = "#3a2442" # device border
TITLE_FG = "#ffb3d9"     # neon pink
HINT_FG = "#e7b6ff"      # soft lavender
ACCENT_MINT = "#b8ffb1"  # mint accent
ACCENT_ROSEGOLD = "#ff86b7"  # rose-pink accent

ACCENT_GOLD = "#ffd36a"       # warm gold
ACCENT_RED = "#ff6b8a"        # soft red-pink (fail)
SCREEN_BG = "#09050a"

# keyword tags for highlighting
HIGHLIGHT_RULES = [
    ("tag_win", ["you win", "round cleared", "perfect guess", "yatta", "sugoi", "kawaii"]),
    ("tag_lose", ["you lose", "game over", "wrong", "life -1", "streak reset", "failed"]),
    ("tag_unlock", ["congratulations dazy", "unlocked the challenge mode", "challenge cleared", "password accepted"]),
    ("tag_warn", ["wrong password", "type exactly", "already guessed", "doesn't move"]),
]

# Font selection (lazy init: Tk must exist before querying families)
FONT_FAMILY = "Menlo"
FONT_MONO = (FONT_FAMILY, 11)
FONT_MONO_BOLD_10 = (FONT_FAMILY, 10, "bold")
FONT_MONO_BOLD_12 = (FONT_FAMILY, 12, "bold")
FONT_MONO_BOLD_20 = (FONT_FAMILY, 20, "bold")

# =====================
#  Windows glyph-safe text helpers
# =====================
USE_ASCII_UI = (sys.platform == "win32")

_UI_REPL = {
    "📶": "NET",
    "🔋": "BAT",
    "♡": "<3",
    "✦": "*",
    "✧": "*",
    "▶": ">",
    "■": "[]",
}

_KAOMOJI_REPL = {
    "(ฅ^•ﻌ•^ฅ)": "(^_^)" ,
    "(ฅ^•ﻌ•^ฅ) ♡": "(^_^) <3",
    "(ง •̀_•́)ง": "(>_<)",
}

_CONSOLE_REPL = {
    "◆": "*",
    "◇": ".",
    "✅": "[OK]",
    "❌": "[X]",
    "📺": "From",
    "💗": "HP",
    "🔥": "[FIRE]",
    "✨": "*",
    "♡": "<3",
    "✦": "*",
    "✧": "*",
}

def ui_text(s: str) -> str:
    if not s:
        return s
    if not USE_ASCII_UI:
        return s
    for k, v in _KAOMOJI_REPL.items():
        s = s.replace(k, v)
    for k, v in _UI_REPL.items():
        s = s.replace(k, v)
    return s

def console_text(s: str) -> str:
    if not s:
        return s
    if not USE_ASCII_UI:
        return s
    for k, v in _CONSOLE_REPL.items():
        s = s.replace(k, v)
    try:
        s = s.replace("\u200b", "").replace("\ufeff", "")
    except Exception:
        pass
    return s

def _init_fonts():
    """Initialize FONT_* after Tk root exists (fixes Windows glyph/garble issues)."""
    global FONT_FAMILY, FONT_MONO, FONT_MONO_BOLD_10, FONT_MONO_BOLD_12, FONT_MONO_BOLD_20
    try:
        fams = set(tkfont.families())
    except Exception:
        fams = set()

    def pick(preferred, fallback):
        for f in preferred:
            if f in fams:
                return f
        return fallback

    if sys.platform == "win32":
        # Prefer MONOSPACE fonts with good box-drawing; avoid proportional fonts.
        # MS Gothic is fixed-width and supports JP; Cascadia/Consolas/Lucida Console are common.
        FONT_FAMILY = pick([
            "Cascadia Mono",
            "Consolas",
            "Lucida Console",
            "MS Gothic",
            "Courier New",
        ], "Consolas")
    else:
        FONT_FAMILY = "Menlo"

    if sys.platform == "win32":
        # Slightly smaller to fit full menus/frames vertically
        FONT_MONO = (FONT_FAMILY, 10)
        FONT_MONO_BOLD_10 = (FONT_FAMILY, 9, "bold")
        FONT_MONO_BOLD_12 = (FONT_FAMILY, 11, "bold")
        FONT_MONO_BOLD_20 = (FONT_FAMILY, 18, "bold")
    else:
        FONT_MONO = (FONT_FAMILY, 11)
        FONT_MONO_BOLD_10 = (FONT_FAMILY, 10, "bold")
        FONT_MONO_BOLD_12 = (FONT_FAMILY, 12, "bold")
        FONT_MONO_BOLD_20 = (FONT_FAMILY, 20, "bold")

class OtakuGUI:
    def _beep_hit(self):
        try:
            if sys.platform == "win32" and HAS_WINSOUND:
                # short, low beep
                try:
                    winsound.Beep(440, 70)
                except Exception:
                    winsound.MessageBeep(winsound.MB_ICONHAND)
            else:
                self.root.bell()
        except Exception:
            pass

    def _beep_win(self):
        try:
            if sys.platform == "win32" and HAS_WINSOUND:
                # single, softer higher beep
                try:
                    winsound.Beep(880, 90)
                except Exception:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
            else:
                self.root.bell()
        except Exception:
            pass

    def _beep_sparkle(self):
        try:
            if sys.platform == "win32" and HAS_WINSOUND:
                # two tiny chirps, different from hit/win
                try:
                    winsound.Beep(660, 60)
                    winsound.Beep(990, 60)
                except Exception:
                    winsound.MessageBeep(winsound.MB_OK)
            else:
                self.root.bell()
        except Exception:
            pass
    def __init__(self, root):
        self.root = root
        self.root.title("OTAKU HANGMAN — Pocket Edition")
        if sys.platform == "win32":
            self.root.geometry("600x920")
        else:
            self.root.geometry("520x680")
        self.root.configure(bg=BG_TOP)
        # Keep a stable layout (avoid canvas being smaller than our fixed UI)
        try:
            self.root.resizable(False, False)
            if sys.platform == "win32":
                self.root.minsize(600, 920)
            else:
                self.root.minsize(520, 680)
        except Exception:
            pass

        # bring to front (best-effort, but keep it minimal to avoid macOS Tk weirdness)
        try:
            self.root.update_idletasks()
            self.root.lift()
        except Exception:
            pass

        # subprocess state
        self.proc = None
        self.out_queue = queue.Queue()
        # in-proc game runner (for frozen/Windows builds)
        self.in_queue = queue.Queue()
        self._game_thread = None
        self._orig_input = None
        self._stop_requested = False
        self._orig_stdin = None
        self._stdin_proxy = None
        # stdout decoding (incremental, for non-blocking reads)
        self._stdout_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._reader_thread = None
        self._grad_after_id = None

        # shutdown / scheduled-job tracking (prevents macOS Tk crashes on close)
        self._closing = False
        self._clock_after_id = None
        self._drain_after_id = None
        self._boot_after_ids = []

        # macOS stability mode: reduce Tk churn and disable heavy features
        self._safe_mode = (sys.platform == "darwin")

        # parse / highlight state
        self._parse_buf = ""
        self._tag_scan_index = "1.0"

        # HUD state
        self._hud_hp = "--/--"
        self._hud_mode = "BOOT"
        self._hud_sigil = "◇ ◇ ◇ ◇"
        # Track HP numerically to detect wrong guesses reliably (HP decreases)
        self._last_hp_cur = None
        self._last_hp_max = None

        # screen FX state (safe: short flash + tiny shake)
        self._base_x = 0
        self._base_y = 0
        self._shaking = False
        self._flash_job = None
        self._shake_jobs = []
        # FX timing (avoid overlap between hit and sparkle)
        self._last_hit_ts = 0.0
        self._last_sparkle_ts = 0.0
        self._last_win_ts = 0.0
        # Suppress hit FX briefly during win/dazy/challenge-clear sequences
        self._suppress_hit_until = 0.0

        self._screen_outline_normal = "#5a3a66"
        self._screen_outline_flash = "#ff86b7"      # rose hit flash (negative)
        self._screen_outline_sparkle = "#ffd36a"    # warm gold sparkle (DAZY)
        self._screen_outline_win = ACCENT_MINT       # mint green (normal correct guess)
        self._screen_outline = self._screen_outline_normal
        self._screen_outline_width = 1

        # Initialize fonts now that Tk exists (important on Windows)
        try:
            _init_fonts()
        except Exception:
            pass

        try:
            self.build_ui()
        except Exception as e:
            # If UI construction fails, keep a minimal window open and show the error
            log_exc("[otaku_gui] build_ui failed:", e)
            try:
                fallback = tk.Text(self.root, bg=BG_TOP, fg=TITLE_FG, relief="flat", highlightthickness=0)
                fallback.pack(fill="both", expand=True, padx=16, pady=16)
                fallback.insert("end", "[GUI] build_ui() failed.\n\n")
                fallback.insert("end", "".join(traceback.format_exception(type(e), e, e.__traceback__)))
                fallback.configure(state="disabled")
            except Exception:
                pass

        # Ensure the window is actually visible (macOS sometimes launches it behind/hidden)
        try:
            self.root.after(0, self.root.deiconify)
        except Exception:
            pass

        # Log any Tk callback exceptions (otherwise they can look like "it just crashed")
        def _tk_exc_handler(exc, val, tb):
            try:
                log("[otaku_gui] Tk callback exception:", repr(val))
                log("".join(traceback.format_exception(exc, val, tb)))
            except Exception:
                pass
            try:
                # also show inside the console if possible
                self._append_output("\n[GUI] ERROR (Tk callback):\n" + "".join(traceback.format_exception(exc, val, tb)) + "\n")
            except Exception:
                pass

        try:
            self.root.report_callback_exception = _tk_exc_handler
        except Exception:
            pass

    def _cancel_boot_jobs(self):
        """Cancel any scheduled boot/loading callbacks."""
        try:
            for jid in list(getattr(self, "_boot_after_ids", [])):
                try:
                    self.root.after_cancel(jid)
                except Exception:
                    pass
            self._boot_after_ids = []
        except Exception:
            pass

    def _update_clock(self):
        """Update the status bar clock every 30 seconds (safe, stops on close)."""
        try:
            if self._closing:
                return
            if not self.root.winfo_exists():
                return
            if hasattr(self, "left_status") and self.left_status is not None:
                now = time.strftime("%H:%M")
                self.left_status.configure(text=ui_text(f"📶 ▂▄▆█  |  {now}"))
        except Exception as e:
            log_exc("[otaku_gui] clock update error:", e)
        finally:
            try:
                # avoid stacking multiple clock jobs
                if self._clock_after_id is not None:
                    try:
                        self.root.after_cancel(self._clock_after_id)
                    except Exception:
                        pass
                    self._clock_after_id = None
                if not self._closing and self.root.winfo_exists():
                    self._clock_after_id = self.root.after(30000, self._update_clock)
            except Exception:
                pass

    # ---------------------
    # UI
    # ---------------------
    def build_ui(self):
        # Background gradient canvas
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0, bg=BG_TOP)
        self.bg_canvas.pack(fill="both", expand=True)

        # Content container on top of gradient
        self.container = tk.Frame(self.bg_canvas, bg=BG_TOP)
        self.container_id = self.bg_canvas.create_window(0, 0, window=self.container, anchor="nw")

        def _paint_gradient():
            try:
                w = self.bg_canvas.winfo_width()
                h = self.bg_canvas.winfo_height()
                if w <= 2 or h <= 2:
                    return

                self.bg_canvas.delete("grad")

                band = 6
                r1, g1, b1 = self.root.winfo_rgb(BG_TOP)
                r2, g2, b2 = self.root.winfo_rgb(BG_BOTTOM)
                steps = max(1, h // band)
                r_ratio = float(r2 - r1) / steps
                g_ratio = float(g2 - g1) / steps
                b_ratio = float(b2 - b1) / steps

                for s in range(steps + 1):
                    nr = int(r1 + (r_ratio * s))
                    ng = int(g1 + (g_ratio * s))
                    nb = int(b1 + (b_ratio * s))
                    color = f"#{nr//256:02x}{ng//256:02x}{nb//256:02x}"
                    y1 = s * band
                    y2 = min(h, y1 + band)
                    self.bg_canvas.create_rectangle(0, y1, w, y2, tags=("grad",), outline=color, fill=color)

                self.bg_canvas.tag_lower("grad")
                target_w = 600 if sys.platform == "win32" else 520
                self._base_x = max(0, (w - target_w) // 2)
                self._base_y = 0
                self.bg_canvas.coords(self.container_id, self._base_x, self._base_y)
            except Exception as e:
                log_exc("[otaku_gui] gradient error:", e)

        def draw_gradient(event=None):
            try:
                if self._closing:
                    return
                if self._grad_after_id is not None:
                    self.root.after_cancel(self._grad_after_id)
            except Exception:
                pass
            try:
                if not self._closing and self.root.winfo_exists():
                    self._grad_after_id = self.root.after(60, _paint_gradient)
            except Exception:
                pass

        self.bg_canvas.bind("<Configure>", draw_gradient)
        self.root.after(120, draw_gradient)

        # Top status bar (fake UI)
        status = tk.Frame(self.container, bg=BG_TOP)
        status.pack(pady=((6, 2) if sys.platform == "win32" else (10, 2)), padx=18, fill="x")

        self.left_status = tk.Label(
            status,
            text=ui_text("📶 ▂▄▆█  |  --:--"),
            font=FONT_MONO_BOLD_10,
            bg=BG_TOP,
            fg=HINT_FG,
        )
        self.left_status.pack(side="left")

        right_status = tk.Label(
            status,
            text=ui_text("🔋 ███░  78%  ♡"),
            font=FONT_MONO_BOLD_10,
            bg=BG_TOP,
            fg=TITLE_FG,
        )
        right_status.pack(side="right")

        # Start real-time clock updates (every 30s)
        self._update_clock()

        # Title (retro)
        title = tk.Label(
            self.container,
            text="OTAKU HANGMAN",
            font=FONT_MONO_BOLD_20,
            bg=BG_TOP,
            fg=TITLE_FG,
        )
        title.pack(pady=((12, 6) if sys.platform == "win32" else (16, 10)))

        badge = tk.Label(
            self.container,
            text=ui_text("Pocket Console ✦ v1   (ฅ^•ﻌ•^ฅ) ♡"),
            font=FONT_MONO_BOLD_10,
            bg=BG_TOP,
            fg=HINT_FG,
        )
        badge.pack(pady=((0, 6) if sys.platform == "win32" else (0, 8)))

        # Card panel (retro device screen)
        card_shadow = tk.Frame(self.container, bg="#000000")
        card_shadow.pack(pady=10)
        card_panel = tk.Frame(card_shadow, bg=PANEL_BORDER, padx=10, pady=12)
        card_panel.pack(padx=6, pady=6)

        # Screen canvas draws bezel + pixel corners + scanlines
        self.screen_canvas = tk.Canvas(
            card_panel,
            bg="#09050a",
            highlightthickness=0,
            width=(540 if sys.platform == "win32" else 480),
            height=(560 if sys.platform == "win32" else 380),
        )
        self.screen_canvas.pack()
        self.screen_canvas.bind("<Configure>", self._redraw_screen)

        # HUD strip (HP / MODE / SIGIL) inside the screen
        self.hud = tk.Frame(self.screen_canvas, bg=SCREEN_BG)

        self.hud_hp = tk.Label(
            self.hud,
            text="HP --/--",
            font=FONT_MONO_BOLD_10,
            bg=SCREEN_BG,
            fg=ACCENT_GOLD,
        )
        self.hud_hp.pack(side="left")

        self.hud_mode = tk.Label(
            self.hud,
            text="MODE BOOT",
            font=FONT_MONO_BOLD_10,
            bg=SCREEN_BG,
            fg=HINT_FG,
        )
        self.hud_mode.pack(side="left", padx=(12, 0))

        self.hud_sigil = tk.Label(
            self.hud,
            text="SIGIL ◇ ◇ ◇ ◇",
            font=FONT_MONO_BOLD_10,
            bg=SCREEN_BG,
            fg=TITLE_FG,
        )
        self.hud_sigil.pack(side="right")

        self.hud_win_id = self.screen_canvas.create_window(18, 14, anchor="nw", window=self.hud, tags=("hud",))

        # Embedded console (text) inside the screen (no scrollbars)
        self.console_frame = tk.Frame(self.screen_canvas, bg=SCREEN_BG)

        self.console = tk.Text(
            self.console_frame,
            wrap="none",
            font=FONT_MONO,
            bg=SCREEN_BG,
            fg="#ffe6f2",          # soft pink text
            insertbackground="#ffb3d9",  # pink caret
            relief="flat",
            padx=(5 if sys.platform == "win32" else 10),
            pady=(5 if sys.platform == "win32" else 10),
            highlightthickness=0,
            borderwidth=0,
        )

        # layout inside frame (no scrollbars; terminal-style)
        self.console.grid(row=0, column=0, sticky="nsew")
        self.console_frame.grid_rowconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)

        # keyword highlight tags
        self.console.tag_configure("tag_win", foreground=ACCENT_MINT)
        self.console.tag_configure("tag_lose", foreground=ACCENT_RED)
        self.console.tag_configure("tag_unlock", foreground=ACCENT_GOLD)
        self.console.tag_configure("tag_warn", foreground=ACCENT_ROSEGOLD)

        self.console.configure(state="disabled")
        # Disable user scrolling/dragging: behave like a terminal that always stays at the bottom
        for seq in ("<MouseWheel>", "<Shift-MouseWheel>", "<Button-4>", "<Button-5>"):
            self.console.bind(seq, lambda e: "break")
        # Disable middle-button paste/scroll on some systems
        for seq in ("<Button-2>", "<B2-Motion>"):
            self.console.bind(seq, lambda e: "break")
        self.console_win_id = self.screen_canvas.create_window(
            18, 44,
            anchor="nw",
            window=self.console_frame,
            width=(500 if sys.platform == "win32" else 444),
            height=(520 if sys.platform == "win32" else 320),
            tags=("console",)
        )

        # initial draw (bezel + scanlines)
        self.root.after(40, self._redraw_screen)

        # Controls
        controls = tk.Frame(self.container, bg=BG_TOP)
        controls.pack(pady=(10, 6), padx=18, fill="x")

        self.start_btn = tk.Button(
            controls,
            text="▶ START",
            command=self.start_game,
            font=FONT_MONO_BOLD_12,
            bg="#5a5a5a",
            fg=ACCENT_MINT,
            activebackground="#707070",
            activeforeground=ACCENT_MINT,
            relief="flat",
            padx=14,
            pady=8,
        )
        self.start_btn.pack(side="left")

        self.stop_btn = tk.Button(
            controls,
            text="■ STOP",
            command=self.stop_game,
            font=FONT_MONO_BOLD_12,
            bg="#5a5a5a",
            fg=ACCENT_ROSEGOLD,
            activebackground="#707070",
            activeforeground=ACCENT_ROSEGOLD,
            relief="flat",
            padx=14,
            pady=8,
        )
        self.stop_btn.pack(side="left", padx=(10, 0))

        # Input row
        input_row = tk.Frame(self.container, bg=BG_TOP)
        input_row.pack(pady=(8, 2), padx=18, fill="x")

        self.input_entry = tk.Entry(
            input_row,
            font=(FONT_MONO[0], 13),
            bg="#1a1a1a",
            fg="#ffffff",
            insertbackground="#ffb3d9",
            relief="solid",
            bd=1,
        )
        self.input_entry.configure(highlightthickness=1, highlightbackground="#5a5a5a", highlightcolor="#ffb3d9")
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=(6 if sys.platform == "win32" else 8))
        self.input_entry.configure(state="disabled")
        self.input_entry.bind("<Return>", self.send_input)

        self.send_btn = tk.Button(
            input_row,
            text="SEND",
            command=self.send_input,
            font=FONT_MONO_BOLD_12,
            bg="#d6d6d6",
            fg="#ffb3d9",
            activebackground="#e6e6e6",
            activeforeground="#ffb3d9",
            relief="flat",
            padx=14,
            pady=8,
        )
        self.send_btn.pack(side="left", padx=(10, 0))
        self.send_btn.configure(state="disabled")

        hint = tk.Label(
            self.container,
            text=ui_text("TIP: press ▶ START, then type 1/3/4 + letters ✧ (ง •̀_•́)ง  ♡"),
            font=("Helvetica", (9 if sys.platform == "win32" else 10)),
            bg=BG_TOP,
            fg=HINT_FG,
        )
        hint.pack(pady=((4, 6) if sys.platform == "win32" else (6, 8)))

    
    def _set_hud(self, hp=None, mode=None, sigil=None):
        if hp is not None:
            self._hud_hp = hp
        if mode is not None:
            self._hud_mode = mode
        if sigil is not None:
            self._hud_sigil = sigil
        try:
            self.hud_hp.configure(text=f"HP {self._hud_hp}")
            self.hud_mode.configure(text=f"MODE {self._hud_mode}")
            self.hud_sigil.configure(text=f"SIGIL {self._hud_sigil}")
        except Exception:
            pass

    def _parse_line_for_hud(self, line: str):
        """Best-effort parse of terminal output lines to update HUD."""
        try:
            s = line.strip()
            if not s:
                return

            # HP pattern like: (7/8)
            m = re.search(r"\((\d+)\/(\d+)\)", s)
            if m:
                cur = int(m.group(1))
                mx = int(m.group(2))
                # If HP decreased since last time, treat it as a wrong guess and trigger hit FX
                try:
                    if (self._last_hp_cur is not None) and (cur < self._last_hp_cur):
                        # Skip hit FX during win/dazy/challenge-clear sequences
                        try:
                            if time.time() >= getattr(self, "_suppress_hit_until", 0.0):
                                if (not self._closing) and self.root.winfo_exists():
                                    self.root.after(0, self._trigger_hit_fx)
                        except Exception:
                            pass
                except Exception:
                    pass

                self._last_hp_cur = cur
                self._last_hp_max = mx
                self._set_hud(hp=f"{cur}/{mx}")

            # Mode patterns
            if "challenge" in s.lower():
                self._set_hud(mode="CHALLENGE")
            if "level" in s.lower():
                # try to keep exact level token
                m2 = re.search(r"level\s*([0-9]+)", s.lower())
                if m2:
                    self._set_hud(mode=f"LEVEL {m2.group(1)}")

            # Sigil bar lines contain 4 symbols ◆/◇
            if ("◆" in s) or ("◇" in s):
                symbols = [ch for ch in s if ch in ("◆", "◇")]
                if len(symbols) >= 4:
                    bar = " ".join(symbols[:4])
                    self._set_hud(sigil=bar)
        except Exception:
            pass

    def _scan_and_tag_new_text(self):
        """Scan newly appended text and apply highlight tags to full lines."""
        try:
            txt = self.console
            end = txt.index("end-1c")
            start = self._tag_scan_index
            if txt.compare(start, ">=", end):
                return

            for tag, keys in HIGHLIGHT_RULES:
                for kw in keys:
                    pos = start
                    while True:
                        found = txt.search(kw, pos, stopindex=end, nocase=True)
                        if not found:
                            break
                        line_start = txt.index(f"{found} linestart")
                        line_end = txt.index(f"{found} lineend")
                        txt.tag_add(tag, line_start, line_end)
                        pos = txt.index(f"{found}+1c")

            self._tag_scan_index = end
        except Exception:
            # never crash UI due to highlight
            try:
                self._tag_scan_index = self.console.index("end-1c")
            except Exception:
                pass

    # ---------------------
    # Screen styling (pixel border + scanlines)
    # ---------------------
    def _redraw_screen(self, event=None):
        """Redraw the faux handheld screen (border + pixel corners + scanlines)."""
        try:
            c = self.screen_canvas
            w = c.winfo_width()
            h = c.winfo_height()
            if w <= 4 or h <= 4:
                return

            c.delete("screen")

            # Outer bezel with subtle highlight edge
            c.create_rectangle(0, 0, w, h, outline=PANEL_BORDER, width=2, fill="#09050a", tags=("screen",))

            # Subtle plastic highlight edge
            c.create_line(2, 2, w - 2, 2, fill="#6a4a78", tags=("screen",))
            c.create_line(2, 2, 2, h - 2, fill="#6a4a78", tags=("screen",))
            c.create_line(2, h - 2, w - 2, h - 2, fill="#1a0f1f", tags=("screen",))
            c.create_line(w - 2, 2, w - 2, h - 2, fill="#1a0f1f", tags=("screen",))

            # Inner viewport
            pad = 10
            ix1, iy1, ix2, iy2 = pad, pad, w - pad, h - pad
            c.create_rectangle(ix1, iy1, ix2, iy2, outline=self._screen_outline, width=self._screen_outline_width, fill="#09050a", tags=("screen",))

            # Resize embedded HUD/console windows to fit the inner viewport
            inner_w = max(100, int(w - 2 * pad - 8))
            inner_h = max(100, int(h - 2 * pad - 8))

            # Keep HUD near the top inside the inner viewport
            try:
                if hasattr(self, "hud_win_id"):
                    c.coords(self.hud_win_id, pad + 8, pad + 4)
            except Exception:
                pass

            # Console below HUD, fill remaining space
            hud_h = 26
            console_x = pad + 8
            console_y = pad + 4 + hud_h
            console_w = inner_w
            console_h = max(80, inner_h - hud_h - 6)
            try:
                if hasattr(self, "console_win_id"):
                    c.coords(self.console_win_id, console_x, console_y)
                    c.itemconfigure(self.console_win_id, width=console_w, height=console_h)
            except Exception:
                pass

            # Pixel-corner cutouts (tiny squares) to fake rounded corners
            cut = 6
            corner_color = BG_TOP  # match shell
            # top-left
            c.create_rectangle(ix1, iy1, ix1 + cut, iy1 + cut, outline=corner_color, fill=corner_color, tags=("screen",))
            # top-right
            c.create_rectangle(ix2 - cut, iy1, ix2, iy1 + cut, outline=corner_color, fill=corner_color, tags=("screen",))
            # bottom-left
            c.create_rectangle(ix1, iy2 - cut, ix1 + cut, iy2, outline=corner_color, fill=corner_color, tags=("screen",))
            # bottom-right
            c.create_rectangle(ix2 - cut, iy2 - cut, ix2, iy2, outline=corner_color, fill=corner_color, tags=("screen",))

            # Scanlines (subtle, behind the text)
            line_color = "#0b070c"  # slightly darker than screen bg
            step = 7
            for y in range(int(iy1) + 2, int(iy2) - 2, step):
                c.create_line(ix1 + 2, y, ix2 - 2, y, fill=line_color, tags=("screen",))

            # Handheld decorations on bezel (safe, simple)
            screw_fill = "#0f0a10"
            screw_outline = "#6a4a78"
            r = 3
            for sx, sy in [(8, 8), (w - 8, 8), (8, h - 8), (w - 8, h - 8)]:
                c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=screw_fill, outline=screw_outline, tags=("screen",))

            # Speaker holes (right bezel)
            hole_fill = "#060406"
            hole_outline = "#2a1b31"
            hx = w - 14
            for yy in range(84, min(h - 36, 210), 14):
                c.create_oval(hx - 2, yy - 2, hx + 2, yy + 2, fill=hole_fill, outline=hole_outline, tags=("screen",))

            # Small label plate
            c.create_text(18, h - 18, anchor="w", text="BIFROST MICRO ✦ OTAKU", fill="#6a4a78", font=(FONT_MONO[0], 9, "bold"), tags=("screen",))

            # Keep the drawing behind the embedded Text widget
            c.tag_lower("screen")
        except Exception as e:
            log_exc("[otaku_gui] redraw_screen error:", e)

    # ---------------------
    # Hit feedback (flash + shake)
    # ---------------------
    def _flash_screen(self):
        """Briefly flash the inner screen border to simulate a hit."""
        try:
            if self._flash_job is not None:
                try:
                    self.root.after_cancel(self._flash_job)
                except Exception:
                    pass
                self._flash_job = None

            self._screen_outline = self._screen_outline_flash
            self._redraw_screen()

            def _reset():
                self._screen_outline = self._screen_outline_normal
                self._screen_outline_width = 1
                self._redraw_screen()
                self._flash_job = None

            self._flash_job = self.root.after(120, _reset)
        except Exception:
            # never crash the UI due to FX
            self._screen_outline = self._screen_outline_normal

    def _sparkle_screen(self):
        """Brief gold sparkle flash (positive feedback)."""
        try:
            if self._flash_job is not None:
                try:
                    self.root.after_cancel(self._flash_job)
                except Exception:
                    pass
                self._flash_job = None

            self._screen_outline = self._screen_outline_sparkle
            self._redraw_screen()

            def _reset():
                self._screen_outline = self._screen_outline_normal
                self._screen_outline_width = 1
                self._redraw_screen()
                self._flash_job = None

            # slightly longer than hit flash for a "shiny" feel
            self._flash_job = self.root.after(170, _reset)
        except Exception:
            self._screen_outline = self._screen_outline_normal

    def _shake_window(self):
        """Tiny shake (no loops). Always retriggers by canceling any in-flight shake."""
        # If already shaking, cancel scheduled steps and restart so every hit feels responsive
        if self._shaking:
            for jid in list(self._shake_jobs):
                try:
                    self.root.after_cancel(jid)
                except Exception:
                    pass
            self._shake_jobs.clear()
            try:
                self.bg_canvas.coords(self.container_id, self._base_x, self._base_y)
            except Exception:
                pass

        self._shaking = True

        seq = [2, -2, 1, -1, 0]
        step_ms = 30

        def _apply(dx):
            try:
                self.bg_canvas.coords(self.container_id, self._base_x + dx, self._base_y)
            except Exception:
                pass

        def _end():
            try:
                self.bg_canvas.coords(self.container_id, self._base_x, self._base_y)
            except Exception:
                pass
            self._shaking = False

        for i, dx in enumerate(seq):
            jid = self.root.after(step_ms * i, lambda d=dx: _apply(d))
            self._shake_jobs.append(jid)
        jid_end = self.root.after(step_ms * len(seq) + 10, _end)
        self._shake_jobs.append(jid_end)

    def _trigger_hit_fx(self):
        """Run both flash + shake safely, with a small sound. Avoid overlap with sparkle."""
        try:
            now = time.time()
            # Suppress hit feedback during win/dazy/challenge-clear sequences
            if now < getattr(self, "_suppress_hit_until", 0.0):
                return
            # If sparkle fired very recently, don't stack hit FX/sound on top
            if (now - getattr(self, "_last_sparkle_ts", 0.0)) < 0.35:
                return
            # debounce: if another hit fired very recently, skip
            if (now - getattr(self, "_last_hit_ts", 0.0)) < 0.08:
                return
            self._last_hit_ts = now
            self._flash_screen()
            self._shake_window()
            # small sound
            self._beep_hit()
        except Exception:
            pass

    def _win_screen(self):
        """Mint green flash (correct guess feedback): thicker + longer for clear visibility."""
        try:
            if self._flash_job is not None:
                try:
                    self.root.after_cancel(self._flash_job)
                except Exception:
                    pass
                self._flash_job = None

            self._screen_outline = self._screen_outline_win
            self._screen_outline_width = 3
            self._redraw_screen()

            def _reset():
                self._screen_outline = self._screen_outline_normal
                self._screen_outline_width = 1
                self._redraw_screen()
                self._flash_job = None

            # slightly longer than hit; strong but not DAZY-long
            self._flash_job = self.root.after(220, _reset)
        except Exception:
            self._screen_outline = self._screen_outline_normal
            self._screen_outline_width = 1

    def _trigger_win_fx(self):
        """Correct guess feedback: green flash + win chime. Avoid overlap with DAZY."""
        try:
            now = time.time()
            # If DAZY sparkle fired very recently, don't stack win FX on top
            if (now - getattr(self, "_last_sparkle_ts", 0.0)) < 0.35:
                return
            # debounce
            if (now - getattr(self, "_last_win_ts", 0.0)) < 0.08:
                return
            self._last_win_ts = now
            self._win_screen()
            # Win sound: single chime (less loud)
            self._beep_win()
        except Exception:
            pass

    def _trigger_sparkle_fx(self):
        """Positive sigil feedback: sparkle flash. Prevent hit overlap."""
        try:
            self._last_sparkle_ts = time.time()
            self._sparkle_screen()
            # tiny chime: delayed so it doesn't feel like the hit sound
            try:
                self.root.after(40, self._beep_sparkle)
            except Exception:
                pass
        except Exception:
            pass

    # ---------------------
    # Terminal helpers
    # ---------------------
    def _wrap_to_console_width(self, s: str) -> str:
        """Hard-wrap long lines to the current console width on Windows.

        IMPORTANT: Preserve menu/frame borders like `║ ... ║` by wrapping the *inside* and
        re-applying borders on each wrapped line. This avoids the "missing vertical border"
        look and restores the original menu layout.
        """
        try:
            if not s:
                return s
            if sys.platform != "win32":
                return s
            if not hasattr(self, "console") or self.console is None:
                return s

            # Ensure geometry is up to date
            try:
                self.root.update_idletasks()
            except Exception:
                pass

            try:
                wpx = int(self.console.winfo_width())
            except Exception:
                wpx = 0

            # Compute max columns from pixel width using current font
            if wpx <= 0:
                max_cols = 70
            else:
                try:
                    f = tkfont.Font(font=self.console.cget("font"))
                    ch = max(6, int(f.measure("M")))
                    max_cols = max(48, int((wpx - 18) / ch))
                except Exception:
                    max_cols = 70

            import unicodedata

            def dwidth(text: str) -> int:
                # Approximate display width: treat East Asian Wide/Fullwidth as 2 columns
                w = 0
                for ch in text:
                    if ch == "\t":
                        w += 4
                        continue
                    if unicodedata.east_asian_width(ch) in ("W", "F"):
                        w += 2
                    else:
                        w += 1
                return w

            def take_by_width(text: str, width: int) -> tuple[str, str]:
                # Return (head, tail) where head has display width <= width
                if width <= 0:
                    return "", text
                w = 0
                i = 0
                while i < len(text):
                    ch = text[i]
                    cw = 4 if ch == "\t" else (2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1)
                    if w + cw > width:
                        break
                    w += cw
                    i += 1
                return text[:i], text[i:]

            def pad_to_width(text: str, width: int) -> str:
                cur = dwidth(text)
                if cur >= width:
                    return text
                return text + (" " * (width - cur))

            out_lines: list[str] = []
            for line in s.split("\n"):
                if not line:
                    out_lines.append("")
                    continue

                # If it already fits, keep it
                if dwidth(line) <= max_cols:
                    out_lines.append(line)
                    continue

                # Detect framed lines like: ║ .... ║  or | .... |
                left = line[:1]
                right = line[-1:]
                is_frame = (left in ("║", "|", "┃") and right in ("║", "|", "┃"))

                if is_frame and max_cols >= 4:
                    inner = line[1:-1]
                    inner_w = max_cols - 2

                    # Do NOT wrap framed lines into multiple lines (that breaks box layouts).
                    # Instead, clip the inner content to the visible width and pad.
                    head, _tail = take_by_width(inner, inner_w)
                    head = pad_to_width(head, inner_w)
                    out_lines.append(left + head + right)
                    continue

                # Non-frame line: wrap by display width (preserve leading indentation)
                m = re.match(r"^(\s+)", line)
                prefix = m.group(1) if m else ""
                prefix_w = dwidth(prefix)
                avail = max(10, max_cols - prefix_w)

                rest = line
                first = True
                while dwidth(rest) > max_cols:
                    if first:
                        head, rest2 = take_by_width(rest, max_cols)
                        out_lines.append(head)
                        rest = rest2
                        first = False
                    else:
                        # Wrap continuation with prefix
                        # Strip prefix from rest if it already has it
                        if prefix and rest.startswith(prefix):
                            rest = rest[len(prefix):]
                        head, rest2 = take_by_width(rest, avail)
                        out_lines.append(prefix + head)
                        rest = rest2

                    if rest == "":
                        break

                if rest:
                    if first:
                        out_lines.append(rest)
                    else:
                        if prefix and not rest.startswith(prefix):
                            out_lines.append(prefix + rest)
                        else:
                            out_lines.append(rest)

            return "\n".join(out_lines)
        except Exception:
            return s
    def _clear_console(self):
        """Clear the embedded console safely and reset tagging state."""
        try:
            self.console.configure(state="normal")
            self.console.delete("1.0", "end")
            self.console.configure(state="disabled")
        except Exception:
            pass
        # reset parse/tag scan
        self._parse_buf = ""
        self._tag_scan_index = "1.0"
    def _append_output(self, text: str):
        try:
            # If the game requests a full-screen redraw (ANSI clear), emulate it by clearing
            # the Text widget BEFORE inserting the new frame. Otherwise frames accumulate and
            # the top of the current screen scrolls out of view.
            if text:
                has_clear = ("\x1b[2J" in text) or ("\x1b[H" in text) or ("\x1b[3J" in text)
                if has_clear:
                    try:
                        self._clear_console()
                        # Also reset parse/tag scan so HUD/highlights remain consistent
                        self._parse_buf = ""
                        self._tag_scan_index = "1.0"
                    except Exception:
                        pass
                text = text.replace("\x1b[2J", "").replace("\x1b[H", "").replace("\x1b[3J", "")
            # Strip ANSI escape sequences produced by terminal clear-screen commands
            if text:
                text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
            # Normalize carriage returns (some terminal output uses \r for in-place updates)
            if text:
                text = text.replace("\r\n", "\n").replace("\r", "\n")
            # Feedback cues (precedence: DAZY sparkle > WIN green > HIT pink)
            if text:
                t = text.lower()
                hit_cue = ("-1 hp" in t) or ("bonk" in t) or ("crit hit" in t) or ("wrong" in t) or ("life -1" in t)
                sparkle_cue = ("sigil resonance" in t) or ("something secret is forming" in t) or ("unlocked the challenge mode" in t) or ("congratulations dazy" in t)
                # Win cues: correct guess / progress / clear messages (distinct from DAZY)
                win_cue = ("correct" in t) or ("nice" in t) or ("good job" in t) or ("well done" in t) or ("yatta" in t) or ("sugoi" in t) or ("kawaii" in t) or ("round cleared" in t) or ("you win" in t) or ("perfect guess" in t) or ("challenge cleared" in t)

                if (not self._closing) and self.root.winfo_exists():
                    if sparkle_cue:
                        # prevent hit flashes caused by recap HP lines
                        self._suppress_hit_until = time.time() + 0.9
                        self.root.after(0, self._trigger_sparkle_fx)
                    elif win_cue:
                        # prevent hit flashes caused by recap HP lines
                        self._suppress_hit_until = time.time() + 0.9
                        self.root.after(0, self._trigger_win_fx)
                    elif hit_cue:
                        # every wrong should trigger
                        self.root.after(0, self._trigger_hit_fx)

            # HUD parsing: accumulate into line buffer and parse completed lines
            if text:
                self._parse_buf += text
                while "\n" in self._parse_buf:
                    line, self._parse_buf = self._parse_buf.split("\n", 1)
                    self._parse_line_for_hud(line)

            self.console.configure(state="normal")
            if text:
                text = console_text(text)
                text = self._wrap_to_console_width(text)
            self.console.insert("end", text)
            self.console.see("end")
            try:
                self.console.yview_moveto(1.0)
                self.console.xview_moveto(0.0)
            except Exception:
                pass
            self.console.configure(state="disabled")
            if not self._safe_mode:
                self._scan_and_tag_new_text()
        except Exception as e:
            log_exc("[otaku_gui] append_output error:", e)

    def _drain_queue(self):
        """Drain queued stdout and append in a single Text insert.

        This avoids thousands of tiny Tk calls which can crash Tk on macOS.
        """
        try:
            parts = []
            # Read available bytes from child stdout on the Tk main thread.
            # POSIX: we make the pipe non-blocking (fcntl) and can safely os.read here.
            # Windows: os.read on a pipe is blocking; use the reader thread instead.
            try:
                if self.proc and self.proc.stdout and (sys.platform != "win32") and HAS_FCNTL:
                    fd = self.proc.stdout.fileno()
                    while True:
                        try:
                            b = os.read(fd, 4096)
                        except BlockingIOError:
                            break
                        except OSError:
                            break
                        if not b:
                            break
                        try:
                            parts.append(self._stdout_decoder.decode(b))
                        except Exception:
                            parts.append(b.decode("utf-8", errors="replace"))
            except Exception:
                pass
            # hard cap per tick to keep UI responsive
            for _ in range(200):
                try:
                    parts.append(self.out_queue.get_nowait())
                except queue.Empty:
                    break
            if parts:
                self._append_output("".join(parts))
        except Exception as e:
            log_exc("[otaku_gui] drain_queue error:", e)
        finally:
            try:
                if self._drain_after_id is not None:
                    try:
                        self.root.after_cancel(self._drain_after_id)
                    except Exception:
                        pass
                    self._drain_after_id = None
                running_subproc = bool(self.proc and (self.proc.poll() is None))
                running_inproc = bool((self._game_thread is not None) and (self._game_thread.is_alive()))
                if (not self._closing) and (running_subproc or running_inproc) and self.root.winfo_exists():
                    self._drain_after_id = self.root.after(60, self._drain_queue)
            except Exception:
                pass

    def _reader_loop(self):
        """Windows-safe stdout reader (blocking). Puts decoded text into out_queue."""
        p = self.proc
        try:
            if not p or not p.stdout:
                return
            while True:
                try:
                    b = p.stdout.read(4096)
                except Exception:
                    break
                if not b:
                    break
                try:
                    s = self._stdout_decoder.decode(b)
                except Exception:
                    s = b.decode("utf-8", errors="replace")
                try:
                    self.out_queue.put(s)
                except Exception:
                    pass
        except Exception:
            pass

    # ---------------------
    # In-process game runner (for frozen/Windows builds)
    # ---------------------
    class _QueueStdout:
        def __init__(self, put_fn):
            self._put = put_fn
        def write(self, s):
            if not s:
                return 0
            try:
                self._put(s)
            except Exception:
                pass
            return len(s)
        def flush(self):
            return

    class _StdinProxy:
        def __init__(self, read_fn):
            self._read_fn = read_fn

        def readline(self, *args, **kwargs):
            # Match sys.stdin.readline() contract: return a string ending with \n
            s = self._read_fn("")
            if s is None:
                return ""
            if not isinstance(s, str):
                try:
                    s = str(s)
                except Exception:
                    return "\n"
            if s.endswith("\n"):
                return s
            return s + "\n"

    def _input_provider(self, prompt: str = "") -> str:
        # Send prompt to UI if present
        try:
            if prompt:
                self.out_queue.put(prompt)
        except Exception:
            pass
        # Block until user provides a line, but allow stop to interrupt
        try:
            if getattr(self, "_stop_requested", False):
                raise EOFError
        except Exception:
            pass
        while True:
            try:
                if getattr(self, "_stop_requested", False):
                    raise EOFError
                s = self.in_queue.get(timeout=0.2)
                return s
            except queue.Empty:
                continue
            except EOFError:
                raise
            except Exception:
                return ""

    def _run_game_inproc(self, script_path: str):
        """Run the hangman script inside this process (Windows/frozen-safe)."""
        # Patch input/print to route through queues
        try:
            self._orig_input = getattr(builtins, "input", None)
            builtins.input = self._input_provider
        except Exception:
            pass

        # Some parts of the game use sys.stdin.readline() (e.g., secret password). Provide a compatible stdin.
        try:
            self._orig_stdin = getattr(sys, "stdin", None)
            self._stdin_proxy = self._StdinProxy(self._input_provider)
            sys.stdin = self._stdin_proxy
        except Exception:
            pass

        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        try:
            sys.stdout = self._QueueStdout(lambda s: self.out_queue.put(s))
            sys.stderr = sys.stdout
        except Exception:
            pass

        try:
            runpy.run_path(script_path, run_name="__main__")
        except (SystemExit, EOFError):
            pass
        except Exception as e:
            try:
                self.out_queue.put("\n[GUI] Game crashed: " + repr(e) + "\n")
                self.out_queue.put("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            except Exception:
                pass
        finally:
            try:
                if self._orig_input is not None:
                    builtins.input = self._orig_input
            except Exception:
                pass
            try:
                if self._orig_stdin is not None:
                    sys.stdin = self._orig_stdin
            except Exception:
                pass
            try:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
            except Exception:
                pass
            # ensure UI stops polling if process is gone
            try:
                self.proc = None
            except Exception:
                pass

    def _launch_game_process(self):
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "otaku_hang_man.py")
        if not os.path.exists(script_path):
            self._append_output("[GUI] ERROR: otaku_hang_man.py not found next to otaku_gui.py\n")
            return

        # In PyInstaller onefile on Windows, sys.executable is the EXE bootloader (not python).
        # Run the game in-process to avoid child-process launch failures.
        is_frozen = bool(getattr(sys, "frozen", False))
        if sys.platform == "win32" or is_frozen:
            try:
                log("[otaku_gui] launching in-proc:", script_path)
                self._game_thread = threading.Thread(target=self._run_game_inproc, args=(script_path,), daemon=True)
                self._game_thread.start()
            except Exception as e:
                self._append_output(f"[GUI] Failed to start game: {e}\n")
                return
        else:
            try:
                log("[otaku_gui] launching child:", script_path)
                env = os.environ.copy()
                env.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
                self.proc = subprocess.Popen(
                    [sys.executable, script_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=False,
                    cwd=os.path.dirname(script_path),
                    env=env,
                    close_fds=True,
                    start_new_session=True,
                )
                try:
                    log("[otaku_gui] child pid:", self.proc.pid)
                except Exception:
                    pass
                # POSIX: Make stdout non-blocking so we can os.read() safely from the Tk main thread.
                # Windows: fcntl is unavailable; use a reader thread instead.
                try:
                    if self.proc and self.proc.stdout and (sys.platform != "win32") and HAS_FCNTL:
                        fd = self.proc.stdout.fileno()
                        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                except Exception:
                    pass

                # Windows: start a blocking reader thread to avoid freezing the Tk thread
                try:
                    if sys.platform == "win32":
                        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
                        self._reader_thread.start()
                except Exception:
                    pass
                # reset decoder for a fresh run
                try:
                    self._stdout_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
                except Exception:
                    pass
            except Exception as e:
                self._append_output(f"[GUI] Failed to launch: {e}\n")
                self.proc = None
                return

        # enable input
        self.input_entry.configure(state="normal")
        self.send_btn.configure(state="normal")
        self.input_entry.focus_set()

        try:
            if (not self._closing) and self.root.winfo_exists():
                self._drain_after_id = self.root.after(50, self._drain_queue)
        except Exception:
            pass

    def start_game(self):
        log("[otaku_gui] START clicked")

        # cancel any previous boot/loading callbacks (kept for safety)
        self._cancel_boot_jobs()

        # already running (subprocess or in-proc)
        try:
            if self.proc and (self.proc.poll() is None):
                return
        except Exception:
            pass
        try:
            if (self._game_thread is not None) and (self._game_thread.is_alive()):
                return
        except Exception:
            pass

        # if the window is closing, do nothing
        try:
            if self._closing or (not self.root.winfo_exists()):
                return
        except Exception:
            return

        # clear console
        self._clear_console()
        try:
            self.console.xview_moveto(0)
        except Exception:
            pass

        # reset parse/tag scan
        self._parse_buf = ""
        self._tag_scan_index = "1.0"

        # Show an immediate start banner (no scheduled boot steps)
        self._set_hud(hp="--/--", mode="MENU", sigil="◇ ◇ ◇ ◇")
        self._append_output(ui_text(
            "╭──────────────────────────────╮\n"
            "│  OTAKU HANGMAN — POCKET v1   │\n"
            "│  starting... (ฅ^•ﻌ•^ฅ) ♡     │\n"
            "╰──────────────────────────────╯\n\n"
        ))

        # disable input until the process is launched
        try:
            self.input_entry.configure(state="disabled")
            self.send_btn.configure(state="disabled")
        except Exception:
            pass
        # Reset stop flag before launching game
        self._stop_requested = False
        # Launch immediately (no after-based loading)
        try:
            self._launch_game_process()
        except Exception as e:
            log_exc("[otaku_gui] immediate launch error:", e)
            try:
                self._append_output(f"\n[GUI] Launch failed: {e}\n")
            except Exception:
                pass

    def send_input(self, event=None):
        # In-proc mode (Windows/frozen): route input to queue
        if (self._game_thread is not None) and (self._game_thread.is_alive()) and (self.proc is None):
            msg = self.input_entry.get()
            if msg is None:
                return
            if msg.strip() != "":
                self._append_output(f"> {msg}\n")
            try:
                self.in_queue.put(msg)
            except Exception:
                pass
            self.input_entry.delete(0, "end")
            return

        # Subprocess mode
        if not (self.proc and self.proc.stdin and (self.proc.poll() is None)):
            return

        msg = self.input_entry.get()
        if msg is None:
            return

        if msg.strip() != "":
            self._append_output(f"> {msg}\n")

        try:
            payload = (msg + "\n").encode("utf-8", errors="replace")
            self.proc.stdin.write(payload)
            self.proc.stdin.flush()
        except Exception as e:
            self._append_output(f"[GUI] send failed: {e}\n")

        self.input_entry.delete(0, "end")

    def stop_game(self):
        # mark as closing-safe if called from window close
        try:
            # best effort to stop repeating jobs
            self._cancel_boot_jobs()
            if self._grad_after_id is not None:
                try:
                    self.root.after_cancel(self._grad_after_id)
                except Exception:
                    pass
                self._grad_after_id = None
            if self._clock_after_id is not None:
                try:
                    self.root.after_cancel(self._clock_after_id)
                except Exception:
                    pass
                self._clock_after_id = None
            if self._drain_after_id is not None:
                try:
                    self.root.after_cancel(self._drain_after_id)
                except Exception:
                    pass
                self._drain_after_id = None
        except Exception:
            pass

        p = self.proc
        self.proc = None

        # Stop in-proc mode: request stop and unblock input()
        try:
            self._stop_requested = True
        except Exception:
            pass
        try:
            if self._game_thread is not None and self._game_thread.is_alive():
                # Try a clean quit option first (menu option 4)
                try:
                    self.in_queue.put("4")
                except Exception:
                    pass
                # Also unblock any pending input() calls
                try:
                    self.in_queue.put("")
                except Exception:
                    pass
        except Exception:
            pass

        # disable input immediately
        try:
            self.input_entry.configure(state="disabled")
            self.send_btn.configure(state="disabled")
        except Exception:
            pass

        if p and (p.poll() is None):
            try:
                # close stdin first to let the child exit cleanly
                try:
                    if p.stdin:
                        p.stdin.close()
                except Exception:
                    pass

                p.terminate()
                try:
                    p.wait(timeout=1.2)
                except Exception:
                    # last resort
                    try:
                        p.kill()
                    except Exception:
                        pass
            except Exception:
                pass

        # close remaining pipes
        try:
            if p:
                try:
                    if p.stdout:
                        p.stdout.close()
                except Exception:
                    pass
        except Exception:
            pass

        # reset decoder for next run
        try:
            self._stdout_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        except Exception:
            pass

        # only append to console if UI is still alive
        try:
            if (not self._closing) and self.root.winfo_exists():
                self._append_output("\n[GUI] Game stopped.\n")
        except Exception:
            pass

if __name__ == "__main__":
    try:
        log("[otaku_gui] creating Tk root...")
        root = tk.Tk()
        root.update_idletasks()
        time.sleep(0.2)

        log("[otaku_gui] starting app...")
        app = OtakuGUI(root)

        # Visibility watchdog (macOS sometimes keeps the window behind)
        def _ensure_visible():
            try:
                # If the window isn't viewable yet, force it
                if not root.winfo_viewable():
                    root.deiconify()
                root.lift()
                # brief topmost toggle to bring to front, then disable again
                try:
                    root.attributes("-topmost", True)
                    root.after(180, lambda: root.attributes("-topmost", False))
                except Exception:
                    pass
                root.focus_force()
                log("[otaku_gui] visibility:", "viewable=", root.winfo_viewable(), "mapped=", root.winfo_ismapped(), "state=", root.state())
            except Exception as e:
                log_exc("[otaku_gui] visibility watchdog error:", e)

        try:
            root.after(120, _ensure_visible)
            root.after(600, _ensure_visible)
        except Exception:
            pass

        def _on_close():
            try:
                app._closing = True
            except Exception:
                pass
            try:
                app.stop_game()
            except Exception:
                pass
            try:
                root.quit()
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass

        root.protocol("WM_DELETE_WINDOW", _on_close)

        log("[otaku_gui] entering mainloop...")
        root.mainloop()
    except Exception as e:
        try:
            import traceback
            log_exc("[otaku_gui] fatal:", e)
            log(traceback.format_exc())
        except Exception:
            pass
        raise
    