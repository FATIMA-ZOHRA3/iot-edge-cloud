"""Simulateur de capteurs : température, humidité et vibration.

Chaque mesure est un dictionnaire avec l'identifiant du capteur et l'heure
d'émission en UTC. Ce script ne publie pas sur MQTT : un autre module importe
create_measurement() pour envoyer les mesures à Mosquitto.

Exemples :
    python simulator/sensors.py
    python simulator/sensors.py --sensors 5 --interval 1
"""
import argparse
import json
import random
import time
from datetime import datetime, timezone

# Plages de valeurs simulées
TEMPERATURE_RANGE = (18.0, 35.0)  # degrés Celsius
HUMIDITY_RANGE = (30.0, 80.0)     # pourcentage
VIBRATION_RANGE = (0.0, 5.0)      # unité arbitraire

DEFAULT_SENSORS = 1
DEFAULT_INTERVAL = 2.0  # secondes entre deux séries de mesures


def create_measurement(sensor_id: str) -> dict:
    """Crée une mesure simulée pour un capteur."""
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": round(random.uniform(*TEMPERATURE_RANGE), 2),
        "humidity": round(random.uniform(*HUMIDITY_RANGE), 2),
        "vibration": round(random.uniform(*VIBRATION_RANGE), 3),
    }


def sensor_ids(count: int) -> list[str]:
    """Retourne les identifiants sensor-01, sensor-02, ..."""
    return [f"sensor-{number:02d}" for number in range(1, count + 1)]


def parse_args() -> argparse.Namespace:
    """Lit les options de la ligne de commande."""
    parser = argparse.ArgumentParser(description="Simulateur de capteurs")
    parser.add_argument(
        "--sensors", type=int, default=DEFAULT_SENSORS,
        help="nombre de capteurs (défaut : 1)",
    )
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL,
        help="secondes entre deux mesures (défaut : 2)",
    )
    args = parser.parse_args()
    if args.sensors < 1:
        parser.error("--sensors doit être au moins 1")
    if args.interval <= 0:
        parser.error("--interval doit être supérieur à 0")
    return args


def main() -> None:
    args = parse_args()
    ids = sensor_ids(args.sensors)
    print(f"Simulateur démarré : {len(ids)} capteur(s), "
          f"une mesure toutes les {args.interval} s (Ctrl+C pour arrêter)")
    try:
        while True:
            for sensor_id in ids:
                print(json.dumps(create_measurement(sensor_id)))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Arrêt demandé.")


if __name__ == "__main__":
    main()