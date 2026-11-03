# IoT Edge–Cloud avec capteurs simulés

Prototype d'une architecture IoT comparant un traitement **Edge** (local) et un traitement **Cloud simulé**, avec des capteurs simulés en Python.

## Architecture visée

```
Python (capteurs simulés) → MQTT/Mosquitto → traitements Edge et Cloud simulé → InfluxDB → Grafana
```

Node-RED est ajouté en option, après validation de la chaîne principale.

> Le délai ajouté au scénario « Cloud simulé » (par défaut 100 ms) est **artificiel** : ce n'est pas une mesure réelle d'Internet. Il doit être mentionné dans les résultats.

## Structure

```
simulator/   capteurs simulés (sensors.py)
processor/   traitements Edge et Cloud simulé (à venir)
results/     exports et mesures des essais
compose.yaml configuration Docker Compose (Mosquitto)
mosquitto.conf configuration du broker (essais locaux uniquement)
```

## Prérequis

- Python 3
- Docker et Docker Compose (ou Mosquitto installé directement)

## Démarrage rapide

### 1. Capteur simulé seul

```bash
python simulator/sensors.py      # ou python3 sur Ubuntu
```

Résultat attendu : une ligne JSON toutes les 2 secondes (`sensor_id`, `timestamp`, `temperature`, `humidity`, `pressure`). `Ctrl+C` pour arrêter.

### 2. Broker Mosquitto

```bash
docker compose up -d
docker compose ps
docker compose logs mosquitto
```

> La configuration de `mosquitto.conf` autorise les connexions anonymes : elle est réservée aux essais locaux et ne doit pas être exposée à Internet.

## Avancement

- [x] Capteur simulé (affichage console)
- [x] Configuration Mosquitto
- [ ] Publication MQTT (paho-mqtt)
- [ ] Traitements Edge et Cloud simulé
- [ ] Stockage InfluxDB
- [ ] Dashboards Grafana
- [ ] Node-RED (facultatif)
- [ ] Expériences et rapport

## Indicateurs prévus

Temps de traitement (ms), latence de bout en bout, débit (messages/s), taux de réception, moyenne et médiane sur plusieurs essais. Les résultats doivent provenir d'exécutions réelles.
