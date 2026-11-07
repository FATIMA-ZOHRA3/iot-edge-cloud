import paho.mqtt.client as mqtt
import json
import time
import os
from sensors import create_measurement, sensor_ids

# Configuration (utilise "mosquitto" car on sera dans Docker)
BROKER = os.getenv("MQTT_HOST", "mosquitto")
PORT = int(os.getenv("MQTT_PORT", 1883))
N_SENSORS = int(os.getenv("N_SENSORS", 1))
INTERVAL = float(os.getenv("INTERVAL_SECONDS", 2.0))

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="simulator-publisher")
client.connect(BROKER, PORT, 60)
client.loop_start()

ids = sensor_ids(N_SENSORS)
print(f"Connecté à {BROKER}. Envoi pour {N_SENSORS} capteur(s)...")

try:
    while True:
        for sensor_id in ids:
            data = create_measurement(sensor_id) # On utilise la fonction de sensor.py
            topic = f"iot/sensors/{sensor_id}"
            client.publish(topic, json.dumps(data), qos=1)
            print(f"Publié sur {topic} : {data}")
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    print("Arrêt.")
finally:
    client.loop_stop()
    client.disconnect()