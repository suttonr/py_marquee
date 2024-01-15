import time
import secrets
from umqtt.simple import MQTTClient

class mqtt_client():
    def __init__(self) -> None:
        self.connect()
        self.set_callback()
        
    def connect(self):
        self.mqtt = MQTTClient("umqtt_client", 
                          secrets.MQTT_BROKER,
                          secrets.MQTT_PORT,
                          secrets.MQTT_USERNAME,
                          secrets.MQTT_PASSWORD
                          )
        self.mqtt.connect()
        self.mqtt.set_last_will(
            secrets.MQTT_LOGGING_TOPIC, "marquee disconnect")
        self.mqtt.publish(
            secrets.MQTT_LOGGING_TOPIC, "marquee connected")

    def pub(self, msg, topic=secrets.MQTT_LOGGING_TOPIC):
        self.mqtt.publish(topic, msg)
    
    def sub(self, topic):
        self.mqtt.subscribe(topic)
    
    def message_arrived(self, topic, message):
        print(topic, message)

    def set_callback(self, sub_cb=None):
        if sub_cb:
            self.mqtt.set_callback(sub_cb)
        else:
            self.mqtt.set_callback(self.message_arrived)

    def get_msg(self, blocking=False):
        if blocking:
            return self.mqtt.wait_msg()
        else:
            return self.mqtt.check_msg()
