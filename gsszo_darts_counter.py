import pygame
import sys

pygame.init()

# ---- SETTINGS ----
START_SCORE = 301

# Get current display resolution and use fullscreen
display_info = pygame.display.Info()
WIDTH, HEIGHT = display_info.current_w, display_info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Darts Counter - 2 Players (501)")

# Colors
BG_COLOR = (20, 20, 20)
TEXT_COLOR = (230, 230, 230)
HINT_COLOR = (160, 160, 160)
ACCENT_ACTIVE = (100, 220, 100)
ACCENT_INACTIVE = (100, 100, 100)
DIVIDER_COLOR = (80, 80, 80)

# Fonts (bigger than before)
font_huge = pygame.font.SysFont(None, 110)
font_big = pygame.font.SysFont(None, 72)
font_med = pygame.font.SysFont(None, 46)
font_small = pygame.font.SysFont(None, 30)
font_round = pygame.font.SysFont(None, 36)

clock = pygame.time.Clock()

# State
current_input = ""         # what you're typing now as string
scores = [[], []]          # scores[0] -> Player 1, scores[1] -> Player 2
active_player = 0          # 0 or 1
history = []               # list of (player_index, score) for undo


def draw_player_section(player_idx, x_start, width, is_active):
    """Draw one half of the screen for the given player."""
    # Title
    title = f"Player {player_idx + 1}"
    title_color = ACCENT_ACTIVE if is_active else ACCENT_INACTIVE
    title_surf = font_big.render(title, True, title_color)
    title_rect = title_surf.get_rect(center=(x_start + width // 2, 70))
    screen.blit(title_surf, title_rect)

    # Remaining score (501 - sum of scores)
    total_scored = sum(scores[player_idx])
    remaining = START_SCORE - total_scored

    rem_label_surf = font_med.render("Remaining:", True, TEXT_COLOR)
    rem_label_rect = rem_label_surf.get_rect(center=(x_start + width // 2, 150))
    screen.blit(rem_label_surf, rem_label_rect)

    rem_surf = font_huge.render(str(remaining), True, TEXT_COLOR)
    rem_rect = rem_surf.get_rect(center=(x_start + width // 2, 230))
    screen.blit(rem_surf, rem_rect)

    # Current input only visible on active player side
    if is_active:
        input_label = font_small.render("Current input:", True, TEXT_COLOR)
        screen.blit(input_label, (x_start + 40, 290))

        input_text = current_input if current_input != "" else "-"
        input_surf = font_big.render(input_text, True, TEXT_COLOR)
        screen.blit(input_surf, (x_start + 40, 320))

    # Rounds list (each score under the last)
    rounds_label = font_small.render("Rounds (last at bottom):", True, TEXT_COLOR)
    screen.blit(rounds_label, (x_start + 40, 380))

    # Compute how many lines fit vertically
    start_y = 410
    line_height = 38
    max_lines = max(1, (HEIGHT - start_y - 60) // line_height)

    player_scores = scores[player_idx]
    visible_scores = player_scores[-max_lines:]
    # Adjust round numbers so they match the actual round index
    start_round_index = len(player_scores) - len(visible_scores) + 1

    y = start_y
    for i, s in enumerate(visible_scores):
        round_num = start_round_index + i
        round_text = f"{round_num}.  {s}"
        round_surf = font_round.render(round_text, True, TEXT_COLOR)
        screen.blit(round_surf, (x_start + 40, y))
        y += line_height


def draw_screen():
    screen.fill(BG_COLOR)

    half_width = WIDTH // 2

    # Divider line between players
    pygame.draw.line(screen, DIVIDER_COLOR, (half_width, 0), (half_width, HEIGHT), 3)

    # Left: Player 1
    draw_player_section(0, 0, half_width, active_player == 0)

    # Right: Player 2
    draw_player_section(1, half_width, half_width, active_player == 1)

    pygame.display.flip()


def handle_keydown(event):
    global current_input, scores, active_player, history

    if event.key == pygame.K_ESCAPE:
        pygame.quit()
        sys.exit()

    # Number keys: append digit to current input
    if pygame.K_0 <= event.key <= pygame.K_9:
        digit = event.key - pygame.K_0
        # Limit to 3 digits (0–999) to keep it simple
        if len(current_input) < 3:
            if current_input == "0":
                current_input = str(digit)
            else:
                current_input += str(digit)

    # Enter: commit input as a score for active player, then switch players
    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if current_input != "":
            try:
                value = int(current_input)
            except ValueError:
                value = 0

            # Add score to active player
            scores[active_player].append(value)
            history.append((active_player, value))
            current_input = ""

            # Switch active player automatically
            active_player = 1 - active_player

    # Backspace: delete digit, or undo last committed score (and restore that player's turn)
    elif event.key == pygame.K_BACKSPACE:
        if current_input != "":
            # Delete last digit
            current_input = current_input[:-1]
        else:
            # Undo last committed score globally
            if history:
                last_player, last_score = history.pop()
                if scores[last_player] and scores[last_player][-1] == last_score:
                    scores[last_player].pop()
                else:
                    # Fallback if something got out of sync: remove first matching
                    try:
                        scores[last_player].remove(last_score)
                    except ValueError:
                        pass

                # Give turn back to the player whose score was undone
                active_player = last_player


def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                handle_keydown(event)

        draw_screen()
        clock.tick(30)


if __name__ == "__main__":
    main()
