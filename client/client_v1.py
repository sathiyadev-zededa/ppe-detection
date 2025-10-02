import socket
import cv2
import pickle
import struct
import time
import argparse

parser = argparse.ArgumentParser(description="Send video frames over the network.")
parser.add_argument('--video', type=str, required=True, help="Path to the video file")
parser.add_argument('--host', type=str, required=True, help="Server IP address")
parser.add_argument('--port', type=int, required=True, help="Server port number")
args = parser.parse_args()

host = args.host
port = args.port
video_path = args.video
camera_name = 'CV001'

def reconnect():
    while True:
        try:
            print("[INFO] Attempting to connect to server...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            print("[INFO] Connected to server.")
            return sock
        except socket.error as e:
            print(f"[WARN] Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def send_video():
    while True:
        client_socket = reconnect()

        # Open the video file
        vid = cv2.VideoCapture(video_path)
        if not vid.isOpened():
            print(f"[ERROR] Failed to open video file: {video_path}")
            return

        while True:
            ret, frame = vid.read()

            if not ret:
                print("[INFO] End of video file. Looping...")
                vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Resize frame to reduce bandwidth (optional)
            frame = cv2.resize(frame, (320, 240))

            # Serialize frame data along with camera name
            data = pickle.dumps((camera_name, frame))
            message = struct.pack("Q", len(data)) + data

            try:
                client_socket.sendall(message)
                time.sleep(0.033)  # 30 FPS control
            except (socket.error, BrokenPipeError) as e:
                print(f"[ERROR] Connection lost: {e}. Reconnecting...")
                try:
                    client_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                client_socket.close()
                vid.release()
                break  # Break inner loop to reconnect and restart video

# ---------------------- Entry Point ----------------------
if __name__ == "__main__":
    try:
        send_video()
    except KeyboardInterrupt:
        print("\n[INFO] Streaming interrupted by user.")

