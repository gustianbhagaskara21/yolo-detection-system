from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import numpy as np
import base64
import os
import sys
import tempfile
from pathlib import Path

# ============================================================
#  KONFIGURASI DASAR
#  - PORT diambil dari environment variable (wajib untuk Railway)
#  - webbrowser & threading dihapus (tidak dipakai di server cloud)
# ============================================================
BASE_DIR = Path(__file__).parent.resolve()
MODEL_DIR = BASE_DIR / 'models'
ASSETS_DIR = BASE_DIR / 'assets'
UPLOAD_FOLDER = BASE_DIR / 'uploads'

# Railway otomatis mengisi PORT — jangan hardcode 5500
PORT = int(os.environ.get('PORT', 5500))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
CORS(app)

# ============================================================
#  KONFIGURASI MODEL
# ============================================================
MODELS = {
    'kemudi_komponen': {
        'name': 'Sistem Kemudi - Deteksi Komponen',
        'files': ['best1_1.pt', 'best1.1.pt'],
    },
    'kemudi_kerusakan': {
        'name': 'Sistem Kemudi - Deteksi Kerusakan',
        'files': ['best1_2.pt', 'best1.2.pt'],
    },
    'pemindah_komponen': {
        'name': 'Sistem Pemindah Daya - Deteksi Komponen',
        'files': ['best2_1.pt', 'best2.1.pt'],
    },
    'pemindah_kerusakan': {
        'name': 'Sistem Pemindah Daya - Deteksi Kerusakan',
        'files': ['best2_2.pt', 'best2.2.pt'],
    },
    'pembuangan_komponen': {
        'name': 'Sistem Pembuangan - Deteksi Komponen',
        'files': ['best3_1.pt', 'best3.1.pt'],
    },
    'pembuangan_kerusakan': {
        'name': 'Sistem Pembuangan - Deteksi Kerusakan',
        'files': ['best3_2.pt', 'best3.2.pt'],
    },
}


def _resolve_path(candidates):
    for fname in candidates:
        p = MODEL_DIR / fname
        if p.exists():
            return p
    return None


# ============================================================
#  LOAD SEMUA MODEL
# ============================================================
loaded_models = {}

print("\n" + "=" * 60)
print("Memuat model YOLO...")
print("=" * 60)

for model_key, config in MODELS.items():
    path = _resolve_path(config['files'])
    try:
        if path is not None:
            loaded_models[model_key] = YOLO(str(path))
            classes = list(loaded_models[model_key].names.values())
            print(f"[OK]   {config['name']}")
            print(f"       File   : {path.name}")
            print(f"       Classes: {classes}")
        else:
            print(f"[SKIP] {config['name']}")
            print(f"       File tidak ditemukan: {config['files']}")
    except Exception as e:
        print(f"[ERR]  {config['name']} -> {e}")

print("=" * 60)
print(f"Total model dimuat: {len(loaded_models)}/{len(MODELS)}")
print("=" * 60 + "\n")

# Di Railway: tidak fatal jika 0 model, tapi tetap tampilkan warning
if not loaded_models:
    print("WARNING: Tidak ada model yang berhasil dimuat.")
    print(f"         Pastikan file .pt ditempatkan di: {MODEL_DIR}")


# ============================================================
#  ROUTE: HALAMAN UTAMA
# ============================================================
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


# ============================================================
#  ROUTE: DETEKSI GAMBAR
# ============================================================
@app.route('/detect_image', methods=['POST'])
def detect_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Tidak ada file yang diupload'}), 400
        if 'model' not in request.form:
            return jsonify({'error': 'Model tidak dipilih'}), 400

        file = request.files['file']
        model_key = request.form['model']

        if file.filename == '':
            return jsonify({'error': 'File tidak dipilih'}), 400
        if model_key not in loaded_models:
            return jsonify({'error': f'Model "{model_key}" tidak tersedia. Model yang aktif: {list(loaded_models.keys())}'}), 400

        model = loaded_models[model_key]

        image_bytes = file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'Gambar tidak valid'}), 400

        print(f"[IMG] {file.filename} | {MODELS[model_key]['name']} | {img.shape}")

        results = model(img, conf=0.4, iou=0.45, verbose=False)
        annotated_img = results[0].plot()

        _, buffer = cv2.imencode('.jpg', annotated_img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        detections = []
        for box in results[0].boxes:
            detections.append({
                'class': model.names[int(box.cls[0])],
                'confidence': float(box.conf[0]),
                'bbox': box.xyxy[0].tolist(),
            })

        print(f"      Terdeteksi {len(detections)} objek")

        return jsonify({
            'success': True,
            'image': img_base64,
            'detections': detections,
            'count': len(detections),
            'model_used': MODELS[model_key]['name'],
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
#  ROUTE: DETEKSI VIDEO
# ============================================================
@app.route('/detect_video', methods=['POST'])
def detect_video():
    temp_input_path = None
    temp_output_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Tidak ada file yang diupload'}), 400
        if 'model' not in request.form:
            return jsonify({'error': 'Model tidak dipilih'}), 400

        file = request.files['file']
        model_key = request.form['model']

        if file.filename == '':
            return jsonify({'error': 'File tidak dipilih'}), 400
        if model_key not in loaded_models:
            return jsonify({'error': f'Model "{model_key}" tidak tersedia'}), 400

        model = loaded_models[model_key]
        print(f"[VID] {file.filename} | {MODELS[model_key]['name']}")

        video_bytes = file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(video_bytes)
            temp_input_path = tmp_file.name

        cap = cv2.VideoCapture(temp_input_path)
        if not cap.isOpened():
            raise Exception('Tidak bisa membuka video')

        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        print(f"      {width}x{height} | {fps}fps | {total_frames} frame")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_output:
            temp_output_path = tmp_output.name

        out = None
        for codec in ('avc1', 'H264', 'X264', 'mp4v'):
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))
                if out.isOpened():
                    print(f"      Codec: {codec}")
                    break
                out.release()
            except Exception:
                continue
        if out is None or not out.isOpened():
            raise Exception('Tidak bisa membuat video writer')

        frame_count = 0
        detection_count = 0
        per_class = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            results = model(frame, conf=0.4, iou=0.45, max_det=50, verbose=False)
            detection_count += len(results[0].boxes)
            for box in results[0].boxes:
                cname = model.names[int(box.cls[0])]
                per_class[cname] = per_class.get(cname, 0) + 1
            out.write(results[0].plot())
            frame_count += 1
            if frame_count % 30 == 0 and total_frames:
                print(f"      {frame_count}/{total_frames} ({frame_count / total_frames * 100:.0f}%)")

        cap.release()
        out.release()

        with open(temp_output_path, 'rb') as vf:
            video_data = vf.read()
            video_base64 = base64.b64encode(video_data).decode('utf-8')

        print(f"      Selesai: {frame_count} frame | {detection_count} deteksi | {len(video_data)/(1024*1024):.2f} MB")

        return jsonify({
            'success': True,
            'video_base64': video_base64,
            'total_frames': frame_count,
            'fps': fps,
            'duration': round(duration, 2),
            'detections_count': detection_count,
            'detections_per_class': per_class,
            'resolution': f"{width}x{height}",
            'filename': file.filename,
            'model_used': MODELS[model_key]['name'],
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        for p in (temp_input_path, temp_output_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


# ============================================================
#  ROUTE: INFO MODEL & HEALTH
# ============================================================
@app.route('/models/available', methods=['GET'])
def get_available_models():
    available = {}
    for key, config in MODELS.items():
        available[key] = {
            'name': config['name'],
            'available': key in loaded_models,
            'classes': list(loaded_models[key].names.values()) if key in loaded_models else [],
        }
    return jsonify(available)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'models_loaded': len(loaded_models),
        'models_available': list(loaded_models.keys()),
    })


# ============================================================
#  ENTRY POINT
#  - Di Railway: dijalankan oleh Gunicorn via Procfile
#  - Lokal: python app.py tetap bisa dipakai
# ============================================================
if __name__ == '__main__':
    print(f"Server berjalan di http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)
