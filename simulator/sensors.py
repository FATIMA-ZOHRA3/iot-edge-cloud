"""Simulateur de capteurs : publie des mesures JSON sur MQTT.

Topic de publication : iot/sensors/<sensor_id>
Variables d'environnement (toutes facultatives) :
  MQTT_HOST (localhost)  MQTT_PORT (1883)
  N_SENSORS (1)          INTERVAL_SECONDS (2.0)
"""
import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
N_SENSORS = int(os.getenv("N_SENSORS", "1"))
INTERVAL = float(os.getenv("INTERVAL_SECONDS", "2.0"))


def connect(client_id):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            return client
        except OSError as err:
            print(f"Broker indisponible ({err}), nouvel essai dans 2 s...")
            time.sleep(2)


def measurement(sensor_id):
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": round(random.uniform(18, 35), 2),
        "humidity": round(random.uniform(30, 80), 2),
        "vibration": round(random.uniform(0.0, 5.0), 3),
    }


def main():
    client = connect("simulator")
    client.loop_start()
    sensors = [f"sensor-{i:02d}" for i in range(1, N_SENSORS + 1)]
    print(f"Simulateur : {len(sensors)} capteur(s), un message toutes les {INTERVAL} s")
    try:
        while True:
            for sensor_id in sensors:
                data = measurement(sensor_id)
                client.publish(f"iot/sensors/{sensor_id}", json.dumps(data), qos=1)
                print("Publié :", data)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Arrêt demandé.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
