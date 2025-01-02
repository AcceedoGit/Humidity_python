from pydantic import BaseModel


class ServerData(BaseModel):
    unit_ID: int
    humidity_high: float
    humidity_low: float
    temp_high: float
    temp_low: float
    water_level_high: float
    water_level_low: float