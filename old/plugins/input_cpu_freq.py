from plugins import InputPlugin, HASensor
import psutil

class CpuFreqInputPlugin(InputPlugin):
    def sensors(self):
        return [ HASensor( name="cpu_freq", state_class="measurement", device_class='frequency', unit_of_measurement="khz") ]

    def read(self):
        return {"cpu_freq": int(psutil.cpu_freq(percpu=False).current)}