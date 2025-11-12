import pygame
import sys
import copy  # for leg snapshots

pygame.init()

# ---- DEFAULTS (overridden by menu) ----
START_SCORE = 301
player_names = ["Player 1", "Player 2"]

# Get current display resolution and use fullscreen
display_info = pygame.display.Info()
WIDTH, HEIGHT = display_info.current_w, display_info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption(f"Darts Counter - 2 Players ({START_SCORE})")

# Colors
BG_COLOR = (20, 20, 20)
TEXT_COLOR = (230, 230, 230)
HINT_COLOR = (160, 160, 160)
ACCENT_ACTIVE = (100, 220, 100)
ACCENT_INACTIVE = (100, 100, 100)
DIVIDER_COLOR = (80, 80, 80)
BOX_BG = (35, 35, 35)
BOX_BORDER = (90, 90, 90)
BOX_BORDER_ACTIVE = (160, 160, 160)
BTN_BG = (60, 60, 60)
BTN_BG_HOVER = (80, 80, 80)

# Fonts
font_title = pygame.font.SysFont(None, 100)
font_huge  = pygame.font.SysFont(None, 110)
font_big   = pygame.font.SysFont(None, 72)
font_med   = pygame.font.SysFont(None, 46)
font_small = pygame.font.SysFont(None, 30)
font_round = pygame.font.SysFont(None, 36)

clock = pygame.time.Clock()

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
    "doubleout": True
}
active_input_key = "p1"    # "p1" | "p2" | "score" | "legs" | "doubleout" | "start"
start_btn_rect = None      # set in draw_menu()
doubleout_rect = None      # set in draw_menu()

# ---------------- UTILITIES ----------------

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

# ---------------- MATCH CONTROL ----------------

def reset_game(new_start_score: int, p1: str, p2: str, target_legs: int = None, double_out: bool = True):
    """Reset the WHOLE match (new game from menu)."""
    global START_SCORE, player_names, scores, active_player, history
    global winner_idx, legs_won, leg_starter_idx, LEGS_TO_WIN, state, current_input
    global finished_legs_stack, DOUBLE_OUT_ENABLED

    START_SCORE = new_start_score
    player_names = [p1.strip() or "Player 1", p2.strip() or "Player 2"]

    LEGS_TO_WIN = max(1, int(target_legs) if target_legs is not None else LEGS_TO_WIN)
    legs_won = [0, 0]
    finished_legs_stack = []  # clear snapshots
    DOUBLE_OUT_ENABLED = bool(double_out)

    # First leg setup
    leg_starter_idx = 0
    active_player = leg_starter_idx
    scores = [[], []]
    history = []
    current_input = ""
    winner_idx = None

    state = STATE_GAME
    pygame.display.set_caption(f"Darts Counter - 2 Players ({START_SCORE})")

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

# ---------------- MENU RENDERING & EVENTS ----------------

def draw_input_box(x, y, w, h, label, value, active=False):
    label_surf = font_small.render(label, True, HINT_COLOR)
    screen.blit(label_surf, (x, y - 26))
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, BOX_BG, rect, border_radius=10)
    pygame.draw.rect(screen, BOX_BORDER_ACTIVE if active else BOX_BORDER, rect, 2, border_radius=10)
    text_surf = font_med.render(value, True, TEXT_COLOR)
    text_rect = text_surf.get_rect(midleft=(x + 14, y + h // 2))
    screen.blit(text_surf, text_rect)
    return rect

def draw_score_switch(x, y, w, h, active: bool, selected: str):
    label_surf = font_small.render("Starting score", True, HINT_COLOR)
    screen.blit(label_surf, (x, y - 26))

    outer = pygame.Rect(x, y, w, h)
    half_w = w // 2
    r301 = pygame.Rect(x, y, half_w, h)
    r501 = pygame.Rect(x + half_w, y, w - half_w, h)

    pygame.draw.rect(screen, BOX_BG, outer, border_radius=10)

    if selected == "301":
        pygame.draw.rect(screen, ACCENT_ACTIVE, r301, border_radius=10)
    else:
        pygame.draw.rect(screen, ACCENT_ACTIVE, r501, border_radius=10)

    pygame.draw.line(screen, BOX_BORDER, (outer.x + half_w, outer.y + 6), (outer.x + half_w, outer.y + h - 6), 2)
    pygame.draw.rect(screen, BOX_BORDER_ACTIVE if active else BOX_BORDER, outer, 2, border_radius=10)

    t301 = font_med.render("301", True, TEXT_COLOR)
    t501 = font_med.render("501", True, TEXT_COLOR)
    screen.blit(t301, t301.get_rect(center=r301.center))
    screen.blit(t501, t501.get_rect(center=r501.center))

    return outer, r301, r501

def draw_checkbox(x, y, w, h, label, checked: bool, active: bool):
    """Simple labeled checkbox-style toggle."""
    global doubleout_rect
    label_surf = font_small.render(label, True, HINT_COLOR)
    screen.blit(label_surf, (x, y - 26))

    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, BOX_BG, rect, border_radius=10)
    pygame.draw.rect(screen, BOX_BORDER_ACTIVE if active else BOX_BORDER, rect, 2, border_radius=10)

    pad = 8
    inner = pygame.Rect(x + pad, y + pad, h - 2*pad, h - 2*pad)
    pygame.draw.rect(screen, BTN_BG, inner, border_radius=8)
    if checked:
        pygame.draw.rect(screen, ACCENT_ACTIVE, inner, border_radius=8)

    txt = "ON" if checked else "OFF"
    txt_surf = font_med.render(f"{txt}", True, TEXT_COLOR)
    txt_rect = txt_surf.get_rect(midleft=(inner.right + 16, y + h // 2))
    screen.blit(txt_surf, txt_rect)

    doubleout_rect = rect
    return rect

def draw_button(x, y, w, h, label, focused=False):
    mouse_pos = pygame.mouse.get_pos()
    rect = pygame.Rect(x, y, w, h)
    hover = rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, BTN_BG_HOVER if hover else BTN_BG, rect, border_radius=12)
    pygame.draw.rect(screen, BOX_BORDER_ACTIVE if focused else BOX_BORDER, rect, 3 if focused else 2, border_radius=12)
    txt = font_big.render(label, True, TEXT_COLOR)
    txt_rect = txt.get_rect(center=rect.center)
    screen.blit(txt, txt_rect)
    return rect, hover

def draw_menu():
    global start_btn_rect
    screen.fill(BG_COLOR)

    title = "Darts Counter – Setup"
    title_surf = font_title.render(title, True, TEXT_COLOR)
    title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 330))
    screen.blit(title_surf, title_rect)

    col_x = WIDTH // 2 - 380
    col_w = 760
    box_h = 70
    gap_y = 95
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
        "Legs to win (number)", menu_values["legs"], active_input_key == "legs"
    )

    dob_rect = draw_checkbox(
        col_x, y0 + 4*gap_y, col_w, box_h,
        "Double Out", bool(menu_values["doubleout"]), active_input_key == "doubleout"
    )

    start_btn_rect, _ = draw_button(
        col_x, y0 + 5*gap_y + 10, col_w, box_h + 10,
        "Start",
        focused=(active_input_key == "start")
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
        "start": start_btn_rect,
    }

def menu_toggle_score():
    menu_values["score"] = "501" if menu_values["score"] == "301" else "301"

def menu_start_now():
    legs_txt = ''.join(ch for ch in menu_values["legs"] if ch.isdigit()) or "2"
    reset_game(
        int(menu_values["score"]),
        menu_values["p1"],
        menu_values["p2"],
        int(legs_txt),
        bool(menu_values["doubleout"])
    )
    return True

def handle_menu_event(event, input_rects):
    global active_input_key, state

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
        if input_rects["start"].collidepoint(event.pos):
            active_input_key = "start"
            if menu_start_now():
                state = STATE_GAME
            return

    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
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

# ---------------- GAME RENDERING & EVENTS ----------------

def draw_stat_badge(text, anchor_rect, side: str):
    """Draw a small 'Legs Won' badge next to the name. side='left' or 'right' relative to name rect."""
    badge_w, badge_h = 200, 56
    pad = 16
    if side == "left":
        rect = pygame.Rect(anchor_rect.left - pad - badge_w, anchor_rect.centery - badge_h//2, badge_w, badge_h)
    else:
        rect = pygame.Rect(anchor_rect.right + pad, anchor_rect.centery - badge_h//2, badge_w, badge_h)
    pygame.draw.rect(screen, BOX_BG, rect, border_radius=12)
    pygame.draw.rect(screen, BOX_BORDER, rect, 2, border_radius=12)
    txt = font_small.render(text, True, TEXT_COLOR)
    screen.blit(txt, txt.get_rect(center=rect.center))
    return rect

def draw_player_section(player_idx, x_start, width, is_active, leg_avg_val, match_avg_val):
    title = player_names[player_idx]
    title_color = ACCENT_ACTIVE if is_active else ACCENT_INACTIVE
    title_surf = font_big.render(title, True, title_color)
    title_rect = title_surf.get_rect(center=(x_start + width // 2, 70))
    screen.blit(title_surf, title_rect)

    # Legs badge next to name (left player -> badge on left; right player -> on right)
    side = "left" if player_idx == 0 else "right"
    legs_text = f"Legs Won: {legs_won[player_idx]}"
    legs_badge_rect = draw_stat_badge(legs_text, title_rect, side)

    # Averages under the badge
    avg_leg_surf = font_small.render(f"Leg avg: {leg_avg_val:.1f}", True, HINT_COLOR)
    avg_leg_rect = avg_leg_surf.get_rect(midtop=(legs_badge_rect.centerx, legs_badge_rect.bottom + 8))
    screen.blit(avg_leg_surf, avg_leg_rect)

    avg_match_surf = font_small.render(f"Match avg: {match_avg_val:.1f}", True, HINT_COLOR)
    avg_match_rect = avg_match_surf.get_rect(midtop=(legs_badge_rect.centerx, avg_leg_rect.bottom + 6))
    screen.blit(avg_match_surf, avg_match_rect)

    total_scored = sum(scores[player_idx])
    remaining = START_SCORE - total_scored

    rem_label_surf = font_med.render("Remaining:", True, TEXT_COLOR)
    rem_label_rect = rem_label_surf.get_rect(center=(x_start + width // 2, 150))
    screen.blit(rem_label_surf, rem_label_rect)

    rem_surf = font_huge.render(str(remaining), True, TEXT_COLOR)
    rem_rect = rem_surf.get_rect(center=(x_start + width // 2, 230))
    screen.blit(rem_surf, rem_rect)

    # Decide horizontal divider Y: below remaining number, above input label
    input_label_y = 290               # where "Current input:" is drawn
    pad_below_remaining = 8
    # keep a little gap to the input label
    hline_y = min(rem_rect.bottom + pad_below_remaining, input_label_y - 8)

    if is_active:
        input_label = font_small.render("Current input:", True, TEXT_COLOR)
        screen.blit(input_label, (x_start + 40, input_label_y))
        input_text = current_input if current_input != "" else "-"
        input_surf = font_big.render(input_text, True, TEXT_COLOR)
        screen.blit(input_surf, (x_start + 40, 320))

    rounds_label = font_small.render("Rounds (last at bottom):", True, TEXT_COLOR)
    screen.blit(rounds_label, (x_start + 40, 380))

    start_y = 410
    line_height = 38
    max_lines = max(1, (HEIGHT - start_y - 60) // line_height)

    player_scores = scores[player_idx]
    visible_scores = player_scores[-max_lines:]
    start_round_index = len(player_scores) - len(visible_scores) + 1

    y = start_y
    for i, s in enumerate(visible_scores):
        round_num = start_round_index + i
        round_text = f"{round_num}.  {s}"
        round_surf = font_round.render(round_text, True, TEXT_COLOR)
        screen.blit(round_surf, (x_start + 40, y))
        y += line_height

    # Return the computed horizontal divider Y for this side
    return hline_y

def draw_game():
    screen.fill(BG_COLOR)

    # Compute averages
    leg_avg_vals = [avg(scores[0]), avg(scores[1])]
    match_avg_vals = match_averages()

    half_width = WIDTH // 2

    # Draw both sides first and get their suggested horizontal line Y
    left_hy  = draw_player_section(0, 0, half_width,  active_player == 0, leg_avg_vals[0], match_avg_vals[0])
    right_hy = draw_player_section(1, half_width, half_width, active_player == 1, leg_avg_vals[1], match_avg_vals[1])

    # Use the lower (max) so the line is surely under both "Remaining" numbers
    hline_y = max(left_hy, right_hy)

    # Center vertical line from bottom up to the horizontal divider
    pygame.draw.line(screen, DIVIDER_COLOR, (half_width, HEIGHT), (half_width, hline_y), 3)

    # New horizontal divider across the screen
    pygame.draw.line(screen, DIVIDER_COLOR, (0, hline_y), (WIDTH, hline_y), 3)

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

# ---------------- END SCREEN ----------------

def draw_end():
    screen.fill(BG_COLOR)

    title = "Match Over"
    t_surf = font_title.render(title, True, TEXT_COLOR)
    t_rect = t_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 200))
    screen.blit(t_surf, t_rect)

    if winner_idx is not None:
        win_text = f"Winner: {player_names[winner_idx]}"
        win_surf = font_huge.render(win_text, True, ACCENT_ACTIVE)
        win_rect = win_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
        screen.blit(win_surf, win_rect)

    legs_line = f"Final Legs — {player_names[0]}: {legs_won[0]}   |   {player_names[1]}: {legs_won[1]}   (First to {LEGS_TO_WIN})   •   Double Out: {'ON' if DOUBLE_OUT_ENABLED else 'OFF'}"
    legs_surf = font_med.render(legs_line, True, TEXT_COLOR)
    legs_rect = legs_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
    screen.blit(legs_surf, legs_rect)

    # Informational: remaining scores in the finishing leg snapshot
    rem0 = START_SCORE - sum(scores[0])
    rem1 = START_SCORE - sum(scores[1])
    rem_line = f"{player_names[0]} remaining: {rem0}    |    {player_names[1]} remaining: {rem1}"
    rem_surf = font_small.render(rem_line, True, HINT_COLOR)
    rem_rect = rem_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
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
            reset_game(START_SCORE, player_names[0], player_names[1], LEGS_TO_WIN, DOUBLE_OUT_ENABLED)
            return

# ---------------- MAIN LOOP ----------------

def main():
    global state, active_input_key

    while True:
        if state == STATE_MENU:
            rects = draw_menu()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                handle_menu_event(event, rects)

        elif state == STATE_GAME:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN:
                    handle_game_keydown(event)
            draw_game()

        elif state == STATE_END:
            draw_end()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                handle_end_event(event)

        clock.tick(60)

if __name__ == "__main__":
    main()
