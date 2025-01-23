import time
import platform
import json
from pathlib import Path
import re
import sys
import signal
import os
import psutil
import paho.mqtt.client as mqtt

def quit_signal_handler(signum, frame):
    print("shutdown")
    sys.exit()
signal.signal(signal.SIGINT, quit_signal_handler)
signal.signal(signal.SIGTERM, quit_signal_handler)

hostname = os.environ.get("HA_SYS_AGENT_HOSTNAME", platform.node().split(".")[-1])

interval = float(os.environ.get("HA_SYS_AGENT_INTERVAL", 10.0))
verbose = 'HA_SYS_AGENT_VERBOSE' in os.environ

mqtt_host = os.environ.get("HA_SYS_AGENT_MQTT_HOST")
mqtt_port = int(os.environ.get("HA_SYS_AGENT_MQTT_PORT", "1883"))
mqtt_user = os.environ.get("HA_SYS_AGENT_MQTT_USER")
mqtt_pass = os.environ.get("HA_SYS_AGENT_MQTT_PASS")

if not mqtt_host:
    raise ValueError("HA_SYS_AGENT_MQTT_HOST is required")

if mqtt_user and not mqtt_pass:
    raise ValueError("HA_SYS_AGENT_MQTT_PASS is required when HA_SYS_AGENT_MQTT_USER is provided")

discovery_topic = os.environ.get("HA_SYS_AGENT_DISCO_TOPIC", "homeassistant/device/ha-sys-agent-{hostname}/config").format( hostname=hostname )
topic_prefix = os.environ.get("HA_SYS_AGENT_TOPIC_PREFIX", "ha-sys-agent/{hostname}").format(hostname=hostname)
availability_topic = os.environ.get("HA_SYS_AGENT_AVAIL_TOPIC", f"{topic_prefix}/status").format(hostname=hostname)

net_devices = os.environ.get("HA_SYS_AGENT_NET_DEVS")
net_devices = [ x.strip() for x in net_devices.split(",") ] if net_devices else [] #['eth0']

du_filesystems = os.environ.get("HA_SYS_AGENT_DUS") #{ "du_root": "/", "du_tank": "/mnt/tank", "du_scratch": "/mnt/scratch", "du_vm": "/mnt/vm" }
du_filesystems =  { y[0] : y[1] for y in [ x.strip().split(":") for x in du_filesystems.split(",") ] } if du_filesystems else {}

print(du_filesystems)

class Collector():
    def __init__(self, names, func=None, topics=None, platform="sensor", state_class="measurement", unit_of_measurement=None, device_class=None, icon=None, period=None):
        self.names = [ re.sub('[^0-9a-zA-Z_]+', '_', x) for x in (names if isinstance(names, list) else [names]) ]
        self.func = func
        self.topics = topics if topics else [f"{topic_prefix}/{name}" for name in self.names]
        self.platform = platform if isinstance(platform, list) else [platform] * len(self.names)
        self.state_class = state_class if isinstance(state_class, list) else [state_class] * len(self.names)
        self.unit_of_measurement = unit_of_measurement if isinstance(unit_of_measurement, list) else [unit_of_measurement] * len(self.names)
        self.device_class = device_class if isinstance(device_class, list) else [device_class] * len(self.names)
        self.icon = icon if isinstance(icon, list) else [icon] * len(self.names)
        self.period = period
        self.last_read_time = 0

        for x in ['topics', 'platform', 'state_class', 'unit_of_measurement', 'device_class', 'icon']:
            if len(getattr(self, x)) != len(self.names):
                raise ValueError(f"wrong number of items in {x}, expecting {len(self.names)} got {len(getattr(self,x))}")
             
    def values(self):
        if self.period and (time.time() - self.last_read_time) < self.period:
            return {}

        values = self.read()
        self.last_read_time = time.time()

        if values == None: # if returning None, then return empty to skip read
            return {}

        if not isinstance(values, list):
            values = [values]

        if len(values) != len(self.names):
            raise ValueError(f"wrong number of values for collector {self.names}, expecting {len(self.names)} got {len(values)} => {values}")
        return { name : values[idx] for idx,name in enumerate(self.names) } 
    
    def read(self):
        if self.func == None:
            raise NotImplementedError(f"func was not provided, nor was it implemented in a subclass for collector {self.names}")
        return self.func()

# collector subclass to collect net io stats for all selected netdevs with only one read from psutil 
# each device adds 4 metrics - {dev}_rx, {dev}_rx_kbps, {dev}_tx, {dev}_tx_kbps
class NetIOCollector(Collector):
    def __init__(self, devices):
        self.devices = devices
        self.net_read_time = 0
        self.value = None
        names = []
        scs = []
        uoms = []
        dcs = []
        for d in self.devices:
            names.extend( [ f"{d}_rx", f"{d}_rx_kbps", f"{d}_tx", f"{d}_tx_kbps" ] )
            scs.extend( [ "total_increasing", "measurement", "total_increasing", "measurement" ] )
            uoms.extend( ["bytes", "kbps", "bytes", "kbps"] )
            dcs.extend( ["data_size", "data_rate", "data_size", "data_rate"] )
        super().__init__(names, unit_of_measurement=uoms, device_class=dcs)

    def values(self):
        v = super().values()
        self.last_values = v
        return v
    
    def read(self):
        net_io = psutil.net_io_counters(pernic=True) #, nowrap=True) avoid the overhead and unbounded sensor value growth
        now = time.time()
        
        value = []
        for i,d in enumerate(self.devices):
            rx = net_io[d].bytes_recv
            tx = net_io[d].bytes_sent
            last_rx = self.last_read_result[i*4] if self.net_read_time > 0 else 0
            last_tx = self.last_read_result[i*4+2] if self.net_read_time > 0 else 0

            # if rollover, reset last_rx.  this may lose a few bytes on a rollover, but rollovers are at like 18 Exabytes on a 64-bit system
            last_rx = last_rx if last_rx <= rx else 0
            last_tx = last_tx if last_tx <= tx else 0

            rx_rate = round( ( ( rx - last_rx ) / ( now - self.last_read_time ) ) * 8 / 1000.0 , 2) if self.net_read_time > 0 else 0
            tx_rate = round( ( ( tx - last_tx ) / ( now - self.last_read_time ) ) * 8 / 1000.0 , 2) if self.net_read_time > 0 else 0

            value.append(rx)
            value.append(rx_rate)
            value.append(tx)
            value.append(tx_rate)

        self.last_read_result = value
        self.net_read_time = now
        return value

class DUCollector(Collector):
    def __init__(self, name, path):
        self.path = path
        self.name = name
        super().__init__([f"{name}_percent", f"{name}_total", f"{name}_used"], func=None, topics=None, platform="sensor", state_class="measurement", unit_of_measurement=["%", "GB", "GB"] , device_class=[None, "data_size", "data_size"], icon=None, period=600)

    def read(self):
        du = psutil.disk_usage(self.path)
        return [ du.percent, round(du.total / 1073741824.0, 1), round(du.used / 1073741824.0, 1) ]


def get_discovery_msg(collectors):
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
        "cmps":{}
    }

    for collector in collectors:
        for idx,name in enumerate(collector.names):
            cmp = {
                "name": name,
                "platform":collector.platform[idx],
                "state_class":collector.state_class[idx],
                "object_id": f"ha-sys-agent-{hostname}-{name}",
                "unique_id": f"ha-sys-agent-{hostname}-{name}",
                "state_topic": collector.topics[idx],
                "availability_topic": availability_topic
            }
            if collector.device_class[idx] != None:
                cmp['device_class'] = collector.device_class[idx]
            
            if collector.unit_of_measurement[idx] != None:
                cmp['unit_of_measurement'] = collector.unit_of_measurement[idx]
            
            if collector.icon[idx] != None:
                cmp['icon'] = collector.icon[idx]

            msg['cmps'][name] = cmp

    return msg
    


def get_temperature_files():
    hwmon_path = Path("/sys/class/hwmon")

    if not hwmon_path.is_dir():
        return {}

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
                temp_file = dir / "temp1_input"
                temp_files[f"disk_{device_name}_temp"] = temp_file

    return temp_files

temperature_files = get_temperature_files()

collectors = []
collectors.append( Collector("cpu_percent", lambda: psutil.cpu_percent(), unit_of_measurement="%"))
collectors.append( Collector("cpu_freq", lambda: int(psutil.cpu_freq(percpu=False).current), device_class="frequency", unit_of_measurement="khz"))
collectors.append( Collector( ["load_1", "load_5", "load_15"], lambda: [round(x,2) for x in list(psutil.getloadavg())] , unit_of_measurement="loadavg" ))
collectors.append( Collector("memory_percent", lambda: psutil.virtual_memory().percent , unit_of_measurement="%"))

for name,path in du_filesystems.items():
    collectors.append( DUCollector(name,path) )

for name,f in temperature_files.items():
    collectors.append( Collector( name, lambda: float(f.read_text().strip()) / 1000.0 , period=600 if name.startswith("disk") else None,
                                 unit_of_measurement="°C", device_class="temperature" ))

collectors.append(NetIOCollector(net_devices))

discovery_msg = get_discovery_msg(collectors)
if verbose:
    print(f"discovery_topic: {discovery_topic}")
    print("discovery_message: ")
    print(json.dumps(discovery_msg, indent=2))
    print("")


# mqtt init
mqttc = mqtt.Client()
if mqtt_user:
    mqttc.username_pw_set(mqtt_user, mqtt_pass)

def mqtt_on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("mqtt connected")
        mqttc.publish(discovery_topic, json.dumps(discovery_msg), retain=True)
        client.publish(availability_topic, "online", retain=True)

mqttc.on_connect = mqtt_on_connect

mqttc.will_set(f"{topic_prefix}/status", payload="offline", retain=True)
mqttc.connect(mqtt_host, 1883, 60)
mqttc.loop_start() # start the async loop

# warmup
for c in collectors:
    c.read()
   
time.sleep(1)

print("ha-sys-agent started")
print(f"  mqtt_host: {mqtt_host}")
print(f"  discovery_topic: {discovery_topic}")
print(f"  interval: {interval}")

while True:
    data = {}
    for c in collectors:
        values = c.values()
        data.update(values)
        for i,n in enumerate(c.names):
            if n in values:
                if verbose:
                    print(f"{c.topics[i]}:{values[n]}")
                mqttc.publish(c.topics[i], values[n])

    if verbose: print("")

    # if verbose:
    #     print(json.dumps(data, indent=2))

    time.sleep(interval)



