import json
import os
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
# On garde 1 message sur 5 par défaut
EDGE_BATCH = int(os.getenv("EDGE_BATCH", "5")) 
# Seuil d'alerte configurable (par défaut 32°C)
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "32.0"))

TOPIC_IN = "iot/sensors/#"
TOPIC_OUT = "iot/edge/results"

# Un compteur global pour compter combien de messages on a vus passer
message_count = 0

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Edge connecté à {MQTT_HOST}:{MQTT_PORT}")
    print(f"Configuration : Filtre 1 sur {EDGE_BATCH} | Seuil d'alerte : {ALERT_THRESHOLD}°C")
    client.subscribe(TOPIC_IN, qos=1)

def on_message(client, userdata, msg):
    global message_count
    try:
        data = json.loads(msg.payload)
        message_count += 1
        
        temperature = float(data["temperature"])
        
        # --- LA RÈGLE MÉTIER (Alerte critique) ---
        is_alert = temperature > ALERT_THRESHOLD
        
        # --- LA LOGIQUE DE FILTRE ---
        # Si ce n'est pas un multiple du batch ET que ce n'est pas une alerte, on ignore le message.
        # Sinon (si c'est le 5ème message OU si c'est une alerte), on continue.
        if message_count % EDGE_BATCH != 0 and not is_alert:
            return 
        
        # Si on arrive ici, on traite le message
        start = time.perf_counter()
        
        result = {
            "scenario": "edge",
            "sensor_id": data["sensor_id"],
            "source_timestamp": data["timestamp"],
            "processed_timestamp": utc_now(),
            "temperature": temperature,
            "is_alert": is_alert, # On ajoute cette information
            "processing_ms": round((time.perf_counter() - start) * 1000, 2)
        }
        
        client.publish(TOPIC_OUT, json.dumps(result), qos=1)
        
        # Affichage adapté dans les logs
        if is_alert:
            print(f"🚨 [EDGE] ALERTE CRITIQUE ({temperature}°C) ! Envoi immédiat (Message n°{message_count})")
        else:
            print(f"[EDGE] Message n°{message_count} retenu et envoyé au Cloud : {temperature}°C")

    except Exception as e:
        print(f"Erreur : {e}")

# Initialisation du client MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-processor")
client.on_connect = on_connect
client.on_message = on_message

print("Démarrage de l'Edge...")
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_forever()