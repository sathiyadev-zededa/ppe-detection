#!/bin/bash
/usr/sbin/sshd -D &
python client.py --video $video_stream --host $inference_server --port $port
