# Branchement — Arduino Uno R3 + DHT11 + Écran I2C

## Alimentation 5V — c'est bon

DHT11 et écran I2C en **5V** sur l'Uno R3 : c'est le branchement **correct**.

| Composant | Alimentation | Broche Uno |
|-----------|--------------|------------|
| DHT11 | **5V** | `5V` (pas `3.3V`) |
| Écran I2C | **5V** | `5V` (pas `3.3V`) |

L'Uno R3 fonctionne en **5V**. La plupart des modules DHT11 et des écrans LCD I2C (PCF8574) sont faits pour ça.

> Ne branchez **pas** le VCC sur la broche **3.3V** — réservée aux composants 3.3V seulement.

## Schéma de câblage

```
                    ARDUINO UNO R3
                 ┌─────────────────┐
                 │                 │
    DHT11 DATA ──┤ 2 (D2)          │
    DHT11 VCC  ──┤ 5V              │
    DHT11 GND  ──┤ GND             │
                 │                 │
    LCD SDA    ──┤ A4  (SDA I2C)   │  ← port I2C données
    LCD SCL    ──┤ A5  (SCL I2C)   │  ← port I2C horloge
    LCD VCC    ──┤ 5V              │
    LCD GND    ──┤ GND             │
                 │                 │
    USB        ──┤ PC (Stormer)    │
                 └─────────────────┘
```

## Important : A4 / A5 = I2C (écran)

Sur l'**Uno R3**, les broches **A4** et **A5** sont réservées à l'écran I2C :

| Broche écran | Arduino Uno | Rôle |
|--------------|-------------|------|
| SDA | **A4** | Données I2C |
| SCL | **A5** | Horloge I2C |
| VCC | **5V** | Alimentation |
| GND | **GND** | Masse |

Le **DHT11** se branche sur une **broche digitale** (pin **2** dans le sketch), pas sur A5.

## DHT11

| DHT11 | Arduino |
|-------|---------|
| VCC (+) | 5V |
| DATA (S) | Pin **2** (D2) |
| GND (-) | GND |

> Certains modules DHT11 n'ont que 3 broches. Si le vôtre en a 4, la broche du milieu (NC) reste non connectée.

## Librairies à installer (Arduino IDE)

**Outils → Gérer les bibliothèques**, puis installer :

1. **DHT sensor library** — Adafruit
2. **Adafruit Unified Sensor** — Adafruit (dépendance)
3. **LiquidCrystal I2C** — Frank de Brabander

## Écran I2C ne s'allume pas ?

1. Vérifiez **SDA → A4** et **SCL → A5**
2. Changez l'adresse dans le sketch si besoin :
   ```cpp
   #define LCD_ADDR 0x27   // ou 0x3F selon votre module
   ```
3. Uploadez le sketch et ouvrez le **Moniteur série** (9600 bauds) : un scan I2C liste les adresses détectées au démarrage en cas d'erreur.

## Données envoyées au PC

Toutes les 2 secondes (limite du DHT11) :

```
temp:23.5,hum:45.0
```

Stormer les affiche dans le terminal, les enregistre en `.txt` et les analyse avec l'IA.
