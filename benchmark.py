"""Benchmark : observe les deux brokers pendant DURATION secondes.

Les services doivent déjà tourner (docker compose up -d). Pour chaque flux :
nombre de messages, débit, octets et latence moyenne (heure de réception moins
heure d'émission d'origine). Un CSV est écrit dans results/.

Flux observés :
  sensors        mesures brutes (broker local)
  edge_local     décisions locales de l'Edge (broker local)
  uplink         ce qui traverse le lien Edge -> Cloud (broker Cloud) = bande passante
  cloud_results  résultats finaux du Cloud (broker Cloud) = latence de bout en bout

Usage : python benchmark.py [durée_en_secondes] [étiquette]
  ex.  : python benchmark.py 120 edge-cloud-5-capteurs

Variables : LOCAL_HOST, LOCAL_PORT (1883), CLOUD_HOST, CLOUD_PORT (1884).
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

LOCAL = (os.getenv("LOCAL_HOST", "localhost"), int(os.getenv("LOCAL_PORT", "1883")))
CLOUD = (os.getenv("CLOUD_HOST", "localhost"), int(os.getenv("CLOUD_PORT", "1884")))
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 120
LABEL = sys.argv[2] if len(sys.argv) > 2 else "essai"

# (flux, broker, filtre de topic, champs possibles pour l'heure d'émission d'origine)
STREAMS = [
    ("sensors", "local", "iot/sensors/#", ("timestamp",)),
    ("edge_local", "local", "iot/edge/local", ("timestamp",)),
    ("uplink", "cloud", "iot/uplink/#", ("source_timestamp", "timestamp")),
    ("cloud_results", "cloud", "iot/cloud/results", ("source_timestamp",)),
]
stats = {name: {"messages": 0, "bytes": 0, "latencies": []} for name, *_ in STREAMS}


def make_client(broker):
    def on_connect(client, userdata, flags, reason_code, properties):
        for _, b, topic, _ in STREAMS:
            if b == broker:
                client.subscribe(topic, qos=1)

    def on_message(client, userdata, msg):
        received = datetime.now(timezone.utc)
        for name, b, topic, fields in STREAMS:
            if b == broker and mqtt.topic_matches_sub(topic, msg.topic):
                entry = stats[name]
                entry["messages"] += 1
                entry["bytes"] += len(msg.payload)
                try:
                    obj = json.loads(msg.payload)
                    field = next(f for f in fields if f in obj)
                    sent = datetime.fromisoformat(obj[field])
                    entry["latencies"].append((received - sent).total_seconds() * 1000)
                except (ValueError, StopIteration, TypeError):
                    pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"benchmark-{broker}")
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main():
    clients = []
    for broker, (host, port) in (("local", LOCAL), ("cloud", CLOUD)):
        client = make_client(broker)
        client.connect(host, port, 60)
        client.loop_start()
        clients.append(client)
    print(f"Mesure pendant {DURATION} s ({LABEL})...")
    time.sleep(DURATION)
    for client in clients:
        client.loop_stop()
        client.disconnect()

    rows = []
    for name, *_ in STREAMS:
        entry = stats[name]
        lat = entry["latencies"]
        rows.append({
            "label": LABEL,
            "stream": name,
            "duration_s": DURATION,
            "messages": entry["messages"],
            "messages_per_s": round(entry["messages"] / DURATION, 3),
            "bytes": entry["bytes"],
            "avg_latency_ms": round(sum(lat) / len(lat), 2) if lat else "",
        })

    Path("results").mkdir(exist_ok=True)
    out = Path("results") / f"benchmark_{LABEL}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)
    raw, up = stats["sensors"]["bytes"], stats["uplink"]["bytes"]
    if raw and up:
        print(f"Octets sur le lien Edge->Cloud : {up} soit {up / raw:.0%} du volume brut des capteurs")
    print("CSV écrit :", out)


if __name__ == "__main__":
    main()
