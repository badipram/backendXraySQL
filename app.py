# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from ultralytics import YOLO
# from datetime import datetime
# import mysql.connector
# from mysql.connector import pooling
# import json
# import os
# import uuid
# import cv2
# import base64
# from dotenv import load_dotenv

# load_dotenv()

# # db_config = {
# #     "host": "localhost",
# #     "user": "root",
# #     "password": "",
# #     "database": "db_xray",
# # }

# db_config = {
#     "host": os.getenv("MYSQLHOST", "localhost"),
#     "user": os.getenv("MYSQLUSER", "root"),
#     "password": os.getenv("MYSQLPASSWORD", ""),
#     "database": os.getenv("MYSQLDATABASE", "db_xray"),
#     "port": int(os.getenv("MYSQLPORT", 3306)),
# }

# db = None

# def get_db():
#     """Return a live MySQL connection, reconnecting if necessary."""
#     global db
#     try:
#         if db is None:
#             db = mysql.connector.connect(**db_config)
#         else:
#             # Try to ensure the connection is alive; reconnect if not
#             try:
#                 if not db.is_connected():
#                     db = mysql.connector.connect(**db_config)
#                 else:
#                     # ping to keep/verify connection (reconnect if needed)
#                     db.ping(reconnect=True, attempts=3, delay=2)
#             except Exception:
#                 db = mysql.connector.connect(**db_config)
#     except Exception:
#         # Final attempt to create connection; let caller handle exceptions
#         db = mysql.connector.connect(**db_config)
#     return db

# app = Flask(__name__)
# CORS(app)

# model = YOLO("best.pt")
# os.makedirs("uploads", exist_ok=True)

# def img_to_base64(img_path):
#     if not os.path.exists(img_path):
#         return None
#     with open(img_path, "rb") as f:
#         return base64.b64encode(f.read()).decode("utf-8")

# def enhance_image(img):
#     alpha = 1.0  # contrast
#     beta = 20    # brightness
#     enhanced = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
#     return enhanced

# @app.route('/predict', methods=['POST'])
# def predict():
#     try:
#         file = request.files['image']
#         filename = f"{uuid.uuid4().hex}_{file.filename}"
#         file_path = os.path.join("uploads", filename)
#         file.save(file_path)

#         original_b64 = img_to_base64(file_path)

#         img = cv2.imread(file_path)
#         enhanced_img = enhance_image(img)
#         enhanced_path = os.path.join("uploads", f"enhanced_{filename}")
#         cv2.imwrite(enhanced_path, enhanced_img)
#         enhanced_b64 = img_to_base64(enhanced_path)

#         results = model(file_path)
#         result = results[0]
#         plot_img = result.plot()
#         pred_path = os.path.join("uploads", f"pred_{filename}")
#         cv2.imwrite(pred_path, plot_img)
#         pred_b64 = img_to_base64(pred_path)


#         detection_info = []
#         for box in result.boxes:
#             detection_info.append({
#                 "confidence":  float(box.conf[0]),
#                 "bbox": [float(x) for x in box.xyxy[0].tolist()]
#             })

#         cursor = get_db().cursor()
#         sql = "INSERT INTO detections3 (file_name, detected_at, result_text, detection_info) VALUES (%s, %s, %s, %s)"
#         val = (
#             filename,
#             datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#             "✅ Prediction Completed",
#             json.dumps(detection_info)
#         )
#         cursor.execute(sql, val)
#         get_db().commit()
#         cursor.close()

#         return jsonify({
#             "original": original_b64,
#             "enhanced": enhanced_b64,
#             "predicted": pred_b64,
#             "detection_info": detection_info
#         })
#     except Exception as e:
#         print("❌ Error during prediction:", e)
#         return jsonify({"error": str(e)}), 500
    
# import os

# # @app.route('/last-prediction', methods=['GET'])
# # def last_prediction():
# #     cursor = get_db().cursor(dictionary=True)
# #     cursor.execute("SELECT * FROM detections3 ORDER BY id DESC LIMIT 1")
# #     row = cursor.fetchone()
# #     cursor.close()
# #     if not row:
# #         return jsonify({})
    
# #     filename = row['file_name']
# #     original_path = os.path.join("uploads", filename)
# #     enhanced_path = os.path.join("uploads", f"enhanced_{filename}")
# #     pred_path = os.path.join("uploads", f"pred_{filename}")

# #     return jsonify({
# #         "file_name": filename,
# #         "detected_at": row["detected_at"].strftime('%Y-%m-%d %H:%M:%S'),
# #         "result_text": row["result_text"],
# #         "detection_info": json.loads(row["detection_info"]),
# #         "original": img_to_base64(original_path),
# #         "enhanced": img_to_base64(enhanced_path),
# #         "predicted": img_to_base64(pred_path)
# #     })

# @app.route('/last-prediction', methods=['GET'])
# def last_prediction():
#     cursor = get_db().cursor(dictionary=True)
#     cursor.execute("SELECT * FROM detections3 ORDER BY id DESC LIMIT 1")
#     row = cursor.fetchone()
#     cursor.close()
#     if not row:
#         return jsonify({})

#     filename = row['file_name']
#     original_path = os.path.join("uploads", filename)
#     enhanced_path = os.path.join("uploads", f"enhanced_{filename}")
#     pred_path = os.path.join("uploads", f"pred_{filename}")

#     # Robust parsing of detection_info (works if column is JSON or TEXT/LONGTEXT)
#     raw = row.get("detection_info")
#     detection_info = None
#     if raw is None:
#         detection_info = []
#     else:
#         if isinstance(raw, (bytes, bytearray)):
#             raw = raw.decode('utf-8', errors='ignore')
#         if isinstance(raw, str):
#             try:
#                 detection_info = json.loads(raw)
#             except Exception:
#                 # fallback: try eval-like shallow parse or keep raw string
#                 detection_info = raw
#         else:
#             detection_info = raw

#     return jsonify({
#         "file_name": filename,
#         "detected_at": row["detected_at"].strftime('%Y-%m-%d %H:%M:%S'),
#         "result_text": row["result_text"],
#         "detection_info": detection_info,
#         "original": img_to_base64(original_path),
#         "enhanced": img_to_base64(enhanced_path),
#         "predicted": img_to_base64(pred_path)
#     })



# @app.route('/reset-prediction', methods=['POST'])
# def reset_prediction():
#     cursor = get_db().cursor(dictionary=True)
#     cursor.execute("SELECT * FROM detections3 ORDER BY id DESC LIMIT 1")
#     row = cursor.fetchone()
#     if row:
#         filename = row['file_name']
#         # Hapus file hasil
#         paths = [
#             os.path.join("uploads", filename),
#             os.path.join("uploads", f"enhanced_{filename}"),
#             os.path.join("uploads", f"pred_{filename}")
#         ]
#         for path in paths:
#             if os.path.exists(path):
#                 os.remove(path)
#         # Hapus data dari database
#         cursor2 = get_db().cursor()
#         cursor2.execute("DELETE FROM detections3 WHERE id = %s", (row['id'],))
#         get_db().commit()
#         cursor2.close()
#     cursor.close()
#     return jsonify({"status": "reset"})

# if __name__ == "__main__":
#     port = int(os.getenv("PORT", 5050))
#     app.run(debug=False, host="0.0.0.0", port=port)


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
    "host": os.getenv("MYSQLHOST"),
    "user": os.getenv("MYSQLUSER"),
    "password": os.getenv("MYSQLPASSWORD"),
    "database": os.getenv("MYSQLDATABASE"),
    "port": int(os.getenv("MYSQLPORT")),
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
    alpha = 1.0  # contrast
    beta = 20    # brightness
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

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
        results = model(file_path)
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
