import pygame
import threading
import websocket
import json
import logging
import time

_LOGGER = logging.getLogger(__name__)
LAST_POSITION = (0, 0)
# Define the Player class
class Player:
    def __init__(self, pos_x: float, pos_y: float, name: str):
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.name = name
        self.color = (255, 0, 0)  # Default color red
        self.size = 50.0
        self.speed = 5

    def move(self, keys):
        """Handle player movement based on arrow key input."""
        global LAST_POSITION
        LAST_POSITION = self.pos_x, self.pos_y
        if keys[pygame.K_LEFT]:
            self.pos_x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.pos_x += self.speed
        if keys[pygame.K_UP]:
            self.pos_y -= self.speed
        if keys[pygame.K_DOWN]:
            self.pos_y += self.speed

    def draw(self, screen, font):
        """Draw the player square and name on the screen."""
        # Draw the square
        pygame.draw.rect(screen, self.color, (self.pos_x, self.pos_y, self.size, self.size))
        # Render and draw the player's name
        text_surface = font.render(self.name, True, (0, 0, 0))  # Black text
        screen.blit(text_surface, (self.pos_x + self.size + 10, self.pos_y))  # Display name next to the square


# Initialize Pygame
pygame.init()

# Screen dimensions
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Multiplayer Square')

# Colors (RGB)
WHITE = (255, 255, 255)

# Font settings
font = pygame.font.SysFont(None, 36)  # None uses default font, 36 is the size

# Clock to control the frame rate
clock = pygame.time.Clock()

# Create the local player instance
local_player = Player(pos_x=400, pos_y=300, name="")

# Store positions of other players as Player objects
other_players = {}

fms = 60
# WebSocket functions using threads
def send_position(ws):
    """Send player's current position to the server."""
    while True:
        if LAST_POSITION == (local_player.pos_x,  local_player.pos_y):
            continue
        data = json.dumps({"name": local_player.name, "x": local_player.pos_x, "y": local_player.pos_y})
        ws.send(data)
        time.sleep(1/fms)  # Send data every 100 ms

def receive_positions(ws):
    """Receive positions of other players from the server."""
    global other_players
    while True:
        message = ws.recv()
        players_data = json.loads(message)
        for player_id, position in players_data.items():

            if player_id not in other_players:
                # Create a new player if not already present
                other_players[player_id] = Player(pos_x=position["x"], pos_y=position["y"], name=player_id)
            else:
                # Update the existing player's position
                other_players[player_id].pos_x = position["x"]
                other_players[player_id].pos_y = position["y"]

def multiplayer_game():
    """Main multiplayer game loop with WebSocket using threads."""
    uri = "ws://localhost:8765"
    ws = websocket.WebSocket()
    ws.connect(uri)

    # Start threads for sending and receiving positions
    threading.Thread(target=send_position, args=(ws,), daemon=True).start()
    threading.Thread(target=receive_positions, args=(ws,), daemon=True).start()

    # Main game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Get the current state of the arrow keys
        keys = pygame.key.get_pressed()

        # Move the local player based on key input
        local_player.move(keys)

        # Fill the screen with white to erase previous frames
        screen.fill(WHITE)

        # Draw other players
        for player in other_players.values():
            player.draw(screen, font)

        # Update the display
        pygame.display.flip()

        # Control the frame rate (60 frames per second)
        clock.tick(fms)

    pygame.quit()

# Run the game loop
multiplayer_game()

