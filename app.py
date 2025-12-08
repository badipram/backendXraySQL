from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import mysql.connector
from mysql.connector import pooling
import json
import os
import uuid
import cv2
import base64

# dotenv optional (Railway uses environment variables)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

db_config = {
    "host": os.getenv("MYSQLHOST", "mysql.railway.internal"),
    "user": os.getenv("MYSQLUSER", "root"),
    "password": os.getenv("MYSQLPASSWORD", "hXyyBrmoUSGffKZkZgzElqxxsbxhrUPv"),
    "database": os.getenv("MYSQLDATABASE", "railway"),
    "port": int(os.getenv("MYSQLPORT", 3306)),
}

# Try create a connection pool; fallback to None and use direct connect
db_pool = None
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="xray_pool",
        pool_size=5,
        **db_config
    )
except Exception:
    db_pool = None

def get_db():
    """Get a MySQL connection (from pool if available). Caller must close() the connection."""
    try:
        if db_pool:
            return db_pool.get_connection()
        return mysql.connector.connect(**db_config)
    except Exception:
        # re-raise so caller/logs show clear error
        raise

app = Flask(__name__)
CORS(app)

# lazy-load model to avoid heavy import at container boot
_model = None
def get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO("best.pt")
    return _model

os.makedirs("uploads", exist_ok=True)

def img_to_base64(img_path):
    if not os.path.exists(img_path):
        return None
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def enhance_image(img):
    # Ubah ke grayscale agar lebih fokus pada struktur tulang
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # CLAHE untuk penyesuaian kontras lokal
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Penyesuaian kecerahan dan kontras ringan (linear adjustment)
    alpha = 1.1  # memperkuat kontras sedikit
    beta = 15    # meningkatkan brightness sedikit
    enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)
    
    # 🔹 Tahap noise reduction:
    # 1. Median filter untuk menghilangkan noise bintik (salt & pepper)
    enhanced = cv2.medianBlur(enhanced, 3)
    # 2. Gaussian blur untuk meratakan noise halus
    enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
    
    # Kembalikan ke format BGR agar bisa disimpan dan ditampilkan
    enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    return enhanced_bgr

@app.route('/predict', methods=['POST'])
def predict():
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({"error": "no image file"}), 400

        filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        file.save(file_path)

        original_b64 = img_to_base64(file_path)

        img = cv2.imread(file_path)
        if img is None:
            return jsonify({"error": "invalid image file"}), 400

        enhanced_img = enhance_image(img)
        enhanced_path = os.path.join("uploads", f"enhanced_{filename}")
        cv2.imwrite(enhanced_path, enhanced_img)
        enhanced_b64 = img_to_base64(enhanced_path)

        # inference (lazy-load model)
        model = get_model()
        results = model(enhanced_path)
        result = results[0]
        plot_img = result.plot()
        pred_path = os.path.join("uploads", f"pred_{filename}")
        cv2.imwrite(pred_path, plot_img)
        pred_b64 = img_to_base64(pred_path)

        detection_info = []
        for box in result.boxes:
            detection_info.append({
                "confidence": float(box.conf[0]),
                "bbox": [float(x) for x in box.xyxy[0].tolist()]
            })

        conn = get_db()
        try:
            cursor = conn.cursor()
            sql = "INSERT INTO detections3 (file_name, detected_at, result_text, detection_info) VALUES (%s, %s, %s, %s)"
            val = (
                filename,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "✅ Prediction Completed",
                json.dumps(detection_info)
            )
            cursor.execute(sql, val)
            conn.commit()
            cursor.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return jsonify({
            "original": original_b64,
            "enhanced": enhanced_b64,
            "predicted": pred_b64,
            "detection_info": detection_info
        })
    except Exception as e:
        print("❌ Error during prediction:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/last-prediction', methods=['GET'])
def last_prediction():
    try:
        conn = get_db()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM detections3 ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            cursor.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if not row:
            return jsonify({})

        filename = row['file_name']
        original_path = os.path.join("uploads", filename)
        enhanced_path = os.path.join("uploads", f"enhanced_{filename}")
        pred_path = os.path.join("uploads", f"pred_{filename}")

        raw = row.get("detection_info")
        detection_info = []
        if raw is None:
            detection_info = []
        else:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode('utf-8', errors='ignore')
            if isinstance(raw, str):
                try:
                    detection_info = json.loads(raw)
                except Exception:
                    detection_info = raw
            else:
                detection_info = raw

        detected_at = row.get("detected_at")
        if hasattr(detected_at, "strftime"):
            detected_at = detected_at.strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            "file_name": filename,
            "detected_at": detected_at,
            "result_text": row.get("result_text"),
            "detection_info": detection_info,
            "original": img_to_base64(original_path),
            "enhanced": img_to_base64(enhanced_path),
            "predicted": img_to_base64(pred_path)
        })
    except Exception as e:
        print("❌ Error in last-prediction:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/reset-prediction', methods=['POST'])
def reset_prediction():
    try:
        conn = get_db()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM detections3 ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                filename = row['file_name']
                paths = [
                    os.path.join("uploads", filename),
                    os.path.join("uploads", f"enhanced_{filename}"),
                    os.path.join("uploads", f"pred_{filename}")
                ]
                for path in paths:
                    if os.path.exists(path):
                        os.remove(path)
                cursor2 = conn.cursor()
                cursor2.execute("DELETE FROM detections3 WHERE id = %s", (row['id'],))
                conn.commit()
                cursor2.close()
            cursor.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return jsonify({"status": "reset"})
    except Exception as e:
        print("❌ Error in reset-prediction:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    app.run(debug=False, host="0.0.0.0", port=port)
