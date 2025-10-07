FROM python:3.10-slim
RUN apt update && apt install openssh-server sudo -y
RUN apt install ffmpeg libsm6 libxext6 -y
RUN pip install opencv-python
RUN pip install pickle4
RUN useradd -rm -d /home/ubuntu -s /bin/bash  -g root -G sudo -u 1001 pocuser
RUN echo 'pocuser:pocuser' | chpasswd
ENV video_stream="camera"
ENV inference_server="10.216.2.63"
ENV port="30002"
RUN service ssh start
RUN mkdir -p /home/pocuser/client
COPY client.py /home/pocuser/client/
COPY 1.mp4 /home/pocuser/client/
COPY *.mp4 /home/pocuser/client/
COPY wrapper_script.sh /home/pocuser/client/
WORKDIR /home/pocuser/client
RUN ["chmod", "+x", "./wrapper_script.sh"]
CMD ["./wrapper_script.sh", "$video_stream", "$inference_server", "$port"]
