import math
from core.db import alerts_col, users_col

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_nearby_alerts(user_lat, user_lon, radius_m=1000, exclude_user_id=None):
    from bson.objectid import ObjectId
    from datetime import datetime, timedelta
    
    # Only consider alerts created within the last 2 hours to prevent stale warnings
    two_hours_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    
    query = {
        "status": "active",
        "created_at": {"$gte": two_hours_ago}
    }
    
    active = alerts_col.find(query)
    nearby = []
    
    for alert in active:

        # Exclude the user's own alerts
        if exclude_user_id and str(alert.get("user_id")) == str(exclude_user_id):
            continue

        lat = alert.get("lat")
        lng = alert.get("lng")
        if lat is not None and lng is not None:
            dist = haversine(user_lat, user_lon, lat, lng)
            if dist <= radius_m:
                nearby.append({
                    "alert_id": str(alert["_id"]),
                    "user_id": str(alert.get("user_id")),
                    "timestamp": alert.get("created_at"),
                    "threat_level": alert.get("threat_level", "UNKNOWN"),
                    "lat": lat,
                    "lng": lng
                })
                
    return nearby

def get_nearby_users(center_lat, center_lon, radius_m=200, exclude_user_id=None):
    """
    Finds all users whose last known location is within the target radius using MongoDB's $near 2dsphere index.
    """
    query = {
        "location": {
            "$near": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [float(center_lon), float(center_lat)]
                },
                "$maxDistance": radius_m
            }
        }
    }
    
    if exclude_user_id:
        from bson.objectid import ObjectId
        query["_id"] = {"$ne": ObjectId(exclude_user_id)}
    
    users = users_col.find(query)
    nearby_users = []
    
    for user in users:
        user["_id"] = str(user["_id"])
        nearby_users.append(user)
                
    return nearby_users
