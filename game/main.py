import math
import random
import pygame
import threading
import websocket
import json
import time
import uuid


LAST_POSITION = (0, 0)
# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT_SIZE = 36
FRAMES_PER_SECOND = 60

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Multiplayer Square')
font = pygame.font.SysFont(None, FONT_SIZE)
clock = pygame.time.Clock()

# Global lists


class Particle:
    def __init__(self, position):
        self.position = position
        self.size = random.randint(4, 8)
        self.color = BLACK
        self.lifetime = FRAMES_PER_SECOND / 3  # frames
        self.velocity = [random.uniform(-1, 1), random.uniform(2, 5)]
        self.surface = pygame.Surface((self.size, self.size))
        self.fadeout_alpha = 255
        self.fadeout_rate = 20

    def update(self):
        self.lifetime -= 1
        self.position[0] += self.velocity[0] * random.uniform(-1, 1)
        self.position[1] += self.velocity[1] * random.uniform(-1, 0)
        self.fadeout_alpha -= self.fadeout_rate
        self.surface.set_alpha(self.fadeout_alpha)

    def draw(self, screen):
        screen.blit(self.surface, (self.position[0], self.position[1]))


class Player:
    def __init__(self, x: float, y: float, name: str):
        self.pos_x = x
        self.pos_y = y
        self.name = name
        self.color = (255, 0, 0)  # Default color red
        self.size = 50.0
        self.speed = 5
        self.weapon_range = self.size * 1.05
        self.particles = []

    def move(self, keys):
        """Handle player movement based on arrow key input."""
        global LAST_POSITION
        if LAST_POSITION != (self.pos_x, self.pos_y):
            self.particles.append(Particle([self.pos_x + self.size / 2, self.pos_y + self.size]))

        LAST_POSITION = (self.pos_x, self.pos_y)

        if keys[pygame.K_LEFT]:
            self.pos_x = max(0, self.pos_x - self.speed)
        if keys[pygame.K_RIGHT]:
            self.pos_x = min(SCREEN_WIDTH - self.size, self.pos_x + self.speed)
        if keys[pygame.K_UP]:
            self.pos_y = max(0, self.pos_y - self.speed)
        if keys[pygame.K_DOWN]:
            self.pos_y = min(SCREEN_HEIGHT - self.size, self.pos_y + self.speed)

    @property
    def center(self):
        return (self.pos_x + self.size / 2, self.pos_y + self.size / 2)

    def draw(self, screen):
        """Draw the player square and name on the screen."""
        pygame.draw.rect(screen, self.color, (self.pos_x, self.pos_y, self.size, self.size))
        text_surface = font.render(self.name, True, BLACK)  # Black text
        screen.blit(text_surface, (self.pos_x + self.size + 10, self.pos_y))  # Display name next to the square
        self._draw_weapon_range(screen)

    def _draw_weapon_range(self, screen):
        """Draw the weapon range line from the player's center to the mouse cursor."""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        player_center = self.center
        angle = math.atan2(mouse_y - player_center[1], mouse_x - player_center[0])

        end_x = player_center[0] + self.weapon_range * math.cos(angle)
        end_y = player_center[1] + self.weapon_range * math.sin(angle)
        pygame.draw.line(screen, BLACK, player_center, (end_x, end_y), 2)


# Create the local player instance
# This UUID is only for us to not update manually when testing multiplayer :D
local_player_name = uuid.uuid4().hex[:5]
local_player = Player(x=400, y=300, name=local_player_name)

# Store positions of all players as Player objects
all_players = {local_player_name: local_player}


# WebSocket functions using threads
def send_player_position(ws):
    """Send player's current position to the server."""
    while True:
        if LAST_POSITION != (local_player.pos_x, local_player.pos_y):
            data = json.dumps({
                "name": local_player.name,
                "x": local_player.pos_x,
                "y": local_player.pos_y
            })
            ws.send(data)
            time.sleep(1 / 100)


def receive_player_positions(ws):
    """Receive positions of other players from the server."""
    global all_players
    while True:
        message = ws.recv()
        players_data = json.loads(message)
        for player_data in players_data.values():
            name = player_data["name"]
            if name not in all_players:
                all_players[name] = Player(x=player_data["x"], y=player_data["y"], name=name)
            else:
                all_players[name].pos_x = player_data["x"]
                all_players[name].pos_y = player_data["y"]


def start_multiplayer_game():
    """Main multiplayer game loop with WebSocket using threads."""
    uri = "ws://localhost:8765"
    ws = websocket.WebSocket()
    ws.connect(uri)

    # Start threads for sending and receiving positions
    threading.Thread(target=send_player_position, args=(ws,), daemon=True).start()
    threading.Thread(target=receive_player_positions, args=(ws,), daemon=True).start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        local_player.move(keys)

        screen.fill(WHITE)

        # Draw all players
        for player in all_players.values():
            player.draw(screen)
            # Update and draw particles
            for particle in player.particles:
                particle.update()
                particle.draw(screen)
                if particle.lifetime <= 0:
                    player.particles.remove(particle)

        # Calculate and display FPS
        fps = clock.get_fps()
        fps_text = font.render(f"FPS: {int(fps)}", True, BLACK)
        screen.blit(fps_text, (10, 10))

        # Update the display
        pygame.display.flip()
        clock.tick(FRAMES_PER_SECOND)

    pygame.quit()


if __name__ == '__main__':
    start_multiplayer_game()
