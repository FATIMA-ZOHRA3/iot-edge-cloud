"""Benchmark : compare le flux brut des capteurs, le flux Cloud et le flux Edge.

Le script écoute les trois flux MQTT pendant une durée donnée, puis affiche
pour chacun :
  - le nombre de messages ;
  - le nombre d'octets reçus ;
  - la latence moyenne (heure de réception - heure d'émission de la mesure).

Les services doivent déjà tourner (docker compose up -d). Le délai du Cloud
est ARTIFICIEL : il est inclus dans sa latence et doit être signalé comme tel
dans le rapport.

Exemples :
    python benchmark.py
    python benchmark.py --duration 30
"""
import argparse
import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

DEFAULT_DURATION = 120  # secondes

# Nom du flux -> topic écouté
STREAM_TOPICS = {
    "capteurs": "iot/sensors/#",
    "cloud": "iot/cloud/results",
    "edge": "iot/edge/results",
}

# Compteurs par flux, remplis par on_message
stats = {
    name: {"messages": 0, "bytes": 0, "latencies_ms": []}
    for name in STREAM_TOPICS
}


def stream_of(topic: str) -> str | None:
    """Retourne le flux auquel appartient un topic (None si inconnu)."""
    if topic.startswith("iot/sensors/"):
        return "capteurs"
    if topic == "iot/cloud/results":
        return "cloud"
    if topic == "iot/edge/results":
        return "edge"
    return None


def latency_ms(payload: bytes, received_at: datetime) -> float | None:
    """Latence en ms entre l'émission de la mesure et sa réception.

    Retourne None si le message n'a pas d'horodatage exploitable.
    """
    try:
        data = json.loads(payload)
        sent_at = datetime.fromisoformat(data.get("source_timestamp") or data["timestamp"])
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    return (received_at - sent_at).total_seconds() * 1000


def on_connect(client, userdata, flags, reason_code, properties):
    """S'abonne aux trois flux dès que la connexion est établie."""
    if reason_code.is_failure:
        print(f"Connexion refusée : {reason_code}")
        return
    for topic in STREAM_TOPICS.values():
        client.subscribe(topic)


def on_message(client, userdata, msg):
    """Enregistre un message dans les compteurs de son flux."""
    received_at = datetime.now(timezone.utc)
    name = stream_of(msg.topic)
    if name is None:
        return
    stream = stats[name]
    stream["messages"] += 1
    stream["bytes"] += len(msg.payload)
    latency = latency_ms(msg.payload, received_at)
    if latency is not None:
        stream["latencies_ms"].append(latency)


def summarize() -> list[dict]:
    """Résume les compteurs : une ligne par flux."""
    rows = []
    for name, stream in stats.items():
        latencies = stream["latencies_ms"]
        rows.append({
            "flux": name,
            "messages": stream["messages"],
            "octets": stream["bytes"],
            "latence_moyenne_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        })
    return rows


def print_report(rows: list[dict], elapsed: float) -> None:
    """Affiche le tableau des résultats."""
    print(f"\nRésultats sur {elapsed:.0f} s")
    print(f"{'flux':<10}{'messages':>10}{'octets':>10}{'latence moy. (ms)':>20}")
    for row in rows:
        latency = "-" if row["latence_moyenne_ms"] is None else row["latence_moyenne_ms"]
        print(f"{row['flux']:<10}{row['messages']:>10}{row['octets']:>10}{latency:>20}")

    sensors = next(r for r in rows if r["flux"] == "capteurs")["messages"]
    if sensors:
        for row in rows:
            if row["flux"] != "capteurs":
                share = 100 * row["messages"] / sensors
                print(f"{row['flux']} : {share:.0f} % des messages des capteurs")


def parse_args() -> argparse.Namespace:
    """Lit les options de la ligne de commande."""
    parser = argparse.ArgumentParser(description="Benchmark des flux MQTT")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION,
                        help="durée de mesure en secondes (défaut : 120)")
    parser.add_argument("--host", default="localhost", help="adresse du broker")
    parser.add_argument("--port", type=int, default=1883, help="port du broker")
    args = parser.parse_args()
    if args.duration < 1:
        parser.error("--duration doit être au moins 1")
    return args


def main() -> None:
    args = parse_args()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="benchmark")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=60)

    print(f"Mesure pendant {args.duration} s (Ctrl+C pour arrêter plus tôt)...")
    start = time.monotonic()
    client.loop_start()
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("Arrêt demandé, résultats partiels.")
    finally:
        client.loop_stop()
        client.disconnect()
    print_report(summarize(), time.monotonic() - start)


if __name__ == "__main__":
    main()