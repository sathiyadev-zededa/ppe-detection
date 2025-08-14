FROM python:3.12-slim
RUN apt update && apt install openssh-server sudo -y
RUN apt update && \
    apt install -y openssh-server sudo libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*
RUN pip install flask
RUN pip install pickle4
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN pip install opencv-python
RUN pip install lapx>=0.5.2
RUN pip install ultralytics
RUN useradd -rm -d /home/ubuntu -s /bin/bash  -g root -G sudo -u 1001 pocuser
RUN echo 'pocuser:pocuser' | chpasswd
RUN service ssh start
RUN mkdir -p /home/pocuser/server
RUN mkdir -p /home/pocuser/server/templates
VOLUME ["/app/data"]
COPY inference_helmet.py /home/pocuser/server/
COPY templates/index.html /home/pocuser/server/templates/
COPY helmet_jacket_detection_yolov8_latest_v3.pt /home/pocuser/server/
COPY wrapper_script.sh /home/pocuser/server/
WORKDIR /home/pocuser/server/
EXPOSE 22
EXPOSE 8080
EXPOSE 5000
RUN ["chmod", "+x", "./wrapper_script.sh"]
CMD ["./wrapper_script.sh"]
