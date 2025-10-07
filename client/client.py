import socket
import cv2
import pickle
import struct
import time

import argparse

parser = argparse.ArgumentParser(description="Send video frames over the network.")
parser.add_argument('--video', type=str, required=True, help="Path to the video file")
parser.add_argument('--host', type=str, required=True, help="Host IP address")
parser.add_argument('--port', type=int, required=True, help="Port number")

args = parser.parse_args()

host = args.host
port = args.port
if args.video == 'camera':
    video_path = 0
else:
    video_path = args.video
camera_name = 'CV001'

if host is None or port is None or camera_name is None:
    raise ValueError("Configuration values missing in config.txt")

def send_frame(ClientSocket, camera_name):
    while True:
        vid = cv2.VideoCapture(video_path)
        if not vid.isOpened():
            print("Error: Unable to open video file.")
            break

        while vid.isOpened():
            ret, frame = vid.read()
            if not ret:
                # Restart video playback when it ends
                print("Restarting video...")
                vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Resize frame to reduce bandwidth
            frame = cv2.resize(frame, (320, 240))

            # Serialize frame data with camera name
            data = pickle.dumps((camera_name, frame))
            message = struct.pack("Q", len(data)) + data
            try:
                ClientSocket.sendall(message)
                time.sleep(0.1)
            except (socket.error, BrokenPipeError) as e:
                print("Connection to the server lost. Attempting to reconnect...")
                vid.release()
                reconnect(ClientSocket)
                break  # Exit the inner loop to reset video capture

        vid.release()

def reconnect(ClientSocket):
    while True:
        try:
            ClientSocket.connect((host, port))
            print("Reconnected to the server.")
            break
        except socket.error as e:
            print(f"Reconnection failed: {str(e)}. Retrying in 5 seconds...")
            time.sleep(5)

# Initialize client socket
ClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Waiting for connection...")
try:
    ClientSocket.connect((host, port))
    print("Connected to the server.")
except socket.error as e:
    print(f"Error connecting to server: {str(e)}")
    reconnect(ClientSocket)

# Send frames in a loop
try:
    send_frame(ClientSocket, camera_name)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    ClientSocket.close()

