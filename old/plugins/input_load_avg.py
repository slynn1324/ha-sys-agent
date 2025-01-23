from plugins import InputPlugin, HASensor
import psutil

class LoadAvgInputPlugin(InputPlugin):
    
    def sensors(self):
        return [
            HASensor( name="load_1", state_class="measurement", device_class=None, unit_of_measurement="load" ),
            HASensor( name="load_5", state_class="measurement", device_class=None, unit_of_measurement="load" ),
            HASensor( name="load_15", state_class="measurement", device_class=None, unit_of_measurement="load" )
        ]
    
    def read(self):
        load = psutil.getloadavg()
        return {
            "load_1": round(load[0], 2),
            "load_5": round(load[1], 2),
            "load_15": round(load[2], 2)
        }