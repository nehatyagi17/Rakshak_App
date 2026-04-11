import tensorflow as tf
from tensorflow.keras import layers, models
import librosa
import numpy as np

def build_model():
    model = models.Sequential([
        layers.Input(shape=(40, 100, 1)), # Example max time steps of 100
        layers.Conv2D(32, (3, 3), activation='relu'),
        layers.BatchNormalization(),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D(),
        layers.GlobalAveragePooling2D(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(2, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

def extract_mfcc(audio_path):
    y, sr = librosa.load(audio_path, sr=16000)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40, hop_length=512)
    # Pad or truncate to fixed 100 timesteps
    if mfccs.shape[1] < 100:
        mfccs = np.pad(mfccs, ((0, 0), (0, 100 - mfccs.shape[1])))
    else:
        mfccs = mfccs[:, :100]
    return np.expand_dims(mfccs, axis=-1)

# Training loop placeholder
# model = build_model()
# model.fit(x_train, y_train, epochs=20)
# model.save('saved_model')

# Export logic provided
# converter = tf.lite.TFLiteConverter.from_saved_model('saved_model/')
# converter.optimizations = [tf.lite.Optimize.DEFAULT]
# converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
# tflite_model = converter.convert()
# with open('model.tflite', 'wb') as f: f.write(tflite_model)
