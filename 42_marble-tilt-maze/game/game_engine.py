import pygame
import math
from .marble import Marble
from .wall import Wall

# Game Engine

WHITE      = (255, 255, 255)
DARK       = (40,  40,  50)
WALL_COLOR = (90,  90,  110)
GOAL_COLOR = (60,  200, 120)
GRAY       = (160, 160, 170)
GREEN      = (60,  200, 120)
RED        = (220, 80,  80)
YELLOW     = (240, 200, 60)
HIGHLIGHT  = (255, 255, 255)

# Difficulty presets: (tilt_strength, friction, max_speed, time_limit_sec)
DIFFICULTIES = {
    "Easy":   (0.4, 0.035, 7,  60),
    "Medium": (0.6, 0.020, 9,  45),
    "Hard":   (0.9, 0.010, 12, 30),
}


def _synth(freq_fn, duration_ms, amplitude=20000):
    """Generate a mono 16-bit PCM Sound using stdlib array (no numpy needed)."""
    import array as _array
    sample_rate = 44100
    n = int(sample_rate * duration_ms / 1000)
    raw = _array.array("h", [0] * n)
    for i in range(n):
        t    = i / sample_rate
        fade = max(0.0, 1.0 - i / n)
        freq = freq_fn(i, n)
        raw[i] = int(math.sin(2 * math.pi * freq * t) * amplitude * fade)
    return pygame.mixer.Sound(buffer=raw)


def _make_bounce_sound():
    return _synth(lambda i, n: 440, 60, 16000)


def _make_goal_sound():
    """Three-note ascending arpeggio."""
    import array as _array
    sample_rate = 44100
    duration_ms = 500
    n   = int(sample_rate * duration_ms / 1000)
    raw = _array.array("h", [0] * n)
    freqs = [523, 659, 784]
    seg   = n // len(freqs)
    for fi, freq in enumerate(freqs):
        for i in range(seg):
            idx  = fi * seg + i
            t    = i / sample_rate
            fade = max(0.0, 1.0 - i / seg)
            raw[idx] = int(math.sin(2 * math.pi * freq * t) * 20000 * fade)
    return pygame.mixer.Sound(buffer=raw)


def _make_timeout_sound():
    return _synth(lambda i, n: 300 - 200 * (i / n), 700)


class GameEngine:
    def __init__(self, width, height, difficulty="Medium"):
        self.width  = width
        self.height = height

        self._init_sounds()
        self._apply_difficulty(difficulty)
        self._new_game()

        self.font       = pygame.font.SysFont("Arial", 26)
        self.font_big   = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 20)

        # State machine: "playing" | "game_over" | "menu"
        self.state = "playing"
        self._selected_difficulty = difficulty

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_sounds(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        try:
            self.snd_bounce  = _make_bounce_sound()
            self.snd_goal    = _make_goal_sound()
            self.snd_timeout = _make_timeout_sound()
            self.snd_bounce.set_volume(0.4)
            self.snd_goal.set_volume(0.7)
            self.snd_timeout.set_volume(0.7)
            self._sounds_ok = True
        except Exception:
            self._sounds_ok = False

    def _play(self, sound):
        if self._sounds_ok:
            sound.play()

    def _apply_difficulty(self, difficulty):
        ts, fr, ms, tl = DIFFICULTIES.get(difficulty, DIFFICULTIES["Medium"])
        self.tilt_strength  = ts
        self.friction       = fr
        self.max_speed      = ms
        self.time_limit_ms  = tl * 1000
        self._difficulty    = difficulty

    def _new_game(self):
        self.marble         = Marble(50, 50)
        self.walls          = self._build_maze()
        self.goal_x         = self.width  - 60
        self.goal_y         = self.height - 60
        self.goal_radius    = 22
        self.start_ticks    = pygame.time.get_ticks()
        self.game_over      = False
        self.result         = None   # "solved" | "timeout"
        self.finish_time_ms = None
        self._sound_played  = False
        self._last_bounce   = 0      # tick of last bounce (for cooldown)

    def _build_maze(self):
        walls = []
        t = 16

        walls.append(Wall(0, 0, self.width, t))
        walls.append(Wall(0, self.height - t, self.width, t))
        walls.append(Wall(0, 0, t, self.height))
        walls.append(Wall(self.width - t, 0, t, self.height))

        walls.append(Wall(0,   140, self.width  - 140, t))
        walls.append(Wall(140, 260, self.width  - 140, t))
        walls.append(Wall(0,   380, self.width  - 140, t))

        return walls

    # ------------------------------------------------------------------
    # Task 1 – true circle-vs-AABB collision
    # ------------------------------------------------------------------

    @staticmethod
    def _circle_aabb_collision(cx, cy, r, rect):
        """Return (penetration_x, penetration_y) if circle overlaps rect, else None."""
        # Closest point on rect to circle center
        closest_x = max(rect.left,   min(cx, rect.right))
        closest_y = max(rect.top,    min(cy, rect.bottom))
        dx = cx - closest_x
        dy = cy - closest_y
        dist_sq = dx * dx + dy * dy
        if dist_sq >= r * r:
            return None
        dist = math.sqrt(dist_sq) if dist_sq > 0 else 0
        # penetration depth along the collision normal
        penetration = r - dist
        if dist == 0:
            # center is inside the rect – push out along shortest axis
            ox = min(cx - rect.left, rect.right  - cx)
            oy = min(cy - rect.top,  rect.bottom - cy)
            if ox < oy:
                return (ox if cx < rect.centerx else -ox, 0)
            else:
                return (0, oy if cy < rect.centery else -oy)
        nx = dx / dist
        ny = dy / dist
        return (nx * penetration, ny * penetration)

    def _resolve_wall_collisions(self):
        now = pygame.time.get_ticks()
        bounced = False
        for wall in self.walls:
            result = self._circle_aabb_collision(
                self.marble.x, self.marble.y, self.marble.radius, wall.rect()
            )
            if result is None:
                continue
            px, py = result
            self.marble.x += px
            self.marble.y += py
            # Reflect velocity along the collision normal
            if abs(px) > abs(py):
                self.marble.vx *= -0.6
            else:
                self.marble.vy *= -0.6
            bounced = True

        if bounced and now - self._last_bounce > 80:   # 80 ms cooldown
            self._play(self.snd_bounce)
            self._last_bounce = now

    # ------------------------------------------------------------------
    # Main loop interface
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if self.state == "game_over":
            self._handle_game_over_event(event)
        elif self.state == "menu":
            self._handle_menu_event(event)

    def handle_input(self):
        if self.state != "playing":
            return
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = mouse_x - self.width  // 2
        dy = mouse_y - self.height // 2
        dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)
        ax = (dx / dist) * self.tilt_strength
        ay = (dy / dist) * self.tilt_strength
        self.marble.vx += ax
        self.marble.vy += ay

    def update(self):
        if self.state != "playing":
            return

        elapsed = pygame.time.get_ticks() - self.start_ticks
        if elapsed >= self.time_limit_ms:
            self.game_over = True
            self.result    = "timeout"
            self.state     = "game_over"
            if not self._sound_played:
                self._play(self.snd_timeout)
                self._sound_played = True
            return

        self.marble.vx *= (1 - self.friction)
        self.marble.vy *= (1 - self.friction)

        speed = (self.marble.vx ** 2 + self.marble.vy ** 2) ** 0.5
        if speed > self.max_speed:
            scale = self.max_speed / speed
            self.marble.vx *= scale
            self.marble.vy *= scale

        self.marble.x += self.marble.vx
        self.marble.y += self.marble.vy

        self._resolve_wall_collisions()

        gx = self.goal_x - self.marble.x
        gy = self.goal_y - self.marble.y
        if (gx ** 2 + gy ** 2) ** 0.5 <= self.goal_radius:
            self.game_over      = True
            self.result         = "solved"
            self.finish_time_ms = elapsed
            self.state          = "game_over"
            if not self._sound_played:
                self._play(self.snd_goal)
                self._sound_played = True

    def render(self, screen):
        if self.state == "playing":
            self._render_game(screen)
        elif self.state == "game_over":
            self._render_game(screen)          # show final board behind overlay
            self._render_game_over(screen)
        elif self.state == "menu":
            self._render_menu(screen)

    # ------------------------------------------------------------------
    # Task 2 – game-over screen
    # ------------------------------------------------------------------

    def _render_game_over(self, screen):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        if self.result == "solved":
            title     = "YOU WIN!"
            color     = GREEN
            sub       = f"Finished in {self.finish_time_ms / 1000:.1f}s"
        else:
            title     = "TIME'S UP!"
            color     = RED
            sub       = "Better luck next time."

        title_surf = self.font_big.render(title, True, color)
        sub_surf   = self.font.render(sub,   True, WHITE)
        hint_surf  = self.font_small.render("Press SPACE to play again  |  ESC to quit", True, GRAY)

        cx = self.width // 2
        screen.blit(title_surf, title_surf.get_rect(center=(cx, self.height // 2 - 60)))
        screen.blit(sub_surf,   sub_surf.get_rect(center=(cx, self.height // 2)))
        screen.blit(hint_surf,  hint_surf.get_rect(center=(cx, self.height // 2 + 55)))

    def _handle_game_over_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.state = "menu"
            elif event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    # ------------------------------------------------------------------
    # Task 3 – difficulty menu / replay
    # ------------------------------------------------------------------

    _MENU_OPTIONS = ["Easy", "Medium", "Hard"]

    def _render_menu(self, screen):
        screen.fill(DARK)
        title_surf = self.font_big.render("Choose Difficulty", True, WHITE)
        screen.blit(title_surf, title_surf.get_rect(center=(self.width // 2, 100)))

        descriptions = {
            "Easy":   "Gentle tilt · slow marble · 60s",
            "Medium": "Normal tilt · medium speed · 45s",
            "Hard":   "Aggressive tilt · fast marble · 30s",
        }

        for i, opt in enumerate(self._MENU_OPTIONS):
            y = 210 + i * 80
            selected = (opt == self._selected_difficulty)
            box_color = YELLOW if selected else GRAY
            label     = self.font.render(opt, True, DARK if selected else WHITE)
            desc      = self.font_small.render(descriptions[opt], True, DARK if selected else GRAY)
            box = pygame.Rect(self.width // 2 - 140, y - 20, 280, 56)
            pygame.draw.rect(screen, box_color, box, border_radius=8)
            screen.blit(label, label.get_rect(center=(self.width // 2, y + 5)))
            screen.blit(desc,  desc.get_rect(center=(self.width // 2, y + 27)))

        hint = self.font_small.render("Click a difficulty or press 1/2/3  ·  ESC to quit", True, GRAY)
        screen.blit(hint, hint.get_rect(center=(self.width // 2, self.height - 30)))

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self._start_with("Easy")
            elif event.key == pygame.K_2:
                self._start_with("Medium")
            elif event.key == pygame.K_3:
                self._start_with("Hard")
            elif event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            for i, opt in enumerate(self._MENU_OPTIONS):
                y   = 210 + i * 80
                box = pygame.Rect(self.width // 2 - 140, y - 20, 280, 56)
                if box.collidepoint(mx, my):
                    self._start_with(opt)
                    break

    def _start_with(self, difficulty):
        self._selected_difficulty = difficulty
        self._apply_difficulty(difficulty)
        self._new_game()
        self.state = "playing"

    # ------------------------------------------------------------------
    # Shared game render
    # ------------------------------------------------------------------

    def _render_game(self, screen):
        screen.fill(DARK)

        for wall in self.walls:
            pygame.draw.rect(screen, WALL_COLOR, wall.rect())

        pygame.draw.circle(screen, GOAL_COLOR,
                           (self.goal_x, self.goal_y), self.goal_radius)
        pygame.draw.circle(screen, WHITE,
                           (int(self.marble.x), int(self.marble.y)),
                           self.marble.radius)

        elapsed      = pygame.time.get_ticks() - self.start_ticks
        seconds_left = max(0, (self.time_limit_ms - elapsed) // 1000)
        color        = RED if seconds_left <= 5 else WHITE
        timer_text   = self.font.render(f"Time: {seconds_left}s", True, color)
        screen.blit(timer_text, (10, 10))

        diff_text = self.font_small.render(self._difficulty, True, GRAY)
        screen.blit(diff_text, (self.width - diff_text.get_width() - 10, 10))
