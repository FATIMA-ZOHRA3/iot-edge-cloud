# Architecture

## Vue d'ensemble : deux brokers, deux scénarios

```
 RÉSEAU LOCAL (site)                               LIEN                 "CLOUD"
┌──────────────────────────────────────┐          Edge -> Cloud   ┌──────────────────────────┐
│ simulator ──► mosquitto-edge (1883)  │                          │ mosquitto-cloud (1884)   │
│                    │                 │                          │        │                 │
│                    ▼                 │   iot/uplink/raw  (A)    │        ▼                 │
│                  edge  ──────────────┼─────────────────────────►│     cloud (délai         │
│   décision locale  │   iot/uplink/edge (B)                      │     artificiel) ──►      │
│   iot/edge/local ◄─┘                 │                          │     iot/cloud/results    │
└──────────────────────────────────────┘                          └──────────────────────────┘
```

Chaque service tourne dans son **propre conteneur Docker**.

| Scénario | `EDGE_MODE` | Ce que fait l'Edge | Ce que reçoit le Cloud |
| --- | --- | --- | --- |
| **A : cloud-only** (référence) | `forward` | rien, il relaie chaque mesure brute | toutes les mesures |
| **B : edge-cloud** | `reduce` | décision locale immédiate + une moyenne pour `EDGE_BATCH` mesures | un flux réduit |

On lance les mêmes capteurs dans chaque scénario et on compare : volume sur le lien,
latence de bout en bout, comportement quand le Cloud est coupé.

## Pourquoi cette architecture

- **Deux brokers** : le lien Edge vers Cloud est un vrai point de passage, donc le
  trafic qui le traverse (messages et octets) se mesure directement.
- **Edge et Cloud séparés** : ils ne partagent ni boucle ni processus, donc les
  mesures de latence et de bande passante sont crédibles.
- **Edge = décision locale + réduction** : l'alerte locale ne dépend pas du Cloud, et
  le Cloud reçoit moins de messages.
- **Coupure du Cloud** : l'Edge continue ses décisions locales et garde les messages du
  lien montant en mémoire (`UPLINK_BUFFER_MAX`), puis les envoie à la reconnexion.
- **MQTT et Docker Compose** : services découplés, même environnement pour les deux
  développeurs.

## Contrat entre les services

### Topics

| Broker | Topic | Publié par | Lu par |
| --- | --- | --- | --- |
| local | `iot/sensors/<sensor_id>` | simulator | edge, benchmark |
| local | `iot/edge/local` | edge (mode reduce) | benchmark |
| cloud | `iot/uplink/raw` | edge (mode forward) | cloud, benchmark |
| cloud | `iot/uplink/edge` | edge (mode reduce) | cloud, benchmark |
| cloud | `iot/cloud/results` | cloud | InfluxDB (semaine 2), benchmark |

### Messages

Mesure d'un capteur (UTC, ISO 8601) :

```json
{"sensor_id": "sensor-01", "timestamp": "2026-11-04T20:10:00+00:00",
 "temperature": 23.4, "humidity": 59.04, "vibration": 1.234}
```

Décision locale de l'Edge (`iot/edge/local`) :

```json
{"sensor_id": "sensor-01", "timestamp": "...", "processed_timestamp": "...",
 "temperature": 31.2, "status": "ALERTE", "processing_ms": 0.05}
```

Flux réduit vers le Cloud (`iot/uplink/edge`) :

```json
{"sensor_id": "sensor-01", "source_timestamp": "...", "edge_timestamp": "...",
 "avg_temperature": 24.1, "window_size": 5}
```

Résultat du Cloud (`iot/cloud/results`) :

```json
{"scenario": "edge-cloud", "sensor_id": "sensor-01", "source_timestamp": "...",
 "processed_timestamp": "...", "avg_temperature": 24.1, "window_size": 5,
 "processing_ms": 200.4}
```

### InfluxDB (semaine 2)

Version 2.x. Tags : `scenario` (`cloud-only` ou `edge-cloud`) et `sensor_id`.
Champs : `avg_temperature`, `processing_ms`, `window_size`.

## Ce que mesure `benchmark.py`

| Flux | Où | Ce qu'il montre |
| --- | --- | --- |
| `sensors` | broker local | volume brut produit par les capteurs |
| `edge_local` | broker local | latence de la décision locale |
| `uplink` | broker Cloud | trafic sur le lien Edge vers Cloud (bande passante) |
| `cloud_results` | broker Cloud | latence de bout en bout jusqu'au résultat Cloud |

## Limites à citer dans le rapport

- Le délai du Cloud (`CLOUD_DELAY_SECONDS`, 0,2 s par défaut) est **artificiel**.
- Les deux brokers tournent sur la même machine : le lien Edge vers Cloud n'a ni
  latence ni perte réelles.
- Les capteurs sont simulés (valeurs tirées au hasard).
- Les messages mis en attente pendant une coupure sont gardés en mémoire : ils sont
  perdus si le service Edge s'arrête.
- Mosquitto est ouvert (connexions anonymes) : essais en local uniquement.
- Le service Cloud traite un message à la fois : avec un délai de 0,2 s il sature
  vers 5 messages par seconde. Dans le scénario A avec beaucoup de capteurs, la
  latence monte : c'est un résultat à observer et à discuter, pas une erreur.
