from abc import ABC,abstractmethod
import time
from collections import namedtuple

HASensor = namedtuple('HASensor', ['name', 'state_class', 'device_class', 'unit_of_measurement'])

class InputPlugin(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def sensors(self): 
        pass

    @abstractmethod
    def read(self):
        pass



class OutputPlugin(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def write(self):
        pass



class Ratable:
    def __init__(self):
        self.value = 0.0
        self.read_time = 0.0
        self.rate = 0.0

    def update(self, value, read_time=None):
        if read_time == None:
            read_time = time.time()
        if self.read_time > 0:
            self.rate = ( value - self.value ) / (read_time - self.read_time )
        self.value = value
        self.read_time = read_time