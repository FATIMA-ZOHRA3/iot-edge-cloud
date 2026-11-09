"""Service Cloud simulé : reçoit les mesures, les traite avec un délai, publie le résultat.
Ajout : Écriture des résultats dans InfluxDB.
"""
import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
CLOUD_DELAY_SECONDS = float(os.getenv("CLOUD_DELAY_SECONDS", "0.2"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "10"))

# Configuration InfluxDB
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "iot-token-dev")
INFLUX_ORG = os.getenv("INFLUX_ORG", "ensah")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "iot")

TOPIC_IN = "iot/sensors/#"
TOPIC_OUT = "iot/cloud/results"
RETRY_SECONDS = 2

# Initialisation InfluxDB
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Dernières températures reçues, par capteur
windows = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))


def utc_now() -> str:
    """Heure actuelle en UTC, au format ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def process_measurement(measurement: dict) -> dict:
    """Applique le délai artificiel, met à jour la moyenne et construit le résultat."""
    start = time.perf_counter()
    time.sleep(CLOUD_DELAY_SECONDS)

    sensor_id = measurement["sensor_id"]
    window = windows[sensor_id]
    window.append(float(measurement["temperature"]))

    return {
        "scenario": "cloud",
        "sensor_id": sensor_id,
        "source_timestamp": measurement["timestamp"],
        "processed_timestamp": utc_now(),
        "avg_temperature": round(sum(window) / len(window), 2),
        "window_size": len(window),
        "processing_ms": round((time.perf_counter() - start) * 1000, 2),
    }


def on_connect(client, userdata, flags, reason_code, properties):
    """S'abonne aux mesures dès que la connexion au broker est établie."""
    if reason_code.is_failure:
        print(f"Connexion refusée : {reason_code}")
        return
    print(f"Cloud connecté à {MQTT_HOST}:{MQTT_PORT}, abonné à {TOPIC_IN}")
    client.subscribe(TOPIC_IN, qos=1)


def on_message(client, userdata, msg):
    """Traite une mesure reçue, publie le résultat et l'écrit dans InfluxDB."""
    try:
        result = process_measurement(json.loads(msg.payload))
    except (ValueError, KeyError, TypeError) as err:
        print(f"Message ignoré ({err!r}) : {msg.payload[:80]!r}")
        return
    
    # 1. Publication MQTT
    client.publish(TOPIC_OUT, json.dumps(result), qos=1)
    
    # 2. Écriture dans InfluxDB
    try:
        point = Point("iot_results") \
            .tag("scenario", "cloud") \
            .tag("sensor_id", result["sensor_id"]) \
            .field("temperature", result["avg_temperature"]) \
            .field("processing_ms", result["processing_ms"]) \
            .time(result["processed_timestamp"])
        
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    except Exception as e:
        print(f"Erreur InfluxDB : {e}")

    print(f"{result['sensor_id']} : moyenne {result['avg_temperature']} °C "
          f"sur {result['window_size']} mesure(s), {result['processing_ms']} ms -> InfluxDB")


def connect_with_retry(client: mqtt.Client) -> None:
    """Réessaie tant que le broker n'est pas joignable."""
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            return
        except OSError as err:
            print(f"Broker indisponible ({err}), nouvel essai dans {RETRY_SECONDS} s...")
            time.sleep(RETRY_SECONDS)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-consumer")
    client.on_connect = on_connect
    client.on_message = on_message
    connect_with_retry(client)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Arrêt demandé.")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()