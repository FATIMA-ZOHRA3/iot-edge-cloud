"""Service Cloud simulé : reçoit les mesures, les traite avec un délai, publie le résultat.

Pour chaque mesure reçue sur iot/sensors/# :
  1. attend un délai artificiel (liaison et traitement distants simulés) ;
  2. calcule la moyenne glissante de la température du capteur ;
  3. publie le résultat sur iot/cloud/results.

Le délai est ARTIFICIEL : il doit être signalé comme tel dans le rapport.

Variables d'environnement (toutes facultatives) :
    MQTT_HOST            adresse du broker           (défaut : localhost)
    MQTT_PORT            port du broker              (défaut : 1883)
    CLOUD_DELAY_SECONDS  délai artificiel en secondes (défaut : 0.2)
    WINDOW_SIZE          mesures dans la moyenne      (défaut : 10)
"""
import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
CLOUD_DELAY_SECONDS = float(os.getenv("CLOUD_DELAY_SECONDS", "0.2"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "10"))

TOPIC_IN = "iot/sensors/#"
TOPIC_OUT = "iot/cloud/results"
RETRY_SECONDS = 2

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
    """Traite une mesure reçue et publie le résultat."""
    try:
        result = process_measurement(json.loads(msg.payload))
    except (ValueError, KeyError, TypeError) as err:
        print(f"Message ignoré ({err!r}) : {msg.payload[:80]!r}")
        return
    client.publish(TOPIC_OUT, json.dumps(result), qos=1)
    print(f"{result['sensor_id']} : moyenne {result['avg_temperature']} °C "
          f"sur {result['window_size']} mesure(s), {result['processing_ms']} ms")


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