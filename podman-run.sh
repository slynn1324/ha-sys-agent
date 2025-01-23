#!/bin/sh

#HA_SYS_AGENT_MQTT_HOST=192.168.1.3 HA_SYS_AGENT_MQTT_USER=homeassistant HA_SYS_AGENT_MQTT_PASS=homeassistant HA_SYS_AGENT_NET_DEVS=eth0 python3 ha-sys-agent.py

# use --net host to get access to read net stats for host network devices
podman run -d \
    --pull newer \
    --name ha-sys-agent \
    -e HA_SYS_AGENT_MQTT_HOST=192.168.1.3 \
    -e HA_SYS_AGENT_MQTT_USER=homeassistant \
    -e HA_SYS_AGENT_MQTT_PASS=homeassistant \
    -e HA_SYS_AGENT_NET_DEVS=eth0 \
    --net host \
    ghcr.io/slynn1324/ha-sys-agent:latest
    
    #ha-sys-agent