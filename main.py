import curses
import threading
import random
import time

# Configurações do jogo
WIDTH, HEIGHT = 50, 20
FPS = 60
ROCKET_CAPACITY = 5
RELOAD_TIME = 1
ROCKET_SPEED = 0.05
ALIEN_SPAWN_INTERVAL = 2  # Intervalo em segundos para novos alienígenas aparecerem

# Dificuldades do jogo
DIFFICULTY = {
    "fácil": {"alien_speed": 1, "num_aliens": 10},
    "médio": {"alien_speed": 0.5, "num_aliens": 15},
    "difícil": {"alien_speed": 0.2, "num_aliens": 20}
}

class Cannon:
    def __init__(self):
        self.angle = 90  # Inicialmente vertical
        self.rockets = ROCKET_CAPACITY
        self.lock = threading.Lock()
        self.reloading = False

    def move_left(self):
        with self.lock:
            if self.angle > 0:
                self.angle -= 45

    def move_right(self):
        with self.lock:
            if self.angle < 180:
                self.angle += 45

    def fire(self):
        with self.lock:
            if self.rockets > 0:
                self.rockets -= 1
                return True
            return False

    def reload(self):
        if not self.reloading:
            self.reloading = True
            for i in range(5):
                time.sleep(RELOAD_TIME)
                with self.lock:
                    self.rockets = min(self.rockets + 1, ROCKET_CAPACITY)
            self.reloading = False


class Alien(threading.Thread):
    def __init__(self, game, x, y, speed):
        super().__init__()
        self.game = game
        self.x = x
        self.y = y
        self.alive = True
        self.speed = speed

    def run(self):
        while self.y < HEIGHT and self.alive and not self.game.game_over:
            self.y += 1
            time.sleep(self.speed)
        if self.alive:
            self.game.alien_landed(self)

    def destroy(self):
        self.alive = False


class Rocket(threading.Thread):
    def __init__(self, game, x, y, angle):
        super().__init__()
        self.game = game
        self.x = x
        self.y = y
        self.angle = angle

    def run(self):
        match self.angle:
            case 0:
                while self.x > 0:
                    self.x -= 1
                    time.sleep(ROCKET_SPEED)
                    self.game.check_collisions(self)
            case 45:
                while self.y > 0 and self.x > 0:
                    self.y -= 1
                    self.x -= 1
                    time.sleep(ROCKET_SPEED)
                    self.game.check_collisions(self)
            case 90:
                while self.y > 0 and self.angle == 90:
                    self.y -= 1
                    time.sleep(ROCKET_SPEED)
                    self.game.check_collisions(self)

            case 135:
                while self.y > 0 and self.x < WIDTH:
                    self.y -= 1
                    self.x += 1
                    time.sleep(ROCKET_SPEED)
                    self.game.check_collisions(self)
            case 180:
                while self.x < WIDTH:
                    self.x += 1
                    time.sleep(ROCKET_SPEED)
                    self.game.check_collisions(self)


class Game:
    def __init__(self, difficulty):
        self.cannon = Cannon()
        self.aliens = []
        self.aliens_to_spawn = []
        self.rockets = []
        self.lock = threading.Lock()
        self.victory = False
        self.defeat = False
        self.game_over = False
        self.aliens_landed = 0
        self.aliens_defeated = 0
        self.difficulty = difficulty
        self.alien_speed = DIFFICULTY[difficulty]["alien_speed"]
        self.num_aliens = DIFFICULTY[difficulty]["num_aliens"]

    def start(self, stdscr):
        curses.curs_set(0)
        stdscr.nodelay(1)
        stdscr.timeout(100)

        # Prepara lista de alienígenas a serem gerados
        self.aliens_to_spawn = [Alien(self, random.randint(0, WIDTH - 1), 0, self.alien_speed) for _ in range(self.num_aliens)]

        # Inicia thread para gerar alienígenas
        alien_thread = threading.Thread(target=self.spawn_aliens)
        alien_thread.start()

        while not self.victory and not self.defeat:
            self.handle_events(stdscr)
            self.draw(stdscr)
            time.sleep(1 / FPS)

        stdscr.nodelay(0)
        if self.victory:
            gameover_status = "VICTORY"
        else:
            gameover_status = "DEFEAT"
        stdscr.addstr(HEIGHT // 2, WIDTH // 2 - 7, "GAME OVER")
        stdscr.addstr(HEIGHT // 2 + 1, WIDTH // 2 - 7, f"- {gameover_status} -")
        stdscr.addstr(HEIGHT // 2 + 2, WIDTH // 2 - 7, "Press c to continue")
        key = stdscr.getch()
        while key != ord('c'):
            key = stdscr.getch()
        stdscr.refresh()

    def spawn_aliens(self):
        while len(self.aliens_to_spawn) > 0 and not self.victory and not self.defeat:
            with self.lock:
                alien = self.aliens_to_spawn.pop(0)
                self.aliens.append(alien)
                alien.start()
            time.sleep(ALIEN_SPAWN_INTERVAL)

    def handle_events(self, stdscr):
        key = stdscr.getch()
        if key == curses.KEY_LEFT:
            self.cannon.move_left()
        elif key == curses.KEY_RIGHT:
            self.cannon.move_right()
        elif key == ord(' '):
            if self.cannon.fire():
                x = WIDTH // 2
                y = HEIGHT - 1
                angle = self.cannon.angle
                rocket = Rocket(self, x, y, angle)
                self.rockets.append(rocket)
                rocket.start()
        elif key == ord('r'):
            reload_thread = threading.Thread(target=self.cannon.reload)
            reload_thread.start()

    def alien_landed(self, alien):
        with self.lock:
            if alien in self.aliens:
                self.aliens.remove(alien)
                self.aliens_landed += 1
                if self.aliens_landed > self.num_aliens / 2:
                    self.defeat = True

    def check_collisions(self, rocket):
        with self.lock:
            for alien in self.aliens:
                if rocket.x == alien.x and rocket.y == alien.y:
                    alien.destroy()
                    self.aliens.remove(alien)
                    self.rockets.remove(rocket)
                    self.aliens_defeated += 1
                    if self.aliens_defeated > self.num_aliens / 2:
                        self.victory = True
                    return

    def draw(self, stdscr):
        stdscr.clear()
        # Desenhar canhão
        match self.cannon.angle:
            case 0:
                 cannon_char = '_  '
            case 45:
                cannon_char = ' \\ '
            case 90:
                cannon_char = ' | '
            case 135:
                cannon_char = ' / '
            case 180:
                cannon_char = '  _'
        # Verificar se a posição do canhão está dentro dos limites da tela
        if 0 <= HEIGHT - 1 < HEIGHT and 0 <= WIDTH // 2 < WIDTH:
            stdscr.addstr(HEIGHT - 1, WIDTH // 2, cannon_char)
        
        # Desenhar foguetes
        with self.lock:
            for rocket in self.rockets:
                if 0 < rocket.y < HEIGHT and 0 < rocket.x < WIDTH:
                    stdscr.addstr(rocket.y, rocket.x, '¤')

        # Desenhar naves
        with self.lock:
            for alien in self.aliens:
                if 0 <= alien.y < HEIGHT and 0 <= alien.x < WIDTH:
                    stdscr.addstr(alien.y, alien.x, 'Ж')

        # Mostrar quantidade de foguetes
        stdscr.addstr(HEIGHT + 1, 0, f"Foguetes: {self.cannon.rockets}")
        stdscr.addstr(HEIGHT + 2, 0, "Aliens Restantes: " + " Ж " * (len(self.aliens_to_spawn) + len(self.aliens)))
        stdscr.addstr(HEIGHT + 3, 0, "Aliens Pousados: " + " O " * self.aliens_landed)
        stdscr.addstr(HEIGHT + 4, 0, "Aliens Derrotados: " + " X " * self.aliens_defeated)
        
        stdscr.refresh()


def menu(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(0)
    stdscr.clear()
    stdscr.addstr(HEIGHT // 2 - 2, WIDTH // 2 - 7, "Escolha a dificuldade")
    stdscr.addstr(HEIGHT // 2, WIDTH // 2 - 7, "1. Fácil")
    stdscr.addstr(HEIGHT // 2 + 1, WIDTH // 2 - 7, "2. Médio")
    stdscr.addstr(HEIGHT // 2 + 2, WIDTH // 2 - 7, "3. Difícil")
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == ord('1'):
            return "fácil"
        elif key == ord('2'):
            return "médio"
        elif key == ord('3'):
            return "difícil"


if __name__ == "__main__":
    while True:
        difficulty = curses.wrapper(menu)
        game = Game(difficulty)
        curses.wrapper(game.start)
