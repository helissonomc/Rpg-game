import math
import random
import pygame
import threading
import websocket
import json
import time
import uuid


# Constants
SCREEN_WIDTH = 800 * 2
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT_SIZE = 36
FRAMES_PER_SECOND = 60

# I added this normalizer because i want to all velocity be visually the same no matter the FPS
NORMALIZER = 60 / FRAMES_PER_SECOND

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Multiplayer Square')
font = pygame.font.SysFont(None, FONT_SIZE)
clock = pygame.time.Clock()


SPAWN_RECT_EVENT = pygame.USEREVENT + 1
CAN_SPAWN_PARTICLE = None
pygame.time.set_timer(SPAWN_RECT_EVENT, 17)  # milliseconds


class Particle:
    def __init__(self, position):
        self.position = position
        self.size = random.randint(4, 8)
        self.color = BLACK
        self.lifetime = 20  # frames
        self.velocity = [random.uniform(-1, 1), random.uniform(2, 5)]
        self.surface = pygame.Surface((self.size, self.size))
        self.fadeout_alpha = 255
        self.fadeout_rate = 120 / FRAMES_PER_SECOND

    def update(self):
        self.lifetime -= 1 * NORMALIZER
        self.position[0] += self.velocity[0] * random.uniform(-1, 1) * NORMALIZER
        self.position[1] += self.velocity[1] * random.uniform(-1, 0) * NORMALIZER
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
        self.last_position = None

    def move(self, keys):
        """Handle player movement based on arrow key input."""
        pos_x, pos_y = self.pos_x, self.pos_y
        if keys[pygame.K_LEFT]:
            pos_x = max(0, self.pos_x - self.speed * NORMALIZER)
        if keys[pygame.K_RIGHT]:
            pos_x = min(SCREEN_WIDTH - self.size, self.pos_x + self.speed * NORMALIZER)
        if keys[pygame.K_UP]:
            pos_y = max(0, self.pos_y - self.speed * NORMALIZER)
        if keys[pygame.K_DOWN]:
            pos_y = min(SCREEN_HEIGHT - self.size, self.pos_y + self.speed * NORMALIZER)

        self.update_position(pos_x, pos_y)

    def update_position(self, pos_x, pos_y):
        # I am adding this SPAWN_RECT_EVENT because i want to create the particales at the same rate no matter
        # The FPS
        global CAN_SPAWN_PARTICLE
        self.last_position = (self.pos_x, self.pos_y)
        if self.last_position != (pos_x, pos_y) and CAN_SPAWN_PARTICLE == SPAWN_RECT_EVENT:
            self.particles.append(Particle([pos_x + self.size / 2, pos_y + self.size]))
        self.pos_x, self.pos_y = pos_x, pos_y

    @property
    def center(self):
        return (self.pos_x + self.size / 2, self.pos_y + self.size / 2)

    def draw(self, screen):
        """Draw the player square and name on the screen."""
        pygame.draw.rect(screen, self.color, (self.pos_x, self.pos_y, self.size, self.size))
        text_surface = font.render(self.name, True, BLACK)  # Black text
        screen.blit(text_surface, (self.pos_x + self.size + 10, self.pos_y))  # Display name next to the square
        if self == local_player:
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
        time.sleep(1 / FRAMES_PER_SECOND)
        if local_player.last_position != (local_player.pos_x, local_player.pos_y):
            data = json.dumps({
                "name": local_player.name,
                "x": local_player.pos_x,
                "y": local_player.pos_y
            })
            ws.send(data)


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
                all_players[name].update_position(player_data["x"], player_data["y"])


def start_multiplayer_game():
    """Main multiplayer game loop with WebSocket using threads."""
    uri = "ws://localhost:8765"
    ws = websocket.WebSocket()
    ws.connect(uri)

    # Start threads for sending and receiving positions
    threading.Thread(target=send_player_position, args=(ws,), daemon=True).start()
    threading.Thread(target=receive_player_positions, args=(ws,), daemon=True).start()
    global CAN_SPAWN_PARTICLE
    running = True
    while running:
        CAN_SPAWN_PARTICLE = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == SPAWN_RECT_EVENT:
                CAN_SPAWN_PARTICLE = event.type

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
