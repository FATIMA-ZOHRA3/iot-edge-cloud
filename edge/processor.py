import json
import os
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
# On garde 1 message sur 5
EDGE_BATCH = int(os.getenv("EDGE_BATCH", "5")) 

TOPIC_IN = "iot/sensors/#"
TOPIC_OUT = "iot/edge/results"

# Un compteur global pour compter combien de messages on a vus passer
message_count = 0

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Edge connecté à {MQTT_HOST}:{MQTT_PORT}")
    client.subscribe(TOPIC_IN, qos=1)

def on_message(client, userdata, msg):
    global message_count
    try:
        data = json.loads(msg.payload)
        message_count += 1
        
        # LA FORCE DE L'EDGE : On filtre !
        # Si le numéro du message n'est pas un multiple de 5, on s'arrête là (on ignore)
        if message_count % EDGE_BATCH != 0:
            return 
        
        # Si on passe ce filtre, c'est qu'on est au 5ème, 10ème, 15ème message...
        # On le traite et on l'envoie au Cloud
        start = time.perf_counter()
        
        result = {
            "scenario": "edge",
            "sensor_id": data["sensor_id"],
            "source_timestamp": data["timestamp"],
            "processed_timestamp": utc_now(),
            "temperature": data["temperature"],
            "processing_ms": round((time.perf_counter() - start) * 1000, 2)
        }
        
        client.publish(TOPIC_OUT, json.dumps(result), qos=1)
        print(f"[EDGE] Message n°{message_count} retenu et envoyé au Cloud : {result['temperature']}°C")

    except Exception as e:
        print(f"Erreur : {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-processor")
client.on_connect = on_connect
client.on_message = on_message

print("Démarrage de l'Edge...")
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_forever()