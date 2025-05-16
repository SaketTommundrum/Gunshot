import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap, Circle } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const BASE_URL = "http://127.0.0.1:8000";

const eventIcon = new L.Icon({
  iconUrl: "/images/marker-icon.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

const gunshotIcon = new L.Icon({
  iconUrl: "/images/marker-icon-red.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

export default function GunshotMap() {
  const [sensors, setSensors] = useState([]);
  const [gunshotLocations, setGunshotLocations] = useState([]);
  const [mapCenter, setMapCenter] = useState([37.7749, -122.4194]);
  const [userTriggeredCenter, setUserTriggeredCenter] = useState(false);
  const [timestamps, setTimestamps] = useState([]);
  const [selectedTimestamp, setSelectedTimestamp] = useState(null);
  const [allLogs, setAllLogs] = useState([]);
  const [triggeredMicIds, setTriggeredMicIds] = useState([]);

  useEffect(() => {
    fetchSensors();
    fetchTimestamps();
    let ws;

    const connectWebSocket = () => {
      ws = new WebSocket(`ws://127.0.0.1:8000/ws`);

      ws.onopen = () => console.log("WebSocket connected");
      ws.onmessage = (event) => {
        console.log("Message received:", event.data);
        const data = JSON.parse(event.data);
        if (data.type === "sensor_update") {
          setSensors(data.sensors);
        } else if (data.gunshot_events) {
          const currentTimeMicro = Date.now() * 1000;
          const recentEvents = data.gunshot_events.filter((event) => {
            const eventTimeMicro = event.estimated_location.time;
            return currentTimeMicro - eventTimeMicro <= 10 * 1_000_000;
          });

          setGunshotLocations((prevLocations) => {
            const filteredLocations = prevLocations.filter((gunshot) => {
              const eventTimeMicro = gunshot.estimated_location.time;
              return currentTimeMicro - eventTimeMicro <= 10 * 1_000_000;
            });
            return [...filteredLocations, ...recentEvents];
          });
        }
      };
      ws.onerror = (error) => console.error("WebSocket error:", error);
      ws.onclose = (event) => {
        console.log("WebSocket closed:", event.reason);
        setTimeout(connectWebSocket, 5000);
      };
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const fetchSensors = async () => {
    try {
      const response = await fetch(`${BASE_URL}/get_sensors`);
      if (!response.ok) throw new Error("Failed to fetch sensors");
      const data = await response.json();
      setSensors(data);
    } catch (error) {
      console.error("Error fetching sensors:", error);
      setSensors([]);
    }
  };

  const fetchTimestamps = async () => {
    try {
      const response = await fetch(`${BASE_URL}/get_all_logs`);
      if (!response.ok) throw new Error("Failed to fetch timestamps");
      const data = await response.json();
      setAllLogs(data); // ✅ store all logs

      const uniqueTimestamps = [...new Set(data.map(log => log.timestamp))];
      uniqueTimestamps.sort((a, b) => b - a);
      setTimestamps(uniqueTimestamps);
    } catch (error) {
      console.error("Error fetching timestamps:", error);
      setTimestamps([]);
    }
  };

  // Update triggered mic IDs when timestamp changes
  useEffect(() => {
    if (!selectedTimestamp || allLogs.length === 0) {
      setTriggeredMicIds([]);
      return;
    }

    const matchingMicIds = allLogs
      .filter(log => Math.abs(log.timestamp - selectedTimestamp) <= 1)
      .map(log => log.mic_id);

    setTriggeredMicIds(matchingMicIds);
  }, [selectedTimestamp, allLogs]);

  const estimateConfidenceRadius = (gunshot) => {
    const speedOfSound = 343;
    const timeError = 0.100;
    const radius = speedOfSound * timeError;
    const timestampMs = gunshot.estimated_location.time / 1000;
    const localTime = new Date(timestampMs).toLocaleString();

    return {
      lat: gunshot.estimated_location.lat,
      lon: gunshot.estimated_location.lon,
      confidenceRadius: radius,
      time: localTime
    };
  };

  const updateMapCenter = () => {
    if (sensors.length === 0) return;

    const avgLat = sensors.reduce((sum, s) => sum + s.lat, 0) / sensors.length;
    const avgLon = sensors.reduce((sum, s) => sum + s.lon, 0) / sensors.length;

    setMapCenter([avgLat, avgLon]);
    setUserTriggeredCenter(true);
  };

  function getMicColor(micId) {
    const colors = ["red", "blue", "green", "orange", "purple", "brown", "pink"];
    return colors[micId % colors.length];
  }

  function MapCenterUpdater({ center, userTriggered }) {
    const map = useMap();

    useEffect(() => {
      if (userTriggered) {
        map.setView(center, map.getZoom());
        setUserTriggeredCenter(false);
      }
    }, [center, userTriggered, map]);

    return null;
  }

  const currentTimeMicro = Date.now() * 1000;
  const recentGunshotLocations = gunshotLocations.filter((gunshot) => {
    const eventTimeMicro = gunshot.estimated_location.time;
    if (selectedTimestamp) {
      return Math.abs(eventTimeMicro - selectedTimestamp) < 50_000;
    }
    return currentTimeMicro - eventTimeMicro <= 10 * 1_000_000;
  });

  return (
    <div style={{ position: "relative", height: "100vh", width: "100vw", margin: 0, padding: 0, overflow: "hidden" }}>
      
      {/* Timestamp dropdown */}
      <div style={{ position: "absolute", top: "10px", left: "200px", zIndex: 1000 }}>
        <select
          value={selectedTimestamp || ""}
          onChange={(e) => setSelectedTimestamp(Number(e.target.value))}
          style={{ padding: "6px", borderRadius: "5px", fontSize: "14px" }}
        >
          <option value="" disabled>Select a timestamp</option>
          {timestamps.map((ts) => (
            <option key={ts} value={ts}>
              {new Date(ts * 1000).toLocaleString()}
            </option>
          ))}
        </select>
      </div>

      {/* Map container */}
      <MapContainer center={mapCenter} zoom={13} style={{ height: "100%", width: "100%" }}>
        <MapCenterUpdater center={mapCenter} userTriggered={userTriggeredCenter} />
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        {sensors
          .filter(sensor => triggeredMicIds.length === 0 || triggeredMicIds.includes(sensor.mic_id))
          .map((sensor) => (
            <Marker key={sensor.mic_id} position={[sensor.lat, sensor.lon]} icon={L.divIcon({
              className: "custom-marker",
              html: `<div style='background-color: ${getMicColor(sensor.mic_id)}; width: 10px; height: 10px; border-radius: 50%'></div>`
            })}>
              <Popup>Mic {sensor.mic_id}</Popup>
            </Marker>
        ))}

        {recentGunshotLocations.map((gunshot, index) => {
          const { lat, lon, confidenceRadius, time } = estimateConfidenceRadius(gunshot);
          return (
            <div key={index}>
              <Marker position={[lat, lon]} icon={gunshotIcon}>
                <Popup>Estimated Gunshot Location<br/>Confidence Radius: {confidenceRadius.toFixed(2)} m<br/>Time: {time}</Popup>
              </Marker>
              <Circle 
                center={[lat, lon]} 
                radius={confidenceRadius} 
                pathOptions={{ color: 'rgba(255, 0, 0, 0.5)', fillColor: 'rgba(255, 0, 0, 0.2)', fillOpacity: 0.4 }}
              />
            </div>
          );
        })}
      </MapContainer>

      {/* Center map button */}
      <button
        onClick={updateMapCenter}
        style={{
          position: "absolute",
          top: "10px",
          left: "70px",
          zIndex: 1000,
          padding: "8px 12px",
          backgroundColor: "#007BFF",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer"
        }}
      >
        Center Map
      </button>
    </div>
  );
}
