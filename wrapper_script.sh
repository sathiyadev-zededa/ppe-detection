#!/bin/bash

/usr/sbin/sshd -D &
python inference_helmet.py --path helmet_detection_yolov8_latest_v3.pt
