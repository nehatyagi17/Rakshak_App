import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger('django')

class SafetyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # We expect user_id passed in the query string, e.g., ws://.../ws/safety/?user_id=123
        query_string = self.scope['query_string'].decode()
        params = dict(x.split('=') for x in query_string.split('&') if '=' in x)
        self.user_id = params.get('user_id')

        if self.user_id:
            self.user_group_name = f"user_{self.user_id}"
            
            # Join room group
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"WebSocket Connected & Accepted: {self.user_group_name}")
        else:
            logger.info("WebSocket Rejected: user_id missing in Query Params")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            logger.info(f"WebSocket Disconnected: {self.user_group_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            logger.info(f"WS Recv [{self.user_id}]: {data}")
            
            if data.get("type") == "location_update":
                lat = data.get("lat")
                lng = data.get("lng")
                victim_id = data.get("victim_id") # Optional: used if user is rescuing
                
                if lat and lng and self.user_id:
                    from asgiref.sync import sync_to_async
                    from core.db import users_col
                    from bson.objectid import ObjectId
                    from datetime import datetime
                    
                    # Update volunteer's own position in DB
                    await sync_to_async(users_col.update_one)(
                        {"_id": ObjectId(self.user_id)},
                        {"$set": {
                            "location": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                            "last_seen_ws": datetime.utcnow().isoformat()
                        }}
                    )

                    # If this user is on a rescue mission, relay their position to the victim
                    if victim_id:
                        await self.channel_layer.group_send(
                            f"user_{victim_id}",
                            {
                                "type": "emergency_alert",
                                "payload": {
                                    "type": "VOLUNTEER_UPDATE",
                                    "volunteer_id": self.user_id,
                                    "lat": lat,
                                    "lng": lng
                                }
                            }
                        )
            
            elif data.get("type") == "accept_rescue":
                victim_id = data.get("victim_id")
                if victim_id:
                    # Notify victim that help is on the way
                    from core.db import users_col
                    from bson.objectid import ObjectId
                    from asgiref.sync import sync_to_async
                    
                    v_doc = await sync_to_async(users_col.find_one)({"_id": ObjectId(self.user_id)})
                    v_name = v_doc.get("name", "A Volunteer") if v_doc else "A Volunteer"
                    
                    await self.channel_layer.group_send(
                        f"user_{victim_id}",
                        {
                            "type": "emergency_alert",
                            "payload": {
                                "type": "VOLUNTEER_COMING",
                                "volunteer_id": self.user_id,
                                "name": v_name
                            }
                        }
                    )
                    logger.info(f"Volunteer {self.user_id} accepted rescue for {victim_id}")

        except Exception as e:
            logger.error(f"WS Receive Error: {e}")

    async def emergency_alert(self, event):
        # We handle both nested 'payload' and flat top-level messages
        data = event.get('payload', event)
        # Ensure we don't send internal Channels metadata if it's flat
        if 'type' in data and data['type'] == 'emergency_alert':
            # This is likely the internal dispatcher metadata, try to find content
            pass 
        
        logger.info(f"WS Dispatching alert to client: {self.user_id}")
        await self.send(text_data=json.dumps(data))

class AuthorityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "authority_group"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("Authority Dashboard Connected to Channel Layer")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def broadcast_event(self, event):
        # Dispatch SOS_START, LOCATION_UPDATE, NEW_CHUNK to the dashboard
        await self.send(text_data=json.dumps(event['payload']))

