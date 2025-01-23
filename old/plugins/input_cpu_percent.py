from plugins import InputPlugin, HASensor
import psutil

class CpuPercentInputPlugin(InputPlugin):

    def sensors(self):
        return [ HASensor(name="cpu_percent", state_class="measurement", device_class=None, unit_of_measurement="%") ]

    def read(self):
        return { "cpu_percent": psutil.cpu_percent() }