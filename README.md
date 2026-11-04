# IoT Edge–Cloud avec capteurs simulés

Comparaison de deux chemins pour des mesures de capteurs simulés :

- **A, cloud-only** : l'Edge relaie tout au Cloud.
- **B, edge-cloud** : l'Edge décide localement et n'envoie au Cloud qu'un flux réduit.

Tout tourne dans des conteneurs Docker, avec deux brokers MQTT (un local, un « cloud »).

> Le délai du Cloud est **artificiel** : il doit être signalé comme tel dans tous les résultats.

## Structure

```
simulator/            capteurs simulés (sensors.py)
edge/                 service Edge (processor.py)
cloud/                service Cloud simulé (consumer.py)
dashboard/            dashboards Grafana exportés (JSON)
docs/                 architecture, plan de travail, rapport
results/              mesures des tests (CSV, non versionnés)
benchmark.py          mesure messages, octets et latence sur les deux brokers
docker-compose.yml    brokers et services
mosquitto.conf        configuration des brokers (essais locaux uniquement)
.env.example          variables à copier dans .env
```

Voir `docs/ARCHITECTURE.md` (schéma, topics, formats) et `docs/TASKS.md` (plan sur 4 semaines).

## Prérequis

Docker (avec Docker Compose), Python 3, Git.

## Démarrage

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f edge cloud
```

Cinq services : `mosquitto-edge`, `mosquitto-cloud`, `simulator`, `edge`, `cloud`.
Arrêter : `docker compose down`.

### Choisir le scénario

Scénario B, edge-cloud (par défaut) :

```bash
docker compose up -d
```

Scénario A, cloud-only :

```powershell
$env:EDGE_MODE="forward"; docker compose up -d --force-recreate edge
```

(Linux ou macOS : `EDGE_MODE=forward docker compose up -d --force-recreate edge`.)
Pour revenir au scénario B : `$env:EDGE_MODE="reduce"` puis la même commande.

Nombre de capteurs, délai Cloud, taille des groupes : copier `.env.example` en `.env`
et modifier `N_SENSORS`, `CLOUD_DELAY_SECONDS`, `EDGE_BATCH`.

### Voir les messages

```bash
docker compose exec mosquitto-edge mosquitto_sub -h localhost -t "iot/#" -v
docker compose exec mosquitto-cloud mosquitto_sub -h localhost -t "iot/#" -v
```

### Benchmark

```bash
python -m pip install -r requirements.txt
python benchmark.py 120 edge-cloud-1-capteur
```

Les services doivent tourner. Un CSV est écrit dans `results/`. Lancer le même test
dans chaque scénario, avec 1, 5 puis 10 capteurs.

### Scénario de coupure du Cloud

```bash
docker compose stop mosquitto-cloud
docker compose logs -f edge
docker compose start mosquitto-cloud
```

En mode `reduce`, l'Edge continue ses décisions locales (`iot/edge/local`), garde les
messages du lien montant en mémoire et les envoie à la reconnexion.

### Développer hors Docker

```bash
docker compose up -d mosquitto-edge mosquitto-cloud
python simulator/sensors.py
```

(dans d'autres terminaux : `python edge/processor.py` et `python cloud/consumer.py`)

## Avancement

Voir `docs/TASKS.md`.
