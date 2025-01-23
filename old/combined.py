import time
import json
import platform
import paho.mqtt.client as mqtt
import psutil 
import re
import subprocess
from pathlib import Path
import sys

# get the hostname to use in config
hostname = platform.node().split(".")[-1]



# config

mqtt_host = "192.168.1.3"
mqtt_port = 1883
mqtt_user = "homeassistant"
mqtt_pass = "homeassistant"

discovery_topic = f"homeassistant/device/ha-sys-agent-{hostname}/config"
state_topic = f"ha-sys-agent/{hostname}/state"

net_devices = ['eth0']
du_filesystems = { "du_root": "/", "du_tank": "/mnt/tank", "du_scratch": "/mnt/scratch", "du_vm": "/mnt/vm" }

# end config



# helper class to track a "rate" computed from a total_increasing value (e.g. net io counters)
class Ratable:
    def __init__(self):
        self.value = 0.0
        self.read_time = 0.0
        self.rate = 0.0

    def update(self, value, read_time=None):
        if read_time == None:
            read_time = time.time()
        if self.read_time > 0:
            self.rate = ( value - self.value ) / (read_time - self.read_time )
        self.value = value
        self.read_time = read_time


# build a discovery component section
def discovery_component(name, platform="sensor", state_class="measurement", device_class=None, unit_of_measurement=None, icon=None):
    c = {
        "name": name,
        "platform": platform,
        "state_class": state_class,
        "object_id": f"ha-sys-agent-{hostname}-{name}",
        "unique_id": f"ha-sys-agent-{hostname}-{name}"
    }
    
    #c["value_template"] = f"{{{{ value_json.{name} }}}}"
    c["state_topic"] = f"ha-sys-agent/{hostname}/{name}"
    
    if device_class:
        c['device_class'] = device_class
    if unit_of_measurement:
        c['unit_of_measurement'] = unit_of_measurement
    if icon:
        c['icon'] = icon
    return c

# build the ha discovery message
def get_discovery_msg(net_devices, temperature_files):
    msg = {
        "dev":{
            "ids":f"ha-sys-agent-{hostname}",
            "name":f"ha-sys-agent-{hostname}",
            "mf":"ha-sys-agent",
            "mdl":hostname
        },
        "o":{
            "name":"ha-sys-agent"
        },
        # "state_topic": state_topic,
        "components": {
            "cpu_percent": discovery_component("cpu_percent", unit_of_measurement="%", icon="mdi:percent"),
            "cpu_freq": discovery_component("cpu_freq", device_class="frequency", unit_of_measurement="khz"),
            "load_1": discovery_component("load_1"),
            "load_5": discovery_component("load_5"),
            "load_15": discovery_component("load_15"),
            "memory_percent": discovery_component("memory_percent", unit_of_measurement="%", icon="mdi:percent")
        }
    }

    for nd in net_devices:
        msg['components'][f"{nd}_rx"] = discovery_component(f"{nd}_rx", unit_of_measurement="bytes", device_class="data_size")
        msg['components'][f"{nd}_tx"] = discovery_component(f"{nd}_tx", unit_of_measurement="bytes", device_class="data_size")
        msg['components'][f"{nd}_rx_kbps"] = discovery_component(f"{nd}_rx_kbps", unit_of_measurement="kbps", device_class="data_rate")
        msg['components'][f"{nd}_tx_kbps"] = discovery_component(f"{nd}_tx_kbps", unit_of_measurement="kbps", device_class="data_rate")

    for name in temperature_files:
        msg['components'][name] = discovery_component(name, unit_of_measurement="°C", device_class="temperature")

    for name, path in du_filesystems.items():
        msg['components'][f"{name}_percent"] = discovery_component(f"{name}_percent", unit_of_measurement="%")
        msg['components'][f"{name}_total"] = discovery_component(f"{name}_total", unit_of_measurement="GB", device_class="data_size")
        msg['components'][f"{name}_used"] = discovery_component(f"{name}_used", unit_of_measurement="GB", device_class="data_size")

    return msg


# walk the /sys/class/hwmon directory for cpu package and drivetemp files
def get_temperature_files():
    hwmon_path = Path("/sys/class/hwmon")

    if not hwmon_path.is_dir():
        return {}
    
    disk_names = {}
    try:
        proc = subprocess.run(['/usr/bin/lsblk', '--json', '-o', 'NAME,MODEL,SERIAL'], capture_output=True)
        parsed = json.loads(proc.stdout)
        disk_names = {}
        for bd in parsed['blockdevices']:
            disk_names[bd['name']] = re.sub('[^0-9a-zA-Z_]+', '_', f"{bd['model']}_{bd['serial']}")
    except Exception as e:
        print(e)

    temp_files = {}

    for dir in hwmon_path.iterdir():
        name_path = dir / "name"
        if name_path.is_file():
            name = name_path.read_text().strip()
            if name == "coretemp":
                for f in dir.iterdir():
                    if f.is_file() and f.name.endswith("_label"):
                        label = f.read_text().strip()
                        if label == "Package id 0":
                            temp_files['cpu_temp'] = dir / f.name.replace("_label", "_input")
            elif name == "drivetemp":
                device_path = dir / "device" / "block"
                device_name = [ x for x in device_path.iterdir() if x.is_dir() ][0].name
                disk_name = device_name
                if device_name in disk_names:
                    disk_name = disk_names[device_name]
                disk_name = re.sub('[^0-9a-zA-Z_]+', '_', disk_name) # clean up disk name
                temp_file = dir / "temp1_input"
                temp_files[f"disk_{disk_name}_temp"] = temp_file

    return temp_files
    

# init net devices
net_stats = {}
for nd in net_devices:
    net_stats[nd] = { "rx" : Ratable(), "tx" : Ratable() }

# init temperature files
temperature_files = get_temperature_files()

# mqtt init
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if mqtt_user:
    mqttc.username_pw_set(mqtt_user, mqtt_pass)
mqttc.connect(mqtt_host, 1883, 60)
mqttc.loop_start() # start the async loop

# publish discovery message as retained so it's available on HA restart
discovery_msg = get_discovery_msg(net_devices, temperature_files)
mqttc.publish(discovery_topic, json.dumps(discovery_msg), retain=True)

topic_map = {}
for name,value in discovery_msg['components'].items():
    topic_map[name] = value['state_topic']

# warm up cpu and net counters
psutil.cpu_percent()

net_io = psutil.net_io_counters(pernic=True, nowrap=True)
for k,v in net_stats.items():
    v["rx"].update(net_io[k].bytes_recv)
    v["tx"].update(net_io[k].bytes_sent)

time.sleep(1)



last_du_time = 0

while True:
    data = {}
    data['cpu_percent'] = psutil.cpu_percent()

    data['cpu_freq'] = int(psutil.cpu_freq(percpu=False).current)

    load = psutil.getloadavg()
    data['load_1'] = round(load[0], 2)
    data['load_5'] = round(load[0], 2)
    data['load_15'] = round(load[0], 2)

    data['memory_percent'] = psutil.virtual_memory().percent

    net_io = psutil.net_io_counters(pernic=True, nowrap=True)
    for k,v in net_stats.items():
        v["rx"].update(net_io[k].bytes_recv)
        v["tx"].update(net_io[k].bytes_sent)
        data[f"{k}_rx"] = v["rx"].value
        data[f"{k}_tx"] = v["tx"].value
        data[f"{k}_rx_kbps"] = round( ( v["rx"].rate * 8 ) / 1000.0 , 2)
        data[f"{k}_tx_kbps"] = round( ( v["tx"].rate * 8 ) / 1000.0 , 2)

    for name, f in temperature_files.items():
        data[name] = float(f.read_text().strip()) / 1000.0

    # only grab disk usage every hour
    if time.time() - last_du_time > 3600:
        for name, value in du_filesystems.items():
            du = psutil.disk_usage(value).percent
            data[f"{name}_used"] = round(psutil.disk_usage(value).used / 1073741824.0, 1)
            data[f"{name}_total"] = round(psutil.disk_usage(value).total / 1073741824.0, 1)
            data[f"{name}_percent"] = psutil.disk_usage(value).percent
        last_du_time = time.time()

    print(json.dumps(data, indent=2))
    # mqttc.publish(state_topic, json.dumps(data))
    for name,value in data.items():
        mqttc.publish(topic_map[name], str(value))

    time.sleep(10)
