# Helmet and Jacket Detection with YOLOv8

This repository contains scripts and models for detecting helmets and jackets in images or video streams using YOLOv8.

## Repository Structure



.
├── wrapper_script.sh # Utility script for running inference
├── templates/ # Template files (if any)
├── inference_v1.py # Base inference script
├── inference_helmet.py # Helmet detection script latest version
├── inference_helmet_safety.py # Helmet and safety gear detection latest version
├── inference.py # General inference script
├── helmet_detection_yolov8_latest_v1.pt
├── helmet_detection_yolov8_latest_v2.pt
├── helmet_detection_yolov8_latest_v3.pt #current latest version helmet detection model
├── helmet_jacket_detection_yolov8_latest_v2.pt
├── best_jacket.pt # current latest version helmet and safety-jacket detection model
└── Dockerfile # Dockerfile to containerize the application
