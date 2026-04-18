# 🚀 OSRM Routing: Frontend Integration Guide

This guide explains how to integrate the RAKSHAK OSRM Routing API with a frontend application using **Leaflet.js**.

---

## 📍 API Specification

- **Endpoint**: `/api/alerts/route/`
- **Method**: `POST`
- **Authentication**: `Bearer <JWT_TOKEN>`
- **Content-Type**: `application/json`

### Request Body
```json
{
    "src_lat": 30.3244,
    "src_lng": 78.0335,
    "dest_lat": 30.2880,
    "dest_lng": 77.9960
}
```

### JSON Response
The API returns a GeoJSON `geometry` object, which is the standard format for Leaflet layers.
```json
{
    "geometry": {
        "type": "LineString",
        "coordinates": [
            [78.0335, 30.3244],
            [78.0331, 30.3245],
            ...
        ]
    },
    "distance": 6005.4,
    "duration": 607.2
}
```

---

## 🛠️ Step-by-Step Frontend Implementation

### 1. Helper Function to Fetch Route
Create a function that calls the backend and returns the GeoJSON geometry.

```javascript
async function getRoute(src, dest, token) {
    const response = await fetch('http://<your-api-url>/api/alerts/route/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            src_lat: src.lat,
            src_lng: src.lng,
            dest_lat: dest.lat,
            dest_lng: dest.lng
        })
    });

    if (!response.ok) {
        throw new Error('Routing service unavailable');
    }

    return await response.json();
}
```

### 2. Displaying the Route on Leaflet
Once you have the GeoJSON data, use `L.geoJSON()` to draw it on the map.

```javascript
// Example Usage
const sourceCoords = { lat: 30.3244, lng: 78.0335 };
const destCoords = { lat: 30.2880, lng: 77.9960 };

getRoute(sourceCoords, destCoords, userToken)
    .then(data => {
        // Remove existing route if any
        if (window.activeRoute) {
            map.removeLayer(window.activeRoute);
        }

        // Create the route layer
        window.activeRoute = L.geoJSON(data.geometry, {
            style: {
                color: '#FF3B30',  // Rakshak Red
                weight: 5,
                opacity: 0.8,
                lineJoin: 'round'
            }
        }).addTo(map);

        // Zoom map to fit the entire route
        map.fitBounds(window.activeRoute.getBounds(), { padding: [50, 50] });
        
        console.log(`Route displayed: ${data.distance} meters`);
    })
    .catch(err => console.error("Routing Error:", err));
```

---

## 💡 Pro Tips

### 🔄 Coordinate Order
The API accepts `lat, lng` for input, but **GeoJSON coordinates are `[lng, lat]`**. Leaflet's `L.geoJSON()` function handles this conversion automatically, so you don't need to swap them manually.

### 🛑 Error Handling
If the API returns a **503**, it's likely the Render microservice is waking up. Implement a retry mechanism or show a "Calculating route..." loader to the user.

### 📏 Units
- **Distance**: Returned in **meters**.
- **Duration**: Returned in **seconds**.
