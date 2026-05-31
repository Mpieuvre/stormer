# Stormer

Application PC pour **acquérir**, **afficher**, **enregistrer** et **analyser** les données envoyées par une carte Arduino via le port série.

## Fonctionnalités

- **Connexion automatique** à l'Arduino (détection des ports COM)
- **Terminal en temps réel** qui intercepte et affiche chaque ligne reçue
- **Enregistrement** de la session complète en fichier `.txt`
- **Analyse IA** locale : statistiques, tendances, prédictions et alertes

## Prérequis

- Windows 10/11
- [Python 3.10+](https://python.org) (cocher "Add to PATH" à l'installation)
- Carte Arduino (Uno, Nano, Mega, etc.)
- [Arduino IDE](https://www.arduino.cc/en/software) pour uploader le sketch

## Installation rapide

1. Double-cliquez sur **`run.bat`** — l'environnement et les dépendances s'installent automatiquement au premier lancement.

Ou manuellement :

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Configuration Arduino (Uno R3 + DHT11 + écran I2C)

Voir le guide détaillé : [`arduino/BRANCHEMENT.md`](arduino/BRANCHEMENT.md)

| Composant | Broche Arduino |
|-----------|----------------|
| DHT11 DATA | Pin **2** (D2) |
| DHT11 VCC / GND | 5V / GND |
| Écran I2C SDA | **A4** |
| Écran I2C SCL | **A5** |
| Écran VCC / GND | 5V / GND |

1. Installez les librairies : **DHT sensor library**, **Adafruit Unified Sensor**, **LiquidCrystal I2C**
2. Ouvrez `arduino/stormer_sensor.ino` dans l'Arduino IDE
3. Carte : **Arduino Uno**, uploadez le sketch
4. Fermez le moniteur série avant de lancer Stormer sur le PC

Le sketch affiche les valeurs brutes sur l'écran I2C et envoie au PC toutes les 2 s :

```
temp:23.5,hum:45.0
```

### Formats de données supportés

L'application parse automatiquement plusieurs formats :

| Format | Exemple |
|--------|---------|
| Clé:valeur | `temp:23.5,hum:45.2` |
| Clé=valeur | `temp=23.5 hum=45.2` |
| CSV numérique | `23.5,45.2,512` |
| Valeur seule | `1024` |

## Utilisation

1. Lancez **Stormer** (`run.bat` ou `python main.py`)
2. Branchez l'Arduino
3. Cliquez **Auto-détecter** ou sélectionnez le port COM
4. Cliquez **Connecter** — les données apparaissent dans le terminal
5. Cliquez **Enregistrer en .txt** pour sauvegarder la session
6. Cliquez **Analyser avec l'IA** pour obtenir statistiques et prédictions

## Analyse IA

L'IA locale (scikit-learn) calcule pour chaque capteur :

- Min, max, moyenne, écart-type
- Tendance (croissante / décroissante / stable)
- Prédiction des 10 prochaines valeurs (régression linéaire)
- Alertes (variabilité élevée, tendance marquée, etc.)

> Aucune connexion internet requise — tout tourne en local sur votre PC.

## Structure du projet

```
Stormer/
├── main.py              # Point d'entrée
├── run.bat              # Lanceur Windows
├── requirements.txt
├── arduino/
│   └── stormer_sensor.ino
└── stormer/
    ├── app.py           # Interface graphique
    ├── serial_manager.py
    ├── data_parser.py
    └── ai_engine.py
```

## Personnalisation

- Modifiez `stormer/config.py` pour changer le débit série (9600 par défaut) ou l'horizon de prédiction
- Adaptez le sketch Arduino à vos capteurs réels (DHT22, BMP280, etc.)

## Dépannage

| Problème | Solution |
|----------|----------|
| Port COM introuvable | Vérifiez le câble USB, installez le driver CH340/CP210x si clone |
| Données illisibles | Vérifiez que le débit série Arduino = 9600 bauds |
| "Données insuffisantes" pour l'IA | Attendez au moins 3 lignes avec des valeurs numériques |
| Arduino IDE occupe le port | Fermez le moniteur série de l'Arduino IDE avant de connecter Stormer |
