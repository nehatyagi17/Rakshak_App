# 🛡️ RAKSHAK: Quick Setup Guide

This guide will help you get the Rakshak Emergency Response System running on your local machine for development and testing.

## 📋 Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Expo Go App** (installed on your physical Android/iOS device)
- **MongoDB** (Local instance or Atlas URI)

---

## 🛠️ 1. Backend Setup (Django)

1. **Navigate to the backend folder:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in `backend/` and add:
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key
   MONGO_URI=mongodb://localhost:27017/rakshak_db
   ```

5. **Initialize Database:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Start the server:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   *Note: Using `0.0.0.0` allows your mobile phone to connect.*

---

## 📱 2. Mobile App Setup (Expo)

1. **Navigate to the mobile folder:**
   ```bash
   cd mobile
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure the API Endpoint:**
   Create a `.env` file in `mobile/`. **Crucial step for physical devices:**
   ```env
   EXPO_PUBLIC_API_URL=http://<YOUR_PC_IP_ADDRESS>:8000/api
   ```
   *Find your IP using `ipconfig` (Windows) or `ifconfig` (Mac/Linux). Ensure your phone and PC are on the same Wi-Fi.*

4. **Start the app:**
   ```bash
   npx expo start
   ```
   Scan the QR code with your **Expo Go** app.

---

## 🔑 3. Testing the System

- **Test Account:**
  - Email: `test@rakshak.ai`
  - Password: `password123`
- **Authority Dashboard:**
  - Access the live monitoring screen at: `http://localhost:8000/api/alerts/authority/dashboard/`

## 💡 Pro-Tips
- **Handshake Scan:** If testing on an emulator, the Bluetooth scan is simulated and will "find" the victim after 10 seconds of clicking "Verify Handshake" on a nearby alert.
- **Evidence Chunks:** The app records 5-second video segments via the camera and streams them to the dashboard automatically when SOS is active.
- **ngrok:** If your phone and PC cannot see each other on the Wi-Fi, run `ngrok http 8000` and update your `EXPO_PUBLIC_API_URL` to the ngrok link.
