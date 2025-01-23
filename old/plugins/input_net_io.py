from plugins import InputPlugin, Ratable, HASensor
import psutil

class NetIOInputPlugin(InputPlugin):
    def __init__(self):
        self.eth0_rx = Ratable()
        self.eth0_tx = Ratable()

    def sensors(self):
        return [ 
            HASensor(name="eth0_rx", state_class="total_increasing", device_class="data_size", unit_of_measurement="bytes" ),
            HASensor(name="eth0_tx", state_class="total_increasing", device_class="data_size", unit_of_measurement="bytes" ),
            HASensor(name="eth0_rx_kbps", state_class="measurement", device_class="data_rate", unit_of_measurement="kbps" ),
            HASensor(name="eth0_tx_kbps", state_class="measurement", device_class="data_rate", unit_of_measurement="kbps" ),
        ]

    def read(self):
        net_io = psutil.net_io_counters(pernic=True, nowrap=True)
        self.eth0_rx.update(net_io['eth0'].bytes_recv)
        self.eth0_tx.update(net_io['eth0'].bytes_sent)
        data = {}
        data['eth0_rx'] = self.eth0_rx.value #net_io['eth0'].bytes_recv
        data['eth0_tx'] = self.eth0_tx.value #net_io['eth0'].bytes_sent
        data['eth0_rx_kbps'] = round( (self.eth0_rx.rate * 8 ) / 1000.0 , 2)
        data['eth0_tx_kbps'] = round( (self.eth0_tx.rate * 8 ) / 1000.0 , 2)
        return data