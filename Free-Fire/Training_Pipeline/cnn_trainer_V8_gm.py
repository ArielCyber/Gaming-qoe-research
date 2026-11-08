# cnn_trainer_V8_gm.py
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import os

# הגדרות
DATA_PATH = 'final_training_data'
MODEL_NAME = 'thin_ping_model_final.keras'

# וידוא קיום התיקייה
if not os.path.exists(DATA_PATH):
    print(f"[ERROR] Directory '{DATA_PATH}' not found!")
    exit()

# הכנת הדאטה
datagen = ImageDataGenerator(rescale=1./255, validation_split=0.2)

train_gen = datagen.flow_from_directory(
    DATA_PATH, target_size=(64, 40), color_mode='grayscale',
    class_mode='sparse', subset='training'
)

val_gen = datagen.flow_from_directory(
    DATA_PATH, target_size=(64, 40), color_mode='grayscale',
    class_mode='sparse', subset='validation'
)

# ארכיטקטורה 
model = models.Sequential([
    layers.Input(shape=(64, 40, 1)),
    layers.Conv2D(32, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(10, activation='softmax')
])

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

print("[INFO] Training model on merged dataset...")
model.fit(train_gen, epochs=12, validation_data=val_gen)
model.save(MODEL_NAME)
print(f"[SUCCESS] {MODEL_NAME} saved!")