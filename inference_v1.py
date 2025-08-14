import argparse
import pickle
import struct
import threading
import numpy as np
import cv2
import socket
import torch
import ssl
import time, os, json
from flask import Flask, Response, render_template, jsonify, send_file
from ultralytics import YOLO

ssl._create_default_https_context = ssl._create_unverified_context

parser = argparse.ArgumentParser(description="YOLOv8 Stream Inference Server")
parser.add_argument("--path", required=True, help="Path to the YOLOv8 model")
args = parser.parse_args()
path = args.path

model = YOLO(path)

host = '0.0.0.0'
port = 8080
CLIENT_TIMEOUT = 10

app = Flask(__name__)
current_frame = None
frame_lock = threading.Lock()
file_path = 'data.json'
video_writer = None
video_file = 'output.mp4'
frame_size = (640, 480)  # Set your expected frame size
fps = 20


def client_handler(connection):
    global current_frame, video_writer
    data = b""
    payload_size = struct.calcsize("Q")
    last_data_time = time.time()
    frame_count = 0
    save_directory = '/app/data/low_confidence_frames'

    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

    while True:
        try:
            while len(data) < payload_size:
                packet = connection.recv(2 * 1024)
                if not packet:
                    break
                data += packet

            if not data:
                current_time = time.time()
                if current_time - last_data_time > CLIENT_TIMEOUT:
                    print("Client stopped sending data. Closing the connection.")
                    break

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data) < msg_size:
                data += connection.recv(2 * 1024)

            frame_data = data[:msg_size]
            data = data[msg_size:]

            camera_name, frame = pickle.loads(frame_data)
            frame = cv2.resize(frame, frame_size)
            results = model.track(frame, persist=True)

            for result in results:
                detections = {
                    "helmet": [],
                    "head": [],
                    "safety-jacket": []
                }

                for box in result.boxes:
                    confidence = float(box.conf)
                    if confidence < 0.5:
                        frame_count += 1
                        frame_name = f"low_confidence_frame_{frame_count}.jpg"
                        frame_path = os.path.join(save_directory, frame_name)
                        cv2.imwrite(frame_path, frame)

                    detection = {
                        "class": result.names[int(box.cls)],
                        "confidence": confidence
                    }
                    if detection["class"] == "helmet":
                        detections['helmet'].append(detection)
                    elif detection["class"] == "head":
                        detections['head'].append(detection)
                    elif detection["class"] == "safety-jacket":
                        detections.setdefault('safety-jacket', []).append(detection)

                with open(file_path, 'w') as file:
                    json.dump(detections, file, indent=4)
                print(f"prediction = {json.dumps(detections, indent=4)}")

            annotated_frame = results[0].plot()

            # Save current frame for video stream and recording
            with frame_lock:
                current_frame = annotated_frame.copy()

            # Save to video
            if video_writer:
                video_writer.write(annotated_frame)

            # Optional: save for MJPEG stream
            np.save('array.npy', annotated_frame)

            last_data_time = time.time()

        except Exception as e:
            print(f"Client disconnected - exception {e}")
            cv2.destroyWindow(camera_name)
            for _ in range(4):
                cv2.waitKey(1)
            break
    connection.close()
    return 0

def accept_connections(server_socket):
    while True:
        client, address = server_socket.accept()
        print('Connected to: ' + address[0] + ':' + str(address[1]))
        threading.Thread(target=client_handler, args=(client,)).start()

def start_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((host, port))
    except socket.error as e:
        print(str(e))
    print(f'Server is listening on port {port}...')
    server_socket.listen()
    threading.Thread(target=accept_connections, args=(server_socket,)).start()

def generate_frames():
    loaded_array = None

    while True:
        try:
            loaded_array = np.load('array.npy')
            os.remove('array.npy')
        except:
            pass

        if loaded_array is None:
            continue

        ret, buffer = cv2.imencode('.jpg', loaded_array)
        if not ret:
            print("Failed to encode frame")
            continue
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return {}

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
    threading.Thread(target=start_server, args=(host, port)).start()
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

