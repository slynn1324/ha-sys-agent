import importlib.util
from pathlib import Path
from plugins import InputPlugin, OutputPlugin
import importlib
import time
import signal
import sys

def sigint_handler(signum, frame):
    sys.exit()

signal.signal(signal.SIGINT, sigint_handler)




config = {
    "interval": 10.0
}

plugin_paths = [Path("./plugins")] #, Path("./ext_plugins")

modules = {}

# discover plugins
for plugin_path in plugin_paths:
    for f in plugin_path.iterdir():
        if f.is_file() and f.name.endswith(".py") and ( f.name.startswith("input_") or f.name.startswith("output_")):
            spec = importlib.util.spec_from_file_location("plugins." + f.stem, f.resolve())
            module = importlib.util.module_from_spec(spec)
            modules[f.stem] = module # if we don't keep a reference to the module, it might get unloaded
            spec.loader.exec_module(module)

# init plugins
input_plugins = {}
for cls in InputPlugin.__subclasses__():
    input_plugins[cls.__name__] = cls()


output_plugins = {}
for cls in OutputPlugin.__subclasses__():
    output_plugins[cls.__name__] = cls(input_plugins)


# warmup plugins
for name,plugin in input_plugins.items():
    plugin.read()
time.sleep(1)

# loop read
while True:
    data = {}
    for name,plugin in input_plugins.items():
        data.update(plugin.read())
        # plugin.read()
    
    for name,plugin in output_plugins.items():
        plugin.write(data)

    time.sleep(config['interval'])

