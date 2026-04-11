# 🛡️ RAKSHAK: Technical Documentation

## 1. Introduction
**RAKSHAK** (Sanskrit for "Protector") is an integrated safety ecosystem designed to bridge the gap between distress detection and emergency response. Unlike traditional safety apps that require manual interaction, RAKSHAK leverages ambient intelligence to trigger help when the user cannot.

---

## 2. System Architecture

RAKSHAK is built on a distributed architecture comprising four main pillars:

### A. Mobile Client (The "Edge")
- **Framework**: React Native / Expo.
- **The Ear (Background Monitor)**: A persistent service using `expo-audio` to capture 3-second rolling buffers.
- **On-Device ML**: TFLite models analyze these buffers for distress keywords.
- **Dual-Stream Controller**: Orchestrates simultaneous uploads of audio/video chunks to Supabase and location telemetry to the Django backend.

### B. Backend Engine (The "Brain")
- **Framework**: Django & Django Rest Framework.
- **Real-Time Layer**: Django Channels (WebSockets) for low-latency location updates and incident broadcasting.
- **Escalation Logic**: A state-machine based system that manages the transition from "Check-in" to "Guardian Notification" to "Community Broadcast".

### C. Storage & Data (The "Vault")
- **Primary DB**: MongoDB Atlas (Geospatial indexes for 2D-sphere queries).
- **Blob Storage**: Supabase Buckets for encrypted evidence (M4A/MP4 chunks).
- **Auth**: JWT-based stateless authentication with biometric cross-verification.

### D. Authority Dashboard (The "Command Center")
- **Stack**: React / WebSockets.
- **Features**: Live incident feed, real-time map tracking of victims and volunteers, and buffered evidence playback.

---

## 3. The SOS Pipeline: From Silence to Siren

The core of RAKSHAK is the **Autonomous SOS Lifecycle**:

1.  **Detection**: "The Ear" detects a distress keyword or the user triggers SOS manually.
2.  **Tier 0 (Verification)**:
    - 15-second silent countdown starts.
    - Local recording begins immediately.
3.  **Tier 1 (Guardian Escalation)**:
    - If not cancelled, backend sends immediate alerts (Email/SMS) to predefined guardians.
    - Evidence streaming to Supabase starts.
    - A unique "Live Tracking URL" is generated for guardians.
4.  **Tier 2 (Community Broadcast)**:
    - At 30 seconds, a `BROADCAST_SOS` event is emitted via WebSockets.
    - Nearby users (within 200m) receive a high-priority push notification.
    - The incident appears on the Authority Dashboard.
5.  **Resolution**:
    - Volunteers can "Accept" the rescue via the app.
    - Both victim and volunteer see each other's live positions on the map.
    - Incident is archived once the user marks themselves as "Safe".

---

## 4. Key Components Deep-Dive

### 🎙️ The Ear (Mobile)
`The Ear` is a sophisticated audio processing pipeline. It uses a circular buffer to minimize memory footprint and ensures that sensitivity is balanced against battery life. When a keyword is detected, it performs a second pass with a higher-fidelity model before escalating to the server.

### 📍 Geospatial Broadcasting (Backend)
RAKSHAK uses MongoDB's `$nearSphere` operator to identify responders. The system calculates the proximity in real-time, ensuring that only those who can realistically help are notified, preserving community trust and reducing "alarm fatigue".

### 📹 Evidence Handshaking
To ensure evidence is never lost due to spotty connectivity, RAKSHAK uses an **Acknowledge-based Chunking** mechanism. The mobile app won't delete a locally cached chunk until the server confirms a successful Supabase write.

---

## 5. Security & Privacy

Privacy is not a feature; it is the foundation:
- **Audio Privacy**: Background listening is strictly local. No audio is ever uploaded unless a trigger is confirmed.
- **Data Retention**: SOS evidence is automatically purged after 30 days unless flagged for legal review.
- **Access Logs**: Every time a volunteer or authority views a location, an immutable audit log is created in the database.

---

## 6. Future Roadmap
- **Visual Threat Detection**: Using the front camera to detect weapons or aggressive gestures.
- **Smart-Watch Integration**: Pulse-rate monitoring for automated SOS during medical emergencies.
- **Offline Mesh Networking**: Using Bluetooth Low Energy (BLE) to signal for help in areas without cellular coverage.

