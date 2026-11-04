"""Service EDGE : passerelle entre le broker local et le broker Cloud.

Il lit les mesures brutes sur le broker LOCAL (iot/sensors/#) et envoie vers le
broker CLOUD selon EDGE_MODE :

  reduce  (scénario edge-cloud, par défaut)
      - décision locale immédiate (ALERTE / NORMAL) publiée sur le broker local
        (iot/edge/local), qui continue de marcher même si le Cloud est coupé ;
      - une moyenne par groupe de EDGE_BATCH mesures envoyée au Cloud
        (iot/uplink/edge) : flux réduit.
  forward (scénario cloud-only)
      - chaque mesure brute est envoyée telle quelle au Cloud (iot/uplink/raw),
        sans aucun traitement local. Sert de référence « tout au Cloud ».

Si le Cloud est coupé, les messages du lien montant sont gardés en mémoire
(jusqu'à UPLINK_BUFFER_MAX) puis envoyés à la reconnexion.

Variables d'environnement : LOCAL_HOST (localhost), LOCAL_PORT (1883),
CLOUD_HOST (localhost), CLOUD_PORT (1884), EDGE_MODE (reduce), EDGE_BATCH (5),
ALERT_TEMPERATURE (30), UPLINK_BUFFER_MAX (10000).
"""
import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

LOCAL_HOST = os.getenv("LOCAL_HOST", "localhost")
LOCAL_PORT = int(os.getenv("LOCAL_PORT", "1883"))
CLOUD_HOST = os.getenv("CLOUD_HOST", "localhost")
CLOUD_PORT = int(os.getenv("CLOUD_PORT", "1884"))
MODE = os.getenv("EDGE_MODE", "reduce")
BATCH = int(os.getenv("EDGE_BATCH", "5"))
ALERT_TEMPERATURE = float(os.getenv("ALERT_TEMPERATURE", "30"))
BUFFER_MAX = int(os.getenv("UPLINK_BUFFER_MAX", "10000"))

if MODE not in ("reduce", "forward"):
    raise SystemExit(f"EDGE_MODE invalide : {MODE} (reduce ou forward)")

buffers = defaultdict(list)           # mesures en attente de moyenne, par capteur
pending = deque(maxlen=BUFFER_MAX)    # messages du lien montant en attente
dropped = 0
lock = threading.Lock()

local = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-local")
uplink = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-uplink")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def flush_pending():
    """À appeler avec le verrou pris."""
    sent = 0
    while pending and uplink.is_connected():
        topic, payload = pending[0]
        if uplink.publish(topic, payload, qos=1).rc != mqtt.MQTT_ERR_SUCCESS:
            break
        pending.popleft()
        sent += 1
    return sent


def send_uplink(topic, payload):
    global dropped
    with lock:
        if len(pending) == pending.maxlen:
            dropped += 1
        pending.append((topic, payload))
        flush_pending()


def on_uplink_connect(client, userdata, flags, reason_code, properties):
    with lock:
        waiting = len(pending)
        sent = flush_pending()
    print(f"Lien Cloud établi ({sent} message(s) en attente envoyé(s) sur {waiting})")


def on_uplink_disconnect(client, userdata, flags, reason_code, properties):
    print(f"Lien Cloud coupé ({reason_code}) : les messages sont gardés en mémoire")


def on_local_connect(client, userdata, flags, reason_code, properties):
    print(f"Edge connecté au broker local, mode={MODE}")
    client.subscribe("iot/sensors/#", qos=1)


def on_local_message(client, userdata, msg):
    start = time.perf_counter()
    try:
        data = json.loads(msg.payload)
        temperature = float(data["temperature"])
        sensor_id = data["sensor_id"]
    except (ValueError, KeyError, TypeError) as err:
        print("Message ignoré :", err)
        return

    if MODE == "forward":
        send_uplink("iot/uplink/raw", msg.payload)
        return

    # --- mode reduce : décision locale, puis flux réduit vers le Cloud ---
    status = "ALERTE" if temperature > ALERT_TEMPERATURE else "NORMAL"
    client.publish("iot/edge/local", json.dumps({
        "sensor_id": sensor_id,
        "timestamp": data.get("timestamp"),
        "processed_timestamp": now_iso(),
        "temperature": temperature,
        "status": status,
        "processing_ms": round((time.perf_counter() - start) * 1000, 3),
    }), qos=1)

    buffer = buffers[sensor_id]
    buffer.append((temperature, data.get("timestamp")))
    if len(buffer) >= BATCH:
        send_uplink("iot/uplink/edge", json.dumps({
            "sensor_id": sensor_id,
            "source_timestamp": buffer[-1][1],
            "edge_timestamp": now_iso(),
            "avg_temperature": round(sum(t for t, _ in buffer) / len(buffer), 2),
            "window_size": len(buffer),
        }))
        buffer.clear()


def main():
    uplink.on_connect = on_uplink_connect
    uplink.on_disconnect = on_uplink_disconnect
    uplink.reconnect_delay_set(min_delay=1, max_delay=5)
    uplink.connect_async(CLOUD_HOST, CLOUD_PORT, 60)
    uplink.loop_start()

    local.on_connect = on_local_connect
    local.on_message = on_local_message
    while True:
        try:
            local.connect(LOCAL_HOST, LOCAL_PORT, 60)
            break
        except OSError as err:
            print(f"Broker local indisponible ({err}), nouvel essai dans 2 s...")
            time.sleep(2)
    local.loop_forever()


if __name__ == "__main__":
    main()
