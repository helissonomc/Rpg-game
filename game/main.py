import math
import random
import pygame
import threading
import websocket
import json
import time
import uuid
import spritesheet


# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT_SIZE = 36
FRAMES_PER_SECOND = 60

# I added this normalizer because i want to all velocity be visually the same no matter the FPS
NORMALIZER = 60 / FRAMES_PER_SECOND
TOGGLE_HITBOX = False

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Multiplayer Square')
font = pygame.font.SysFont(None, FONT_SIZE)
clock = pygame.time.Clock()


SPAWN_RECT_EVENT = pygame.USEREVENT + 1
CAN_SPAWN_PARTICLE = None
pygame.time.set_timer(SPAWN_RECT_EVENT, 17)  # milliseconds

# Ssprite
sprite_sheet_image_player = pygame.image.load('sprites/doux.png').convert_alpha()
sprite_sheet_player = spritesheet.SpriteSheet(sprite_sheet_image_player)

sprites_sword = []
for i in range(1, 7):
    image = pygame.image.load(f'sprites/Sprite-000{i}.png').convert_alpha()
    sprites_sword.append(image)


class Particle:
    def __init__(self, position):
        self.position = position
        self.size = random.randint(2, 4)
        self.color = (119, 64, 1)
        self.lifetime = 20  # frames
        self.velocity = [random.uniform(-1, 1), random.uniform(2, 5)]
        self.surface = pygame.Surface((self.size, self.size))
        self.surface.fill(self.color)
        self.fadeout_alpha = 255
        self.fadeout_rate = 900 / FRAMES_PER_SECOND

    def update(self):
        self.lifetime -= 1 * NORMALIZER
        self.position[0] += self.velocity[0] * random.uniform(-1, 1) * NORMALIZER
        self.position[1] += self.velocity[1] * random.uniform(-1, 0) * NORMALIZER
        self.fadeout_alpha -= self.fadeout_rate
        self.surface.set_alpha(self.fadeout_alpha)

    def draw(self, screen):
        screen.blit(self.surface, (self.position[0], self.position[1]))


class Player(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, name: str):
        super().__init__()
        self.pos_x = x
        self.pos_y = y
        self.name = name
        self.color = (255, 0, 0)  # Default color red
        self.speed = 4

        self.particles = []
        self.last_position = (0, 0, 0)

        self.sprites_stopped = []
        self.sprites_stopped.append((sprite_sheet_player.get_image(0, 24, 24, 3, BLACK)))
        self.sprites_stopped.append((sprite_sheet_player.get_image(1, 24, 24, 3, BLACK)))
        self.sprites_stopped.append((sprite_sheet_player.get_image(2, 24, 24, 3, BLACK)))
        self.sprites_stopped.append((sprite_sheet_player.get_image(3, 24, 24, 3, BLACK)))

        self.sprites_walking = []
        self.sprites_walking.append((sprite_sheet_player.get_image(6, 24, 24, 3, BLACK)))
        self.sprites_walking.append((sprite_sheet_player.get_image(7, 24, 24, 3, BLACK)))
        self.sprites_walking.append((sprite_sheet_player.get_image(8, 24, 24, 3, BLACK)))
        self.sprites_walking.append((sprite_sheet_player.get_image(9, 24, 24, 3, BLACK)))

        self.current_player_sprite = 0
        self.current_sword_sprite = 0
        self.player_image = self.sprites_stopped[self.current_player_sprite]
        self.sword_image = sprites_sword[self.current_sword_sprite]
        self.sword_rect = self.sword_image.get_rect()
        self.player_rect = self.player_image.get_rect()

        self.hitbox = self.player_image.get_bounding_rect(min_alpha=1)

        self.weapon_range = self.hitbox.height * 1.05
        self.player_rect.topleft = [self.pos_x, self.pos_y]

        self.sword_pivot = pygame.Vector2(self.hitbox.x + self.hitbox.width // 2, self.hitbox.y + self.hitbox.height // 2)

        self.is_walking_right = False
        self.is_walking_left = False
        self.is_walking_up = False
        self.is_walking_down = False
        self.is_facing_left = False
        ## Other player
        self.last_time_walking = 0

    @property
    def hitbox_position(self):
        x_readjustiment = (self.player_rect.width - self.hitbox.width) // 2
        y_readjustiment = (self.player_rect.height - self.hitbox.height) // 2
        return [self.pos_x + x_readjustiment, self.pos_y + y_readjustiment + 1]

    def move(self, keys):
        """Handle player movement based on arrow key input."""
        pos_x, pos_y = self.pos_x, self.pos_y
        if keys[pygame.K_LEFT]:
            self.is_facing_left = True
            self.is_walking_left = self.hitbox.x > self.speed
            pos_x -= self.speed if self.is_walking_left else self.hitbox.x
        elif keys[pygame.K_RIGHT]:
            self.is_facing_left = False
            self.is_walking_right = (self.hitbox.x + self.hitbox.width + self.speed < SCREEN_WIDTH)
            pos_x += self.speed if self.is_walking_right else SCREEN_WIDTH - (self.hitbox.x + self.hitbox.width)
        else:
            self.is_walking_left = self.is_walking_right = False

        if keys[pygame.K_UP]:
            self.is_walking_up = self.hitbox.y > self.speed
            pos_y -= self.speed if self.is_walking_up else self.hitbox.y
        elif keys[pygame.K_DOWN]:
            self.is_walking_down = (self.hitbox.y + self.hitbox.height + self.speed < SCREEN_HEIGHT)
            pos_y += self.speed if self.is_walking_down else SCREEN_HEIGHT - (self.hitbox.y + self.hitbox.height)
        else:
            self.is_walking_up = self.is_walking_down = False

        self.update_position(pos_x, pos_y)

    def update_position(self, pos_x, pos_y):
        # I am adding this SPAWN_RECT_EVENT because i want to create the particales at the same rate no matter
        # The FPS
        global CAN_SPAWN_PARTICLE
        self.last_position = (self.pos_x, self.pos_y)

        if self.last_position != (pos_x, pos_y) and CAN_SPAWN_PARTICLE == SPAWN_RECT_EVENT:
            self.particles.append(Particle([self.hitbox.x + self.hitbox.width / 2, self.hitbox.y + self.hitbox.height]))

        self.pos_x, self.pos_y = pos_x, pos_y
        self.player_rect.topleft = [self.pos_x, self.pos_y]
        self.hitbox.topleft = self.hitbox_position
        self.sword_pivot[0] = self.hitbox.x + self.hitbox.width // 2
        self.sword_pivot[1] = self.hitbox.y + self.hitbox.height // 2

    @property
    def center(self):
        return (self.hitbox.x + self.hitbox.width / 2, self.hitbox.y + self.hitbox.height / 1.5)

    def update_sprite(self):
        self.current_player_sprite += 10 / FRAMES_PER_SECOND
        self.current_sword_sprite += 10 / FRAMES_PER_SECOND

        sprites = self.sprites_stopped
        if (
            self.is_walking_down or
            self.is_walking_up or
            self.is_walking_left or
            self.is_walking_right or
            (self != local_player and pygame.time.get_ticks() - self.last_time_walking < 100)
        ):
            sprites = self.sprites_walking

        if self.current_player_sprite >= len(sprites):
            self.current_player_sprite = 0
        if self.current_sword_sprite >= len(sprites_sword):
            self.current_sword_sprite = 0

        self.sword_image = sprites_sword[int(self.current_sword_sprite)]
        player_image = sprites[int(self.current_player_sprite)]

        if self.is_facing_left:
            self.player_image = pygame.transform.flip(player_image, True, False).convert_alpha()
        else:
            self.player_image = player_image

    def draw(self, screen):
        """Draw the player square and name on the screen."""
        if TOGGLE_HITBOX:
            pygame.draw.rect(screen, (255, 0, 0), self.hitbox, 1)

        screen.blit(self.player_image, self.player_rect)
        text_surface = font.render(self.name, True, BLACK)  # Black text
        screen.blit(text_surface, (self.pos_x + self.hitbox.width + 10, self.pos_y))
        if self == local_player:
            self._draw_weapon_range(screen)

    def _draw_weapon_range(self, screen):
        """Draw the weapon range line from the player's center to the mouse cursor."""
        mouse_pos = pygame.mouse.get_pos()
        mouse_offset = mouse_pos - self.sword_pivot
        mouse_angle = -math.degrees(math.atan2(mouse_offset.y, mouse_offset.x)) - 90

        pos = self.sword_pivot + (0, -self.sword_rect.height//2)

        image, rect = rotate_on_pivot(self.sword_image, mouse_angle, self.sword_pivot, pos)
        if TOGGLE_HITBOX:
            pygame.draw.rect(screen, (255, 0, 0), rect, 1)
        screen.blit(image, rect)


def rotate_on_pivot(image, angle, pivot, origin):

    surf = pygame.transform.rotate(image, angle)

    offset = pivot + (origin - pivot).rotate(-angle)
    rect = surf.get_rect(center=offset)

    return surf, rect


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
                if all_players[name].last_position != (player_data["x"], player_data["y"]):
                    all_players[name].last_time_walking = pygame.time.get_ticks()
                    all_players[name].is_facing_left = player_data["x"] < all_players[name].last_position[0]

                all_players[name].update_position(player_data["x"], player_data["y"])


def start_multiplayer_game():
    """Main multiplayer game loop with WebSocket using threads."""
    uri = "ws://localhost:8765"
    ws = websocket.WebSocket()
    ws.connect(uri)
    ws.send(
        json.dumps({
            "name": local_player.name,
            "x": local_player.pos_x,
            "y": local_player.pos_y
        })
    )
    # Start threads for sending and receiving positions
    threading.Thread(target=send_player_position, args=(ws,), daemon=True).start()
    threading.Thread(target=receive_player_positions, args=(ws,), daemon=True).start()
    global CAN_SPAWN_PARTICLE, TOGGLE_HITBOX
    toggle_hitbox_cool_down = 500  # millisecond
    toggle_hitbox_lasttime_clicked = 0
    running = True
    while running:
        CAN_SPAWN_PARTICLE = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == SPAWN_RECT_EVENT:
                CAN_SPAWN_PARTICLE = event.type

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            current_time = pygame.time.get_ticks()
            if current_time - toggle_hitbox_lasttime_clicked > toggle_hitbox_cool_down:
                TOGGLE_HITBOX = not TOGGLE_HITBOX
                toggle_hitbox_lasttime_clicked = current_time

        local_player.move(keys)

        screen.fill(WHITE)
        # Draw all players
        for player in all_players.values():
            player.update_sprite()
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
