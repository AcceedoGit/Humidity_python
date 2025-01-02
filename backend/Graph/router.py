from fastapi import FastAPI, WebSocket, APIRouter, Query
from typing import List, Optional, Dict
from datetime import datetime, date ,timedelta ,timezone
import pytz
from configuration.database import Board_1, Board_2, Board_3
from collections import defaultdict

app = FastAPI()
GraphRouter = APIRouter()

# Map unit_IDs to their corresponding collections
BOARD_COLLECTIONS = {
    1: Board_1,
    2: Board_2,
    3: Board_3,
}

# Define the IST timezone
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.utc

# Store connected clients and data history
clients = defaultdict(list)
data_history = defaultdict(list)  # Store history per unit

# Function to update the collection and broadcast the latest data
async def update_graph_collection(
    unit_ID: int, t: Optional[int], h: Optional[int], w: Optional[int],
    eb: Optional[int], ups: Optional[int], x: Optional[int], y: Optional[int]
):
    if unit_ID not in BOARD_COLLECTIONS:
        raise ValueError(f"Invalid unit_ID: {unit_ID}")

    collection = BOARD_COLLECTIONS[unit_ID]
    now_ist = datetime.now(IST)  # Get current time in IST

    # Create the log entry with IST time
    log_entry = {
        "unit_ID": unit_ID,
        "t": t,
        "h": h,
        "w": w,
        "eb": eb,
        "ups": ups,
        "x": x,
        "y": y,
        "created_at": now_ist.replace(tzinfo=None),  # Remove timezone info
        "updated_at": now_ist.replace(tzinfo=None),  # Remove timezone info
    }

    # Insert the log entry into the database
    result = collection.insert_one(log_entry)
    
    # Store the entry in data history for future broadcasts
    data_history[unit_ID].append(log_entry)

    # Broadcast the latest graph data to clients
    await broadcast_graph_data(unit_ID)

    return {"status": "success", "inserted_id": str(result.inserted_id)}


async def broadcast_graph_data(unit_ID: int):
    if unit_ID not in clients:
        return  # No clients connected for this unit_ID

    collection = BOARD_COLLECTIONS[unit_ID]

    # Get the current time in IST
    now = datetime.now(IST)

    # Calculate the start and end times (8:30 AM to next day 8:29:59 AM)
    start_of_window = now.replace(hour=14, minute=00, second=0, microsecond=0)
    end_of_window = (start_of_window + timedelta(days=1)).replace(hour=13, minute=29, second=59, microsecond=999999)

    # Convert to UTC before querying MongoDB
    start_of_window_utc = start_of_window.astimezone(timezone.utc)
    end_of_window_utc = end_of_window.astimezone(timezone.utc)

    # Fetch data for the given window
    data = collection.find({
        "created_at": {
            "$gte": start_of_window_utc,
            "$lt": end_of_window_utc
        }
    }).sort("created_at", 1)

    response = [['Time', 'Humidity', 'Temperature']]
    
    # Prepare response with IST-converted timestamps
    for entry in data:
        time = entry["created_at"].astimezone(IST).isoformat()
        humidity = entry.get("h", 0)
        temperature = entry.get("t", 0)
        response.append([time, humidity, temperature])

    # Send the filtered graph data to all connected clients
    message = {"data": response}
    for client in clients[unit_ID]:
        await client.send_json(message)

# WebSocket endpoint to handle real-time data
@GraphRouter.websocket("/ws/graphdata/{unit_ID}")
async def websocket_endpoint(websocket: WebSocket, unit_ID: int):
    await websocket.accept()
    print(f"WebSocket connection established for unit_ID: {unit_ID}")

    clients[unit_ID].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()  # Receive data from client
            print(f"Received data: {data}")

            # Add new data to the history and broadcast it to clients
            data_history[unit_ID].append(data)
            for client in clients[unit_ID]:
                await client.send_json(data_history[unit_ID])
    except Exception as e:
        print(f"WebSocket connection closed: {e}")
    finally:
        clients[unit_ID].remove(websocket)
        if not clients[unit_ID]:  # Clean up if no clients remain
            del clients[unit_ID]

@GraphRouter.get("/api/v1/graphdata/{unit_ID}")
async def get_graph_data(unit_ID: int, start_time: Optional[str] = None, end_time: Optional[str] = None):
    if unit_ID not in BOARD_COLLECTIONS:
        return {"error": "Invalid unit ID"}

    collection = BOARD_COLLECTIONS[unit_ID]

    # Parse start and end times from the query parameters
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError:
        return {"error": "Invalid date format"}

    # Query MongoDB with parsed UTC times
    data = collection.find({
        "created_at": {
            "$gte": start_dt,
            "$lt": end_dt
        }
    }).sort("created_at", 1)

    # Prepare the response with IST-converted timestamps
    response = [['Time', 'Humidity', 'Temperature']]
    for entry in data:
        time = entry["created_at"].astimezone(IST).isoformat()
        humidity = entry.get("h", 0)
        temperature = entry.get("t", 0)
        response.append([time, humidity, temperature])

    return {"data": response}

#http://192.168.0.84:9001/api/v1/graphdata/1?start_time=2024-10-16T08:30:00Z&end_time=2024-10-17T08:29:59Z
