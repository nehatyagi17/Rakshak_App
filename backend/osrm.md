# 🗺️ OSRM Routing Engine Integration

This document details the configuration and usage of the OSRM (Open Source Routing Machine) microservice within the RAKSHAK backend.

---

## ⚙️ Configuration

The backend communicates with an external OSRM microservice. The base URL is configured in the `.env` file.

- **Variable**: `OSRM_BASE_URL`
- **Default**: `https://osrm-hukn.onrender.com`

Example `.env` entry:
```env
OSRM_BASE_URL=https://osrm-hukn.onrender.com
```

---

## 📍 Routing API Endpoint

The routing endpoint provides GeoJSON geometries for routes between source and destination coordinates, specifically optimized for Leaflet integration.

### 🛣️ Get Route
Fetches the primary driving route between two points.

- **URL**: `/api/alerts/route/`
- **Method**: `POST`
- **Auth Required**: Yes (JWT Bearer Token)
- **Content-Type**: `application/json`

**Body Params**:
- `src_lat` (float): Latitude of the starting point.
- `src_lng` (float): Longitude of the starting point.
- `dest_lat` (float): Latitude of the destination point.
- `dest_lng` (float): Longitude of the destination point.

**Sample Request**:
```json
{
    "src_lat": 28.6139,
    "src_lng": 77.2090,
    "dest_lat": 28.5355,
    "dest_lng": 77.3910
}
```

**OSRM Parameters Used**:
- `overview=full`: Returns the highest resolution geometry.
- `geometries=geojson`: Returns geometry in GeoJSON format (ready for Leaflet).
- `steps=false`: Simplifies the response by omitting turn-by-turn instructions.

**Sample Response (200 OK)**:
```json
{
    "geometry": {
        "type": "LineString",
        "coordinates": [
            [77.2090, 28.6139],
            ...
            [77.3910, 28.5355]
        ]
    },
    "distance": 22435.2,
    "duration": 1845.5
}
```

---

## 🛠️ Error Handling
- **400 Bad Request**: Missing mandatory coordinate fields.
- **404 Not Found**: OSRM could not find a valid driving route between the points.
- **503 Service Unavailable**: The OSRM microservice is unreachable or returned a server error.

---

## 🎨 Leaflet Integration Example
The `geometry` returned can be directly added to a Leaflet map:
```javascript
fetch('/api/alerts/route/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
    body: JSON.stringify({ src_lat, src_lng, dest_lat, dest_lng })
})
.then(res => res.json())
.then(data => {
    L.geoJSON(data.geometry, { color: 'red' }).addTo(map);
});
```
