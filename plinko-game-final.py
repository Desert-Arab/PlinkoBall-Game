###############################################################################
# plinko_game.py
###############################################################################

import pygame
import sys
import math
import random
import os
from datetime import datetime

###############################################################################
# GLOBAL SETTINGS
###############################################################################

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

BALL_RADIUS = 12
GRAVITY = 0.4
MAX_BALL_SPEED = 25
WALL_BOUNCE_FACTOR = 0.8
COLLISION_DAMPING = 0.9

PEG_RADIUS = 12       # bigger pegs
PEG_SPACING_X = 70    # bigger horizontal spacing
PEG_SPACING_Y = 70    # bigger vertical spacing
PEG_OFFSET_TOP = 80
NUM_PEG_ROWS = 8      # 8 total rows, skipping the old top row

BOX_COUNT = 5
BOX_HEIGHT = 80
BOX_VALUES = [10, 20, 50, 20, 10]

FONT_SIZE_SMALL = 24
FONT_SIZE_MEDIUM = 32
FONT_SIZE_LARGE = 48

WHITE     = (255, 255, 255)
BLACK     = (0, 0, 0)
RED       = (255, 0, 0)
GREEN     = (0, 255, 0)
BLUE      = (0, 0, 255)
YELLOW    = (255, 255, 0)
CYAN      = (0, 255, 255)
MAGENTA   = (255, 0, 255)
ORANGE    = (255, 165, 0)
PURPLE    = (128, 0, 128)
LIGHT_GREY= (200, 200, 200)
GRAY      = (128, 128, 128)
DARK_GREY = (70, 70, 70)

PARTICLE_COUNT_ON_COLLISION = 10
PARTICLE_LIFETIME = 30
PARTICLE_SPEED_RANGE = (1, 4)

pygame.init()
pygame.display.set_caption("Plinko Game")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

font_small  = pygame.font.SysFont(None, FONT_SIZE_SMALL)
font_medium = pygame.font.SysFont(None, FONT_SIZE_MEDIUM)
font_large  = pygame.font.SysFont(None, FONT_SIZE_LARGE)

def draw_text(surface, text, x, y, font_obj, color=WHITE, center=False):
    rendered = font_obj.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(rendered, rect)

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

###############################################################################
# PARTICLE CLASS
###############################################################################
class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.lifetime -= 1

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 3)

###############################################################################
# BALL CLASS
###############################################################################
class Ball:
    def __init__(self, x, y, radius=BALL_RADIUS, color=WHITE):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.vx = 0
        self.vy = 0
        self.finalized = False

    def update(self, pegs, box_y_top):
        self.vy += GRAVITY
        speed = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        if speed > MAX_BALL_SPEED:
            factor = MAX_BALL_SPEED / speed
            self.vx *= factor
            self.vy *= factor

        self.x += self.vx
        self.y += self.vy

        # Walls
        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx = -self.vx * WALL_BOUNCE_FACTOR
        elif self.x + self.radius > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.vx = -self.vx * WALL_BOUNCE_FACTOR

        # Ceiling
        if self.y - self.radius < 0:
            self.y = self.radius
            self.vy = -self.vy * WALL_BOUNCE_FACTOR

        # Peg collisions
        for peg in pegs:
            self.handle_peg_collision(peg)

        # Check if below scoring zone
        if self.y + self.radius >= box_y_top:
            self.finalized = True

    def handle_peg_collision(self, peg):
        dx = self.x - peg.x
        dy = self.y - peg.y
        dist_centers = math.sqrt(dx * dx + dy * dy)
        min_dist = self.radius + peg.radius
        if dist_centers < min_dist:
            overlap = min_dist - dist_centers
            if dist_centers == 0:
                # Prevent division by zero
                nx, ny = 1, 0
            else:
                nx = dx / dist_centers
                ny = dy / dist_centers
            self.x += nx * overlap
            self.y += ny * overlap
            dot = self.vx * nx + self.vy * ny
            self.vx -= 2 * dot * nx * COLLISION_DAMPING
            self.vy -= 2 * dot * ny * COLLISION_DAMPING

            # Particles
            color_particle = random.choice([WHITE, YELLOW, BLUE, CYAN, MAGENTA])
            for _ in range(PARTICLE_COUNT_ON_COLLISION):
                speed_mag = random.uniform(*PARTICLE_SPEED_RANGE)
                angle = random.uniform(0, 2 * math.pi)
                vx_p = speed_mag * math.cos(angle)
                vy_p = speed_mag * math.sin(angle)
                peg.particles.append(
                    Particle(self.x, self.y, vx_p, vy_p, color_particle, PARTICLE_LIFETIME)
                )

    def draw(self, surface, debug=False):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        if debug:
            pygame.draw.rect(surface, RED,
                             (int(self.x - self.radius), int(self.y - self.radius),
                              self.radius * 2, self.radius * 2), 1)

###############################################################################
# PEG CLASS
###############################################################################
class Peg:
    def __init__(self, x, y, radius=PEG_RADIUS, color=RED):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.particles = []

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.lifetime > 0]

    def draw(self, surface, debug=False):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        if debug:
            pygame.draw.rect(surface, GREEN, (int(self.x - self.radius), int(self.y - self.radius),
                                              self.radius * 2, self.radius * 2), 1)
        for p in self.particles:
            p.draw(surface)

###############################################################################
# BUTTON CLASS
###############################################################################
class Button:
    def __init__(self, x, y, w, h, text, font_obj,
                 color_bg=GRAY, color_fg=BLACK, color_hover=LIGHT_GREY):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.font = font_obj
        self.color_bg = color_bg
        self.color_fg = color_fg
        self.color_hover = color_hover

    def draw(self, surface):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        rect = pygame.Rect(self.x, self.y, self.w, self.h)
        if rect.collidepoint(mouse_x, mouse_y):
            pygame.draw.rect(surface, self.color_hover, rect)
        else:
            pygame.draw.rect(surface, self.color_bg, rect)
        draw_text(surface, self.text, self.x + self.w//2, self.y + self.h//2,
                  self.font, self.color_fg, center=True)

    def is_clicked(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        rect = pygame.Rect(self.x, self.y, self.w, self.h)
        return rect.collidepoint(mouse_x, mouse_y) and pygame.mouse.get_pressed()[0]

###############################################################################
# SETTINGS CLASS
###############################################################################
class Settings:
    def __init__(self):
        self.debug_mode = False

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode

###############################################################################
# GAME STATES
###############################################################################
STATE_MENU      = "menu"
STATE_PLAY      = "play"
STATE_PAUSE     = "pause"
STATE_GAMEOVER  = "game_over"
STATE_HIGHSCORE = "highscore"
STATE_SETTINGS  = "settings"

###############################################################################
# PLINKO GAME
###############################################################################
class PlinkoGame:
    def __init__(self):
        self.state = STATE_MENU
        self.settings = Settings()

        self.score = 0
        self.balls_allowed = 25
        self.balls_dropped = 0

        self.best_score = 0  # ephemeral best score

        self.pegs = []
        self.balls = []
        self.init_pegs()

        self.boxes = []
        self.init_boxes()

        self.game_over_reason = ""

        self.menu_buttons = []
        self.pause_buttons = []
        self.gameover_buttons = []
        self.highscore_buttons = []
        self.settings_buttons = []
        self.pause_button = None

        self.init_buttons()

    def init_pegs(self):
        self.pegs.clear()
        for row in range(NUM_PEG_ROWS):
            peg_count = row + 3  # row=0 => 3 pegs, row=7 => 10 pegs
            row_width = (peg_count - 1) * PEG_SPACING_X
            start_x = (SCREEN_WIDTH - row_width) / 2
            y_pos = PEG_OFFSET_TOP + row * PEG_SPACING_Y
            for i in range(peg_count):
                x_pos = start_x + i * PEG_SPACING_X
                color = random.choice([RED, BLUE, GREEN, ORANGE, PURPLE])
                self.pegs.append(Peg(x_pos, y_pos, PEG_RADIUS, color))

    def init_boxes(self):
        self.boxes.clear()
        width_per_box = SCREEN_WIDTH // BOX_COUNT
        for i in range(BOX_COUNT):
            rect = pygame.Rect(
                i * width_per_box,
                SCREEN_HEIGHT - BOX_HEIGHT,
                width_per_box,
                BOX_HEIGHT
            )
            value = BOX_VALUES[i % len(BOX_VALUES)]
            self.boxes.append((rect, value))

    def init_buttons(self):
        # Main Menu
        self.menu_buttons.append(Button(SCREEN_WIDTH//2 - 75, 270, 150, 50,
                                        "Play", font_medium))
        self.menu_buttons.append(Button(SCREEN_WIDTH//2 - 75, 340, 150, 50,
                                        "High Scores", font_medium))
        self.menu_buttons.append(Button(SCREEN_WIDTH//2 - 75, 410, 150, 50,
                                        "Settings", font_medium))
        self.menu_buttons.append(Button(SCREEN_WIDTH//2 - 75, 480, 150, 50,
                                        "Exit", font_medium))

        # Pause
        self.pause_buttons.append(Button(SCREEN_WIDTH//2 - 75, 250, 150, 50,
                                         "Resume", font_medium))
        self.pause_buttons.append(Button(SCREEN_WIDTH//2 - 75, 320, 150, 50,
                                         "Settings", font_medium))
        self.pause_buttons.append(Button(SCREEN_WIDTH//2 - 75, 390, 150, 50,
                                         "Main Menu", font_medium))

        # Game Over
        self.gameover_buttons.append(Button(SCREEN_WIDTH//2 - 75, 400, 150, 50,
                                            "Main Menu", font_medium))

        # High Score
        self.highscore_buttons.append(Button(SCREEN_WIDTH//2 - 75, 500, 150, 50,
                                             "Main Menu", font_medium))

        # Settings
        # Adjusted positions as per your instructions
        self.settings_buttons.append(Button(SCREEN_WIDTH//2 - 100, 200, 200, 50,
                                            "Toggle Debug", font_medium))
        self.settings_buttons.append(Button(SCREEN_WIDTH//2 - 125, 260, 75, 50,
                                            "Balls -", font_medium))
        self.settings_buttons.append(Button(SCREEN_WIDTH//2 + 50, 260, 75, 50,
                                            "Balls +", font_medium))
        self.settings_buttons.append(Button(SCREEN_WIDTH//2 - 100, 320, 200, 50,
                                            "Back", font_medium))

        # Pause button top-right
        self.pause_button = Button(
            SCREEN_WIDTH - 50, 10, 30, 40,
            "||", font_large,
            color_bg=BLACK,
            color_fg=WHITE,
            color_hover=GRAY
        )

    def reset_game(self):
        self.score = 0
        self.balls_dropped = 0
        self.balls.clear()
        self.game_over_reason = ""
        self.init_pegs()

    def update(self):
        if self.state == STATE_MENU:
            self.update_menu()
        elif self.state == STATE_PLAY:
            self.update_play()
        elif self.state == STATE_PAUSE:
            self.update_pause()
        elif self.state == STATE_GAMEOVER:
            self.update_gameover()
        elif self.state == STATE_HIGHSCORE:
            self.update_highscore()
        elif self.state == STATE_SETTINGS:
            self.update_settings()

    def draw(self):
        if self.state == STATE_MENU:
            self.draw_menu()
        elif self.state == STATE_PLAY:
            self.draw_play()
        elif self.state == STATE_PAUSE:
            self.draw_pause()
        elif self.state == STATE_GAMEOVER:
            self.draw_gameover()
        elif self.state == STATE_HIGHSCORE:
            self.draw_highscore()
        elif self.state == STATE_SETTINGS:
            self.draw_settings()
        pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == STATE_MENU:
                self.handle_menu_events(event)
            elif self.state == STATE_PLAY:
                self.handle_play_events(event)
            elif self.state == STATE_PAUSE:
                self.handle_pause_events(event)
            elif self.state == STATE_GAMEOVER:
                self.handle_gameover_events(event)
            elif self.state == STATE_HIGHSCORE:
                self.handle_highscore_events(event)
            elif self.state == STATE_SETTINGS:
                self.handle_settings_events(event)

    ############################################################################
    # MENU
    ############################################################################
    def update_menu(self):
        pass

    def draw_menu(self):
        screen.fill(DARK_GREY)
        draw_text(screen, "PLINKO GAME", SCREEN_WIDTH//2, 150, font_large, WHITE, center=True)
        for btn in self.menu_buttons:
            btn.draw(screen)

    def handle_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu_buttons[0].is_clicked():
                self.reset_game()
                self.state = STATE_PLAY
            elif self.menu_buttons[1].is_clicked():
                self.state = STATE_HIGHSCORE
            elif self.menu_buttons[2].is_clicked():
                self.state = STATE_SETTINGS
            elif self.menu_buttons[3].is_clicked():
                pygame.quit()
                sys.exit()

    ############################################################################
    # PLAY
    ############################################################################
    def update_play(self):
        for peg in self.pegs:
            peg.update()

        box_y_top = SCREEN_HEIGHT - BOX_HEIGHT
        for ball in self.balls:
            if not ball.finalized:
                ball.update(self.pegs, box_y_top)

        finalized_balls = [b for b in self.balls if b.finalized]
        for b in finalized_balls:
            self.handle_ball_box_score(b)
        self.balls = [b for b in self.balls if not b.finalized]

        if self.balls_dropped == self.balls_allowed and len(self.balls) == 0:
            self.game_over_reason = "All Balls Used"
            if self.score > self.best_score:
                self.best_score = self.score
            self.state = STATE_GAMEOVER

    def handle_ball_box_score(self, ball):
        for (rect, value) in self.boxes:
            if (rect.left <= ball.x <= rect.right) and (ball.y + ball.radius >= rect.top):
                self.score += value
                break

    def draw_play(self):
        screen.fill(BLACK)
        for peg in self.pegs:
            peg.draw(screen, debug=self.settings.debug_mode)
        for ball in self.balls:
            ball.draw(screen, debug=self.settings.debug_mode)

        for (rect, value) in self.boxes:
            pygame.draw.rect(screen, GRAY, rect)
            draw_text(screen, str(value), rect.centerx, rect.centery,
                      font_medium, WHITE, center=True)

        width_per_box = SCREEN_WIDTH // BOX_COUNT
        for i in range(1, BOX_COUNT):
            x_line = i * width_per_box
            top_y = SCREEN_HEIGHT - BOX_HEIGHT
            pygame.draw.line(screen, BLACK, (x_line, top_y),
                             (x_line, SCREEN_HEIGHT), 4)

        draw_text(screen, f"Score: {self.score}", 20, 20, font_small, WHITE)
        left = self.balls_allowed - self.balls_dropped
        draw_text(screen, f"Balls Left: {left}", 20, 50, font_small, WHITE)

        self.pause_button.draw(screen)

    def handle_play_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = STATE_PAUSE
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.pause_button.is_clicked():
                self.state = STATE_PAUSE
                return
            if self.balls_dropped < self.balls_allowed:
                mx, my = pygame.mouse.get_pos()
                spawn_y = 30
                color = random.choice([WHITE, YELLOW, BLUE, CYAN, MAGENTA])
                ball = Ball(mx, spawn_y, BALL_RADIUS, color)
                ball.vx = random.uniform(-2, 2)
                self.balls.append(ball)
                self.balls_dropped += 1

    ############################################################################
    # PAUSE
    ############################################################################
    def update_pause(self):
        pass

    def draw_pause(self):
        self.draw_play()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        draw_text(screen, "PAUSED", SCREEN_WIDTH//2, 150,
                  font_large, WHITE, center=True)
        for btn in self.pause_buttons:
            btn.draw(screen)

    def handle_pause_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = STATE_PLAY
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # [0] = Resume, [1] = Settings, [2] = Main Menu
            if self.pause_buttons[0].is_clicked():
                self.state = STATE_PLAY
            elif self.pause_buttons[1].is_clicked():
                self.state = STATE_SETTINGS
            elif self.pause_buttons[2].is_clicked():
                self.state = STATE_MENU

    ############################################################################
    # GAME OVER
    ############################################################################
    def update_gameover(self):
        pass

    def draw_gameover(self):
        screen.fill(BLACK)
        draw_text(screen, "GAME OVER", SCREEN_WIDTH//2, 100,
                  font_large, RED, center=True)
        draw_text(screen, self.game_over_reason, SCREEN_WIDTH//2, 160,
                  font_medium, WHITE, center=True)
        draw_text(screen, f"Your Score: {self.score}", SCREEN_WIDTH//2, 220,
                  font_medium, WHITE, center=True)

        for btn in self.gameover_buttons:
            btn.draw(screen)

    def handle_gameover_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.gameover_buttons[0].is_clicked():
                self.state = STATE_MENU

    ############################################################################
    # HIGH SCORE
    ############################################################################
    def update_highscore(self):
        pass

    def draw_highscore(self):
        screen.fill(BLACK)
        draw_text(screen, "HIGH SCORES", SCREEN_WIDTH//2, 80,
                  font_large, WHITE, center=True)

        if self.best_score <= 0:
            draw_text(screen, "No high scores yet!", SCREEN_WIDTH//2, 200,
                      font_medium, WHITE, center=True)
        else:
            draw_text(screen, f"Best Score: {self.best_score}",
                      SCREEN_WIDTH//2, 200, font_medium, WHITE, center=True)

        for btn in self.highscore_buttons:
            btn.draw(screen)

    def handle_highscore_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.highscore_buttons[0].is_clicked():
                self.state = STATE_MENU

    ############################################################################
    # SETTINGS
    ############################################################################
    def update_settings(self):
        pass

    def draw_settings(self):
        screen.fill(BLACK)
        # The user wants "SETTINGS" and "Debug Mode: X" 1 cm (40px) down from original:
        #   Original was y=80 for "SETTINGS" => now 80+40=120
        #   Original was y=120 for "Debug Mode: X" => now 120+40=160
        draw_text(screen, "SETTINGS", SCREEN_WIDTH//2, 120,
                  font_large, WHITE, center=True)
        draw_text(screen, f"Debug Mode: {self.settings.debug_mode}",
                  SCREEN_WIDTH//2, 160, font_medium, WHITE, center=True)

        for btn in self.settings_buttons:
            btn.draw(screen)

        # The new positions for the buttons are up 2 cm => subtract 80 from old values
        # The user wants the "Toggle Debug", "Balls -", "Balls +", "Back" ~2 cm up
        # So we updated them in init_buttons() => we reflect that in the code
        # Indices => [0]=ToggleDebug, [1]=Balls-, [2]=Balls+, [3]=Back
        minus_btn = self.settings_buttons[1]
        plus_btn  = self.settings_buttons[2]
        count_x   = (minus_btn.x + minus_btn.w + plus_btn.x) // 2
        count_y   = minus_btn.y + minus_btn.h // 2
        draw_text(screen, str(self.balls_allowed),
                  count_x, count_y, font_medium, WHITE, center=True)

    def handle_settings_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # [0]=ToggleDebug, [1]=Balls-, [2]=Balls+, [3]=Back
            if self.settings_buttons[0].is_clicked():
                self.settings.toggle_debug()
            elif self.settings_buttons[1].is_clicked():
                self.balls_allowed = clamp(self.balls_allowed - 1, 1, 50)
            elif self.settings_buttons[2].is_clicked():
                self.balls_allowed = clamp(self.balls_allowed + 1, 1, 50)
            elif self.settings_buttons[3].is_clicked():
                self.state = STATE_MENU  # Directly go to Main Menu

def main():
    game = PlinkoGame()
    running = True
    while running:
        clock.tick(FPS)
        game.handle_events()
        game.update()
        game.draw()

if __name__ == "__main__":
    main()
