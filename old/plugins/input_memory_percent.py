from plugins import InputPlugin, HASensor
import psutil

class MemoryPercentInputPlugin(InputPlugin):

    def sensors(self):
        return [ HASensor( name="memory_percent", state_class="measurement", device_class=None, unit_of_measurement="%" ) ]
    
    def read(self):
        return { "memory_percent" : psutil.virtual_memory().percent }
