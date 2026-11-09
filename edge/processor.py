import json
import os
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration MQTT
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
EDGE_BATCH = int(os.getenv("EDGE_BATCH", "5")) 
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "32.0"))

TOPIC_IN = "iot/sensors/#"
TOPIC_OUT = "iot/edge/results"

# Configuration InfluxDB
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "iot-token-dev")
INFLUX_ORG = os.getenv("INFLUX_ORG", "ensah")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "iot")

# Initialisation InfluxDB
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

message_count = 0

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Edge connecté à {MQTT_HOST}:{MQTT_PORT}")
    print(f"Configuration : Filtre 1 sur {EDGE_BATCH} | Alerte > {ALERT_THRESHOLD}°C")
    client.subscribe(TOPIC_IN, qos=1)

def on_message(client, userdata, msg):
    global message_count
    try:
        data = json.loads(msg.payload)
        message_count += 1
        temperature = float(data["temperature"])
        
        is_alert = temperature > ALERT_THRESHOLD
        
        if message_count % EDGE_BATCH != 0 and not is_alert:
            return 
        
        start = time.perf_counter()
        
        result = {
            "scenario": "edge",
            "sensor_id": data["sensor_id"],
            "source_timestamp": data["timestamp"],
            "processed_timestamp": utc_now(),
            "temperature": temperature,
            "is_alert": is_alert,
            "processing_ms": round((time.perf_counter() - start) * 1000, 2)
        }
        
        # 1. Envoi MQTT
        client.publish(TOPIC_OUT, json.dumps(result), qos=1)
        
        # 2. Écriture dans InfluxDB
        point = Point("iot_results") \
            .tag("scenario", "edge") \
            .tag("sensor_id", result["sensor_id"]) \
            .field("temperature", result["temperature"]) \
            .field("is_alert", 1 if result["is_alert"] else 0) \
            .field("processing_ms", result["processing_ms"]) \
            .time(result["processed_timestamp"])
        
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        
        if is_alert:
            print(f"🚨 [EDGE] ALERTE ({temperature}°C) -> Envoyé à InfluxDB (Message n°{message_count})")
        else:
            print(f"[EDGE] Message n°{message_count} -> Envoyé à InfluxDB : {temperature}°C")

    except Exception as e:
        print(f"Erreur : {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-processor")
client.on_connect = on_connect
client.on_message = on_message

print("Démarrage de l'Edge...")
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_forever()