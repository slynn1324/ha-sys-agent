from pathlib import Path
import subprocess
import json
  
# could also possibly scan through the links on /dev/disk/by-id... but this was easier
def get_disk_names():
    proc = subprocess.run(['/usr/bin/lsblk', '--json', '-o', 'NAME,MODEL,SERIAL'], capture_output=True)
    parsed = json.loads(proc.stdout)
    rval = {}
    for bd in parsed['blockdevices']:
        rval[bd['name']] = bd['model'].replace(" ","_") + "_" + bd['serial'].replace(" ","_") 
    return rval

def get_temp_files():
    temp_files = {}

    disk_names = get_disk_names()
     
    for dir in Path("/sys/class/hwmon").iterdir():
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
                disk_name = disk_names[device_name]
                temp_file = dir / "temp1_input"
                temp_files[f"disk_{disk_name}_temp"] = temp_file
   
    return temp_files
               
def read_temps(temp_files):
    rval = {}
    for name,f in temp_files.items():
        rval[name] = float(f.read_text().strip()) / 1000.0
    return rval


