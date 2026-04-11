import os, re

path = r'mobile/App.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add dismissedAlerts ref at the top
if 'const dismissedAlerts = useRef' not in content:
    content = re.sub(r'const isEscalating = useRef\(false\);', 
                     r'const isEscalating = useRef(false);\n  const dismissedAlerts = useRef<Set<string>>(new Set());', 
                     content)

# 2. Update onmessage with the guard and flat payload support
old_onmessage = r'socket\.onmessage = \(e\) => \{.*?const alertId = data\.alert_id \|\| data\.id;.*?if \(count < 2\) \{.*?setActiveRescue\(data\);.*?\}'
new_onmessage = r'''socket.onmessage = (e) => {
      console.log("WS Message Received:", e.data);
      try {
        const data = JSON.parse(e.data);
        const alertType = data.alert_type || data.type;
        
        if (alertType === 'EMERGENCY_ALERT') {
          const alertId = data.alert_id || data.id;
          
          // --- DISMISS GUARD ---
          if (dismissedAlerts.current.has(alertId)) {
            console.log(` RAKSHAK: Alert ${alertId} IGNORED (Previously Dismissed)`);
            return;
          }

          const count = notifiedAlerts.current[alertId] || 0;
          if (count < 2) {
             notifiedAlerts.current[alertId] = count + 1;
             Notifications.scheduleNotificationAsync({
                content: {
                   title: "🚨 URGENT: DISTRESS NEARBY",
                   body: "A citizen needs help! Tap for Map.",
                   data: { type: 'NEARBY_SOS', lat: data.location[1], lng: data.location[0] }
                },
                trigger: null,
             });
          }
          setActiveRescue(data);
        }'''

if re.search(r'socket\.onmessage = \(e\) => \{.*?if \(data\.type === \'EMERGENCY_ALERT\'\)', content, re.DOTALL):
    content = re.sub(r'socket\.onmessage = \(e\) => \{.*?if \(data\.type === \'EMERGENCY_ALERT\'\).*?\}', new_onmessage, content, flags=re.DOTALL)
    print("Success: Updated onmessage with Dismiss Guard and Flat Payload")

# 3. Update the "Dismiss Map" button logic to save the ID
old_dismiss = r'onPress=\{\(\) => setActiveRescue\(null\)\}'
new_dismiss = r'onPress={() => { dismissedAlerts.current.add(activeRescue.alert_id || activeRescue.id); setActiveRescue(null); }}'
if old_dismiss in content:
    content = content.replace(old_dismiss, new_dismiss)
    print("Success: Updated Dismiss Button with Persistent Guard")

# 4. Map Safety Guard (prevent centering crash if location is missing)
old_map_region = r'initialRegion=\{\{\s+latitude: userLocation\?\.latitude \|\| activeRescue\.location\[1\],'
new_map_region = r'initialRegion={{ latitude: activeRescue?.location ? activeRescue.location[1] : (userLocation?.latitude || 0.0),'

if re.search(r'initialRegion=\{\{\s+latitude: userLocation\?\.latitude \|\| activeRescue\.location\[1\],', content):
    content = re.sub(r'initialRegion=\{\{\s+latitude: userLocation\?\.latitude \|\| activeRescue\.location\[1\],', new_map_region, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
