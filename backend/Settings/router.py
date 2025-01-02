from fastapi import APIRouter, HTTPException
from configuration.database import setting, Board_1 ,Board_3,Board_2# Import both collections
from backend.Settings.schemas import ServerData
from backend.externalservice.router import send_to_all_clients
import logging

serverRouter = APIRouter()
logger = logging.getLogger("my_logger")

# WebSocket Connections
connected_websockets = []  # To hold connected WebSocket clients

async def broadcast_new_server(message: dict):
    for websocket in connected_websockets:
        await websocket.send_json(message)



# SETTINGS PAGE
@serverRouter.get("/api/v1/settings")
async def get_servers():
    servers = list(setting.find())  # Fetch all server data from the collection
    for srv in servers:
        srv['_id'] = str(srv['_id'])  # Convert ObjectId to string for JSON serialization
    return {"servers": servers}


def get_board_collection(unit_ID: int):
    if unit_ID == 1:
        return Board_1
    elif unit_ID == 2:
        return Board_2
    elif unit_ID == 3:
        return Board_3
    else:
        raise ValueError(f"Invalid unit_ID: {unit_ID}")

# Add Server
@serverRouter.post("/api/v1/settings/add_server")
async def add_server(data: ServerData):
    # Convert the Pydantic model to a dictionary
    server_dict = data.dict()

    # Assign unit_ID if not provided
    existing_servers = list(setting.find())
    if not data.unit_ID:
        if existing_servers:
            unit_ID = max(server['unit_ID'] for server in existing_servers) + 1
        else:
            unit_ID = 1  # Start with unit_ID 1 if no servers exist
        server_dict['unit_ID'] = unit_ID
    else:
        unit_ID = data.unit_ID

    # Check for duplicate unit_ID
    if setting.find_one({"unit_ID": unit_ID}):
        raise HTTPException(status_code=400, detail=f"Server with unit_ID {unit_ID} already exists")

    # Insert the server data into the 'Server' collection
    setting.insert_one(server_dict)

    # Create a new entry in the corresponding Board collection
    board_entry = {
        "unit_ID": unit_ID,
        "t": 0,  # Default temperature
        "h": 0,  # Default humidity
        "w": 0,  # Default water level
        "eb": 0,  # Default External Board Value
        "ups": 0,  # Default UPS Status
        "x": 0,
        "y": 0
    }
    
    # Insert board entry into the respective Board collection
    collection = get_board_collection(unit_ID)
    collection.insert_one(board_entry)

    # Notify all connected clients (via WebSocket or other mechanisms)
    await send_to_all_clients(board_entry)

    # Return a success response
    return {"message": "Server and corresponding Board entry added successfully", "unit_ID": unit_ID}

# Edit Server
@serverRouter.put("/api/v1/settings/update_server/{unit_ID}")
async def update_server(unit_ID: int, data: ServerData):
    result = setting.update_one(
        {"unit_ID": unit_ID}, 
        {"$set": data.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"message": "Server updated successfully"}

# Delete Server
@serverRouter.delete("/api/v1/settings/delete_server/{unit_ID}")
async def delete_server(unit_ID: int):
    # Delete the server from the settings collection
    result = setting.delete_one({"unit_ID": unit_ID})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Server not found in settings")

    # Determine the correct board collection based on unit_ID
    collection = get_board_collection(unit_ID)

    # Additionally, delete the corresponding board entry from the correct Board collection
    board_result = collection.delete_one({"unit_ID": unit_ID})

    if board_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Board entry not found for the given unit_ID")

    return {"message": "Server and corresponding Board entry deleted successfully"}

