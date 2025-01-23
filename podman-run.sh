#!/bin/sh

# use --net host to get access to read net stats for host network devices
podman run -d \
    --pull newer \
    --name ha-sys-agent \
    --restart always \
    -e HA_SYS_AGENT_MQTT_HOST=192.168.1.3 \
    -e HA_SYS_AGENT_MQTT_USER=homeassistant \
    -e HA_SYS_AGENT_MQTT_PASS=homeassistant \
    -e HA_SYS_AGENT_NET_DEVS=eth0 \
    -e HA_SYS_AGENT_DUS="root:/, tank:/tank, scratch:/scratch, vm:/vm" \
    -v /mnt/tank:/tank:ro \
    -v /mnt/scratch:/scratch:ro \
    -v /mnt/vm:/vm:ro \
    --net host \
    ghcr.io/slynn1324/ha-sys-agent:latest

# -e HA_SYS_AGENT_DUS="root:/,tank:/mnt/tank,scratch:/mnt/scratch,vm:/mnt/vm" \
    
