import paho.mqtt.client as mqtt
import json
import time
import os
import argparse # <-- AJOUTEZ CECI
from sensors import create_measurement, sensor_ids

# Configuration du parser d'arguments
parser = argparse.ArgumentParser(description="Simulateur IoT")
parser.add_argument("--sensors", type=int, help="Nombre de capteurs")
parser.add_argument("--interval", type=float, help="Intervalle en secondes")
args = parser.parse_args()

# On utilise l'argument s'il est fourni, sinon on utilise la variable d'environnement, sinon la valeur par défaut
N_SENSORS = args.sensors if args.sensors is not None else int(os.getenv("N_SENSORS", 1))
INTERVAL = args.interval if args.interval is not None else float(os.getenv("INTERVAL_SECONDS", 2.0))

# Configuration MQTT
BROKER = os.getenv("MQTT_HOST", "mosquitto")
PORT = int(os.getenv("MQTT_PORT", 1883))

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="simulator-publisher")
client.connect(BROKER, PORT, 60)
client.loop_start()

ids = sensor_ids(N_SENSORS)
print(f"Connecté à {BROKER}. Envoi pour {N_SENSORS} capteur(s) toutes les {INTERVAL}s...")

try:
    while True:
        for sensor_id in ids:
            data = create_measurement(sensor_id)
            topic = f"iot/sensors/{sensor_id}"
            client.publish(topic, json.dumps(data), qos=1)
            print(f"Publié sur {topic} : {data}")
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    print("Arrêt.")
finally:
    client.loop_stop()
    client.disconnect()