import asyncio
import websockets
import json

# Store active WebSocket connections
connected_clients = set()

# Store player data (player_id: position)
players = {}

async def handle_client(websocket, path):
    global players
    player_id = websocket.remote_address[1]  # Using the port number as a unique player ID
    connected_clients.add(websocket)
    players[player_id] = {"x": 400, "y": 300}  # Default starting position
    try:
        async for message in websocket:
            data = json.loads(message)
            # Update player position
            players[player_id] = {"x": data["x"], "y": data["y"]}

            # Broadcast all players' positions to all connected clients
            await broadcast_positions()
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {player_id} disconnected")
    finally:
        # Remove player on disconnect
        del players[player_id]
        connected_clients.remove(websocket)
        await broadcast_positions()

async def broadcast_positions():
    if players:
        message = json.dumps(players)
        # Send the message to all connected clients
        if connected_clients:  # Only broadcast if there are clients
            await asyncio.gather(*[client.send(message) for client in connected_clients])

async def main():
    async with websockets.serve(handle_client, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
