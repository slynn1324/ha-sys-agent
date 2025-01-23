#!/bin/sh

# use --net host to get access to read net stats for host network devices
podman run -d \
    --name ha-sys-agent \
    -e HA_SYS_AGENT_MQTT_HOST=192.168.1.3 \
    -e HA_SYS_AGENT_MQTT_USER=homeassistant \
    -e HA_SYS_AGENT_MQTT_PASS=homeassistant \
    -e HA_SYS_AGENT_NET_DEVS=eth0 \
    --net host \
    ha-sys-agent
