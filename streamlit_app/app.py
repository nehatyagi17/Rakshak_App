import streamlit as st
from deepface import DeepFace
import numpy as np
import os
from scipy.spatial.distance import cosine
from PIL import Image

# Folder to store embeddings
DB_PATH = "database"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

st.title("🛡️ RAKSHAK Face Verification System")

menu = ["Register", "Verify"]
choice = st.sidebar.selectbox("Select Option", menu)

# -------------------------------
# 🔹 REGISTER
# -------------------------------
if choice == "Register":
    st.header("Register Your Face")

    user_id = st.text_input("Enter User ID")
    uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png"])

    if st.button("Register"):
        if user_id and uploaded_file:
            img = Image.open(uploaded_file)
            img_path = f"{DB_PATH}/{user_id}.jpg"
            img.save(img_path)

            with st.spinner("Processing..."):
                embedding = DeepFace.represent(img_path, model_name="Facenet")[0]["embedding"]
                np.save(f"{DB_PATH}/{user_id}.npy", embedding)

            st.success("✅ User Registered Successfully")

        else:
            st.warning("Please enter user ID and upload image")


# -------------------------------
# 🔹 VERIFY
# -------------------------------
elif choice == "Verify":
    st.header("Verify Your Face")

    user_id = st.text_input("Enter User ID")
    uploaded_file = st.camera_input("Take a photo for Verification")

    if st.button("Verify"):
        if user_id and uploaded_file:
            stored_path = f"{DB_PATH}/{user_id}.npy"

            if not os.path.exists(stored_path):
                st.error("❌ User not found")
            else:
                img = Image.open(uploaded_file)
                temp_path = f"{DB_PATH}/temp.jpg"
                img.save(temp_path)

                with st.spinner("Verifying..."):
                    stored_embedding = np.load(stored_path)
                    new_embedding = DeepFace.represent(temp_path, model_name="Facenet")[0]["embedding"]

                    distance = cosine(stored_embedding, new_embedding)

                if distance < 0.4:
                    st.success("✅ Verified")
                else:
                    st.error("❌ Not Verified")

                st.write(f"Distance: {distance:.4f}")

        else:
            st.warning("Please enter user ID and upload image")