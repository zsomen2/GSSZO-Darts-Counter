import pygame
import sys
import os
import copy
import re

pygame.init()

# region DEFAULTS
START_SCORE = 301
player_names = ["Player 1", "Player 2"]

# Get current display resolution and use fullscreen
display_info = pygame.display.Info()
WIDTH, HEIGHT = display_info.current_w, display_info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption(f"GSSZO Darts Counter")

# --- icon helpers ---

def resource_path(relative_path: str) -> str:
    """
    Works both in dev and in PyInstaller .exe
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

try:
    icon_path = resource_path(os.path.join("assets", "gsszo_logo_32x32.png"))
    icon_surface = pygame.image.load(icon_path).convert_alpha()
    pygame.display.set_icon(icon_surface)
except Exception as e:
    print("Could not set window icon:", e)

# Colours
PALETTE_DARK = {
    "BG_COLOUR": (20, 20, 20),
    "TEXT_COLOUR": (230, 230, 230),
    "HINT_COLOUR": (160, 160, 160),
    "ACCENT_ACTIVE": (100, 220, 100),
    "ACCENT_INACTIVE": (100, 100, 100),
    "DIVIDER_COLOUR": (80, 80, 80),
    "BOX_BG": (35, 35, 35),
    "BOX_BORDER": (90, 90, 90),
    "BOX_BORDER_ACTIVE": (100, 220, 100),
    "BTN_BG": (60, 60, 60),
    "BTN_BG_HOVER": (80, 80, 80),
    "SPONSOR_BAR_BG": (35, 35, 35),
    "SPONSOR_BAR_BORDER": (80, 80, 80),
    "SPONSOR_TEXT_COLOUR": (230, 230, 230),
}

PALETTE_LIGHT = {
    "BG_COLOUR": (230, 230, 230),
    "TEXT_COLOUR": (20, 20, 20),
    "HINT_COLOUR": (95, 95, 95),
    "ACCENT_ACTIVE": (138, 36, 50),
    "ACCENT_INACTIVE": (175, 175, 175),
    "DIVIDER_COLOUR": (155, 155, 155),
    "BOX_BG": (220, 220, 220),
    "BOX_BORDER": (165, 165, 165),
    "BOX_BORDER_ACTIVE": (138, 36, 50),
    "BTN_BG": (230, 234, 240),
    "BTN_BG_HOVER": (214, 222, 232),
    "SPONSOR_BAR_BG": (220, 220, 220),
    "SPONSOR_BAR_BORDER": (155, 155, 155),
    "SPONSOR_TEXT_COLOUR": (20, 20, 20),
}

BG_COLOUR = PALETTE_DARK["BG_COLOUR"]
TEXT_COLOUR = PALETTE_DARK["TEXT_COLOUR"]
HINT_COLOUR = PALETTE_DARK["HINT_COLOUR"]
ACCENT_ACTIVE = PALETTE_DARK["ACCENT_ACTIVE"]
ACCENT_INACTIVE = PALETTE_DARK["ACCENT_INACTIVE"]
DIVIDER_COLOUR = PALETTE_DARK["DIVIDER_COLOUR"]
BOX_BG = PALETTE_DARK["BOX_BG"]
BOX_BORDER = PALETTE_DARK["BOX_BORDER"]
BOX_BORDER_ACTIVE = PALETTE_DARK["BOX_BORDER_ACTIVE"]
BTN_BG = PALETTE_DARK["BTN_BG"]
BTN_BG_HOVER = PALETTE_DARK["BTN_BG_HOVER"]
SPONSOR_BAR_BG = PALETTE_DARK["SPONSOR_BAR_BG"]
SPONSOR_BAR_BORDER = PALETTE_DARK["SPONSOR_BAR_BORDER"]
SPONSOR_TEXT_COLOUR = PALETTE_DARK["SPONSOR_TEXT_COLOUR"]

def _apply_palette(palette):
    for key, value in palette.items():
        globals()[key] = value

_apply_palette(PALETTE_DARK)

# Constants
SPONSOR_BAR_HEIGHT = 40  # adjustable height for the sponsor ticker
SPONSOR_SCROLL_SPEED = 20  # pixels per second
SPONSOR_LOGO_GAP = 20
SPONSOR_ENTRY_GAP = 40

current_fullscreen = True
current_dark_mode = True

# Display mode helpers

def _maximize_window_if_possible():
    try:
        from pygame._sdl2 import Window  # type: ignore

        window = Window.from_display_module()
        window.maximize()
    except Exception:
        pass

def apply_display_mode(fullscreen: bool, force: bool = False):
    """Switch between fullscreen and maximized windowed modes."""
    global screen, WIDTH, HEIGHT, current_fullscreen

    if screen is not None and not force and fullscreen == current_fullscreen:
        return

    flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE

    info = pygame.display.Info()
    size = (info.current_w, info.current_h)
    screen_surface = pygame.display.set_mode(size, flags)

    if not fullscreen:
        _maximize_window_if_possible()

    WIDTH, HEIGHT = screen_surface.get_size()
    screen = screen_surface
    current_fullscreen = fullscreen

apply_display_mode(True, force=True)
pygame.display.set_caption("GSSZO Darts Counter")

# Fonts
font_title = pygame.font.SysFont(None, 100)
font_huge  = pygame.font.SysFont(None, 110)
font_big   = pygame.font.SysFont(None, 72)
font_med   = pygame.font.SysFont(None, 46)
font_small = pygame.font.SysFont(None, 30)
font_round = pygame.font.SysFont(None, 46)
font_sponsor = pygame.font.SysFont(None, 28)

clock = pygame.time.Clock()
frame_dt = 0.0

# ---- STATES ----
STATE_MENU = "MENU"
STATE_GAME = "GAME"
STATE_END  = "END"
state = STATE_MENU

# ---- MATCH / LEG STATE ----
current_input = ""         # current numeric input while throwing
scores = [[], []]          # per-leg list of throws
active_player = 0          # 0 or 1 (whose turn)
history = []               # list of (player_index, score) for undo (per leg)
winner_idx = None          # match winner when STATE_END

LEGS_TO_WIN = 2            # target legs to win the match
legs_won = [0, 0]          # legs won by players
leg_starter_idx = 0        # who started the CURRENT leg
DOUBLE_OUT_ENABLED = True  # double out rule active?

# Stack of finished-leg snapshots for cross-leg undo
finished_legs_stack = []   # each item: dict with scores, history, active_player, leg_starter_idx, winner

# ---- MENU STATE ----
menu_values = {
    "p1": player_names[0],
    "p2": player_names[1],
    "score": "301",   # "301" or "501"
    "legs": "2",      # number as string
    "doubleout": True,
    "showsponsors": False,
    "darkmode": True,
    "fullscreen": True,
}
active_input_key = "p1"    # "p1" | "p2" | "score" | "legs" | "doubleout" | "start"
start_btn_rect = None      # set in draw_menu()
settings_menu_open = False
settings_panel_rect = None

# ---- ASSETS: LOGO (two-layer, with fallback) ----
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_TOP_GAP = 20          # px gap between screen top and logo top
LOGO_BOTTOM_GAP = 20       # px gap between logo bottom and horizontal divider
LOGO_SIDE_MARGIN = 20      # px side margin for width constraint

# Rotation settings
LOGO_ROT_SPEED_DEG = 40.0  # degrees per second
LOGO_ANGLE = 0.0           # will be updated every frame

def _load_alpha(path):
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None

# Preferred two-piece assets
LOGO_INNER_DARK = _load_alpha(os.path.join(ASSETS_DIR, "gsszo_logo_inner_white.png"))
LOGO_RING_DARK  = _load_alpha(os.path.join(ASSETS_DIR, "gsszo_logo_outer_white.png"))
LOGO_INNER_LIGHT = _load_alpha(os.path.join(ASSETS_DIR, "gsszo_logo_inner_black.png"))
LOGO_RING_LIGHT  = _load_alpha(os.path.join(ASSETS_DIR, "gsszo_logo_outer_black.png"))

LOGO_INNER_ORIG = LOGO_INNER_DARK or LOGO_INNER_LIGHT
LOGO_RING_ORIG = LOGO_RING_DARK or LOGO_RING_LIGHT

# region SPONSOR BAR SUPPORT

SPONSOR_LIST_PATH = resource_path(os.path.join("display_bar", "sponsors.txt"))
ORGANIZERS_LIST_PATH = resource_path(os.path.join("display_bar", "organizers.txt"))
SPONSOR_LOGO_DIR = resource_path(os.path.join("display_bar", "logos"))


class SponsorTicker:
    def __init__(self):
        self.height = max(40, int(SPONSOR_BAR_HEIGHT))
        self.entries = []
        self.segment_surface = None
        self.segment_width = 0
        self.scroll_offset = 0.0

    def _normalize_name(self, name: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        return normalized

    def _append_surface_entry(self, entry_specs, surface: pygame.Surface):
        """Append a plain surface entry if it has a visible width."""
        if surface is None or surface.get_width() <= 0:
            return
        entry_specs.append({
            "kind": "surface",
            "surface": surface,
            "width": surface.get_width(),
        })

    def _read_sponsor_names(self):
        try:
            with open(SPONSOR_LIST_PATH, "r", encoding="utf-8") as handle:
                return [line.strip() for line in handle if line.strip()]
        except FileNotFoundError:
            return []
        except Exception as exc:
            print("Could not read sponsors.txt:", exc)
            return []

    def _read_organizer_names(self):
        try:
            with open(ORGANIZERS_LIST_PATH, "r", encoding="utf-8") as handle:
                return [line.strip() for line in handle if line.strip()]
        except FileNotFoundError:
            return []
        except Exception as exc:
            print("Could not read organizers.txt:", exc)
            return []

    def _load_logo(self, normalized_name: str):
        if not normalized_name:
            return None
        possible_exts = ("png", "jpg", "jpeg", "bmp", "gif")
        for ext in possible_exts:
            logo_path = os.path.join(SPONSOR_LOGO_DIR, f"{normalized_name}_logo.{ext}")
            if os.path.isfile(logo_path):
                try:
                    return pygame.image.load(logo_path).convert_alpha()
                except Exception as exc:
                    print(f"Failed to load sponsor logo '{logo_path}':", exc)
        return None

    def reload(self):
        self.height = max(40, int(SPONSOR_BAR_HEIGHT))
        names = self._read_sponsor_names()
        organizers = self._read_organizer_names()
        self.entries = []
        self.segment_surface = None
        self.segment_width = 0
        self.scroll_offset = 0.0

        entry_specs = []
        logo_target_h = max(10, self.height - 10)

        if names:
            prefix_surface = font_sponsor.render("Támogatóink:", True, SPONSOR_TEXT_COLOUR)
            self._append_surface_entry(entry_specs, prefix_surface)

        for name in names:
            text_surface = font_sponsor.render(name, True, SPONSOR_TEXT_COLOUR)
            normalized = self._normalize_name(name)
            raw_logo = self._load_logo(normalized)
            logo_surface = None

            if raw_logo is not None and raw_logo.get_height() > 0:
                scale_ratio = logo_target_h / raw_logo.get_height()
                logo_width = max(1, int(raw_logo.get_width() * scale_ratio))
                logo_surface = pygame.transform.smoothscale(raw_logo, (logo_width, logo_target_h))

            entry_width = text_surface.get_width()
            if logo_surface is not None:
                entry_width += logo_surface.get_width()
                if text_surface.get_width() > 0:
                    entry_width += SPONSOR_LOGO_GAP

            entry_specs.append({
                "kind": "sponsor",
                "text_surface": text_surface,
                "logo_surface": logo_surface,
                "entry_width": entry_width,
            })

        if organizers:
            header_surface = font_sponsor.render("Szervezők:", True, SPONSOR_TEXT_COLOUR)
            self._append_surface_entry(entry_specs, header_surface)

            for name in organizers:
                text_surface = font_sponsor.render(name, True, SPONSOR_TEXT_COLOUR)
                self._append_surface_entry(entry_specs, text_surface)

        if not entry_specs:
            return

        leading_padding = SPONSOR_ENTRY_GAP
        trailing_padding = SPONSOR_ENTRY_GAP
        total_width = leading_padding + trailing_padding

        for spec in entry_specs:
            if spec["kind"] == "sponsor":
                total_width += spec["entry_width"] + SPONSOR_ENTRY_GAP
            else:
                total_width += spec["width"] + SPONSOR_ENTRY_GAP

        self.segment_width = max(1, int(total_width))
        self.segment_surface = pygame.Surface((self.segment_width, self.height), pygame.SRCALPHA)
        center_y = self.height // 2

        x = leading_padding
        for spec in entry_specs:
            if spec["kind"] == "sponsor":
                logo_surface = spec["logo_surface"]
                if logo_surface is not None:
                    logo_rect = logo_surface.get_rect(midleft=(x, center_y))
                    self.segment_surface.blit(logo_surface, logo_rect)
                    x = logo_rect.right
                    if spec["text_surface"].get_width() > 0:
                        x += SPONSOR_LOGO_GAP

                text_surface = spec["text_surface"]
                if text_surface.get_width() > 0:
                    text_rect = text_surface.get_rect(midleft=(x, center_y))
                    self.segment_surface.blit(text_surface, text_rect)
                    x = text_rect.right

                x += SPONSOR_ENTRY_GAP
            else:
                surface = spec["surface"]
                surf_rect = surface.get_rect(midleft=(x, center_y))
                self.segment_surface.blit(surface, surf_rect)
                x = surf_rect.right + SPONSOR_ENTRY_GAP

        self.entries = entry_specs

    def update(self, dt: float):
        if not self.segment_surface or self.segment_width <= 0:
            return
        self.scroll_offset -= SPONSOR_SCROLL_SPEED * dt
        while self.scroll_offset <= -self.segment_width:
            self.scroll_offset += self.segment_width
        while self.scroll_offset > 0:
            self.scroll_offset -= self.segment_width

    def draw(self, target_surface: pygame.Surface, top_y: int):
        bar_rect = pygame.Rect(0, top_y, target_surface.get_width(), self.height)
        pygame.draw.rect(target_surface, SPONSOR_BAR_BG, bar_rect)
        pygame.draw.line(target_surface, SPONSOR_BAR_BORDER, (0, top_y), (target_surface.get_width(), top_y), 2)

        if not self.segment_surface:
            return

        x = self.scroll_offset
        while x < bar_rect.width:
            target_surface.blit(self.segment_surface, (x, top_y))
            x += self.segment_width

        x = self.scroll_offset - self.segment_width
        while x + self.segment_width > 0:
            target_surface.blit(self.segment_surface, (x, top_y))
            x -= self.segment_width

    def has_entries(self) -> bool:
        return bool(self.entries)

sponsor_bar_enabled = False
sponsor_ticker = SponsorTicker()

def apply_theme(dark_mode: bool):
    """Switch between dark and light colour palettes and update logo assets."""
    global current_dark_mode, LOGO_INNER_ORIG, LOGO_RING_ORIG

    if dark_mode == current_dark_mode:
        return

    palette = PALETTE_DARK if dark_mode else PALETTE_LIGHT
    _apply_palette(palette)

    current_dark_mode = dark_mode

    if dark_mode:
        LOGO_INNER_ORIG = LOGO_INNER_DARK or LOGO_INNER_LIGHT or LOGO_INNER_ORIG
        LOGO_RING_ORIG = LOGO_RING_DARK or LOGO_RING_LIGHT or LOGO_RING_ORIG
    else:
        LOGO_INNER_ORIG = LOGO_INNER_LIGHT or LOGO_INNER_DARK or LOGO_INNER_ORIG
        LOGO_RING_ORIG = LOGO_RING_LIGHT or LOGO_RING_DARK or LOGO_RING_ORIG

    ticker = globals().get("sponsor_ticker")
    if ticker:
        ticker.reload()

def handle_window_resize(event: pygame.event.Event):
    """Update the window surface when the user resizes in windowed mode."""
    global screen, WIDTH, HEIGHT

    if event.type != pygame.VIDEORESIZE or current_fullscreen:
        return

    new_width = max(1, event.w)
    new_height = max(1, event.h)
    flags = screen.get_flags() if screen is not None else pygame.RESIZABLE
    screen_surface = pygame.display.set_mode((new_width, new_height), flags)
    WIDTH, HEIGHT = screen_surface.get_size()
    screen = screen_surface

# region UTILITIES

def is_leg_pristine():
    """True if the current leg has no typed digits and no committed throws."""
    return current_input == "" and not history and not scores[0] and not scores[1]

def current_leg_number():
    return legs_won[0] + legs_won[1] + 1

def avg(lst):
    return (sum(lst) / len(lst)) if lst else 0.0

def match_averages():
    """Compute per-player match averages across all finished legs + current leg."""
    totals = [0, 0]
    counts = [0, 0]
    # finished legs
    for snap in finished_legs_stack:
        for p in (0, 1):
            totals[p] += sum(snap['scores'][p])
            counts[p] += len(snap['scores'][p])
    # current leg
    for p in (0, 1):
        totals[p] += sum(scores[p])
        counts[p] += len(scores[p])
    return [ (totals[p] / counts[p]) if counts[p] else 0.0 for p in (0,1) ]

# region MATCH CONTROL

def reset_game(new_start_score: int, p1: str, p2: str, target_legs: int = None,
               double_out: bool = True, show_sponsor_bar: bool = False):
    """Reset the WHOLE match (new game from menu)."""
    global START_SCORE, player_names, scores, active_player, history
    global winner_idx, legs_won, leg_starter_idx, LEGS_TO_WIN, state, current_input
    global finished_legs_stack, DOUBLE_OUT_ENABLED, sponsor_bar_enabled, sponsor_ticker

    START_SCORE = new_start_score
    player_names = [p1.strip() or "Player 1", p2.strip() or "Player 2"]

    LEGS_TO_WIN = max(1, int(target_legs) if target_legs is not None else LEGS_TO_WIN)
    legs_won = [0, 0]
    finished_legs_stack = []  # clear snapshots
    DOUBLE_OUT_ENABLED = bool(double_out)
    sponsor_bar_enabled = bool(show_sponsor_bar)
    sponsor_ticker.reload()

    # First leg setup
    leg_starter_idx = 0
    active_player = leg_starter_idx
    scores = [[], []]
    history = []
    current_input = ""
    winner_idx = None

    state = STATE_GAME
    pygame.display.set_caption(f"GSSZO Darts Counter")

def start_new_leg():
    """Start the next leg, alternating starter."""
    global scores, history, current_input, active_player, leg_starter_idx
    leg_starter_idx = 1 - leg_starter_idx
    active_player = leg_starter_idx
    scores = [[], []]
    history = []
    current_input = ""

def revert_last_finished_leg():
    """Pop last finished-leg snapshot, roll back legs and delete the winning throw."""
    global scores, history, active_player, leg_starter_idx, legs_won, current_input
    if not finished_legs_stack:
        return
    snap = finished_legs_stack.pop()
    legs_won[snap['winner']] = max(0, legs_won[snap['winner']] - 1)
    scores = copy.deepcopy(snap['scores'])
    history = snap['history'][:]
    active_player = snap['active_player']
    leg_starter_idx = snap['leg_starter_idx']
    current_input = ""
    undo_last_score()  # remove winning throw

# region MENU AND RENDERING EVENTS

def draw_input_box(x, y, w, h, label, value, active=False):
    label_surf = font_small.render(label, True, HINT_COLOUR)
    screen.blit(label_surf, (x, y - 26))

    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, BOX_BG, rect, border_radius=10)
    pygame.draw.rect(
        screen,
        BOX_BORDER_ACTIVE if active else BOX_BORDER,
        rect,
        2,
        border_radius=10,
    )

    text_surf = font_med.render(value, True, TEXT_COLOUR)
    text_rect = text_surf.get_rect(midleft=(x + 14, y + h // 2))
    screen.blit(text_surf, text_rect)

    if active:
        draw_focus_arrows(rect)

    return rect

def draw_score_switch(x, y, w, h, active: bool, selected: str):
    label_surf = font_small.render("Starting score", True, HINT_COLOUR)
    screen.blit(label_surf, (x, y - 26))

    outer = pygame.Rect(x, y, w, h)
    half_w = w // 2
    r301 = pygame.Rect(x, y, half_w, h)
    r501 = pygame.Rect(x + half_w, y, w - half_w, h)

    pygame.draw.rect(screen, BOX_BG, outer, border_radius=10)

    # Highlight the selected side
    if selected == "301":
        pygame.draw.rect(screen, ACCENT_ACTIVE, r301, border_radius=10)
    else:
        pygame.draw.rect(screen, ACCENT_ACTIVE, r501, border_radius=10)

    pygame.draw.line(
        screen,
        BOX_BORDER,
        (outer.x + half_w, outer.y + 6),
        (outer.x + half_w, outer.y + h - 6),
        2,
    )
    pygame.draw.rect(
        screen,
        BOX_BORDER_ACTIVE if active else BOX_BORDER,
        outer,
        2,
        border_radius=10,
    )

    # Text colours
    if selected == "301":
        t301_colour = BTN_BG
        t501_colour = TEXT_COLOUR
    else:
        t301_colour = TEXT_COLOUR
        t501_colour = BTN_BG

    t301 = font_med.render("301", True, t301_colour)
    t501 = font_med.render("501", True, t501_colour)

    screen.blit(t301, t301.get_rect(center=r301.center))
    screen.blit(t501, t501.get_rect(center=r501.center))

    if active:
        draw_focus_arrows(outer)

    return outer, r301, r501

def draw_checkbox(x, y, w, h, label, checked: bool, active: bool):
    """Simple labeled checkbox-style toggle."""
    label_surf = font_small.render(label, True, HINT_COLOUR)
    screen.blit(label_surf, (x, y - 26))

    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, BOX_BG, rect, border_radius=10)
    pygame.draw.rect(
        screen,
        BOX_BORDER_ACTIVE if active else BOX_BORDER,
        rect,
        2,
        border_radius=10,
    )

    pad = 8
    inner = pygame.Rect(x + pad, y + pad, h - 2 * pad, h - 2 * pad)
    pygame.draw.rect(screen, BTN_BG, inner, border_radius=8)
    if checked:
        pygame.draw.rect(screen, ACCENT_ACTIVE, inner, border_radius=8)

    txt = "ON" if checked else "OFF"
    txt_surf = font_med.render(f"{txt}", True, TEXT_COLOUR)
    txt_rect = txt_surf.get_rect(midleft=(inner.right + 16, y + h // 2))
    screen.blit(txt_surf, txt_rect)

    if active:
        draw_focus_arrows(rect)

    return rect

def draw_settings_button(x, y, size, active: bool):
    rect = pygame.Rect(x, y, size, size)
    mouse_pos = pygame.mouse.get_pos()
    hover = rect.collidepoint(mouse_pos)

    fill_colour = ACCENT_ACTIVE if active else (BTN_BG_HOVER if hover else BTN_BG)
    pygame.draw.rect(screen, fill_colour, rect, border_radius=10)
    pygame.draw.rect(
        screen,
        BOX_BORDER_ACTIVE if active else BOX_BORDER,
        rect,
        2,
        border_radius=10,
    )

    line_width = size * 0.75
    line_height = max(3, size // 10)
    spacing = size // 4
    left = x + (size - line_width) / 2
    center_y = y + size / 2

    for offset in (-spacing, 0, spacing):
        line_rect = pygame.Rect(
            left,
            center_y + offset - line_height / 2,
            line_width,
            line_height,
        )
        pygame.draw.rect(screen, TEXT_COLOUR, line_rect, border_radius=int(line_height / 2))

    return rect

def draw_button(x, y, w, h, label, focused=False):
    mouse_pos = pygame.mouse.get_pos()
    rect = pygame.Rect(x, y, w, h)
    hover = rect.collidepoint(mouse_pos)

    pygame.draw.rect(
        screen,
        BTN_BG_HOVER if hover else BTN_BG,
        rect,
        border_radius=12,
    )
    pygame.draw.rect(
        screen,
        BOX_BORDER_ACTIVE if focused else BOX_BORDER,
        rect,
        3 if focused else 2,
        border_radius=12,
    )

    txt = font_big.render(label, True, TEXT_COLOUR)
    txt_rect = txt.get_rect(center=rect.center)
    screen.blit(txt, txt_rect)

    if focused:
        draw_focus_arrows(rect)

    return rect, hover

def draw_menu():
    global start_btn_rect, settings_panel_rect
    screen.fill(BG_COLOUR)

    settings_btn_size = 64
    settings_btn_x = 60
    settings_btn_y = 60
    settings_rect = draw_settings_button(settings_btn_x, settings_btn_y, settings_btn_size, settings_menu_open)

    title = "GSSZO Darts Counter"
    title_surf = font_title.render(title, True, TEXT_COLOUR)
    title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 330))
    screen.blit(title_surf, title_rect)

    col_x = WIDTH // 2 - 380
    col_w = 760
    box_h = 70
    gap_y = 105
    y0 = HEIGHT // 2 - 250

    p1_rect = draw_input_box(col_x, y0 + 0*gap_y, col_w, box_h,
                             "Player 1 name", menu_values["p1"], active_input_key == "p1")
    p2_rect = draw_input_box(col_x, y0 + 1*gap_y, col_w, box_h,
                             "Player 2 name", menu_values["p2"], active_input_key == "p2")

    score_outer, score_301, score_501 = draw_score_switch(
        col_x, y0 + 2*gap_y, col_w, box_h,
        active=(active_input_key == "score"),
        selected=menu_values["score"] if menu_values["score"] in ("301", "501") else "301"
    )

    legs_rect = draw_input_box(
        col_x, y0 + 3*gap_y, col_w, box_h,
        "Legs to win", menu_values["legs"], active_input_key == "legs"
    )

    dob_rect = draw_checkbox(
        col_x, y0 + 4*gap_y, col_w, box_h,
        "Double Out", bool(menu_values["doubleout"]), active_input_key == "doubleout"
    )

    start_btn_rect, _ = draw_button(
        col_x, y0 + 5*gap_y, col_w, box_h + 10,
        "Start",
        focused=(active_input_key == "start")
    )

    showsponsors_rect = None
    darkmode_rect = None
    fullscreen_rect = None
    settings_panel_rect = None
    if settings_menu_open:
        panel_padding = 20
        panel_w = 200
        checkbox_gap = 36
        panel_h = panel_padding * 2 + 26 + box_h * 3 + checkbox_gap * 2
        panel_x = settings_btn_x
        panel_y = settings_btn_y + settings_btn_size + 20
        settings_panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(screen, BOX_BG, settings_panel_rect, border_radius=12)
        pygame.draw.rect(screen, BOX_BORDER_ACTIVE, settings_panel_rect, 2, border_radius=12)

        checkbox_y = panel_y + panel_padding + 26
        fullscreen_rect = draw_checkbox(
            panel_x + panel_padding,
            checkbox_y,
            panel_w - panel_padding * 2,
            box_h,
            "Fullscreen",
            bool(menu_values["fullscreen"]),
            False,
        )
        checkbox_y += box_h + checkbox_gap
        darkmode_rect = draw_checkbox(
            panel_x + panel_padding,
            checkbox_y,
            panel_w - panel_padding * 2,
            box_h,
            "Dark mode",
            bool(menu_values["darkmode"]),
            False,
        )
        checkbox_y += box_h + checkbox_gap
        showsponsors_rect = draw_checkbox(
            panel_x + panel_padding,
            checkbox_y,
            panel_w - panel_padding * 2,
            box_h,
            "Show sponsors",
            bool(menu_values["showsponsors"]),
            False,
        )

    pygame.display.flip()
    return {
        "p1": p1_rect,
        "p2": p2_rect,
        "score_outer": score_outer,
        "score_301": score_301,
        "score_501": score_501,
        "legs": legs_rect,
        "doubleout": dob_rect,
        "settings": settings_rect,
        "showsponsors": showsponsors_rect,
        "darkmode": darkmode_rect,
        "fullscreen": fullscreen_rect,
        "start": start_btn_rect,
    }

def menu_toggle_score():
    menu_values["score"] = "501" if menu_values["score"] == "301" else "301"

def menu_start_now():
    global settings_menu_open
    legs_txt = ''.join(ch for ch in menu_values["legs"] if ch.isdigit()) or "2"
    apply_display_mode(bool(menu_values["fullscreen"]))
    reset_game(
        int(menu_values["score"]),
        menu_values["p1"],
        menu_values["p2"],
        int(legs_txt),
        bool(menu_values["doubleout"]),
        bool(menu_values["showsponsors"])
    )
    settings_menu_open = False
    return True

def handle_menu_event(event, input_rects):
    global active_input_key, state, settings_menu_open, settings_panel_rect

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        settings_rect = input_rects.get("settings")
        if settings_rect and settings_rect.collidepoint(event.pos):
            settings_menu_open = not settings_menu_open
            return
        if settings_menu_open and settings_panel_rect and not settings_panel_rect.collidepoint(event.pos):
            settings_menu_open = False
            # continue handling click for other controls after closing
        if input_rects["p1"].collidepoint(event.pos):
            active_input_key = "p1"; return
        if input_rects["p2"].collidepoint(event.pos):
            active_input_key = "p2"; return
        if input_rects["score_outer"].collidepoint(event.pos):
            active_input_key = "score"
            if input_rects["score_301"].collidepoint(event.pos):
                menu_values["score"] = "301"
            elif input_rects["score_501"].collidepoint(event.pos):
                menu_values["score"] = "501"
            return
        if input_rects["legs"].collidepoint(event.pos):
            active_input_key = "legs"; return
        if input_rects["doubleout"].collidepoint(event.pos):
            active_input_key = "doubleout"
            menu_values["doubleout"] = not bool(menu_values["doubleout"])
            return
        fullscreen_rect = input_rects.get("fullscreen")
        if settings_menu_open and fullscreen_rect and fullscreen_rect.collidepoint(event.pos):
            menu_values["fullscreen"] = not bool(menu_values["fullscreen"])
            apply_display_mode(bool(menu_values["fullscreen"]))
            return
        darkmode_rect = input_rects.get("darkmode")
        if settings_menu_open and darkmode_rect and darkmode_rect.collidepoint(event.pos):
            menu_values["darkmode"] = not bool(menu_values["darkmode"])
            apply_theme(bool(menu_values["darkmode"]))
            return
        showsponsors_rect = input_rects.get("showsponsors")
        if settings_menu_open and showsponsors_rect and showsponsors_rect.collidepoint(event.pos):
            menu_values["showsponsors"] = not bool(menu_values["showsponsors"])
            return
        if input_rects["start"].collidepoint(event.pos):
            active_input_key = "start"
            if menu_start_now():
                state = STATE_GAME
            return

    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            if settings_menu_open:
                settings_menu_open = False
                return
            pygame.quit(); sys.exit()
        if event.key == pygame.K_TAB:
            order = ["p1", "p2", "score", "legs", "doubleout", "start"]
            idx = order.index(active_input_key)
            active_input_key = order[(idx + 1) % len(order)]
            return

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if active_input_key == "score":
                menu_toggle_score(); return
            if active_input_key == "start":
                if menu_start_now():
                    state = STATE_GAME
                return
            if active_input_key == "doubleout":
                menu_values["doubleout"] = not bool(menu_values["doubleout"])
                return
            return

        if active_input_key in ("p1", "p2"):
            if event.key == pygame.K_BACKSPACE:
                menu_values[active_input_key] = menu_values[active_input_key][:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    menu_values[active_input_key] += event.unicode
        elif active_input_key == "score" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            menu_toggle_score(); return
        elif active_input_key == "legs":
            if event.key == pygame.K_BACKSPACE:
                menu_values["legs"] = menu_values["legs"][:-1]
            else:
                if event.unicode and event.unicode.isdigit() and len(menu_values["legs"]) < 3:
                    menu_values["legs"] += event.unicode
        elif active_input_key == "doubleout" and event.key == pygame.K_SPACE:
            menu_values["doubleout"] = not bool(menu_values["doubleout"]); return

def draw_focus_arrows(rect: pygame.Rect):
    """Draw < and > around an actively selected menu element."""
    left_arrow_surf = font_big.render(">", True, ACCENT_ACTIVE)
    right_arrow_surf = font_big.render("<", True, ACCENT_ACTIVE)

    left_arrow_rect = left_arrow_surf.get_rect(
        midright=(rect.left - 10, rect.centery - 5)
    )
    right_arrow_rect = right_arrow_surf.get_rect(
        midleft=(rect.right + 10, rect.centery - 5)
    )

    screen.blit(left_arrow_surf, left_arrow_rect)
    screen.blit(right_arrow_surf, right_arrow_rect)


# region GAME RENDERING & EVENTS

def draw_player_section(player_idx, x_start, width, is_active, leg_avg_val, match_avg_val):
    title = player_names[player_idx]
    title_colour = ACCENT_ACTIVE if is_active else ACCENT_INACTIVE
    title_top_center = (x_start + width // 2, 50)  # adjust 50 up/down if needed

    draw_player_name_multiline(
        screen,
        font_big,          # same font you used before
        title,
        title_colour,
        title_top_center,
    )

    # --- Static stats placement on each side of the screen ---
    is_left = (player_idx == 0)
    stats_margin_x = 40
    stats_top_y = 30

    # Badge geometry (same style for Legs / Leg avg / Match avg)
    badge_w, badge_h = 200, 56
    badge_gap_y = 8

    if is_left:
        badge_x = x_start + stats_margin_x
    else:
        badge_x = x_start + width - stats_margin_x - badge_w

    # ----- Legs Won badge -----
    legs_rect = pygame.Rect(badge_x, stats_top_y, badge_w, badge_h)
    pygame.draw.rect(screen, BOX_BG, legs_rect, border_radius=12)
    pygame.draw.rect(screen, BOX_BORDER, legs_rect, 2, border_radius=12)
    legs_text_surf = font_small.render(f"Legs Won: {legs_won[player_idx]}", True, TEXT_COLOUR)
    screen.blit(legs_text_surf, legs_text_surf.get_rect(center=legs_rect.center))

    # ----- Leg average badge -----
    leg_avg_rect = pygame.Rect(badge_x, legs_rect.bottom + badge_gap_y, badge_w, badge_h)
    pygame.draw.rect(screen, BOX_BG, leg_avg_rect, border_radius=12)
    pygame.draw.rect(screen, BOX_BORDER, leg_avg_rect, 2, border_radius=12)
    leg_avg_text_surf = font_small.render(f"Leg avg: {leg_avg_val:.1f}", True, TEXT_COLOUR)
    screen.blit(leg_avg_text_surf, leg_avg_text_surf.get_rect(center=leg_avg_rect.center))

    # ----- Match average badge -----
    match_avg_rect = pygame.Rect(badge_x, leg_avg_rect.bottom + badge_gap_y, badge_w, badge_h)
    pygame.draw.rect(screen, BOX_BG, match_avg_rect, border_radius=12)
    pygame.draw.rect(screen, BOX_BORDER, match_avg_rect, 2, border_radius=12)
    match_avg_text_surf = font_small.render(f"Match avg: {match_avg_val:.1f}", True, TEXT_COLOUR)
    screen.blit(match_avg_text_surf, match_avg_text_surf.get_rect(center=match_avg_rect.center))

    # ----- Remaining score -----
    total_scored = sum(scores[player_idx])
    remaining = START_SCORE - total_scored

    # Place "Remaining" below the badges so nothing overlaps
    rem_label_y = match_avg_rect.bottom + 40
    rem_label_surf = font_med.render("Remaining:", True, TEXT_COLOUR)
    rem_label_rect = rem_label_surf.get_rect(center=(x_start + width // 2, rem_label_y))
    screen.blit(rem_label_surf, rem_label_rect)

    rem_surf = font_huge.render(str(remaining), True, title_colour)
    rem_rect = rem_surf.get_rect(center=(x_start + width // 2, rem_label_y + 80))
    screen.blit(rem_surf, rem_rect)

    # Decide horizontal divider Y: below remaining number, above input label
    pad_below_remaining = 8

    # ----- Current input (only for active player) -----
    input_label_y = rem_rect.bottom + 40
    if is_active:
        input_label = font_small.render("Current input:", True, TEXT_COLOUR)
        screen.blit(input_label, (x_start + 40, input_label_y))

        input_text = current_input if current_input != "" else "-"
        input_surf = font_big.render(input_text, True, ACCENT_ACTIVE)
        screen.blit(input_surf, (x_start + 40, input_label_y + 30))

    # ----- Rounds list -----
    rounds_label_y = input_label_y + 80
    rounds_label = font_small.render("Rounds:", True, TEXT_COLOUR)
    screen.blit(rounds_label, (x_start + 40, rounds_label_y))

    # Table header
    header_y = rounds_label_y + 30
    col_round_x = x_start + 40
    col_score_x = x_start + 140
    col_rem_x   = x_start + 320

    header_hash  = font_round.render("#", True, TEXT_COLOUR)
    header_score = font_round.render("Score", True, TEXT_COLOUR)
    header_rem   = font_round.render("Remaining", True, TEXT_COLOUR)

    screen.blit(header_hash,  (col_round_x, header_y))
    screen.blit(header_score, (col_score_x, header_y))
    screen.blit(header_rem,   (col_rem_x,   header_y))

    start_y = header_y + 36
    line_height = 36  # bigger spacing for the larger font
    max_lines = max(1, (HEIGHT - start_y - 60) // line_height)

    player_scores = scores[player_idx]

    # Precompute remaining after each throw in this leg
    remaining_list = []
    rem_tmp = START_SCORE
    for s in player_scores:
        rem_tmp -= s
        remaining_list.append(rem_tmp)

    # Only show the last max_lines throws
    visible_scores     = player_scores[-max_lines:]
    visible_remaining  = remaining_list[-max_lines:]
    start_round_index  = len(player_scores) - len(visible_scores) + 1

    y = start_y + 10
    for i, (s, rem_after) in enumerate(zip(visible_scores, visible_remaining)):
        round_num = start_round_index + i

        # Limit display to max 3 digits and right-align in a 3-char field
        score_val = min(s, 999)
        rem_val   = min(rem_after, 999)

        round_text = f"{round_num}."
        score_text = f"{score_val:>3}"
        rem_text   = f"{rem_val:>3}"

        round_surf = font_round.render(round_text, True, TEXT_COLOUR)
        score_surf = font_round.render(score_text, True, TEXT_COLOUR)
        rem_surf   = font_round.render(rem_text,   True, TEXT_COLOUR)

        screen.blit(round_surf, (col_round_x, y))
        screen.blit(score_surf, (col_score_x + 10, y))
        screen.blit(rem_surf,   (col_rem_x + 40,   y))

        y += line_height

    # Horizontal divider should sit just under the remaining score, but above the input label
    hline_y = min(rem_rect.bottom + pad_below_remaining, input_label_y - 8)
    return hline_y

def draw_player_name_multiline(surface, font, text, colour, top_center_pos):
    """
    Draw the player name in up to 3 lines with a fixed top.

    Rules:
    - Max total length of the name: 45 characters (extra is truncated).
    - Wrap only at spaces.
    - Start a new line if adding the next word would make the line > 15 characters.
    - Lines stack downward from a fixed top y.
    """
    if not text:
        return

    # Enforce max total length
    text = text[:45]

    # Split into words (collapses multiple spaces)
    words = text.split()
    if not words:
        return

    # Build lines with max 15 characters per line (wrapping at spaces)
    lines = []
    current_line = words[0]

    for word in words[1:]:
        # +1 for the space
        if len(current_line) + 1 + len(word) <= 15:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)

    # Draw lines with fixed top
    cx, top_y = top_center_pos
    line_gap = 4  # pixels between lines
    y = top_y

    for line in lines:
        surf = font.render(line, True, colour)
        rect = surf.get_rect(midtop=(cx, y))
        surface.blit(surf, rect)
        y = rect.bottom + line_gap

# ---- Logo drawing with 20 px gaps above and below ----
def draw_logo_layers(max_bottom_y: int, angle_deg: float):
    """
    Draw the centered logo at the top as a circle with:
      - top at LOGO_TOP_GAP
      - bottom at max_bottom_y - LOGO_BOTTOM_GAP
    The outer ring rotates by angle_deg, the inner stays fixed.
    Falls back to a single static image if two-piece assets are missing.
    """
    # Compute available diameter from vertical gap and side margin
    available_h = max_bottom_y - LOGO_TOP_GAP - LOGO_BOTTOM_GAP
    if available_h <= 1:
        return

    max_w = max(1, WIDTH - 2 * LOGO_SIDE_MARGIN)
    diameter = int(max(1, min(available_h, max_w)))
    cx = WIDTH // 2
    cy = LOGO_TOP_GAP + diameter // 2

    # Scale both layers to the target diameter once per frame
    inner_scaled = pygame.transform.smoothscale(LOGO_INNER_ORIG, (diameter, diameter))
    ring_scaled  = pygame.transform.smoothscale(LOGO_RING_ORIG,  (diameter, diameter))

    # Rotate the ring around its center.
    # Note: rotozoom enlarges the bounding rectangle due to rotation, so we center it on (cx, cy)
    ring_rot = pygame.transform.rotozoom(ring_scaled, angle_deg, 1.0)

    # Blit order: inner first, then the rotating ring on top
    screen.blit(inner_scaled, inner_scaled.get_rect(center=(cx, cy)))
    screen.blit(ring_rot,     ring_rot.get_rect(center=(cx, cy)))
    return

def draw_game():
    screen.fill(BG_COLOUR)

    # Compute averages
    leg_avg_vals = [avg(scores[0]), avg(scores[1])]
    match_avg_vals = match_averages()

    half_width = WIDTH // 2

    # Draw both sides first and get their suggested horizontal line Y
    left_hy  = draw_player_section(0, 0, half_width,  active_player == 0, leg_avg_vals[0], match_avg_vals[0])
    right_hy = draw_player_section(1, half_width, half_width, active_player == 1, leg_avg_vals[1], match_avg_vals[1])

    # Use the lower (max) so the line is surely under both "Remaining" numbers
    hline_y = max(left_hy, right_hy)

    # Draw layered logo with rotation, honoring the 20 px gaps
    draw_logo_layers(hline_y, LOGO_ANGLE)

    bar_top_y = HEIGHT
    if sponsor_bar_enabled:
        target_height = max(40, int(SPONSOR_BAR_HEIGHT))
        if sponsor_ticker.height != target_height:
            sponsor_ticker.reload()
        sponsor_ticker.update(frame_dt)
        bar_top_y = HEIGHT - sponsor_ticker.height
        sponsor_ticker.draw(screen, bar_top_y)

    # Center vertical line from the top of the sponsor bar (or bottom of screen) up to the horizontal divider
    pygame.draw.line(screen, DIVIDER_COLOUR, (half_width, bar_top_y), (half_width, hline_y), 3)

    # Horizontal divider across the screen
    pygame.draw.line(screen, DIVIDER_COLOUR, (0, hline_y), (WIDTH, hline_y), 3)

    pygame.display.flip()

def commit_throw():
    """Apply current_input for active player with 'bust', Double Out, and leg/match win logic."""
    global current_input, scores, active_player, history, state, winner_idx, legs_won

    # Treat empty input as a 0 score
    if current_input == "":
        value = 0
    else:
        try:
            value = int(current_input)
        except ValueError:
            value = 0

    # Cap any recorded value at 180
    if value > 180:
        value = 180

    remaining_before = START_SCORE - sum(scores[active_player])
    remaining_after = remaining_before - value

    # Double Out rule — cannot leave 1
    if DOUBLE_OUT_ENABLED and remaining_after == 1:
        scores[active_player].append(0)   # bust recorded as 0
        history.append((active_player, 0))
        current_input = ""
        active_player = 1 - active_player
        return

    # Bust: over-scoring
    if value > remaining_before:
        scores[active_player].append(0)
        history.append((active_player, 0))
        current_input = ""
        active_player = 1 - active_player
        return

    # Valid throw (<= remaining, and not leaving 1 under double-out)
    scores[active_player].append(value)
    history.append((active_player, value))
    current_input = ""

    if value == remaining_before:
        # Leg won
        legs_won[active_player] += 1

        # Match finished?
        if legs_won[active_player] >= LEGS_TO_WIN:
            winner_idx = active_player
            state = STATE_END
            return

        # Save snapshot of finished leg BEFORE starting new leg
        finished_legs_stack.append({
            'scores': copy.deepcopy(scores),
            'history': history[:],
            'active_player': active_player,
            'leg_starter_idx': leg_starter_idx,
            'winner': active_player
        })

        # Start a new leg (alternate starter)
        start_new_leg()
        return

    # Otherwise continue, switch to other player
    active_player = 1 - active_player

def undo_last_score():
    """Remove the most recent recorded score and restore turn to that player. Returns (player,score) or (None,None)."""
    global history, scores, active_player
    if not history:
        return (None, None)
    last_player, last_score = history.pop()
    if scores[last_player] and scores[last_player][-1] == last_score:
        scores[last_player].pop()
    else:
        try:
            idx = len(scores[last_player]) - 1 - scores[last_player][::-1].index(last_score)
            scores[last_player].pop(idx)
        except ValueError:
            pass
    active_player = last_player
    return (last_player, last_score)

def handle_game_keydown(event):
    global current_input, state, menu_values, active_player, leg_starter_idx

    if event.key == pygame.K_m:
        menu_values["p1"] = player_names[0]
        menu_values["p2"] = player_names[1]
        menu_values["score"] = str(START_SCORE) if START_SCORE in (301, 501) else "301"
        menu_values["legs"] = str(LEGS_TO_WIN)
        menu_values["doubleout"] = DOUBLE_OUT_ENABLED
        menu_values["showsponsors"] = sponsor_bar_enabled
        menu_values["fullscreen"] = current_fullscreen
        state = STATE_MENU
        return

    if event.key == pygame.K_ESCAPE:
        pygame.quit(); sys.exit()

    # Choose starter ONLY for the very first leg, before any input/throws
    if event.key == pygame.K_TAB:
        if current_leg_number() == 1 and is_leg_pristine():
            active_player = 1 - active_player
            leg_starter_idx = active_player
        return

    if pygame.K_0 <= event.key <= pygame.K_9:
        digit = event.key - pygame.K_0
        if len(current_input) < 3:
            if current_input == "0":
                current_input = str(digit)
            else:
                current_input += str(digit)
            # Clamp the typed value to 180 so UI never shows >180
            try:
                if int(current_input) > 180:
                    current_input = "180"
            except ValueError:
                current_input = ""
    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        # Enter commits; empty input is treated as 0
        commit_throw()
    elif event.key == pygame.K_BACKSPACE:
        if current_input != "":
            current_input = current_input[:-1]
        else:
            # If we're at the very start of a new leg, allow cross-leg undo
            if is_leg_pristine() and finished_legs_stack:
                revert_last_finished_leg()
            else:
                undo_last_score()

# region END SCREEN

def draw_end():
    screen.fill(BG_COLOUR)

    title = "Match Over"
    t_surf = font_title.render(title, True, TEXT_COLOUR)
    t_rect = t_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 200))
    screen.blit(t_surf, t_rect)

    if winner_idx is not None:
        win_text = f"Winner: {player_names[winner_idx]}"
        win_surf = font_huge.render(win_text, True, ACCENT_ACTIVE)
        win_rect = win_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
        screen.blit(win_surf, win_rect)

    player_line = f"{player_names[0]} vs. {player_names[1]}"
    player_surf = font_med.render(player_line, True, TEXT_COLOUR)
    player_rect = player_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
    screen.blit(player_surf, player_rect)

    legs_line = f"Legs won:  {legs_won[0]}   |   {legs_won[1]}"
    legs_surf = font_small.render(legs_line, True, HINT_COLOUR)
    legs_rect = legs_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
    screen.blit(legs_surf, legs_rect)

    # Informational: remaining scores in the finishing leg snapshot
    rem0 = START_SCORE - sum(scores[0])
    rem1 = START_SCORE - sum(scores[1])
    rem_line = f"Remaining:  {rem0}    |    {rem1}"
    rem_surf = font_small.render(rem_line, True, HINT_COLOUR)
    rem_rect = rem_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
    screen.blit(rem_surf, rem_rect)

    pygame.display.flip()

def handle_end_event(event):
    global state, winner_idx, current_input, menu_values, legs_won
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()
        if event.key == pygame.K_m:
            menu_values["p1"] = player_names[0]
            menu_values["p2"] = player_names[1]
            menu_values["score"] = str(START_SCORE) if START_SCORE in (301, 501) else "301"
            menu_values["legs"] = str(LEGS_TO_WIN)
            menu_values["doubleout"] = DOUBLE_OUT_ENABLED
            menu_values["showsponsors"] = sponsor_bar_enabled
            state = STATE_MENU
            return
        if event.key == pygame.K_BACKSPACE:
            # Undo the winning throw and resume the final leg
            last_player, _ = undo_last_score()
            if last_player is not None:
                legs_won[last_player] = max(0, legs_won[last_player] - 1)
            winner_idx = None
            current_input = ""
            state = STATE_GAME
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            reset_game(START_SCORE, player_names[0], player_names[1], LEGS_TO_WIN, DOUBLE_OUT_ENABLED, sponsor_bar_enabled)
            return

# region MAIN LOOP

def main():
    global state, active_input_key

    while True:
        if state == STATE_MENU:
            rects = draw_menu()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                handle_window_resize(event)
                handle_menu_event(event, rects)

        elif state == STATE_GAME:
            # Update rotation angle based on elapsed time since last tick
            dt = clock.get_time() / 1000  # seconds
            global LOGO_ANGLE, frame_dt
            frame_dt = dt
            rot_dir = 1 if active_player == 0 else -1
            LOGO_ANGLE = (LOGO_ANGLE + rot_dir * LOGO_ROT_SPEED_DEG * dt) % 360.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                handle_window_resize(event)
                if event.type == pygame.KEYDOWN:
                    handle_game_keydown(event)

            draw_game()

        elif state == STATE_END:
            draw_end()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                handle_window_resize(event)
                handle_end_event(event)

        clock.tick(60)

if __name__ == "__main__":
    main()
