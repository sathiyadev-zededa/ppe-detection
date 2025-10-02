#!/bin/bash

/usr/sbin/sshd -D &
python app.py --path best_jacket_v1.pt
