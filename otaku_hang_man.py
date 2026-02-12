import random
import os
import json
import time

# ============================================================
#  OTAKU HANGMAN - FINAL (Menu fixed)
#
#  ✅ 2) Challenge: locked until sigil unlock (save["dazy_unlocked"] == True)
#  ✅ Secret Note: NOT shown in menu; auto-shown after Challenge clear
#  ✅ Save file: otaku_save.json next to this .py file
# ============================================================

BASE_LIVES = 8
CHALLENGE_BONUS_LIVES = 5
CHALLENGE_LIVES = BASE_LIVES + CHALLENGE_BONUS_LIVES  # 13
WINS_IN_A_ROW_TO_CLEAR = 5

SIGIL_ORDER = ["d", "a", "z", "y"]
SIGIL_SET = set(SIGIL_ORDER)

# always store save next to this script

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "otaku_save.json")

# ======================
#  DEV TOGGLES
# ======================
# (disabled) keep the game deterministic: menu + access depend ONLY on save file


# =========  WORD LIST =========
# Rules:
# - anime titles: hint=None
# - characters: hint="anime title"

WORDS = [
    # =========================
    #  BIG SHONEN / MAINSTREAM
    # =========================
    {"word": "naruto", "hint": None},
    {"word": "onepiece", "hint": None},
    {"word": "bleach", "hint": None},
    {"word": "dragonball", "hint": None},
    {"word": "jujutsukaisen", "hint": None},
    {"word": "demonslayer", "hint": None},
    {"word": "myheroacademia", "hint": None},
    {"word": "attackontitan", "hint": None},
    {"word": "fullmetalalchemist", "hint": None},
    {"word": "hunterxhunter", "hint": None},
    {"word": "haikyuu", "hint": None},
    {"word": "blackclover", "hint": None},
    {"word": "fairytail", "hint": None},
    {"word": "gintama", "hint": None},
    {"word": "tokyorevengers", "hint": None},
    {"word": "chainsawman", "hint": None},
    {"word": "tokyoghoul", "hint": None},
    {"word": "evangelion", "hint": None},
    {"word": "deathnote", "hint": None},
    {"word": "codegeass", "hint": None},
    {"word": "steinsgate", "hint": None},
    {"word": "madeinabyss", "hint": None},
    {"word": "vinlandsaga", "hint": None},
    {"word": "berserk", "hint": None},
    {"word": "firepunch", "hint": None},
    {"word": "spyxfamily", "hint": None},
    {"word": "bluelock", "hint": None},
    {"word": "sololeveling", "hint": None},

    # =========================
    #  MOVIES / COMFY / ROMANCE
    # =========================
    {"word": "yourname", "hint": None},
    {"word": "weatheringwithyou", "hint": None},
    {"word": "spiritedaway", "hint": None},
    {"word": "howlsmovingcastle", "hint": None},
    {"word": "kaguyasama", "hint": None},
    {"word": "horimiya", "hint": None},
    {"word": "clannad", "hint": None},
    {"word": "toradora", "hint": None},
    {"word": "violetevergarden", "hint": None},
    {"word": "frieren", "hint": None},
    {"word": "mushishi", "hint": None},

    # =========================
    #  GAMES / ANIME-ADJACENT
    # =========================
    {"word": "genshinimpact", "hint": None},
    {"word": "honkai", "hint": None},
    {"word": "zenlesszonezero", "hint": None},
    {"word": "persona5", "hint": None},
    {"word": "danganronpa", "hint": None},

    # =========================
    #  JOJO
    # =========================
    {"word": "jojosbizarreadventure", "hint": None},
    {"word": "stardustcrusaders", "hint": "jojo's bizarre adventure"},
    {"word": "diamondisunbreakable", "hint": "jojo's bizarre adventure"},
    {"word": "goldenwind", "hint": "jojo's bizarre adventure"},
    {"word": "stoneocean", "hint": "jojo's bizarre adventure"},
    {"word": "jotaro", "hint": "jojo's bizarre adventure"},
    {"word": "dio", "hint": "jojo's bizarre adventure"},
    {"word": "josuke", "hint": "jojo's bizarre adventure"},
    {"word": "giorno", "hint": "jojo's bizarre adventure"},
    {"word": "jolyne", "hint": "jojo's bizarre adventure"},

    # =========================
    #  KAMISAMA KISS
    # =========================
    {"word": "kamisamakiss", "hint": None},
    {"word": "tomoe", "hint": "kamisama kiss"},
    {"word": "nanami", "hint": "kamisama kiss"},
    {"word": "mizuki", "hint": "kamisama kiss"},

    # =====================================================
    #  CHARACTERS (POPULAR) — ALWAYS WITH HINT ✅
    # =====================================================

    # ---- Chainsaw Man ----
    {"word": "denji", "hint": "chainsaw man"},
    {"word": "reze", "hint": "chainsaw man"},
    {"word": "power", "hint": "chainsaw man"},
    {"word": "makima", "hint": "chainsaw man"},
    {"word": "aki", "hint": "chainsaw man"},
    {"word": "kobeni", "hint": "chainsaw man"},
    {"word": "himeno", "hint": "chainsaw man"},
    {"word": "kishibe", "hint": "chainsaw man"},
    {"word": "pochita", "hint": "chainsaw man"},

    # ---- Attack on Titan ----
    {"word": "eren", "hint": "attack on titan"},
    {"word": "mikasa", "hint": "attack on titan"},
    {"word": "levi", "hint": "attack on titan"},
    {"word": "armin", "hint": "attack on titan"},
    {"word": "hange", "hint": "attack on titan"},
    {"word": "erwin", "hint": "attack on titan"},
    {"word": "jean", "hint": "attack on titan"},
    {"word": "sasha", "hint": "attack on titan"},
    {"word": "reiner", "hint": "attack on titan"},
    {"word": "zeke", "hint": "attack on titan"},
    {"word": "historia", "hint": "attack on titan"},
    {"word": "annie", "hint": "attack on titan"},

    # ---- Naruto ----
    {"word": "kakashi", "hint": "naruto"},
    {"word": "itachi", "hint": "naruto"},
    {"word": "sasuke", "hint": "naruto"},
    {"word": "sakura", "hint": "naruto"},
    {"word": "jiraiya", "hint": "naruto"},
    {"word": "madara", "hint": "naruto"},
    {"word": "obito", "hint": "naruto"},
    {"word": "minato", "hint": "naruto"},
    {"word": "hinata", "hint": "naruto"},
    {"word": "gaara", "hint": "naruto"},
    {"word": "pain", "hint": "naruto"},
    {"word": "tsunade", "hint": "naruto"},

    # ---- One Piece ----
    {"word": "luffy", "hint": "one piece"},
    {"word": "zoro", "hint": "one piece"},
    {"word": "nami", "hint": "one piece"},
    {"word": "sanji", "hint": "one piece"},
    {"word": "robin", "hint": "one piece"},
    {"word": "chopper", "hint": "one piece"},
    {"word": "usopp", "hint": "one piece"},
    {"word": "ace", "hint": "one piece"},
    {"word": "law", "hint": "one piece"},
    {"word": "shanks", "hint": "one piece"},
    {"word": "mihawk", "hint": "one piece"},
    {"word": "boa", "hint": "one piece"},
    {"word": "doflamingo", "hint": "one piece"},

    # ---- Jujutsu Kaisen ----
    {"word": "gojo", "hint": "jujutsu kaisen"},
    {"word": "sukuna", "hint": "jujutsu kaisen"},
    {"word": "yuji", "hint": "jujutsu kaisen"},
    {"word": "megumi", "hint": "jujutsu kaisen"},
    {"word": "nobara", "hint": "jujutsu kaisen"},
    {"word": "toji", "hint": "jujutsu kaisen"},
    {"word": "geto", "hint": "jujutsu kaisen"},
    {"word": "maki", "hint": "jujutsu kaisen"},

    # ---- Demon Slayer ----
    {"word": "tanjiro", "hint": "demon slayer"},
    {"word": "nezuko", "hint": "demon slayer"},
    {"word": "zenitsu", "hint": "demon slayer"},
    {"word": "inosuke", "hint": "demon slayer"},
    {"word": "rengoku", "hint": "demon slayer"},
    {"word": "giyu", "hint": "demon slayer"},
    {"word": "shinobu", "hint": "demon slayer"},

    # ---- Death Note ----
    {"word": "light", "hint": "death note"},
    {"word": "l", "hint": "death note"},
    {"word": "misa", "hint": "death note"},
    {"word": "ryuk", "hint": "death note"},

    # ---- Evangelion ----
    {"word": "shinji", "hint": "evangelion"},
    {"word": "asuka", "hint": "evangelion"},
    {"word": "rei", "hint": "evangelion"},
    {"word": "misato", "hint": "evangelion"},

    # ---- Spy x Family ----
    {"word": "anya", "hint": "spy x family"},
    {"word": "loid", "hint": "spy x family"},
    {"word": "yor", "hint": "spy x family"},

    # ---- Berserk ----
    {"word": "guts", "hint": "berserk"},
    {"word": "griffith", "hint": "berserk"},
    {"word": "casca", "hint": "berserk"},
]

FRAMES_L1 = [
r"""
   ✦ ｡ﾟ⋆ START ⋆｡ﾟ ✦     (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧
      ╭─────╮        ♪
      │     │       /\_/\ 
      │             ( -.- ) zzz
      │              > ^ <
      │
      │
╭─────┴──────────────╮
│  (｡•̀ᴗ-)✧  READY!    │
╰─────────────────────╯
""",
r"""
   ✦ ｡ﾟ⋆ OOPS ⋆｡ﾟ ✦      (｡•́︿•̀｡)
      ╭─────╮        !!
      │     │       /\_/\ 
      │     O      ( o.o )
      │             > ^ <
      │
      │
╭─────┴──────────────╮
│  (°ロ°)!!  careful! │
╰─────────────────────╯
""",
r"""
   ✦ ｡ﾟ⋆ UH OH ⋆｡ﾟ ✦     (；ω；)
      ╭─────╮       ...
      │     │
      │     O
      │     |
      │
      │
╭─────┴──────────────╮
│  (╥﹏╥)  breathe... │
╰─────────────────────╯
""",
r"""
   ✦ ｡ﾟ⋆ NOOO ⋆｡ﾟ ✦      (ﾉﾟДﾟ)ﾉ
      ╭─────╮      !!!
      │     │
      │     O
      │    /|
      │
      │
╭─────┴──────────────╮
│  (｡•́︿•̀｡)  nope...   │
╰─────────────────────╯
""",
r"""
   ✦ ｡ﾟ⋆ FOCUS ⋆｡ﾟ ✦     (ಠ_ಠ)☆
      ╭─────╮      ✦
      │     │     ✦ ✦
      │     O
      │    /|\
      │
      │
╭─────┴──────────────╮
│  (ง •̀_•́)ง  lock in│
╰─────────────────────╯
""",
r"""
   ✦ ｡ﾟ⋆ LAST ARC ⋆｡ﾟ ✦  (ง •̀_•́)ง🔥
      ╭─────╮     !!
      │     │
      │     O
      │    /|\
      │    /
      │
╭─────┴──────────────╮
│  (＞﹏＜)  clutch!!  │
╰─────────────────────╯
""",
r"""
   ✦ ｡ﾟ⋆ CRITICAL ⋆｡ﾟ ✦  (×_×)
      ╭─────╮     ...
      │     │
      │     O
      │    /|\
      │    / \
      │
╭─────┴──────────────╮
│ (っ˘̩╭╮˘̩)っ  1HP...  │
╰─────────────────────╯
""",
r"""
   ✦ ｡ﾟ⋆ GAME OVER ⋆｡ﾟ ✦  (T_T)
      ╭─────╮
      │     │      ＿|￣|○
      │     O
      │    /|\
      │    / \
      │
╭─────┴──────────────╮
│  (｡•́︿•̀｡)ﾉﾞ RIP...  │
╰─────────────────────╯
""",
]

FRAMES_L2 = [
r"""
🔥🔥🔥 CHALLENGE MODE 🔥🔥🔥   (ง🔥_🔥)ง
      ╭─────╮
      │     │      "LET'S GO!!"
      │
      │
      │
      │
╭─────┴──────────────╮
│  AURA: MAX ✦✦✦✦✦    │
╰─────────────────────╯
""",
r"""
🔥 CHALLENGE MODE 🔥         (ง🔥_🔥)ง
      ╭─────╮
      │     │      "HIT ME!"
      │     O
      │
      │
      │
╭─────┴──────────────╮
│  COMBO: BUILDING…   │
╰─────────────────────╯
""",
r"""
🔥 CHALLENGE MODE 🔥         (ง •̀_•́)ง
      ╭─────╮
      │     │      "FOCUS!"
      │     O
      │     |
      │
      │
╭─────┴──────────────╮
│  HEART: STEEL       │
╰─────────────────────╯
""",
r"""
🔥 CHALLENGE MODE 🔥         (ง •̀_•́)ง✨
      ╭─────╮
      │     │      "NO FEAR!"
      │     O
      │    /|
      │
      │
╭─────┴──────────────╮
│  KEEP PUSHING!!     │
╰─────────────────────╯
""",
r"""
🔥 CHALLENGE MODE 🔥         (ง🔥_🔥)ง✦
      ╭─────╮
      │     │      "POWER!"
      │     O
      │    /|\
      │
      │
╭─────┴──────────────╮
│  LIMIT BREAK!!      │
╰─────────────────────╯
""",
r"""
🔥 CHALLENGE MODE 🔥         (ง🔥_🔥)ง💥
      ╭─────╮
      │     │      "CLUTCH!"
      │     O
      │    /|\
      │    /
      │
╭─────┴──────────────╮
│  LAST STAND!!       │
╰─────────────────────╯
""",
r"""
🔥 CHALLENGE MODE 🔥         (งಠ_ಠ)ง⚡
      ╭─────╮
      │     │      "NOT YET!"
      │     O
      │    /|\
      │    / \
      │
╭─────┴──────────────╮
│  ULTRA CRIT!!       │
╰─────────────────────╯
""",
r"""
🔥 CHALLENGE MODE 🔥         (x_x)
      ╭─────╮
      │     │      "GG..."
      │     O
      │    /|\
      │    / \
      │
╭─────┴──────────────╮
│  TRY AGAIN!!        │
╰─────────────────────╯
""",
]


# ======================
#  Save System
# ======================

def load_save():
    default = {
        "dazy_unlocked": False,
        "dazy_unlock_count": 0,
        "sigil_collected": [],
        "challenge_entries": 0,
        "challenge_clears": 0,
        "secret_note_unlocked": False,
        "secret_note_read_count": 0
    }
    if not os.path.exists(SAVE_FILE):
        return default
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in default.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return default


def write_save(save):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(save, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def reset_save_to_locked():
    """Dev helper: wipe progress back to locked state."""
    save = {
        "dazy_unlocked": False,
        "dazy_unlock_count": 0,
        "sigil_collected": [],
        "challenge_entries": 0,
        "challenge_clears": 0,
        "secret_note_unlocked": False,
        "secret_note_read_count": 0
    }
    write_save(save)
    return save

# ======================
#  Helpers
# ======================

def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def normalize(s):
    return s.strip().lower()

# Cute feedback pools (anime-style)
CUTE_CORRECT = [
    "✨ Kawaii! Nice hit~ (≧◡≦) ♡",
    "🌸 Sugoi!! (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧",
    "💫 Perfect guess! (｡•̀ᴗ-)✧",
    "🍡 Yatta! You got it~ (๑>ᴗ<๑)",
    "⭐ GG! That was clean (ง •̀_•́)ง",
]

CUTE_WRONG = [
    "💦 Ehh?! Not that one... (｡•́︿•̀｡)",
    "🥺 Oopsie... try again! (╥﹏╥)",
    "🌧️ Nande?! Wrong... (；ω；)",
    "🌀 Aaa nooo~ (ﾉﾟДﾟ)ﾉ",
    "😿 It slipped... Life -1 (っ˘̩╭╮˘̩)っ",
]

def pick_cute(pool):
    """Safely pick a random line from a pool."""
    try:
        return random.choice(pool)
    except Exception:
        return ""


def sigil_bar(collected_set) -> str:
    """Return a 4-slot bar using ◆/◇ following SIGIL_ORDER."""
    collected_set = set(collected_set or [])
    return " ".join("◆" if ch in collected_set else "◇" for ch in SIGIL_ORDER)


def sigil_letters(collected_set) -> str:
    """Return per-slot letters only when collected; otherwise show a placeholder dot."""
    collected_set = set(collected_set or [])
    return " ".join((ch if ch in collected_set else "·") for ch in SIGIL_ORDER)
def hp_bar_hearts(lives_left, max_lives):
    filled = max(0, min(max_lives, lives_left))
    empty = max_lives - filled
    return "♥" * filled + "♡" * empty


def frame_for_lives(frames, max_lives, lives_left):
    # 根据剩余命数映射到 frames index
    if not frames:
        return ""
    wrong_used = max_lives - lives_left
    ratio = wrong_used / max_lives if max_lives > 0 else 1
    idx = int(ratio * (len(frames) - 1))
    idx = max(0, min(idx, len(frames) - 1))
    return frames[idx]

# ======================
#  UI
# ======================

def kawaii_banner(save):
    clear_screen()
    route = "Secret Route: OPEN ✅" if save.get("dazy_unlocked") else "Secret Route: ???"
    print(rf"""
╭──────────────────────────────────────────────────────────╮
│ (≧◡≦) ♡  OTAKU HANGMAN  ♡ (≧◡≦)                          │
│  rule: 1 letter per turn                                  │
│  {route:<56}│
╰──────────────────────────────────────────────────────────╯
""")


def kawaii_menu(save):
    """Menu behavior:
    - Locked: show only 1/3/4 (Challenge not shown at all).
      If user types 2 anyway, main() will show the sealed door message.
    - Unlocked: show 1/2/3/4 with Challenge Mode.
    - Secret note is NOT a menu item.
    """
    unlocked = bool(save.get("dazy_unlocked"))

    if not unlocked:
        print(r"""
╔══════════════════════════════════════════════════════╗
║              ✨ MENU / メニュー ✨                    ║
╠══════════════════════════════════════════════════════╣
║  1) ▶ Play / 始める                                   ║
║                                                      ║
║     …a sealed door hums softly.  ◆◇◇◇                ║
║                                                      ║
║  3) 📜 Stats                                           ║
║  4) ❌ Quit / やめる                                   ║
╠══════════════════════════════════════════════════════╣
║  Gambatte! (=^･ω･^=)ฅ                                 ║
╚══════════════════════════════════════════════════════╝
""")
    else:
        print(r"""
╔══════════════════════════════════════════════════════╗
║              ✨ MENU / メニュー ✨                    ║
╠══════════════════════════════════════════════════════╣
║  1) ▶ Play / 始める                                   ║
║  2) 🔥 Challenge Mode 🔥                               ║
║  3) 📜 Stats                                           ║
║  4) ❌ Quit / やめる                                   ║
╠══════════════════════════════════════════════════════╣
║  Gambatte! (=^･ω･^=)ฅ                                 ║
╚══════════════════════════════════════════════════════╝
""")

def show_stats(save):
    clear_screen()
    print(r"""
╔══════════════════════════════════════╗
║              📜 STATS                ║
╚══════════════════════════════════════╝
""")
    print("SAVE FILE:", SAVE_FILE)
    print(f"🌸 Secret Route opened : {'YES' if save.get('dazy_unlocked') else 'NO'}")
    print(f"✨ Route opens count    : {save.get('dazy_unlock_count', 0)}")
    print(f"🔥 Challenge entries    : {save.get('challenge_entries', 0)}")
    print(f"🏆 Challenge clears     : {save.get('challenge_clears', 0)}")
    print(f"📩 Secret note unlocked : {'YES' if save.get('secret_note_unlocked') else 'NO'}")
    print(f"👀 Secret note reads    : {save.get('secret_note_read_count', 0)}")
    input("\nPress Enter to go back...")


def show_secret_note(save):
    """
    Secret note should never be a menu item.
    It is shown automatically right after a successful Challenge clear
    (only after it becomes eligible/unlocked).
    """
    if not save.get("secret_note_unlocked"):
        return

    save["secret_note_read_count"] = int(save.get("secret_note_read_count", 0)) + 1
    write_save(save)

    clear_screen()
    print(r"""
🌸✨ SECRET NOTE ✨🌸
(づ｡◕‿‿◕｡)づ

If you're seeing this…
you are officially an Otaku Grandmaster.

🏆 Achievement Unlocked:
「Touch Grass」(Optional)

Reminder:
Drink water 💧
Maybe open a window.
Maybe laugh a little.

Bonus stat gained:
+1 Softness ✧

System shutting up now.
(๑>ᴗ<๑)♡
""")
    input("Press Enter...")


def unlock_secret_note_if_eligible(save):
    # ONLY after: DAZY unlocked AND challenge cleared at least once
    clears = int(save.get("challenge_clears", 0))
    if save.get("dazy_unlocked") and clears >= 1 and not save.get("secret_note_unlocked"):
        save["secret_note_unlocked"] = True
        write_save(save)

# ======================
#  Game Hooks (you fill these)
# ======================

def play_round(max_lives, level_name, frames, save, allow_sigil=True, **kwargs):
    # pick a random word
    entry = random.choice(WORDS)
    wordchosen = entry["word"]
    hint = entry.get("hint")

    lives = max_lives
    display = ["_"] * len(wordchosen)
    guessed = set()

    # Persist sigil progress across rounds via save file
    sigil_collected = set(save.get("sigil_collected", []))
    can_unlock_route = allow_sigil and (not save.get("dazy_unlocked"))
    sigil_revealed = False  # only show UI after the player triggers it this round
    sigil_triggers = 0  # how many times player typed a sigil letter this round
    sigil_display = set()  # ritual UI: only letters triggered THIS round

    def is_single_latin_letter(s):
        return len(s) == 1 and s.isalpha() and s.isascii()

    while lives > 0 and "_" in display:
        clear_screen()
        # frame (safe if frames exists)
        if frames:
            try:
                print(frame_for_lives(frames, max_lives, lives))
            except Exception:
                pass

        print(f"💗 HP: {hp_bar_hearts(lives, max_lives)}  ({lives}/{max_lives})   🌟 {level_name}")
        print("🧩 Word:", " ".join(display))
        print("📝 Guessed:", " ".join(sorted(guessed)) if guessed else "∅")
        if hint:
            print("📺 From:", hint)

        if allow_sigil and (not save.get("dazy_unlocked")) and sigil_revealed:
            print("🔒 sigil:")
            print(f"   {sigil_bar(sigil_display)}")
            print(f"   {sigil_letters(sigil_display)}")

        print("-" * 60)

        guess = normalize(input("Type 1 letter: "))

        if guess == "" or len(guess) != 1 or (not is_single_latin_letter(guess)):
            print("⚠️  Type exactly 1 letter (a-z).")
            input("Press Enter...")
            continue
        if guess in guessed:
            print("⚠️  Already guessed.")
            input("Press Enter...")
            continue

        guessed.add(guess)

        # -------------------------
        # Sigil collection (D/A/Z/Y)
        # Now triggers even if the guess is NOT in the word.
        # -------------------------
        sigil_new = False
        if allow_sigil and (guess in SIGIL_SET) and (guess not in sigil_collected) and (not save.get("dazy_unlocked")):
            sigil_collected.add(guess)
            sigil_new = True
            sigil_revealed = True
            # persist progress immediately
            save["sigil_collected"] = sorted(sigil_collected)
            write_save(save)
        if allow_sigil and (guess in SIGIL_SET) and (not save.get("dazy_unlocked")):
            sigil_triggers += 1
            sigil_revealed = True
            sigil_display.add(guess)

        # normal hangman logic
        if guess in wordchosen:
            for i, ch in enumerate(wordchosen):
                if ch == guess:
                    display[i] = guess
        else:
            lives -= 1

        # =============================
        # PHASE 1: SIGIL RITUAL SCREEN
        # =============================
        triggered_sigil = allow_sigil and (guess in SIGIL_SET)

        if triggered_sigil:
            clear_screen()
            print("\n✨ SIGIL RESONANCE ✨\n")

            if save.get("dazy_unlocked"):
                print("The DAZY sigil glows steadily... ✧\n")
                ritual_set = set(SIGIL_ORDER)
            else:
                if sigil_new:
                    print("Feels like something secret is forming ... ✨\n")
                else:
                    print("...a familiar rune flickers softly ✧\n")
                ritual_set = sigil_display

            # ritual animation: empty → lit
            print("   " + " ".join(["◇"] * 4))
            print("   " + " ".join(["·"] * 4))
            time.sleep(0.4)
            print()
            print(f"   {sigil_bar(ritual_set)}")
            print(f"   {sigil_letters(ritual_set)}")
            input("\nPress Enter to continue...")

        # =============================
        # PHASE 2: NORMAL GUESS FEEDBACK
        # =============================
        clear_screen()

        if guess in wordchosen:
            print(pick_cute(CUTE_CORRECT))
        else:
            print(pick_cute(CUTE_WRONG))

        # if sigil is complete, unlock route with the congrats message
        if (not save.get("dazy_unlocked")) and len(sigil_collected) == 4 and can_unlock_route:
            # unlock route permanently
            save["dazy_unlocked"] = True
            save["dazy_unlock_count"] = int(save.get("dazy_unlock_count", 0)) + 1
            write_save(save)
            can_unlock_route = False
            sigil_display = set(SIGIL_ORDER)
            clear_screen()
            print("\nCongratulations Dazy✨！You unlocked the challenge mode 🔥！！\n")
            input("Press Enter...")
            continue

        input("Press Enter...")

    return {"won": ("_" not in display), "word": wordchosen}


def challenge_mode(save):
    """Challenge Mode: win 5 rounds in a row.

    - Locked until DAZY sigil is unlocked (save['dazy_unlocked'] == True)
    - On clear: requires final chant 'tomoe'
    - Only after the chant is correct will it increment challenge_clears
    - Returns True only if fully cleared (wins streak + correct chant)
    """
    if not save.get("dazy_unlocked"):
        clear_screen()
        print("…the door doesn't move. ◆◇◇◇\n")
        input("Press Enter...")
        return False

    # Track entry
    save["challenge_entries"] = int(save.get("challenge_entries", 0)) + 1
    write_save(save)

    streak = 0
    while streak < WINS_IN_A_ROW_TO_CLEAR:
        clear_screen()
        print(
            f"🔥 CHALLENGE MODE — Win {WINS_IN_A_ROW_TO_CLEAR} in a row!  (streak: {streak}/{WINS_IN_A_ROW_TO_CLEAR})\n"
        )
        input("Press Enter to start the next round...")

        result = play_round(
            max_lives=CHALLENGE_LIVES,
            level_name=f"CHALLENGE {streak + 1}/{WINS_IN_A_ROW_TO_CLEAR}",
            frames=FRAMES_L2,
            save=save,
            allow_sigil=False,
        )

        # reload save in case play_round wrote anything
        save.update(load_save())

        if result.get("won"):
            streak += 1
            clear_screen()
            print(f"✅ Round cleared! ({streak}/{WINS_IN_A_ROW_TO_CLEAR})\n")
            print(f"WORD：{result.get('word')}！\n")
            input("Press Enter...")
        else:
            streak = 0
            clear_screen()
            print("❌ Round failed. Streak reset to 0.\n")
            input("Press Enter...")

    # streak cleared — now require the secret password before recording the clear
    clear_screen()
    print("🏆 CHALLENGE CLEARED!\n")
    print("Extra check: guess from Kamisama Kiss ✧")
    password = normalize(input("SECRET PASSWORD: "))

    if password != "tomoe":
        print("\n⚠️  Wrong password. Clear not finalized.\n")
        input("Press Enter...")
        return False

    # Finalize clear ONLY if password is correct
    save["challenge_clears"] = int(save.get("challenge_clears", 0)) + 1
    write_save(save)

    print("\n✨ Password accepted.\n")
    input("Press Enter...")
    return True

# ======================
#  Main
# ======================

def main():
    save = load_save()

    while True:
        kawaii_banner(save)
        kawaii_menu(save)
        try:
            option = normalize(input("Option: "))
        except KeyboardInterrupt:
            clear_screen()
            print("\n\nBye bye~ (｡•́‿•̀｡)ﾉﾞ  (Interrupted)\n")
            break


        unlocked = bool(save.get("dazy_unlocked"))

        # -------------------------
        # LOCKED MENU MAPPING
        # 1 Play / 3 Stats / 4 Quit
        # (Challenge is hidden; typing 2 shows sealed door)
        # -------------------------
        if not unlocked:
            if option == "1":
                clear_screen()
                print("\n✨ New run! ✨\n")
                input("Press Enter to start...")

                result = play_round(
                    max_lives=BASE_LIVES,
                    level_name="LEVEL 1",
                    frames=FRAMES_L1,
                    save=save,
                    allow_sigil=True
                )

                save = load_save()

                clear_screen()
                if result.get("won"):
                    print(f"\n🎉 YOU WIN!! The word was: {result.get('word')}  ✧٩(ˊωˋ*)و✧\n")
                    print(f"答案是：{result.get('word')}！\n")
                else:
                    print(f"\n💀 YOU LOSE... The word was: {result.get('word')}  (っ˘̩╭╮˘̩)っ\n")
                input("Press Enter to return to menu...")

            elif option == "2":
                clear_screen()
                print("…the door doesn't move. ◆◇◇◇\n")
                input("Press Enter...")

            elif option == "3":
                show_stats(save)
                save = load_save()

            elif option == "4":
                print("\nBye bye~ (｡•́‿•̀｡)ﾉﾞ  See you next time!\n")
                break

            elif option in ("reset", "99"):
                save = reset_save_to_locked()
                clear_screen()
                print("✅ Save reset to LOCKED state.\n")
                print("SAVE FILE:", SAVE_FILE)
                input("Press Enter...")

            else:
                print("⚠️  Please choose 1/3/4.\n")
                time.sleep(0.7)

            continue

        # -------------------------
        # UNLOCKED MENU MAPPING
        # 1 Play / 2 Challenge / 3 Stats / 4 Quit
        # -------------------------
        if option == "1":
            clear_screen()
            print("\n✨ New run! ✨\n")
            input("Press Enter to start...")

            result = play_round(
                max_lives=BASE_LIVES,
                level_name="LEVEL 1",
                frames=FRAMES_L1,
                save=save,
                allow_sigil=True
            )

            save = load_save()

            clear_screen()
            if result.get("won"):
                print(f"\n🎉 YOU WIN!! The word was: {result.get('word')}  ✧٩(ˊωˋ*)و✧\n")
                print(f"答案是：{result.get('word')}！\n")
            else:
                print(f"\n💀 YOU LOSE... The word was: {result.get('word')}  (っ˘̩╭╮˘̩)っ\n")
            input("Press Enter to return to menu...")

        elif option == "2":
            cleared = challenge_mode(save)
            save = load_save()

            if cleared:
                unlock_secret_note_if_eligible(save)
                save = load_save()
                if save.get("secret_note_unlocked"):
                    show_secret_note(save)
                    save = load_save()

        elif option == "3":
            show_stats(save)
            save = load_save()

        elif option == "4":
            print("\nBye bye~ (｡•́‿•̀｡)ﾉﾞ  See you next time!\n")
            break

        else:
            print("⚠️  Please choose 1/2/3/4.\n")
            time.sleep(0.7)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("\n\nBye bye~ (｡•́‿•̀｡)ﾉﾞ  (Interrupted)\n")