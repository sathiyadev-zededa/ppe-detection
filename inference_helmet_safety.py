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
        results = model.track(frame, persist=True)

        detections = {
                "helmet": [], 
                "head": [],
                "safety-jacket": []
        }

        if len(results) > 0:
            result = results[0]
            for box in result.boxes:
                confidence = float(box.conf)
                cls_name = result.names[int(box.cls)]
                detection = {"class": cls_name, "confidence": confidence}

                if confidence < 0.5:
                    frame_count += 1
                    frame_name = f"low_confidence_frame_{frame_count}.jpg"
                    cv2.imwrite(os.path.join(save_directory, frame_name), frame)

                if cls_name == "helmet":
                    detections["helmet"].append(detection)
                elif cls_name == "head":
                    detections["head"].append(detection)
                elif cls_name == ["safety-jacket"]:
                    detections["safety-jacket"].append(detection)

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
        os.remove(file_path)
        return jsonify(data)
    except:
        return jsonify({})

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

@app.route('/retain_files', methods=['GET'])
def get_retrain_files():
    try:
        directory = os.path.abspath('/app/data/low_confidence_frames')
        if not os.path.isdir(directory):
            return jsonify({'error': 'Directory not found'}), 404
        file_line = os.listdir(directory)
        return jsonify(file_line)
    except Exception as e:
        print(f"Exception while collecting low confidence files: {e}")
        return {}

if __name__ == "__main__":
    threading.Thread(target=tcp_frame_receiver, args=(args.port,), daemon=True).start()
    threading.Thread(target=inference_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

