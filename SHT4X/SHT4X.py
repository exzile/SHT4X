
from smbus2 import SMBus, i2c_msg 
import time 
import struct 
 

_SHT4X_DEFAULT_ADDR = 0x44  # SHT4X I2C Address
_SHT4X_READSERIAL = 0x89  # Read Out of Serial Register
_SHT4X_SOFTRESET = 0x94  # Soft Reset



class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples):
        """Add CV values to the class"""
        cls.string = {}
        cls.delay = {}

        for value_tuple in value_tuples:
            name, value, string, delay = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.delay[value] = delay

    @classmethod
    def is_valid(cls, value):
        """Validate that a given value is a member"""
        return value in cls.string


class Mode(CV):
    """Options for ``power_mode``"""

    pass  # pylint: disable=unnecessary-pass


Mode.add_values(
    (
        ("NOHEAT_HIGHPRECISION", 0xFD, "No heater, high precision", 0.01),
        ("NOHEAT_MEDPRECISION", 0xF6, "No heater, med precision", 0.005),
        ("NOHEAT_LOWPRECISION", 0xE0, "No heater, low precision", 0.002),
        ("HIGHHEAT_1S", 0x39, "High heat, 1 second", 1.1),
        ("HIGHHEAT_100MS", 0x32, "High heat, 0.1 second", 0.11),
        ("MEDHEAT_1S", 0x2F, "Med heat, 1 second", 1.1),
        ("MEDHEAT_100MS", 0x24, "Med heat, 0.1 second", 0.11),
        ("LOWHEAT_1S", 0x1E, "Low heat, 1 second", 1.1),
        ("LOWHEAT_100MS", 0x15, "Low heat, 0.1 second", 0.11),
    )
)


class SHT4x:
 
    def __init__(self,  sht4xAddress=_SHT4X_DEFAULT_ADDR,bus=3): 
        self.address = sht4xAddress
        self.bus = SMBus(bus) 
        self.reset()
        self._mode = Mode.NOHEAT_HIGHPRECISION  # pylint: disable=no-member
    
        
    @property
    def serial_number(self):
        """The unique 32-bit serial number""" 
        msg_w = i2c_msg.write(self.address,[_SHT4X_READSERIAL])
        self.bus.i2c_rdwr(msg_w) 
        time.sleep(0.01)
        msg_r = i2c_msg.read(self.address,6)
        self.bus.i2c_rdwr(msg_r)
        result = bytearray(list(msg_r))   

        ser1 = result[0:2]
        ser1_crc = result[2]
        ser2 = result[3:5]
        ser2_crc = result[5]

        # check CRC of bytes
        if ser1_crc != self._crc8(ser1) or ser2_crc != self._crc8(ser2):
            raise RuntimeError("Invalid CRC calculated")

        serial = (ser1[0] << 24) + (ser1[1] << 16) + (ser2[0] << 8) + ser2[1]
        return serial  
 
 

    def reset(self):
        """Perform a soft reset of the sensor, resetting all settings to their power-on defaults"""         
        msg_w = i2c_msg.write(self.address,[_SHT4X_SOFTRESET])
        self.bus.i2c_rdwr(msg_w) 
        time.sleep(0.001)

    @property
    def mode(self):
        """The current sensor reading mode (heater and precision)"""
        return self._mode

    @mode.setter
    def mode(self, new_mode):

        if not Mode.is_valid(new_mode):
            raise AttributeError("mode must be a Mode")
        self._mode = new_mode

    @property
    def relative_humidity(self):
        """The current relative humidity in % rH. This is a value from 0-100%."""
        return self.measurements[1]

    @property
    def temperature(self) -> float:
        """The current temperature in degrees Celsius"""
        return self.measurements[0]

    @property 
    def measurements(self):

        msg_w = i2c_msg.write(self.address,[self._mode])
        self.bus.i2c_rdwr(msg_w) 
        time.sleep(Mode.delay[self._mode])
        msg_r = i2c_msg.read(self.address,6)
        self.bus.i2c_rdwr(msg_r)
        result = bytearray(list(msg_r)) 
           
        temp_data = result[0:2]
        temp_crc = result[2]
        humidity_data = result[3:5]
        humidity_crc = result[5]

        ## check CRC of bytes
        if temp_crc != self._crc8(temp_data) or humidity_crc != self._crc8(
            humidity_data
        ):
            raise RuntimeError("Invalid CRC calculated")

        # #decode data into human values:
        # #convert bytes into 16-bit signed integer
        # #convert the LSB value to a human value according to the datasheet
        temperature = struct.unpack_from(">H", temp_data)[0]
        temperature = -45.0 + 175.0 * temperature / 65535.0 
        
        ##repeat above steps for humidity data
        humidity = struct.unpack_from(">H", humidity_data)[0]
        humidity = -6.0 + 125.0 * humidity / 65535.0
        humidity = max(min(humidity, 100), 0)
         
        return (temperature, humidity)

   

    @staticmethod
    def _crc8(buffer):
        """verify the crc8 checksum"""
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF  # return the bottom 8 bits


##uncomment and run this python file to test
#x = SHT4x() 
#print(str(x.temperature))
#print(str(x.relative_humidity))
#print(x.serial_number)
