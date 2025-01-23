import time
import psutil
import json
import old.utils as utils
import subprocess
from pathlib import Path
import json
import platform

POLLING_RATE=1

hostname = platform.node().split(".")[-1]

class Ratable:
    def __init__(self):
        self.value = 0.0
        self.read_time = 0.0
        self.rate = 0.0

    def update(self, value, read_time=None):
        if read_time == None:
            read_time = time.time()
        if self.read_time > 0:
            print(f"{value} - {self.value} / {read_time} - {self.read_time}")
            self.rate = ( value - self.value ) / (read_time - self.read_time )
        self.value = value
        self.read_time = read_time


eth0_rx = Ratable()
eth0_tx = Ratable()

def format_label(str):
    return str.lower().replace(" ", "_")

# could also possibly scan through the links on /dev/disk/by-id... but this was easier
def get_disk_names():
    try:
        proc = subprocess.run(['/usr/bin/lsblk', '--json', '-o', 'NAME,MODEL,SERIAL'], capture_output=True)
        parsed = json.loads(proc.stdout)
        rval = {}
        for bd in parsed['blockdevices']:
            rval[bd['name']] = format_label(bd['model'] + "_" + bd['serial'])
        return rval
    except:
        return {}

# map out the files from /sys/class/hwmon to read temperatures for cpu and disks (if drivetemp module loaded)
# this will only work on linux
def get_temp_files():
    hwmon_path = Path("/sys/class/hwmon")

    if not hwmon_path.is_dir():
        return {}

    temp_files = {}

    disk_names = get_disk_names()

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
                    disk_names[device_name]
                temp_file = dir / "temp1_input"
                temp_files[f"disk_{disk_name}_temp"] = temp_file

    return temp_files

def read_temps(temp_files):
    rval = {}
    for name,f in temp_files.items():
        rval[name] = float(f.read_text().strip()) / 1000.0
    return rval


def publish_ha_discovery():

    msg = {
        "dev":{
            "ids":f"ha-sys-agent-{hostname}",
            "name":f"ha-sys-agent-{hostname}"
        },
        "o":{
            "name":"ha-sys-agent"
        },
        "state_topic": "/ha-sys-agent/{hostname}/state",
        "components": {
            "cpu_percent":{
                "platform":"sensor",
                "device_class":"measurement",
                "unit_of_measurement":"%",
                "unique_id":f"ha-sys-agent-{hostname}-cpu_percent"
            }
        }
    }

    print(json.dumps(msg, indent=2))
    


temp_files = get_temp_files()

psutil.cpu_percent()
net_io = psutil.net_io_counters(pernic=True, nowrap=True)
eth0_rx.update(net_io['eth0'].bytes_recv)
eth0_tx.update(net_io['eth0'].bytes_sent)
 
time.sleep(1)

while True:
    data = {}
    data['cpu_percent'] = psutil.cpu_percent()
#    data['memory_percent_zfs'] = utils.apply_zfs_arcstats( psutil.virtual_memory() ).percent
    data['memory_percent'] = psutil.virtual_memory().percent 

    data['cpu_freq'] = int(psutil.cpu_freq(percpu=False).current)

    load = psutil.getloadavg()
    data['load_1'] = round(load[0],2)
    data['load_5'] = round(load[1],2)
    data['load_15'] = round(load[2],2)
    
    net_io = psutil.net_io_counters(pernic=True, nowrap=True)
    eth0_rx.update(net_io['eth0'].bytes_recv)
    eth0_tx.update(net_io['eth0'].bytes_sent)
    data['eth0_rx'] = eth0_rx.value #net_io['eth0'].bytes_recv
    data['eth0_tx'] = eth0_tx.value #net_io['eth0'].bytes_sent
    data['eth0_rx_kbps'] = round( (eth0_rx.rate * 8 ) / 1000.0 , 2)
    data['eth0_tx_kbps'] = round( (eth0_tx.rate * 8 ) / 1000.0 , 2)

    data.update(read_temps(temp_files))

    print(json.dumps(data, indent=2))
    time.sleep(POLLING_RATE)
