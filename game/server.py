import asyncio
import websockets
import json

# Store active WebSocket connections
connected_clients = set()

# Store player data (player_id: position)
all_players = {}

class EventsEnum:
    player_moved = "player_moved"
    player_disconneted = "player_disconnected" 

async def handle_client(websocket, path):
    global all_players
    player_id = websocket.remote_address[1]  # Using the port number as a unique player ID
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            # Update player position
            all_players[player_id] = {
                "x": data["x"],
                "y": data["y"],
                "name": data["name"],
                "type": data["type"],
            }

            # Broadcast all players' positions to all connected clients
            await broadcast_positions()
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {player_id} disconnected")
    finally:
        # Remove player on disconnect
        all_players[player_id]["type"] = EventsEnum.player_disconneted
        connected_clients.remove(websocket)
        await broadcast_positions()
        del all_players[player_id]

async def broadcast_positions():
    if all_players:
        message = json.dumps(all_players)
        # Send the message to all connected clients
        if connected_clients:  # Only broadcast if there are clients
            await asyncio.gather(*[client.send(message) for client in connected_clients])

async def main():
    async with websockets.serve(handle_client, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
