# RAKSHAK: Technical Workflow Architecture

This flowchart illustrates the unified "Supabase Handshake" and SOS alerting pipeline, ensuring high-integrity evidence streaming and real-time authority response.

```mermaid
graph TD
    %% -- User Trigger Phase --
    Start((User Trigger)) -->|Voice/Panic| App[Mobile App]
    App -->|1. SOS Trigger PIN/Voice| TriggerAPI[Backend: /api/alerts/trigger/]
    
    subgraph "Backend Infrastructure"
        TriggerAPI -->|Create Alert| MongoDB[(MongoDB: Alerts)]
        TriggerAPI -->|Create Incident| SQLite[(SQLite: Incidents)]
        TriggerAPI -->|Return| App
        TriggerAPI -->|WS: SOS_START| Dash[Authority Dashboard]
    end

    %% -- Evidence Streaming Handshake --
    App -->|2. Record 5s Chunk| LocalStore[Local App Storage]
    LocalStore -->|3. PHASE 1: Direct Upload| SupabaseAPI[Backend: /api/evidence/upload/]
    SupabaseAPI -->|Upload Object| SupaStorage[(Supabase Storage: RakshakBucket)]
    SupaStorage -->|Public URL| SupabaseAPI
    SupabaseAPI -->|Return public_url| App
    
    App -->|4. PHASE 2: Handshake Pulse| PulseAPI[Backend: /api/alerts/upload-chunk/]
    PulseAPI -->|Store Tracking| LocationTable[(SQLite: Tracking)]
    PulseAPI -->|Signal| WSHub[Django Channels WebSockets]
    
    %% -- Responder Connectivity --
    WSHub -->|5. Push Chunk URL| Dash
    Dash -->|6. Instant Playback| SupaStorage
    
    %% -- Dashboard Polling Fallback --
    Dash -.->|Every 5s: fallback| ListAPI[Backend: /api/alerts/admin/list/]
    ListAPI -.->|Hydrated Alert Data| Dash

    %% -- Styling --
    style Start fill:#f00,stroke:#333,stroke-width:2px,color:#fff
    style SupaStorage fill:#3ecf8e,stroke:#333,stroke-width:2px,color:#fff
    style Dash fill:#2563eb,stroke:#333,stroke-width:2px,color:#fff
    style MongoDB fill:#47a248,stroke:#333,stroke-width:2px,color:#fff
```

### 🔐 Multi-Tier Authentication
*   **Mobile App:** Uses **JWT (JSON Web Token)** for stateless, secure API access via `PyMongoJWTAuthentication`.
*   **Authority Dashboard:** Uses **Django Session/Cookies** for seamless browser-based access and polling via `SessionAuthentication`.
