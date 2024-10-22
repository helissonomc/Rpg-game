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
            if self.pos_x > self.speed:
                self.pos_x -= self.speed
            else:
                self.pos_x -= self.pos_x
                print(self.pos_x)
        if keys[pygame.K_RIGHT]:
            if self.pos_x + self.size + self.speed < screen_width:
                self.pos_x += self.speed
            else:
                self.pos_x = screen_width - self.size
                print(self.pos_x)
        if keys[pygame.K_UP]:
            if self.pos_y > self.speed:
                self.pos_y -= self.speed
            else:
                self.pos_y -= self.pos_y
                print(self.pos_y)
        if keys[pygame.K_DOWN]:
            if self.pos_y + self.size + self.speed < screen_height:
                self.pos_y += self.speed
            else:
                self.pos_y = screen_height - self.size
                print(self.pos_y)


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
local_player = Player(pos_x=400, pos_y=300, name="test")

# Store positions of all players as Player objects
all_players = {"test": local_player}

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
    global all_players
    while True:
        message = ws.recv()
        players_data = json.loads(message)
        for _, player_data in players_data.items():
            name = player_data["name"]
            if name not in all_players:
                # Create a new player if not already present
                all_players[name] = Player(pos_x=player_data["x"], pos_y=player_data["y"], name=name)
            else:
                # Update the existing player's position
                all_players[name].pos_x = player_data["x"]
                all_players[name].pos_y = player_data["y"]

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
        for player in all_players.values():
            player.draw(screen, font)
        # Update the display
        pygame.display.flip()

        # Control the frame rate (60 frames per second)
        clock.tick(fms)

    pygame.quit()
# Run the game loop
multiplayer_game()
