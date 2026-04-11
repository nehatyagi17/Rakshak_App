# 📹 RAKSHAK Evidence API Documentation

This API handles the secure upload, retrieval, and deletion of emergency evidence (video/audio/images) and distress keywords using **Supabase Storage**.

---

## 🔐 Authentication
All endpoints (except where noted) require a valid JWT Bearer Token in the `Authorization` header.
`Authorization: Bearer <your_access_token>`

---

## 📹 1. SOS Evidence Endpoints

### 📤 Upload Evidence Chunk
Upload a 5-second video/audio segment recorded during an active SOS.
- **URL**: `/api/evidence/upload/`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: 
    - `alert_id` (string): The ID of the active alert/incident.
    - `file` (file): The actual evidence chunk (mp4, m4a, jpg, etc.).
- **Response** (201 Created):
    ```json
    {
        "message": "Evidence uploaded securely",
        "evidence_id": "65f1..."
    }
    ```

### 📋 List Evidence for Alert
Retrieve all evidence chunks associated with a specific alert.
- **URL**: `/api/evidence/<alert_id>/`
- **Method**: `GET`
- **Response** (200 OK):
    ```json
    [
        {
            "_id": "65f1...",
            "alert_id": "...",
            "public_url": "https://supabase.co/storage/v1/object/public/...",
            "filename": "..."
        }
    ]
    ```

### 🗑️ Delete Evidence
Permanently remove a piece of evidence from both the database and Supabase Storage.
- **URL**: `/api/evidence/delete/<evidence_id>/`
- **Method**: `DELETE`
- **Response** (200 OK):
    ```json
    { "message": "Evidence deleted forever" }
    ```

---

## 🎤 2. Distress Keyword Endpoints

### 📤 Upload Keyword
Upload or update the user's secret distress trigger phrase.
- **URL**: `/api/keyword/upload/`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: 
    - `file` (file): Audio file (wav, mp3, m4a).
- **Response** (201 Created):
    ```json
    { "message": "Distress keyword uploaded securely" }
    ```

---

## ☁️ Storage Architecture (Supabase)
- **Bucket**: `RakshakBucket`
- **Access**: Public
- **Pathing**: 
    - Evidence: `evidence/filename`
    - Keywords: `keywords/filename`
- **Streaming**: The `public_url` returned by the API can be plugged directly into `<video>` or `<audio>` tags for zero-latency streaming in the dashboard.
