from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
from datetime import datetime
import mysql.connector
import json
import os
import uuid
import cv2
import base64

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="db_xray"
)

app = Flask(__name__)
CORS(app)

model = YOLO("best.pt")
os.makedirs("uploads", exist_ok=True)

def img_to_base64(img_path):
    if not os.path.exists(img_path):
        return None
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def enhance_image(img):
    alpha = 1.0  # contrast
    beta = 20    # brightness
    enhanced = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return enhanced

@app.route('/predict', methods=['POST'])
def predict():
    try:
        file = request.files['image']
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        file.save(file_path)

        original_b64 = img_to_base64(file_path)

        img = cv2.imread(file_path)
        enhanced_img = enhance_image(img)
        enhanced_path = os.path.join("uploads", f"enhanced_{filename}")
        cv2.imwrite(enhanced_path, enhanced_img)
        enhanced_b64 = img_to_base64(enhanced_path)

        results = model(file_path)
        result = results[0]
        plot_img = result.plot()
        pred_path = os.path.join("uploads", f"pred_{filename}")
        cv2.imwrite(pred_path, plot_img)
        pred_b64 = img_to_base64(pred_path)


        detection_info = []
        for box in result.boxes:
            detection_info.append({
                "confidence":  float(box.conf[0]),
                "bbox": [float(x) for x in box.xyxy[0].tolist()]
            })

        cursor = db.cursor()
        sql = "INSERT INTO detections3 (file_name, detected_at, result_text, detection_info) VALUES (%s, %s, %s, %s)"
        val = (
            filename,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "✅ Prediction Completed",
            json.dumps(detection_info)
        )
        cursor.execute(sql, val)
        db.commit()
        cursor.close()

        return jsonify({
            "original": original_b64,
            "enhanced": enhanced_b64,
            "predicted": pred_b64,
            "detection_info": detection_info
        })
    except Exception as e:
        print("❌ Error during prediction:", e)
        return jsonify({"error": str(e)}), 500
    
import os

@app.route('/last-prediction', methods=['GET'])
def last_prediction():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM detections3 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return jsonify({})
    
    filename = row['file_name']
    original_path = os.path.join("uploads", filename)
    enhanced_path = os.path.join("uploads", f"enhanced_{filename}")
    pred_path = os.path.join("uploads", f"pred_{filename}")

    return jsonify({
        "file_name": filename,
        "detected_at": row["detected_at"].strftime('%Y-%m-%d %H:%M:%S'),
        "result_text": row["result_text"],
        "detection_info": json.loads(row["detection_info"]),
        "original": img_to_base64(original_path),
        "enhanced": img_to_base64(enhanced_path),
        "predicted": img_to_base64(pred_path)
    })



@app.route('/reset-prediction', methods=['POST'])
def reset_prediction():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM detections3 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        filename = row['file_name']
        # Hapus file hasil
        paths = [
            os.path.join("uploads", filename),
            os.path.join("uploads", f"enhanced_{filename}"),
            os.path.join("uploads", f"pred_{filename}")
        ]
        for path in paths:
            if os.path.exists(path):
                os.remove(path)
        # Hapus data dari database
        cursor2 = db.cursor()
        cursor2.execute("DELETE FROM detections3 WHERE id = %s", (row['id'],))
        db.commit()
        cursor2.close()
    cursor.close()
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True, port=5050)