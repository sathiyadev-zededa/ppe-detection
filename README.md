# Helmet and Jacket Detection with YOLOv8 on X86_64 CPU

This repository contains scripts and models for detecting helmets and jackets in images or video streams using YOLOv8.

## Repository Structure

.
├── app.py                                        # Main application for PPE detection
├── wrapper_script.sh                             # Utility script for running inference
├── templates/                                    # Template files (e.g., for configuration or HTML templates)
├── scripts/                                      # Additional utility scripts for setup or automation
├── ppe-cpu-helm/                                 # Helm charts for deploying PPE detection on Kubernetes
├── prometheus/                                   # Prometheus configuration for observability
├── grafana/                                      # Grafana dashboards for visualising metrics
├── inference_v1.py                               # Base inference script for YOLOv8 detection
├── inference_helmet.py                           # Helmet detection script (latest version)
├── inference_helmet_safety.py                    # Helmet and safety gear (jacket) detection script
├── inference.py                                  # General inference script for custom models
├── helmet_detection_yolov8_latest_v1.pt          # Earlier helmet detection model
├── helmet_detection_yolov8_latest_v2.pt          # Intermediate helmet detection model
├── helmet_detection_yolov8_latest_v3.pt          # Current latest helmet detection model ( Latest model for helmet detection)
├── helmet_jacket_detection_yolov8_latest_v2.pt   # Helmet + jacket detection model  (please do not use this model) 
├── best_jacket.pt                                # Previous jacket detection model
├── best_jacket_v1.pt                             # Current latest jacket detection model    (Latest model to detect helmet and safety-jacket)
└── Dockerfile                                    # Dockerfile for containerised deployment

## Features
1. Real-Time PPE Detection: Uses Ultralytics YOLOv8 to detect helmets and safety jackets in images, videos, or live streams.
2. Multiple Models: Supports various YOLOv8 model versions for helmet-only, jacket-only, or combined detection.
3. Observability: Prometheus for metrics collection and Grafana for visualisation of inference latency, detection accuracy, and system performance.
4. Containerization: Individual containers and Kubernetes (via Helm charts in ppe-cpu-helm) for scalable deployment.

## Dependency 
For dependency and how to invoke the inference, please refer to Dockerfile and wrapper_script.sh.sh

## Client Script 

docker run -it -e "video_stream=Safety_Full_Hat_and_Vest.mp4" -e "inference_server=172.16.8.48" -e "port=30002" commonpoc.azurecr.io/ppe-hardhat-client-amd64
