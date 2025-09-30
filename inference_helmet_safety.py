iimport argparse
import pickle
import struct
import threading
import queue
import numpy as np
import cv2
import socket
import torch
import ssl
import time, os, json
from flask import Flask, Response, render_template, jsonify
from ultralytics import YOLO
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Allow SSL without cert check
ssl._create_default_https_context = ssl._create_unverified_context

# Config
frame_size = (640, 480)
CLIENT_TIMEOUT = 10
file_path = 'data.json'
save_directory = '/app/data/low_confidence_frames'

if not os.path.exists(save_directory):
    os.makedirs(save_directory, exist_ok=True)

# Arg parsing
parser = argparse.ArgumentParser(description="YOLOv8 TCP Stream (Threaded, CPU/GPU)")
parser.add_argument("--path", required=True, help="Path to YOLOv8 model")
parser.add_argument("--port", type=int, default=8080, help="TCP port for frames")
parser.add_argument("--device", default="cpu", help="Device: cpu or cuda")
args = parser.parse_args()

# Load model
model = YOLO(args.path)
model.to(args.device)

# Frame queues
frame_queue = queue.Queue(maxsize=1)
current_frame = None
frame_lock = threading.Lock()

# ---------------- Prometheus Metrics ---------------- #
inference_latency = Histogram("yolov8_inference_latency_seconds", "Time taken for inference")
detections_total = Counter("yolov8_detections_total", "Total number of detections", ["class"])
violations_total = Counter("ppe_violations_total", "Total PPE violations", ["type"])
current_fps = Gauge("yolov8_fps", "Frames per second")

# ---------------- TCP Receiver ---------------- #
def tcp_frame_receiver(port):
    print("Starting TCP receiver...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(1)
    print(f"[TCP] Listening on port {port}...")

    while True:
        conn, addr = server_socket.accept()
        print(f"[TCP] Connected from {addr}")
        conn.settimeout(5.0)
        data = b""
        payload_size = struct.calcsize("Q")
        last_data_time = time.time()

        try:
            while True:
                while len(data) < payload_size:
                    packet = conn.recv(4096)
                    if not packet:
                        break
                    data += packet

                if not data:
                    if time.time() - last_data_time > CLIENT_TIMEOUT:
                        print("[TCP] Client timeout, closing connection.")
                        break
                    continue

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]

                while len(data) < msg_size:
                    data += conn.recv(4096)

                frame_data = data[:msg_size]
                data = data[msg_size:]
                camera_name, frame = pickle.loads(frame_data)
                frame = cv2.resize(frame, frame_size)

                if frame is None:
                    continue

                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                frame_queue.put(frame)

                last_data_time = time.time()

        except Exception as e:
            print(f"[TCP] Exception: {e}")
        finally:
            conn.close()
            print("[TCP] Connection closed.")

# ---------------- Inference Worker ---------------- #
def inference_worker():
    global current_frame
    frame_count = 0
    print("Starting inference worker...")

    while True:
        try:
            frame = frame_queue.get(timeout=1)
        except queue.Empty:
            continue

        start = time.time()
        results = model.track(frame, persist=True)
        elapsed = time.time() - start

        inference_latency.observe(elapsed)
        if elapsed > 0:
            current_fps.set(1.0 / elapsed)

        detections = {"helmet": [], "head": [], "safety-jacket": []}

        if len(results) > 0:
            result = results[0]
            for box in result.boxes:
                confidence = float(box.conf)
                cls_name = result.names[int(box.cls)]
                detection = {"class": cls_name, "confidence": confidence}

                # Save low-confidence frames occasionally
                if confidence < 0.5 and frame_count % 30 == 0:
                    frame_count += 1
                    frame_name = f"low_confidence_frame_{frame_count}.jpg"
                    cv2.imwrite(os.path.join(save_directory, frame_name), frame)

                # Count detections + violations
                if cls_name == "helmet":
                    detections["helmet"].append(detection)
                    detections_total.labels("helmet").inc()
                elif cls_name == "head":
                    detections["head"].append(detection)
                    detections_total.labels("head").inc()
                    violations_total.labels("no_helmet").inc()
                elif cls_name == "safety-jacket":
                    detections["safety-jacket"].append(detection)
                    detections_total.labels("safety-jacket").inc()
                else:
                    detections_total.labels(cls_name).inc()

            with open(file_path, 'w') as f:
                json.dump(detections, f, indent=4)

            annotated_frame = result.plot()
        else:
            annotated_frame = frame.copy()

        with frame_lock:
            current_frame = annotated_frame.copy()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/inference', methods=['GET'])
def get_inference_data():
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return jsonify(data)
    except:
        return jsonify({})

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

def generate_frames():
    while True:
        with frame_lock:
            frame = None if current_frame is None else current_frame.copy()
        if frame is None:
            time.sleep(0.03)
            continue
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

if __name__ == "__main__":
    threading.Thread(target=tcp_frame_receiver, args=(args.port,), daemon=True).start()
    threading.Thread(target=inference_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

