# Plan de travail (4 semaines)

Cocher chaque tâche quand elle est faite ET testée. **A** = Dev A, **B** = Dev B.
Architecture : deux brokers (local et cloud), deux scénarios (cloud-only et
edge-cloud). Voir `ARCHITECTURE.md`.

## Semaine 1 : fondations et simulation

**Jours 1-2 : setup**
- [ ] Installer Docker, Python, VS Code (A + B)
- [ ] Créer le dépôt, inviter le binôme, créer la structure (A)
- [ ] `docker-compose.yml` avec les deux brokers Mosquitto (B)
- [ ] Test : `docker compose up -d`, les deux brokers démarrent (A + B)

**Jours 3-4 : simulateur**
- [ ] `simulator/sensors.py` : température, humidité, vibration, id, timestamp UTC (A)
- [ ] Connexion à `mosquitto-edge` avec `paho-mqtt`, topic `iot/sensors/<id>` (B)
- [ ] Test : les messages arrivent dans un abonné `mosquitto_sub` (A + B)

**Jours 5-7 : Cloud simulé**
- [ ] `cloud/consumer.py` : lit `iot/uplink/#`, délai artificiel, moyenne, publie `iot/cloud/results` (A)
- [ ] Conteneur Docker du Cloud dans `docker-compose.yml` (B)
- [ ] Test : relais manuel d'un message vers `iot/uplink/raw`, le Cloud répond (A + B)

## Semaine 2 : Edge et données

**Jours 8-10 : Edge**
- [ ] `edge/processor.py` : mode `forward` (relais brut) puis mode `reduce` (décision locale + flux réduit) (B)
- [ ] Service Edge dans `docker-compose.yml`, variable `EDGE_MODE` (A)
- [ ] Test : en `reduce`, le lien Edge vers Cloud porte beaucoup moins de messages qu'en `forward` (A + B)

**Jours 11-12 : InfluxDB**
- [ ] InfluxDB 2.x dans `docker-compose.yml` (A)
- [ ] Le Cloud écrit ses résultats avec `influxdb-client` (tags `scenario`, `sensor_id`) (B)
- [ ] Test : points visibles avec `scenario="cloud-only"` et `scenario="edge-cloud"` (A + B)

**Jours 13-14 : benchmark**
- [ ] `benchmark.py` : messages, octets, latence sur les deux brokers (A)
- [ ] Export CSV et tableau de résultats (B)

## Semaine 3 : visualisation et scénarios

**Jours 15-17 : Grafana**
- [ ] Grafana dans `docker-compose.yml` (A)
- [ ] Connecter Grafana à InfluxDB (B)
- [ ] Dashboard à 3 panneaux : latence, débit, température (A + B)

**Jours 18-19 : scénario de coupure**
- [ ] Couper `mosquitto-cloud` et documenter le comportement (B)
- [ ] Montrer que l'Edge continue ses décisions locales et rattrape à la reconnexion (A)

**Jours 20-21 : tests de charge**
- [ ] Benchmark avec 1, 5 puis 10 capteurs, dans chaque scénario (A + B)
- [ ] Tableau de résultats CSV avec les vraies mesures (A)

## Semaine 4 : rapport et soutenance

**Jours 22-25 : rapport**
- [ ] A : introduction, problématique, architecture (schéma), choix techniques
- [ ] B : protocole, résultats, graphiques, discussion, conclusion

**Jours 26-27 : nettoyage**
- [ ] `docker compose up` lance tout sans erreur (A + B)
- [ ] `README.md` clair (A)

**Jours 28-29 : démo**
- [ ] Présentation de 10 minutes (B)
- [ ] Répétition de la démo en direct (A + B)

**Jour 30 : soutenance**
