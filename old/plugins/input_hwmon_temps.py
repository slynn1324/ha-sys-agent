from plugins import InputPlugin, HASensor
from pathlib import Path
import subprocess
import json

class HwmonTempsInputPlugin(InputPlugin):
    
    @staticmethod
    def format_label(str):
        return str.lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def get_temp_files():
        hwmon_path = Path("/sys/class/hwmon")

        if not hwmon_path.is_dir():
            return {}

        temp_files = {}

        disk_names = HwmonTempsInputPlugin.get_disk_names()

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
                    temp_file = dir / "temp1_input"
                    temp_files[f"disk_{disk_name}_temp"] = temp_file

        return temp_files

    @staticmethod
    def get_disk_names():
        try:
            proc = subprocess.run(['/usr/bin/lsblk', '--json', '-o', 'NAME,MODEL,SERIAL'], capture_output=True)
            parsed = json.loads(proc.stdout)
            rval = {}
            for bd in parsed['blockdevices']:
                rval[bd['name']] = HwmonTempsInputPlugin.format_label(bd['model'] + "_" + bd['serial'])
            return rval
        except Exception as e:
            print(e)
            return {}
        
    def __init__(self):
        self.temp_files = HwmonTempsInputPlugin.get_temp_files()

    def sensors(self):
        sensors = []
        for name,f in self.temp_files.items():
            sensors.append( HASensor( name=name, state_class="measurement", device_class="temperature", unit_of_measurement="°C" ) )
        return sensors

    def read(self):
        rval = {}
        for name,f in self.temp_files.items():
            rval[name] = float(f.read_text().strip()) / 1000.0
        return rval
