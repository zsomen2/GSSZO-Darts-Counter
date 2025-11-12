import pygame
import sys

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

current_input = ""         # current numeric input while throwing
scores = [[], []]          # per-player list of throws
active_player = 0          # 0 or 1
history = []               # list of (player_index, score) for undo
winner_idx = None          # set when someone reaches exactly 0

# ---- MENU STATE ----
menu_values = {
    "p1": player_names[0],
    "p2": player_names[1],
    "score": "301",  # "301" or "501"
}
active_input_key = "p1"    # "p1" | "p2" | "score" | "start"
start_btn_rect = None      # set in draw_menu()

def reset_game(new_start_score: int, p1: str, p2: str):
    """Reset everything for a fresh game using menu parameters."""
    global START_SCORE, player_names, scores, active_player, history, current_input, winner_idx, state
    START_SCORE = new_start_score
    player_names = [p1.strip() or "Player 1", p2.strip() or "Player 2"]
    scores = [[], []]
    active_player = 0
    history = []
    current_input = ""
    winner_idx = None
    state = STATE_GAME
    pygame.display.set_caption(f"Darts Counter - 2 Players ({START_SCORE})")

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
    title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 260))
    screen.blit(title_surf, title_rect)

    col_x = WIDTH // 2 - 380
    col_w = 760
    box_h = 70
    gap_y = 95

    p1_rect = draw_input_box(col_x, HEIGHT // 2 - 180, col_w, box_h,
                             "Player 1 name", menu_values["p1"], active_input_key == "p1")
    p2_rect = draw_input_box(col_x, HEIGHT // 2 - 180 + gap_y, col_w, box_h,
                             "Player 2 name", menu_values["p2"], active_input_key == "p2")

    score_outer, score_301, score_501 = draw_score_switch(
        col_x, HEIGHT // 2 - 180 + 2*gap_y, col_w, box_h,
        active=(active_input_key == "score"),
        selected=menu_values["score"] if menu_values["score"] in ("301", "501") else "301"
    )

    start_btn_rect, _ = draw_button(
        col_x, HEIGHT // 2 - 180 + 3*gap_y + 10, col_w, box_h + 10,
        "Start",
        focused=(active_input_key == "start")
    )

    hint_lines = [
        "TAB cycles: Player 1 → Player 2 → Score → Start.",
        "Enter toggles 301/501 when Score is focused.",
        "Enter on Start begins a new game. ESC quits. M returns here from game.",
    ]
    for i, t in enumerate(hint_lines):
        surf = font_small.render(t, True, HINT_COLOR)
        screen.blit(surf, (col_x, HEIGHT // 2 - 180 + 4*gap_y + 40 + i*26))

    pygame.display.flip()
    return {
        "p1": p1_rect,
        "p2": p2_rect,
        "score_outer": score_outer,
        "score_301": score_301,
        "score_501": score_501,
        "start": start_btn_rect,
    }

def menu_toggle_score():
    menu_values["score"] = "501" if menu_values["score"] == "301" else "301"

def menu_start_now():
    reset_game(int(menu_values["score"]), menu_values["p1"], menu_values["p2"])
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
        if input_rects["start"].collidepoint(event.pos):
            active_input_key = "start"
            if menu_start_now():
                state = STATE_GAME
            return

    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()
        if event.key == pygame.K_TAB:
            order = ["p1", "p2", "score", "start"]
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
            return

        if active_input_key in ("p1", "p2"):
            if event.key == pygame.K_BACKSPACE:
                menu_values[active_input_key] = menu_values[active_input_key][:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    menu_values[active_input_key] += event.unicode
        if active_input_key == "score" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            menu_toggle_score(); return

# ---------------- GAME RENDERING & EVENTS ----------------

def draw_player_section(player_idx, x_start, width, is_active):
    title = player_names[player_idx]
    title_color = ACCENT_ACTIVE if is_active else ACCENT_INACTIVE
    title_surf = font_big.render(title, True, title_color)
    title_rect = title_surf.get_rect(center=(x_start + width // 2, 70))
    screen.blit(title_surf, title_rect)

    total_scored = sum(scores[player_idx])
    remaining = START_SCORE - total_scored

    rem_label_surf = font_med.render("Remaining:", True, TEXT_COLOR)
    rem_label_rect = rem_label_surf.get_rect(center=(x_start + width // 2, 150))
    screen.blit(rem_label_surf, rem_label_rect)

    rem_surf = font_huge.render(str(remaining), True, TEXT_COLOR)
    rem_rect = rem_surf.get_rect(center=(x_start + width // 2, 230))
    screen.blit(rem_surf, rem_rect)

    if is_active:
        input_label = font_small.render("Current input:", True, TEXT_COLOR)
        screen.blit(input_label, (x_start + 40, 290))
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

def draw_game():
    screen.fill(BG_COLOR)
    half_width = WIDTH // 2
    pygame.draw.line(screen, DIVIDER_COLOR, (half_width, 0), (half_width, HEIGHT), 3)
    draw_player_section(0, 0, half_width, active_player == 0)
    draw_player_section(1, half_width, half_width, active_player == 1)

    hint = "Enter: commit • Backspace: delete/undo • Tab: switch starting player (before first throw) • M: menu • ESC: quit"
    hint_surf = font_small.render(hint, True, HINT_COLOR)
    screen.blit(hint_surf, (20, HEIGHT - 36))

    pygame.display.flip()

def commit_throw():
    """Apply current_input for active player with 'bust' and 'win' logic."""
    global current_input, scores, active_player, history, state, winner_idx

    if current_input == "":
        return

    try:
        value = int(current_input)
    except ValueError:
        value = 0

    remaining_before = START_SCORE - sum(scores[active_player])

    if value > remaining_before:
        # Bust: record 0, switch player
        scores[active_player].append(0)
        history.append((active_player, 0))
        current_input = ""
        active_player = 1 - active_player
        return

    # Valid throw (<= remaining)
    scores[active_player].append(value)
    history.append((active_player, value))
    current_input = ""

    if value == remaining_before:
        # Exactly hits 0 -> game over
        winner_idx = active_player
        state = STATE_END
        return

    # Otherwise continue, switch to other player
    active_player = 1 - active_player

def undo_last_score():
    """Remove the most recent recorded score and restore turn to that player."""
    global history, scores, active_player
    if not history:
        return
    last_player, last_score = history.pop()
    # Remove the corresponding score from that player's list (prefer tail pop)
    if scores[last_player] and scores[last_player][-1] == last_score:
        scores[last_player].pop()
    else:
        try:
            idx = len(scores[last_player]) - 1 - scores[last_player][::-1].index(last_score)
            scores[last_player].pop(idx)
        except ValueError:
            pass
    active_player = last_player

def handle_game_keydown(event):
    global current_input, state, menu_values, active_player, history

    if event.key == pygame.K_m:
        menu_values["p1"] = player_names[0]
        menu_values["p2"] = player_names[1]
        menu_values["score"] = str(START_SCORE) if START_SCORE in (301, 501) else "301"
        state = STATE_MENU
        return

    if event.key == pygame.K_ESCAPE:
        pygame.quit(); sys.exit()

    # NEW: allow choosing the starting player before any score is recorded
    if event.key == pygame.K_TAB:
        # Only when the game just started and no throw was committed yet, and no digits typed
        if not history and not scores[0] and not scores[1] and current_input == "":
            active_player = 1 - active_player
        return

    if pygame.K_0 <= event.key <= pygame.K_9:
        digit = event.key - pygame.K_0
        if len(current_input) < 3:
            if current_input == "0":
                current_input = str(digit)
            else:
                current_input += str(digit)
    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        commit_throw()
    elif event.key == pygame.K_BACKSPACE:
        if current_input != "":
            current_input = current_input[:-1]
        else:
            undo_last_score()

# ---------------- END SCREEN ----------------

def draw_end():
    screen.fill(BG_COLOR)

    title = "Game Over"
    t_surf = font_title.render(title, True, TEXT_COLOR)
    t_rect = t_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 180))
    screen.blit(t_surf, t_rect)

    if winner_idx is not None:
        win_text = f"Winner: {player_names[winner_idx]}"
        win_surf = font_huge.render(win_text, True, ACCENT_ACTIVE)
        win_rect = win_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        screen.blit(win_surf, win_rect)

    # Show final remaining scores
    rem0 = START_SCORE - sum(scores[0])
    rem1 = START_SCORE - sum(scores[1])
    rem_line = f"{player_names[0]} remaining: {rem0}    |    {player_names[1]} remaining: {rem1}"
    rem_surf = font_med.render(rem_line, True, TEXT_COLOR)
    rem_rect = rem_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
    screen.blit(rem_surf, rem_rect)

    hint_lines = [
        "Enter: start a new game with the same players and starting score",
        "Backspace: undo last score and resume the game",
        "M: back to setup menu",
        "ESC: quit",
    ]
    for i, h in enumerate(hint_lines):
        s = font_small.render(h, True, HINT_COLOR)
        screen.blit(s, (WIDTH // 2 - 380, HEIGHT // 2 + 120 + i * 30))

    pygame.display.flip()

def handle_end_event(event):
    global state, winner_idx, current_input, menu_values
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()
        if event.key == pygame.K_m:
            menu_values["p1"] = player_names[0]
            menu_values["p2"] = player_names[1]
            menu_values["score"] = str(START_SCORE) if START_SCORE in (301, 501) else "301"
            state = STATE_MENU
            return
        if event.key == pygame.K_BACKSPACE:
            undo_last_score()
            winner_idx = None
            current_input = ""
            state = STATE_GAME
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            reset_game(START_SCORE, player_names[0], player_names[1])
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
