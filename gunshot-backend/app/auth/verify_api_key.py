# Dictionary of allowed API keys (Store securely in a database in production)
from fastapi import FastAPI, Depends, HTTPException, Header

ALLOWED_KEYS = {
    "esp32-001": "DEFAULT_API_KEY_1234",
    "esp32-002": "API_KEY_ESP32_002",
}

async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in ALLOWED_KEYS.values():
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key  # Optionally return API key for further use