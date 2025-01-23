FROM alpine

wORKDIR /app

RUN apk add python3 py3-paho-mqtt py3-psutil lsblk

COPY ha-sys-agent.py /app/ha-sys-agent.py

ENTRYPOINT ["python3", "-u", "ha-sys-agent.py"]