import json
import random
import time
from datetime import datetime, timezone


def create_measurement(sensor_id):
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": round(random.uniform(18, 35), 2),
        "humidity": round(random.uniform(30, 80), 2),
        "pressure": round(random.uniform(990, 1020), 2)
    }


if __name__ == "__main__":
    try:
        while True:
            data = create_measurement("sensor-01")
            print(json.dumps(data, ensure_ascii=False))
            time.sleep(2)
    except KeyboardInterrupt:
        print("Arrêt demandé.")
