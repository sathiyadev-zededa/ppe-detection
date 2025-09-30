import argparse
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
from prometheus_client import start_http_server, Counter, Gauge, Histogram
from ultralytics import YOLO

ssl._create_default_https_context = ssl._create_unverified_context
frame_size = (640, 480)
CLIENT_TIMEOUT = 10
file_path = 'data.json'
save_directory = '/app/data/low_confidence_frames'

if not os.path.exists(save_directory):
    os.makedirs(save_directory, exist_ok=True)

parser = argparse.ArgumentParser(description="YOLOv8 TCP Stream (Threaded, CPU)")
parser.add_argument("--path", required=True, help="Path to YOLOv8 model")
parser.add_argument("--port", type=int, default=8080, help="TCP port")
args = parser.parse_args()

model = YOLO(args.path)
model.to('cpu')

frame_queue = queue.Queue(maxsize=1)
current_frame = None
frame_lock = threading.Lock()

start_http_server(8000)

detections_total = Counter('ppe_detections_total', 'Total PPE detections', ['class'])
violations_total = Counter('ppe_violations_total', 'Total PPE violations', ['type'])
confidence_avg = Gauge('ppe_confidence_avg', 'Average confidence score', ['class'])
inference_latency = Histogram('ppe_inference_latency_seconds', 'Inference latency', buckets=[0.1, 0.5, 1.0, 2.0, 5.0])
error_count = Counter('ppe_errors_total', 'Total errors during detection')
health_gauge = Gauge('ppe_app_health', 'Application health status (1=healthy, 0=unhealthy)')

def tcp_frame_receiver(port):
    print("before connection")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(1)
    print(f"[TCP] Listening on port {port}...")
    print("after connection")
    while True:
        conn, addr = server_socket.accept()
        print(f"[TCP] Connected from {addr}")
        conn.settimeout(5.0)
        data = b""
        payload_size = struct.calcsize("Q")
        print(f"payload size: {payload_size}")
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

                #np_data = np.frombuffer(frame_data, np.uint8)
                #frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
                #print(f"FRAME ::::: {frame}")

                if frame is None:
                    continue

                #frame = cv2.resize(frame, frame_size)

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

def process_inference(frame):
    try:
        start_time = time.time()
        results = model.track(frame, persist=True)
        output = {
            "helmet": [],
            "head": [],
            "safety-jacket": []
        }

        if len(results) > 0:
            result = results[0]
            for box in result.boxes:
                cls_name = result.names[int(box.cls)]
                confidence = float(box.conf)
                output[cls_name].append({"class": cls_name, "confidence": confidence})

            helmet_detections = len(output["helmet"])
            head_detection = len(output["head"])
            jacket_detection = len(output["safety-jacket"]

            detections_total.labels('helmet').inc(helmet_detections)
            detections_total.labels('head').inc(head_detection)
            detections_total.labels('safety-jacket').inc(jacket_detection)

            no_helmet_violations = 0
            no_jacket_violations = 0
            if head_detections > 0:
                if helmet_detections == 0:
                    no_helmet_violations = head_detections
                    violations_total.labels('no_helmet').inc(head_detections)
                if jacket_detections == 0:
                    no_jacket_violations = head_detections
                    violations_total.labels('no_safety_jacket').inc(head_detections)
            return result
        else:
            return None
    except Exception as e:
        error_count.inc()
        health_gauge.set(0)
        print(f"Error: {e}")
        return None

def inference_worker():
    global current_frame
    frame_count = 0
    print(f"inside inference_worker")
    while True:
        try:
            frame = frame_queue.get(timeout=1)
        except queue.Empty:
            print("Queue empty...", flush=True)
            continue

        print("Processing frame...", flush=True)
        result = process_inference(frame)

        if result == None:
            annotated_frame = frame.copy()
        else:
            annotated_frame = result.plot()

        with frame_lock:
            current_frame = annotated_frame.copy()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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
