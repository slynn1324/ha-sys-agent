# ha-sys-agent - Home Assistant System Agent

A simplified linux host stats collector that reports sensors in a Home Assistant compatible format via MQTT, including Home Assistant MQTT Discovery messages.

Only tested on Debian 12, but should in theory work on any Linux.  Temperature reports depend on a functional `/sys` filesystem, and will be omitted if not present.  To get hard drive temperatures, ensure that the 'drivetemp' kernel module is loaded.

## Dependencies
dependencies are limted to psutil and paho-mqtt

## Configuration

All configuration is assigned via environment variables as to be prime for containerization.

| Variable Name             | Description                                                   | Required          | Default   |
| ---                       | ---                                                           | ---               | ---       |
| HA_SYS_AGENT_MQTT_HOST    | The hostname or ip address of the mqtt server                 | Yes               | None      |
| HA_SYS_AGENT_MQTT_PORT    | The port number of the mqtt server                            | No                | 1883      |
| HA_SYS_AGENT_MQTT_USER    | The username to connect to the mqtt server                    | No                | None      |
| HA_SYS_AGENT_MQTT_PASS    | The password to connect to the mqtt server                    | If User given     | None      |
| HA_SYS_AGENT_INTERVAL     | The interval to poll for and report stats in seconds          | No                | 10.0      |     
| HA_SYS_AGENT_VERBOSE      | Verbose output to stdout (any value enables)                  | No                | False     |
| HA_SYS_AGENT_DISCO_TOPIC  | The topic to publish the HA device discovery message to.  `{hostname}` will be replaced if present.   | No | homeassistant/device/ha-sys-agent-{hostname}/config
| HA_SYS_AGENT_TOPIC_PREFIX | The prefix to use for the state topics. `{hostname}` will be replaced if present.  | No | ha-sys-agent/{hostname}
| HA_SYS_AGENT_NET_DEVS     | Comma-separated list of network devices to include stats for  | No                | None      |
| HA_SYS_AGENT_DUS          | Disk usage paths in the format `name:path`.  e.g, `root:/,tank:/mnt/tank` | No    | None      |

## running
python3 venv ./venv
source venv/bin/activate
pip3 install psutil paho-mqtt
`./python3 c.py`

## podman build | docker
see `./podman-build.sh` 

```
podman build -t ha-sys-agent .
```

## podman run
see `./podman-run.sh`

```
podman run -d \
    --name ha-sys-agent \
    -e HA_SYS_AGENT_MQTT_HOST=192.168.1.3 \
    -e HA_SYS_AGENT_MQTT_USER=homeassistant \
    -e HA_SYS_AGENT_MQTT_PASS=homeassistant \
    -e HA_SYS_AGENT_NET_DEVS=eth0 \
    --net host \
    ha-sys-agent
```