"""
AGROSENTINAL AI — Plant Disease Detection Model
Uses EfficientNetB3 trained on PlantVillage dataset
Serves as a Flask REST API for the Node.js backend
"""

import os
import io
import json
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS

# Try importing TensorFlow, fall back to mock for development
try:
    import tensorflow as tf
    from tensorflow.keras.applications import EfficientNetB3
    from tensorflow.keras.models import Model, load_model
    from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️  TensorFlow not found — using mock predictions for development")

app = Flask(__name__)
CORS(app)

# ── Disease Classes (PlantVillage 38 classes) ─────────────────────────────────
DISEASE_CLASSES = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
    "Blueberry___healthy", "Cherry___Powdery_mildew", "Cherry___healthy",
    "Corn___Cercospora_leaf_spot", "Corn___Common_rust", "Corn___Northern_Leaf_Blight", "Corn___healthy",
    "Grape___Black_rot", "Grape___Esca", "Grape___Leaf_blight", "Grape___healthy",
    "Orange___Haunglongbing", "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper___Bacterial_spot", "Pepper___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy", "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight",
    "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot", "Tomato___Spider_mites",
    "Tomato___Target_Spot", "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus", "Tomato___healthy"
]

# ── Treatment Database ────────────────────────────────────────────────────────
TREATMENTS = {
    "Early_blight": {
        "treatment": [
            "Apply mancozeb fungicide (2g/L water) every 7-10 days",
            "Remove and destroy infected leaves immediately",
            "Avoid overhead irrigation — water at base only",
            "Apply copper oxychloride (3g/L) as backup",
            "Improve air circulation by pruning dense foliage"
        ],
        "prevention": "Crop rotation (3-year cycle), use certified disease-free seeds",
        "recovery": "7-14 days with consistent treatment",
        "severity": "Moderate"
    },
    "Late_blight": {
        "treatment": [
            "Spray metalaxyl-M + mancozeb immediately",
            "Apply chlorothalonil (2ml/L) as preventive",
            "Destroy infected plants — do NOT compost",
            "Drain fields and avoid waterlogging",
            "Use systemic fungicide (propiconazole) for severe cases"
        ],
        "prevention": "Plant resistant varieties, ensure good field drainage",
        "recovery": "14-21 days — act immediately to prevent spread",
        "severity": "High"
    },
    "healthy": {
        "treatment": [
            "No treatment needed! Plant looks healthy ✓",
            "Continue current agricultural practices",
            "Maintain optimal irrigation schedule",
            "Monitor weekly for early signs of stress"
        ],
        "prevention": "Keep up current practices — you're doing great!",
        "recovery": "N/A — plant is healthy",
        "severity": "None"
    },
    "default": {
        "treatment": [
            "Apply broad-spectrum fungicide (mancozeb 2g/L)",
            "Remove severely infected plant parts",
            "Improve drainage and reduce humidity",
            "Consult local agriculture officer for severe cases"
        ],
        "prevention": "Use disease-resistant varieties, practice crop rotation",
        "recovery": "10-21 days depending on severity",
        "severity": "Moderate"
    }
}

# ── Model Architecture ────────────────────────────────────────────────────────
def build_model(num_classes=38):
    """Build EfficientNetB3 transfer learning model"""
    base = EfficientNetB3(weights='imagenet', include_top=False, input_shape=(300, 300, 3))
    base.trainable = False  # Freeze base initially

    x = base.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(512, activation='relu')(x)
    x = Dropout(0.3)(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.2)(x)
    output = Dense(num_classes, activation='softmax')(x)

    model = Model(inputs=base.input, outputs=output)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

def preprocess_image(image_bytes, target_size=(300, 300)):
    """Preprocess image for model inference"""
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img = img.resize(target_size, Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)

# ── Load Model ────────────────────────────────────────────────────────────────
MODEL_PATH = os.environ.get('MODEL_PATH', 'models/agrosentinal_efficientnet.h5')
model = None

if TF_AVAILABLE:
    if os.path.exists(MODEL_PATH):
        print(f"✅ Loading model from {MODEL_PATH}")
        model = load_model(MODEL_PATH)
    else:
        print("⚠️  No saved model found. Run train.py first or use mock mode.")

# ── Prediction Endpoint ───────────────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    image_bytes = file.read()

    try:
        if TF_AVAILABLE and model is not None:
            # Real prediction
            processed = preprocess_image(image_bytes)
            predictions = model.predict(processed)[0]
            top_idx = int(np.argmax(predictions))
            confidence = float(predictions[top_idx]) * 100
            disease_class = DISEASE_CLASSES[top_idx]

            # Parse disease name
            parts = disease_class.split('___')
            crop = parts[0].replace('_', ' ')
            condition = parts[1].replace('_', ' ') if len(parts) > 1 else 'Unknown'
            is_healthy = 'healthy' in disease_class.lower()

            # Get treatment info
            treatment_key = 'healthy' if is_healthy else parts[1] if len(parts) > 1 else 'default'
            treatment_info = TREATMENTS.get(treatment_key, TREATMENTS['default'])

            # Top-3 predictions
            top3_indices = np.argsort(predictions)[-3:][::-1]
            alternatives = [
                {"disease": DISEASE_CLASSES[i].split('___')[1].replace('_', ' '),
                 "confidence": round(float(predictions[i]) * 100, 1)}
                for i in top3_indices[1:]
            ]

            result = {
                "disease": f"{'Healthy ' + crop if is_healthy else condition} ({'Healthy ✓' if is_healthy else crop})",
                "crop": crop,
                "condition": condition,
                "confidence": round(confidence, 1),
                "is_healthy": is_healthy,
                "severity": treatment_info["severity"],
                "treatment": treatment_info["treatment"],
                "prevention": treatment_info["prevention"],
                "recovery": treatment_info["recovery"],
                "alternatives": alternatives,
                "model": "EfficientNetB3-PlantVillage"
            }
        else:
            # Mock prediction for development
            import random
            mock_diseases = [
                {"disease": "Early Blight (Alternaria solani)", "crop": "Tomato", "confidence": 94.2, "key": "Early_blight"},
                {"disease": "Late Blight (Phytophthora infestans)", "crop": "Potato", "confidence": 89.7, "key": "Late_blight"},
                {"disease": "Healthy Leaf ✓", "crop": "Tomato", "confidence": 97.8, "key": "healthy"},
                {"disease": "Leaf Rust (Puccinia triticina)", "crop": "Wheat", "confidence": 91.5, "key": "default"},
            ]
            chosen = random.choice(mock_diseases)
            treatment_info = TREATMENTS.get(chosen["key"], TREATMENTS["default"])
            result = {
                "disease": chosen["disease"],
                "crop": chosen["crop"],
                "confidence": chosen["confidence"],
                "is_healthy": chosen["key"] == "healthy",
                "severity": treatment_info["severity"],
                "treatment": treatment_info["treatment"],
                "prevention": treatment_info["prevention"],
                "recovery": treatment_info["recovery"],
                "alternatives": [],
                "model": "mock-development"
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'model_loaded': model is not None,
        'tensorflow': TF_AVAILABLE,
        'classes': len(DISEASE_CLASSES)
    })

# ── Training Script (run separately) ─────────────────────────────────────────
def train():
    """
    Download PlantVillage dataset and train model.
    Run: python predict.py train
    """
    if not TF_AVAILABLE:
        print("TensorFlow required for training")
        return

    print("🌾 Building AGROSENTINAL AI model...")
    model = build_model(num_classes=len(DISEASE_CLASSES))

    # Data generators
    datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        rescale=1./255,
        rotation_range=30,
        width_shift_range=0.2,
        height_shift_range=0.2,
        horizontal_flip=True,
        zoom_range=0.2,
        validation_split=0.2
    )

    print("📁 Loading PlantVillage dataset from ./data/PlantVillage/")
    train_gen = datagen.flow_from_directory(
        './data/PlantVillage',
        target_size=(300, 300),
        batch_size=32,
        class_mode='categorical',
        subset='training'
    )
    val_gen = datagen.flow_from_directory(
        './data/PlantVillage',
        target_size=(300, 300),
        batch_size=32,
        class_mode='categorical',
        subset='validation'
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.2, patience=3),
        tf.keras.callbacks.ModelCheckpoint('models/best_model.h5', save_best_only=True)
    ]

    print("🧠 Training EfficientNetB3...")
    history = model.fit(
        train_gen, validation_data=val_gen,
        epochs=30, callbacks=callbacks
    )

    # Fine-tuning: unfreeze top layers
    for layer in model.layers[-30:]:
        layer.trainable = True
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss='categorical_crossentropy', metrics=['accuracy'])
    model.fit(train_gen, validation_data=val_gen, epochs=10, callbacks=callbacks)

    os.makedirs('models', exist_ok=True)
    model.save(MODEL_PATH)
    print(f"✅ Model saved to {MODEL_PATH}")

    # Convert to TFLite for mobile
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    with open('models/agrosentinal_lite.tflite', 'wb') as f:
        f.write(tflite_model)
    print("📱 TFLite model saved for mobile deployment")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'train':
        train()
    else:
        print("🌾 AGROSENTINAL AI Model Server starting...")
        app.run(host='0.0.0.0', port=5001, debug=False)
