"""Service CLOUD simulé : lit le lien montant sur le broker Cloud.

S'abonne à iot/uplink/# et déduit le scénario du topic :
  iot/uplink/raw  -> scénario "cloud-only" (mesures brutes, tout arrive au Cloud)
  iot/uplink/edge -> scénario "edge-cloud" (flux réduit par l'Edge)

Pour chaque message : délai artificiel (liaison et traitement distants simulés),
moyenne glissante par capteur, puis publication sur iot/cloud/results.
Ce délai est ARTIFICIEL et doit être signalé comme tel dans le rapport.

Variables d'environnement : MQTT_HOST (localhost), MQTT_PORT (1884),
CLOUD_DELAY_SECONDS (0.2), WINDOW_SIZE (10).
"""
import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1884"))
DELAY = float(os.getenv("CLOUD_DELAY_SECONDS", "0.2"))
WINDOW = int(os.getenv("WINDOW_SIZE", "10"))

SCENARIOS = {"iot/uplink/raw": "cloud-only", "iot/uplink/edge": "edge-cloud"}
windows = defaultdict(lambda: deque(maxlen=WINDOW))


def on_connect(client, userdata, flags, reason_code, properties):
    print("Cloud connecté au broker Cloud, abonnement à iot/uplink/#")
    client.subscribe("iot/uplink/#", qos=1)


def on_message(client, userdata, msg):
    start = time.perf_counter()
    scenario = SCENARIOS.get(msg.topic)
    if scenario is None:
        return
    try:
        data = json.loads(msg.payload)
        value = float(data["avg_temperature"] if "avg_temperature" in data else data["temperature"])
        sensor_id = data["sensor_id"]
    except (ValueError, KeyError, TypeError) as err:
        print("Message ignoré :", err)
        return
    source_timestamp = data.get("source_timestamp") or data.get("timestamp")

    time.sleep(DELAY)  # délai ARTIFICIEL

    window = windows[(scenario, sensor_id)]
    window.append(value)
    client.publish("iot/cloud/results", json.dumps({
        "scenario": scenario,
        "sensor_id": sensor_id,
        "source_timestamp": source_timestamp,
        "processed_timestamp": datetime.now(timezone.utc).isoformat(),
        "avg_temperature": round(sum(window) / len(window), 2),
        "window_size": len(window),
        "processing_ms": round((time.perf_counter() - start) * 1000, 2),
    }), qos=1)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-consumer")
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            break
        except OSError as err:
            print(f"Broker Cloud indisponible ({err}), nouvel essai dans 2 s...")
            time.sleep(2)
    client.loop_forever()


if __name__ == "__main__":
    main()
