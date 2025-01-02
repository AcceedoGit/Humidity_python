from fastapi import WebSocket, APIRouter, HTTPException, Query, WebSocketDisconnect
from configuration.database import Board_1, Board_2, Board_3  # Assuming this is the DB connection setup
from typing import Optional, List
from backend.externalservice.schemas import BoardData
from backend.Graph.router import update_graph_collection
import logging
import json

BoardRouter = APIRouter()
logger = logging.getLogger("my_logger")

# Global list to keep track of connected WebSocket clients
connected_clients = []

# Mapping of unit_ID to corresponding board collections
BOARD_COLLECTIONS = {
    1: Board_1,
    2: Board_2,
    3: Board_3,
    # You can add more mappings here if needed
}

@BoardRouter.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # Accept the WebSocket connection
    connected_clients.append(websocket)  # Add the client to the connected clients list

    try:
        while True:
            message = await websocket.receive_text()  # Receive the message as a string
            logging.info(f"Received message: {message}")

            # Parse the message as JSON
            data = json.loads(message)  # Convert the JSON string to a dictionary
            unit_ID = int(data.get("unit_ID"))  # Get unit_ID from the parsed dictionary

            if unit_ID not in BOARD_COLLECTIONS:
                raise ValueError("Invalid unit_ID")

            # Handle the unit_ID message
            board_data = BOARD_COLLECTIONS[unit_ID].find_one({"unit_ID": unit_ID})

            if board_data:
                response = {
                    "unit_ID": board_data["unit_ID"],
                    "t": board_data["t"],
                    "h": board_data["h"],
                    "w": board_data["w"],
                    "eb": board_data["eb"],
                    "ups": board_data["ups"],
                    "x": board_data["x"],
                    "y": board_data["y"],
                }
                await send_to_all_clients(response)  # Send data to all connected clients
            else:
                await send_to_all_clients({"error": "Unit ID not found"})  # Notify all clients if unit_ID is not found

    except WebSocketDisconnect:
        logging.info(f"Client disconnected: {websocket.client}")
        connected_clients.remove(websocket)  # Remove client from the list

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()  # Ensure the connection is closed

async def send_to_all_clients(message: dict):
    for client in connected_clients:
        try:
            # Ensure the complete message with all necessary fields
            await client.send_json(message)
        except Exception as e:
            logging.error(f"Error sending message to client: {e}")
            if client in connected_clients:
                connected_clients.remove(client)  # Remove if failed


@BoardRouter.get("/api/v1/dashboard/create")
async def create_server(unit_ID: int):
    logger.info(f"Creating new server with unit_ID: {unit_ID}")
    
    # Check if the unit_ID is valid
    if unit_ID not in BOARD_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid unit_ID {unit_ID}")

    collection = BOARD_COLLECTIONS[unit_ID]
    existing_server = collection.find_one({"unit_ID": unit_ID})
    
    if existing_server:
        raise HTTPException(status_code=400, detail=f"Server with unit_ID {unit_ID} already exists")

    new_server = {
        "unit_ID": unit_ID,
        "t": 0,
        "h": 0,
        "w": 0,
        "eb": 0,
        "ups": 0,
        "x": 0,
        "y": 0
    }

    result = collection.insert_one(new_server)

    if result.acknowledged:
        logger.info(f"Server created successfully: {new_server}")
        await send_to_all_clients(new_server)  # Notify all connected clients about the new server
        return {"unit_ID": unit_ID, "status": "Server created successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to create server")

@BoardRouter.get("/api/v1/dashboard/{unit_ID}", response_model=BoardData)
async def get_and_update_dashboard(
    unit_ID: int,
    t: Optional[int] = Query(None, description="Temperature"),
    h: Optional[int] = Query(None, description="Humidity"),
    w: Optional[int] = Query(None, description="Water Level"),
    eb: Optional[int] = Query(None, description="External Board Value"),
    ups: Optional[int] = Query(None, description="UPS Status"),
    x: Optional[int] = Query(1, description="X value (default to 1)"),
    y: Optional[int] = Query(1, description="Y value (default to 1)")
):
    logger.info(f"Updating data for unit_ID: {unit_ID}")

    # Check if the unit_ID is valid
    if unit_ID not in BOARD_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Invalid unit_ID")

    collection = BOARD_COLLECTIONS[unit_ID]
    board_data = collection.find_one({"unit_ID": unit_ID})

    if board_data is None:
        raise HTTPException(status_code=404, detail="Data not found")

    # Update board values
    update_values = {
        "t": t if t is not None else board_data["t"],
        "h": h if h is not None else board_data["h"],
        "w": w if w is not None else board_data["w"],
        "eb": eb if eb is not None else board_data["eb"],
        "ups": ups if ups is not None else board_data["ups"],
        "x": x,
        "y": y,
        

    }

    # Update the document with new values
    result = collection.update_one({"unit_ID": unit_ID}, {"$set": update_values})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Failed to update data, unit_ID not found")

    logger.info(f"Board data updated successfully: {update_values}")

    # Update the Graph collection to store the temperature and humidity
    await update_graph_collection(unit_ID, t, h, w, eb, ups, x, y)

    await send_to_all_clients({
        "unit_ID": unit_ID,
        **update_values
    })

    return {
        "unit_ID": unit_ID,
        "status": "Data updated successfully",
        **update_values
    }

@BoardRouter.get("/api/v1/unitIDs", response_model=List[int])
def get_unit_ids():
    logger.info("Fetching all unit IDs")
    
    # Collect unit IDs from all board collections
    unit_ids = set()  # Use a set to avoid duplicates
    for collection in BOARD_COLLECTIONS.values():
        ids = [board["unit_ID"] for board in collection.find({}, {"unit_ID": 1})]
        unit_ids.update(ids)  # Add the IDs to the set

    unit_ids = list(unit_ids)  # Convert set back to list
    logger.info(f"Unit IDs retrieved: {unit_ids}")
    return unit_ids
