#!/bin/bash

/usr/sbin/sshd -D &
python inference_helmet_safety.py --path best_jacket.pt
