import numpy as np
from scipy.optimize import minimize

def estimate_gunshot_location(group):
    if len(group) < 3:
        raise ValueError("At least three sensor logs are required to estimate the gunshot location.")

    SPEED_OF_SOUND = 343.0  # meters per second

    def latlon_to_meters(lat1, lon1, lat2, lon2):
        """Convert lat/lon differences to meters using Haversine approximation."""
        lat_diff = (lat2 - lat1) * 111320  # Rough conversion for latitude (meters)
        lon_diff = (lon2 - lon1) * (111320 * np.cos(np.radians(lat1)))  # Adjusted for longitude
        return np.sqrt(lat_diff**2 + lon_diff**2)

    # Normalize timestamps to seconds relative to the earliest log
    t0 = min(log.timestamp for log in group) / 1e6  # Convert to seconds
    normalized_logs = [
        {"lat": log.lat, "lon": log.lon, "timestamp": log.timestamp / 1e6 - t0} 
        for log in group
    ]

    def error_function(params):
        x, y, t = params  # Estimated gunshot latitude, longitude, and time
        errors = []
        for log in normalized_logs:
            distance = latlon_to_meters(log["lat"], log["lon"], x, y)
            expected_time = t + (distance / SPEED_OF_SOUND)
            errors.append((log["timestamp"] - expected_time) ** 2)
        return sum(errors)

    # Improved initial guess
    initial_lat = np.median([log["lat"] for log in normalized_logs])
    initial_lon = np.median([log["lon"] for log in normalized_logs])
    initial_time = np.median([log["timestamp"] for log in normalized_logs])

    initial_guess = (initial_lat, initial_lon, initial_time)

    # Optimization with better method
    result = minimize(
        error_function,
        initial_guess,
        method='Powell',
        bounds=[(min(log["lat"] for log in normalized_logs), max(log["lat"] for log in normalized_logs)),
                (min(log["lon"] for log in normalized_logs), max(log["lon"] for log in normalized_logs)),
                (min(log["timestamp"] for log in normalized_logs), max(log["timestamp"] for log in normalized_logs))]
    )

    if not result.success:
        raise RuntimeError("Optimization failed to converge.")

    estimated_lat, estimated_lon, estimated_time = result.x

    print(f"Estimated location: lat={estimated_lat}, lon={estimated_lon}, time={int((estimated_time + t0) * 1e6)}")

    return {"lat": estimated_lat, "lon": estimated_lon, "time": int((estimated_time + t0) * 1e6)}  # Convert back to microseconds
