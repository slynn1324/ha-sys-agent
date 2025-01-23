from plugins import OutputPlugin
import json
import paho.mqtt.client as mqtt
import platform

class MqttOutputPlugin(OutputPlugin):

    def create_discovery_message(self, input_plugins):
        hostname = platform.node().split(".")[-1]
        msg = {
            "dev": {
                "ids": f"ha-sys-agent-{hostname}",
                "name":f"ha-sys-agent-{hostname}"
            },
            "o": {
                "name":"ha-sys-agent"
            },
            "state_topic": f"{self._topic}",
            "components":{}
        }

        for name,ip in input_plugins.items():
            for sensor in ip.sensors():
                msg['components'][sensor.name] = {
                    
                    "platform": "sensor",
                    "name": sensor.name,
                    "state_class": sensor.state_class,
                    "unique_id": f"ha-sys-agent-{hostname}-{sensor.name}",
                    "object_id": f"ha-sys-agent-{hostname}-{sensor.name}",
                    "value_template": f"{{{{ value_json.{sensor.name} }}}}",
                }
                if sensor.unit_of_measurement != None:
                    msg['components'][sensor.name]['unit_of_measurement'] = sensor.unit_of_measurement

        return msg

    def __init__(self, input_plugins):
        self.mqttc = mqtt.Client()
        self.mqttc.username_pw_set("homeassistant", "homeassistant")
        self.mqttc.connect("192.168.1.3", 1883, 60)
        self.mqttc.loop_start()

        self._hostname = platform.node().split(".")[-1]
        self._topic = f"ha-sys-agent/{self._hostname}/state"
        
        discovery_msg = self.create_discovery_message(input_plugins)
        self.mqttc.publish(topic=f"homeassistant/device/ha-sys-agent-{self._hostname}/config", payload=json.dumps(discovery_msg), retain=True)


    def write(self, data):
        print(json.dumps(data, indent=2))
        self.mqttc.publish(topic=self._topic, payload=json.dumps(data))