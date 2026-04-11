import tensorflow as tf
from tensorflow.keras import layers, models
import numpy as np

def build_motion_model():
    # 2 second sliding window at 50Hz = 100 timesteps
    # 6 features = acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z
    model = models.Sequential([
        layers.Input(shape=(100, 6)),
        layers.Conv1D(64, kernel_size=3, activation='relu'),
        layers.BatchNormalization(),
        layers.Conv1D(128, kernel_size=3, activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(),
        layers.GlobalAveragePooling1D(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(3, activation='softmax') # normal, suspicious, high-risk
    ])
    
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

# Train logic:
# x_train: array of shape (num_samples, 100, 6), values normalized to [-1, 1]
# y_train: labels 0, 1, 2
# model.fit(x_train, y_train, epochs=50)
