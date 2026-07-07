"""Generation du sketch Arduino et du guide de branchement."""

from __future__ import annotations

from pathlib import Path

from stormer.setup_config import HardwareProfile, uid_to_bytes


def export_dir() -> Path:
    """Dossier Documents/Stormer — accessible et persistant pour l'utilisateur."""
    return Path.home() / "Documents" / "Stormer"

_BOARD_PINS: dict[str, dict] = {
    "uno": {
        "dht": 2, "ds18": 3, "mq_air": "A0", "mq_gas": "A1", "mq_co": "A2",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "A4", "scl": "A5", "rf": 4, "cc_cs": 10, "nrf_ce": 9, "nrf_csn": 10,
        "tft_cs": 10, "tft_dc": 9, "hc12": 7, "bt": 8, "logic": "5V",
    },
    "nano": {
        "dht": 2, "ds18": 3, "mq_air": "A0", "mq_gas": "A1", "mq_co": "A2",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "A4", "scl": "A5", "rf": 4, "cc_cs": 10, "nrf_ce": 9, "nrf_csn": 10,
        "tft_cs": 10, "tft_dc": 9, "hc12": 7, "bt": 8, "logic": "5V",
    },
    "mega": {
        "dht": 2, "ds18": 3, "mq_air": "A0", "mq_gas": "A1", "mq_co": "A2",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "20", "scl": "21", "rf": 4, "cc_cs": 53, "nrf_ce": 9, "nrf_csn": 53,
        "tft_cs": 10, "tft_dc": 9, "hc12": 7, "bt": 8, "logic": "5V",
    },
    "leonardo": {
        "dht": 2, "ds18": 3, "mq_air": "A0", "mq_gas": "A1", "mq_co": "A2",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "2", "scl": "3", "rf": 4, "cc_cs": 10, "nrf_ce": 9, "nrf_csn": 10,
        "tft_cs": 10, "tft_dc": 9, "hc12": 7, "bt": 8, "logic": "5V",
    },
    "micro": {
        "dht": 2, "ds18": 3, "mq_air": "A0", "mq_gas": "A1", "mq_co": "A2",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "2", "scl": "3", "rf": 4, "cc_cs": 10, "nrf_ce": 9, "nrf_csn": 10,
        "tft_cs": 10, "tft_dc": 9, "hc12": 7, "bt": 8, "logic": "5V",
    },
    "pro_mini": {
        "dht": 2, "ds18": 3, "mq_air": "A0", "mq_gas": "A1", "mq_co": "A2",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "A4", "scl": "A5", "rf": 4, "cc_cs": 10, "nrf_ce": 9, "nrf_csn": 10,
        "tft_cs": 10, "tft_dc": 9, "hc12": 7, "bt": 8, "logic": "5V",
    },
    "due": {
        "dht": 2, "ds18": 3, "mq_air": "A0", "mq_gas": "A1", "mq_co": "A2",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "20", "scl": "21", "rf": 4, "cc_cs": 10, "nrf_ce": 9, "nrf_csn": 10,
        "tft_cs": 10, "tft_dc": 9, "hc12": 7, "bt": 8, "logic": "3.3V",
    },
    "esp32": {
        "dht": 4, "ds18": 5, "mq_air": "A0", "mq_gas": "A3", "mq_co": "A6",
        "hygro": "A3", "rain_an": "A4", "rain_do": 5,
        "sda": "21", "scl": "22", "rf": 12, "cc_cs": 5, "nrf_ce": 9, "nrf_csn": 5,
        "tft_cs": 5, "tft_dc": 2, "hc12": 16, "bt": 17, "logic": "3.3V",
    },
}


_EXTRA_PINS = {
    "rfid_rst": 8,
    "rfid_ss": 10,
    "led_g": 6,
    "led_o": 7,
    "led_r": 13,
    "led_rgb_r": 11,
    "led_rgb_g": 12,
    "led_rgb_b": 9,
    "neopixel": 6,
}


def _pins(board: str) -> dict:
    p = dict(_BOARD_PINS.get(board, _BOARD_PINS["uno"]))
    p.update(_EXTRA_PINS)
    return p


def _mq135_do_pin(p: dict, sensors: list[str]) -> int:
    """Broche digitale pour D0 du module (evite conflit avec DS18B20 sur D3)."""
    if "ds18b20" not in sensors:
        return int(p["ds18"])
    return 12


def _sensors(profile: HardwareProfile) -> list[str]:
    return profile.normalized_sensors()


def _dht_type(sensors: list[str]) -> str | None:
    if "dht22" in sensors:
        return "DHT22"
    if "dht11" in sensors:
        return "DHT11"
    return None


def _gas_pin(sensors: list[str], p: dict) -> tuple[str, str] | None:
    if "gas_mq2" in sensors or "gas_mq5" in sensors:
        return "PIN_MQ_GAS", p["mq_gas"]
    if "gas_mq7" in sensors:
        return "PIN_MQ_CO", p["mq_co"]
    return None


def _mq135_wiring_lines(p: dict, board: str, sensors: list[str], has_i2c_display: bool) -> list[str]:
    """Guide de branchement detaille pour le module MQ135."""
    pin_a = p["mq_air"]
    pin_d = _mq135_do_pin(p, sensors)
    ds18_note = ""
    if "ds18b20" in sensors:
        ds18_note = (
            f" (D12 car D{p['ds18']} est deja utilise par le DS18B20 — "
            "ne branchez pas D0 sur D3 dans ce cas)"
        )
    lines = [
        "## MQ135 — qualite de l'air (module breakout 4 broches)",
        "",
        "Le module MQ135 expose **4 fils** : VCC, GND, **A0** et **D0**.",
        "Stormer utilise **les deux sorties** :",
        "- **A0** → mesure analogique fine (0–1023)",
        "- **D0** → alarme tout-ou-rien (seuil regle par le potentiometre du module)",
        "",
        "### Correspondance broches module → Arduino",
        "",
        "| Broche module | Fil type | Arduino | Role |",
        "|---------------|----------|---------|------|",
        "| **VCC** | Rouge | **5V** | Alimentation 5 V |",
        "| **GND** | Noir | **GND** | Masse |",
        f"| **A0** | Jaune / vert | **{pin_a}** | Sortie analogique (mesure continue) |",
        f"| **D0** | Blanc / bleu | **D{pin_d}**{ds18_note} | Sortie digitale (alarme gaz) |",
        "",
        f"> Le fil **A0** du module MQ135 va sur la broche Arduino **{pin_a}**",
        "> (ce n'est pas la meme broche que l'hygrometre sol si vous en avez un).",
        "",
        "### Branchement pas a pas",
        "",
        f"1. **VCC** (rouge) → **5V** Arduino",
        f"2. **GND** (noir) → **GND** Arduino",
        f"3. **A0** du module (jaune/vert) → broche Arduino **{pin_a}**",
        f"4. **D0** du module (blanc/bleu) → broche Arduino **D{pin_d}**",
        "",
        "### A0 vs D0 — quelle difference ?",
        "",
        f"- **A0 → {pin_a}** : tension variable lue par `analogRead()`.",
        "  Stormer affiche `air:512` (0 = air charge, 1023 = air pur).",
        f"- **D0 → D{pin_d}** : sortie HIGH ou LOW selon un seuil interne.",
        "  La **LED du module** s'allume quand D0 passe en alarme.",
        "  Stormer affiche `air_alert:1` si gaz detecte, `air_alert:0` si OK.",
        "",
        "### Reglage du potentiometre (sur le PCB du module)",
        "",
        "- Tournez la vis bleue pour regler la **sensibilite de D0** (pas de A0).",
        "- **Sens anti-horaire** : D0 declenche plus tot (plus sensible).",
        "- **Sens horaire** : D0 declenche plus tard (moins sensible).",
        "- Reglage conseille : dans l'air normal, la LED du module **eteinte**, D0 = HIGH.",
        "  Approchez une source de gaz/fumee : la LED s'allume → D0 = LOW → `air_alert:1`.",
        "",
        "### Prechauffage",
        "",
        "- Laissez le module sous tension **2 à 3 minutes** avant la premiere lecture.",
        "- Pour une mesure CO2 precise : **24 h** de prechauffage la premiere fois.",
        "",
        "### Lecture dans Stormer",
        "",
        f"- Analogique : `analogRead({pin_a})` → cle `air`",
        f"- Digital : `digitalRead({pin_d})` → cle `air_alert` (1 = alarme, 0 = normal)",
        "- Exemple ligne serie : `temp:23.5,hum:45,air:512,air_alert:0`",
        "",
        "### Precautions",
        "",
        "- Alimentation **5 V** (module standard).",
        "- Ne pas mouiller le capteur ; sensible a l'humidite.",
        "- Les deux sorties A0 et D0 partagent la meme masse (GND) et le meme VCC.",
    ]

    others: list[str] = []
    if any(s in sensors for s in ("gas_mq2", "gas_mq5")):
        others.append(f"MQ2/MQ5 ({p['mq_gas']})")
    if "gas_mq7" in sensors:
        others.append(f"MQ7 CO ({p['mq_co']})")
    if "hygro_soil" in sensors:
        others.append(f"Hygrometre sol ({p['hygro']})")
    if "rain_sensor" in sensors and not has_i2c_display:
        others.append(f"Pluie analogique ({p['rain_an']})")
    if others:
        lines += [
            "### Broches analogiques deja utilisees sur ce profil",
            "",
            "- " + ", ".join(others),
            f"- MQ135 occupe **{pin_a}** (A0) et **D{pin_d}** (D0) — ne reutilisez pas ces broches.",
            "",
        ]
    else:
        lines.append("")

    return lines


def _reserved_digital_pins(p: dict, sensors: list[str], profile: HardwareProfile) -> set[int]:
    used = {int(p["rain_do"]), int(p["dht"])}
    if "ds18b20" in sensors:
        used.add(int(p["ds18"]))
    if "air_quality" in sensors:
        used.add(_mq135_do_pin(p, sensors))
    if profile.wireless == "hc12":
        used.add(int(p["hc12"]))
    if profile.wireless in ("hc05", "esp8266_shield"):
        used.add(int(p["bt"]))
    if profile.wireless in ("rf433_tx", "rf433_rx"):
        used.add(int(p["rf"]))
    if profile.access == "mfrc522":
        used.add(int(p["rfid_rst"]))
    if profile.output == "status_3":
        used.update({int(p["led_g"]), int(p["led_o"]), int(p["led_r"])})
    return used


def _pick_digital_pin(p: dict, sensors: list[str], profile: HardwareProfile, prefer: tuple[int, ...]) -> int:
    used = _reserved_digital_pins(p, sensors, profile)
    for pin in prefer:
        if pin not in used:
            return pin
    return 12


def _hygro_do_pin(p: dict, sensors: list[str], profile: HardwareProfile) -> int:
    return _pick_digital_pin(p, sensors, profile, (7, 11, 8, 12))


def _gas_do_pin(p: dict, sensors: list[str], profile: HardwareProfile) -> int:
    return _pick_digital_pin(p, sensors, profile, (8, 11, 12, 7))


def _pin_plan_lines(profile: HardwareProfile, p: dict, sensors: list[str]) -> list[str]:
    """Recapitulatif des broches utilisees sur la carte."""
    rows: list[tuple[str, str, str]] = []
    if dht := _dht_type(sensors):
        rows.append((f"D{p['dht']}", dht, "DATA"))
    if "ds18b20" in sensors:
        rows.append((f"D{p['ds18']}", "DS18B20", "DATA (+ pull-up 4.7k)"))
    if "bme280" in sensors:
        rows.append((f"{p['sda']} / {p['scl']}", "BME280", "SDA / SCL (I2C)"))
    if "air_quality" in sensors:
        rows.append((str(p["mq_air"]), "MQ135", "A0 analogique"))
        rows.append((f"D{_mq135_do_pin(p, sensors)}", "MQ135", "D0 digital"))
    if any(s in sensors for s in ("gas_mq2", "gas_mq5")):
        rows.append((str(p["mq_gas"]), "MQ2/MQ5", "A0 analogique"))
        rows.append((f"D{_gas_do_pin(p, sensors, profile)}", "MQ2/MQ5", "D0 digital"))
    if "gas_mq7" in sensors:
        rows.append((str(p["mq_co"]), "MQ7", "A0 analogique"))
        rows.append((f"D{_gas_do_pin(p, sensors, profile)}", "MQ7", "D0 digital"))
    if "hygro_soil" in sensors:
        rows.append((str(p["hygro"]), "FC-28 sol", "AO analogique"))
        rows.append((f"D{_hygro_do_pin(p, sensors, profile)}", "FC-28 sol", "DO digital"))
    if "rain_sensor" in sensors:
        i2c = profile.display.startswith("lcd_i2c") or profile.display.startswith("oled_i2c")
        rows.append((f"D{p['rain_do']}", "FC-37 pluie", "DO digital"))
        if not i2c:
            rows.append((str(p["rain_an"]), "FC-37 pluie", "AO analogique"))
    if profile.display.startswith("lcd_i2c") or profile.display.startswith("oled_i2c"):
        rows.append((f"{p['sda']} / {p['scl']}", profile.display_label(), "SDA / SCL (I2C)"))

    if not rows:
        return []

    lines = [
        "## Plan des broches — " + profile.board_label(),
        "",
        "| Broche Arduino | Composant | Role |",
        "|----------------|-----------|------|",
    ]
    for pin, comp, role in rows:
        lines.append(f"| **{pin}** | {comp} | {role} |")
    lines += ["", "> Ne rebranchez jamais deux composants sur la meme broche.", ""]

    if "air_quality" in sensors and "hygro_soil" in sensors:
        mq_pin = p["mq_air"]
        hy_pin = p["hygro"]
        hy_do = _hygro_do_pin(p, sensors, profile)
        mq_do = _mq135_do_pin(p, sensors)
        lines += [
            "### ⚠ MQ135 + hygrometre sol : ne pas confondre les fils « A0 »",
            "",
            "Chaque module a une sortie analogique marquee **A0** ou **AO** sur le PCB.",
            "Ce sont des **noms sur le module**, pas la meme broche Arduino :",
            "",
            "| Fil sur le module | Branchez sur Arduino | Capteur |",
            "|-------------------|----------------------|---------|",
            f"| **A0** du MQ135 | **{mq_pin}** | Qualite de l'air |",
            f"| **D0** du MQ135 | **D{mq_do}** | Alarme air |",
            f"| **AO** du FC-28 (sol) | **{hy_pin}** | Humidite sol |",
            f"| **DO** du FC-28 (sol) | **D{hy_do}** | Alerte sol sec |",
            "",
            f"> **Le hygrometre sol ne va PAS sur {mq_pin}** — il va sur **{hy_pin}**.",
            f"> **Le MQ135 ne va PAS sur {hy_pin}** — il va sur **{mq_pin}**.",
            "",
        ]

    return lines


def _dht_wiring_lines(p: dict, dht: str) -> list[str]:
    pin = p["dht"]
    return [
        f"## {dht} — temperature & humidite air",
        "",
        "Module 3 broches (ou 4 avec broche DATA marquee **S** / **OUT**).",
        "",
        "| Broche capteur | Arduino | Fil |",
        "|----------------|---------|-----|",
        "| **VCC** (+) | **5V** | Rouge |",
        "| **DATA** (S/OUT) | **D" + str(pin) + "** | Jaune ou vert |",
        "| **GND** (-) | **GND** | Noir |",
        "",
        "### Branchement pas a pas",
        "",
        f"1. **VCC** → **5V**",
        f"2. **GND** → **GND**",
        f"3. **DATA** → **D{pin}**",
        "4. *(Recommande)* Resistances **10 kΩ** entre DATA et VCC (pull-up interne active dans le code).",
        "",
        "### Lecture Stormer",
        "",
        f"- Broche digitale **D{pin}** → cles `temp` et `hum`",
        "- Exemple : `temp:23.5,hum:45.0`",
        "",
    ]


def _bme280_wiring_lines(p: dict) -> list[str]:
    return [
        "## BME280 — temperature, humidite & pression (I2C)",
        "",
        "| Broche module | Arduino | Role |",
        "|---------------|---------|------|",
        f"| **SDA** | **{p['sda']}** | Donnees I2C |",
        f"| **SCL** | **{p['scl']}** | Horloge I2C |",
        "| **VCC** | **3.3V ou 5V** | Alim. (module 3.3V tolerant) |",
        "| **GND** | **GND** | Masse |",
        "",
        "### Branchement pas a pas",
        "",
        f"1. **VCC** → **3.3V** (ou 5V si votre module l'accepte)",
        f"2. **GND** → **GND**",
        f"3. **SDA** → **{p['sda']}**",
        f"4. **SCL** → **{p['scl']}**",
        "",
        "> Si ecran LCD/OLED I2C sur la meme carte : **SDA et SCL communes** (bus I2C partage).",
        "",
        "### Lecture Stormer",
        "",
        "- Cles : `temp`, `hum`, `press`",
        "",
    ]


def _ds18_wiring_lines(p: dict) -> list[str]:
    pin = p["ds18"]
    return [
        "## DS18B20 — sonde temperature etanche (1-Wire)",
        "",
        "| Broche sonde | Arduino | Role |",
        "|--------------|---------|------|",
        f"| **DATA** (jaune/blanc) | **D{pin}** | Bus 1-Wire |",
        "| **VCC** (rouge) | **5V** | Alimentation |",
        "| **GND** (noir) | **GND** | Masse |",
        "",
        "### Branchement pas a pas",
        "",
        f"1. **VCC** → **5V**",
        f"2. **GND** → **GND**",
        f"3. **DATA** → **D{pin}**",
        f"4. **Pull-up 4.7 kΩ** entre **DATA** et **5V** (obligatoire)",
        "",
        "### Lecture Stormer",
        "",
        f"- Broche **D{pin}** → cle `probe` (temperature sonde en °C)",
        "",
    ]


def _gas_wiring_lines(p: dict, sensors: list[str], profile: HardwareProfile) -> list[str]:
    if "gas_mq7" in sensors:
        name, pin_a = "MQ7 (monoxyde de carbone)", p["mq_co"]
        keys = "`co` + `co_alert`"
        alert_key = "co_alert"
    else:
        name, pin_a = "MQ2 / MQ5 (gaz inflammables)", p["mq_gas"]
        keys = "`gas` + `gas_alert`"
        alert_key = "gas_alert"
    pin_d = _gas_do_pin(p, sensors, profile)
    return [
        f"## {name} — module 4 broches",
        "",
        "Meme principe que le MQ135 : **A0** (mesure) + **D0** (seuil).",
        "",
        "| Broche module | Arduino | Role |",
        "|---------------|---------|------|",
        "| **VCC** | **5V** | Alimentation |",
        "| **GND** | **GND** | Masse |",
        f"| **A0** | **{pin_a}** | Mesure analogique 0–1023 |",
        f"| **D0** | **D{pin_d}** | Alarme gaz (seuil potentiometre) |",
        "",
        "### Branchement pas a pas",
        "",
        f"1. **VCC** → **5V**",
        f"2. **GND** → **GND**",
        f"3. **A0** → **{pin_a}**",
        f"4. **D0** → **D{pin_d}**",
        "",
        "### Reglage",
        "",
        "- Potentiometre bleu : sensibilite de **D0** (LED du module = alarme).",
        "- Prechauffer **1–2 minutes** avant mesure.",
        "",
        "### Lecture Stormer",
        "",
        f"- Analogique : `analogRead({pin_a})` → {keys.split('+')[0].strip()}",
        f"- Digital : `digitalRead({pin_d})` → `{alert_key}` (1 = gaz detecte)",
        "",
    ]


def _hygro_soil_wiring_lines(p: dict, sensors: list[str], profile: HardwareProfile) -> list[str]:
    pin_a = p["hygro"]
    pin_d = _hygro_do_pin(p, sensors, profile)
    mq_note: list[str] = []
    if "air_quality" in sensors:
        mq_pin = p["mq_air"]
        mq_note = [
            f"> ⚠ Vous avez aussi un **MQ135** : son fil **A0** va sur Arduino **{mq_pin}**,",
            f"> **pas** sur **{pin_a}**. L'hygrometre sol utilise **{pin_a}** uniquement.",
            "",
        ]
    return [
        "## FC-28 / YL-69 — hygrometrie du sol (4 broches + sonde)",
        "",
        "Le kit comprend un **module PCB** et une **sonde a piquer** dans le terreau.",
        "Stormer utilise **AO** (pourcentage humidite) et **DO** (alerte secheresse).",
        "",
        *mq_note,
        "",
        "### Partie 1 — Module electronic (PCB)",
        "",
        "| Broche module | Couleur fil | Arduino | Role |",
        "|---------------|-------------|---------|------|",
        "| **VCC** | Rouge | **5V** | Alimentation module |",
        "| **GND** | Noir | **GND** | Masse |",
        f"| **AO** | Jaune / vert | **{pin_a}** | Mesure analogique continue |",
        f"| **DO** | Blanc / bleu | **D{pin_d}** | Seuil sec/humide (potentiometre) |",
        "",
        f"> Le fil **AO** du module hygro va sur Arduino **{pin_a}** —",
        "> ce n'est **pas** la broche A0 du MQ135 (qualite de l'air).",
        "",
        "### Partie 2 — Sonde de sol (2 fils)",
        "",
        "| Fil sonde | Module PCB |",
        "|-----------|------------|",
        "| Fil 1 | **A** (entree analogique sonde) |",
        "| Fil 2 | **G** ou **GND** (masse sonde) |",
        "",
        "> La sonde se visse/plante dans le substrat. **Ne plongez que la partie metallique.**",
        "> Le PCB reste **hors de l'eau**.",
        "",
        "### Branchement pas a pas",
        "",
        f"1. **VCC** module → **5V** Arduino",
        f"2. **GND** module → **GND** Arduino",
        f"3. **AO** du module (pas A0 du MQ135 !) → broche Arduino **{pin_a}**",
        f"4. **DO** du module → broche Arduino **D{pin_d}**",
        "5. Branchez la **sonde** sur les bornes **A** et **G** du module",
        "6. Plantez la sonde dans le sol a **2–4 cm** de profondeur",
        "",
        "### AO vs DO",
        "",
        f"- **AO → {pin_a}** : humidite en % (`soil:0–100`). Sec = valeur basse, humide = haute.",
        f"- **DO → D{pin_d}** : alarme `soil_alert:1` si sol **trop sec** (reglez le potentiometre).",
        "",
        "### Reglage du potentiometre (vis bleue sur le module)",
        "",
        "1. Plantez la sonde dans un sol **bien humide** (apres arrosage).",
        "2. Tournez le potentiometre jusqu'a ce que la **LED du module s'eteigne**.",
        "3. Testez en sortant la sonde de l'eau : LED s'allume → `soil_alert:1`.",
        "",
        "### Calibration conseillee",
        "",
        "- Mesurez dans le **meme pot** a chaque session.",
        "- Evitez que la sonde touche le fond du pot (faux positif sec).",
        "- Sec : `soil` < 30 % | Humide : `soil` > 60 %",
        "",
        "### Lecture Stormer",
        "",
        f"- `analogRead({pin_a})` → `soil:62` (pourcentage)",
        f"- `digitalRead({pin_d})` → `soil_alert:0` (OK) ou `1` (trop sec)",
        "- Exemple : `temp:23.5,hum:45,soil:62,soil_alert:0`",
        "",
    ]


def _rain_wiring_lines(p: dict, has_i2c_display: bool) -> list[str]:
    pin_do = p["rain_do"]
    pin_ao = p["rain_an"]
    lines = [
        "## FC-37 / YD-R804 — detecteur de pluie (4 broches + plaque)",
        "",
        "Kit : **module PCB** + **plaque sensible** connectee par un cable.",
        "",
        "| Broche module | Arduino | Role |",
        "|---------------|---------|------|",
        "| **VCC** | **5V** | Alimentation |",
        "| **GND** | **GND** | Masse |",
        f"| **DO** | **D{pin_do}** | Pluie detectee (seuil potentiometre) |",
    ]
    if has_i2c_display:
        lines += [
            f"| **AO** | *(non branche)* | Conflit : **{pin_ao}** utilise par l'ecran I2C (SDA) |",
            "",
            "### Branchement pas a pas (avec ecran I2C)",
            "",
            f"1. **VCC** → **5V**",
            f"2. **GND** → **GND**",
            f"3. **DO** → **D{pin_do}**",
            f"4. **AO** : **ne pas brancher** (broche {pin_ao} = SDA de l'ecran)",
            "5. Vissez la **plaque de detection** sur le module",
            "",
            "> Stormer utilise **DO uniquement** : `rain:0` (sec) ou `rain:100` (pluie).",
        ]
    else:
        lines += [
            f"| **AO** | **{pin_ao}** | Intensite pluie analogique 0–1023 |",
            "",
            "### Branchement pas a pas",
            "",
            f"1. **VCC** → **5V**",
            f"2. **GND** → **GND**",
            f"3. **DO** → **D{pin_do}**",
            f"4. **AO** → **{pin_ao}**",
            "5. Vissez la **plaque de detection** sur le module",
            "",
            "### AO vs DO",
            "",
            f"- **AO → {pin_ao}** : intensite `rain:0–100` (gouttes = valeur haute)",
            f"- **DO → D{pin_do}** : `rain_alert:1` si pluie au-dela du seuil (potentiometre)",
            "",
            "### Reglage potentiometre",
            "",
            "- Gouttez de l'eau sur la plaque : LED s'allume quand seuil atteint.",
            "- Orientez la plaque pour que l'eau ruisselle correctement.",
        ]
    lines += ["", "### Lecture Stormer", ""]
    if has_i2c_display:
        lines.append(f"- `digitalRead({pin_do})` → `rain:0` ou `rain:100`")
    else:
        lines.append(f"- `analogRead({pin_ao})` + `digitalRead({pin_do})` → `rain` + `rain_alert`")
    lines.append("")
    return lines


def _display_wiring_lines(profile: HardwareProfile, p: dict) -> list[str]:
    disp = profile.display_label()
    return [
        f"## {disp}",
        "",
        "| Broche ecran | Arduino | Role |",
        "|--------------|---------|------|",
        f"| **SDA** | **{p['sda']}** | Donnees I2C |",
        f"| **SCL** | **{p['scl']}** | Horloge I2C |",
        "| **VCC** | **5V** | Alimentation |",
        "| **GND** | **GND** | Masse |",
        "",
        "### Branchement pas a pas",
        "",
        f"1. **VCC** → **5V**",
        f"2. **GND** → **GND**",
        f"3. **SDA** → **{p['sda']}**",
        f"4. **SCL** → **{p['scl']}**",
        "",
        "> Adresse I2C courante : **0x27** (LCD) ou **0x3C** (OLED). Plusieurs peripheriques I2C",
        "> peuvent partager SDA/SCL (capteurs + ecran sur le meme bus).",
        "",
    ]


def generate_wiring(profile: HardwareProfile) -> str:
    p = _pins(profile.board)
    sensors = _sensors(profile)
    i2c_disp = profile.display.startswith("lcd_i2c") or profile.display.startswith("oled_i2c")
    lines = [
        f"# Branchement — {profile.board_label()}",
        "",
        f"Logique carte : **{p['logic']}** | Genere par Stormer",
        "",
    ]
    lines += _pin_plan_lines(profile, p, sensors)

    if dht := _dht_type(sensors):
        lines += _dht_wiring_lines(p, dht)

    if "bme280" in sensors:
        lines += _bme280_wiring_lines(p)

    if "ds18b20" in sensors:
        lines += _ds18_wiring_lines(p)

    if "air_quality" in sensors:
        lines += _mq135_wiring_lines(p, profile.board, sensors, i2c_disp)

    if _gas_pin(sensors, p):
        lines += _gas_wiring_lines(p, sensors, profile)

    if "hygro_soil" in sensors:
        lines += _hygro_soil_wiring_lines(p, sensors, profile)

    if "rain_sensor" in sensors:
        lines += _rain_wiring_lines(p, i2c_disp)

    if i2c_disp:
        lines += _display_wiring_lines(profile, p)

    if profile.wireless == "cc1101":
        lines += ["## CC1101", f"- CS D{p['cc_cs']} | SPI | **VCC 3.3V**", ""]
    elif profile.wireless == "nrf24l01":
        lines += ["## NRF24L01", f"- CE D{p['nrf_ce']} | CSN D{p['nrf_csn']} | **3.3V**", ""]
    elif profile.wireless in ("rf433_tx", "rf433_rx"):
        lines += ["## 433 MHz", f"- DATA D{p['rf']}", ""]

    if profile.access == "mfrc522":
        lines += [
            "## Lecteur RFID RC522 (deverrouillage)",
            f"- SDA (SS) **D{p['rfid_ss']}** | RST **D{p['rfid_rst']}** | MOSI/MISO/SCK (SPI)",
            f"- Puce autorisee : **{profile.rfid_uid or 'A1:B2:C3:D4'}**",
            "- Presentez la puce pour debloquer Stormer sur le PC",
            "",
        ]
    elif profile.access == "pn532":
        lines += [
            "## Lecteur NFC PN532 (I2C)",
            f"- SDA **{p['sda']}** | SCL **{p['scl']}** | VCC 3.3V | GND",
            f"- Puce autorisee : **{profile.rfid_uid or 'A1:B2:C3:D4'}**",
            "",
        ]

    if profile.output == "status_3":
        lines += [
            "## LED status (3 couleurs)",
            f"- Vert **D{p['led_g']}** (+ resistance 220 ohm)",
            f"- Orange **D{p['led_o']}** (+ resistance 220 ohm)",
            f"- Rouge **D{p['led_r']}** (+ resistance 220 ohm)",
            "- Vert = debloque | Orange = mesure | Rouge = verrouille",
            "",
        ]
    elif profile.output == "rgb_1":
        lines += [
            "## LED RGB",
            f"- Rouge **D{p['led_rgb_r']}** | Vert **D{p['led_rgb_g']}** | Bleu **D{p['led_rgb_b']}**",
            "- Cathodes communes vers GND (+ resistance par canal)",
            "",
        ]
    elif profile.output == "neopixel_8":
        lines += [
            "## Ruban NeoPixel WS2812 (8 LED)",
            f"- DATA **D{p['neopixel']}** | VCC 5V | GND",
            "- Ajouter condensateur 1000 uF sur l'alimentation",
            "",
        ]

    fmt = "temp:23.5,hum:45.0,unlock:1"
    if profile.requires_rfid_unlock():
        fmt = "unlock:0 (verrouille) ou unlock:1 (puce OK) + capteurs"
    lines += [
        "## Format PC",
        f"`{fmt}` @ 9600 bauds",
        "",
        "## Bibliotheques Arduino",
        "",
        "Liste complete et installation : voir **DEPENDANCES.txt**",
        "(genere dans le meme dossier que ce fichier).",
        "",
    ]
    return "\n".join(lines)


def _profile_libraries(profile: HardwareProfile) -> list[tuple[str, str, str]]:
    """Bibliotheques requises : (nom, installation IDE, utilite)."""
    sensors = _sensors(profile)
    libs: list[tuple[str, str, str]] = []

    def add(name: str, install: str, why: str) -> None:
        if not any(x[0] == name for x in libs):
            libs.append((name, install, why))

    if any(s in sensors for s in ("dht11", "dht22")):
        add("DHT sensor library", "Gestionnaire : **DHT sensor library** (Adafruit)", "Capteur DHT11/DHT22")
    if "bme280" in sensors:
        add("Adafruit BME280 Library", "Gestionnaire : **Adafruit BME280 Library**", "Capteur BME280")
        add("Adafruit Unified Sensor", "Gestionnaire : **Adafruit Unified Sensor**", "Dependance BME280")
    if "ds18b20" in sensors:
        add("OneWire", "Gestionnaire : **OneWire** (Paul Stoffregen)", "Bus 1-Wire DS18B20")
        add("DallasTemperature", "Gestionnaire : **Dallas Temperature Control Library**", "Lecture DS18B20")
    if profile.display.startswith("lcd_i2c"):
        add("LiquidCrystal I2C", "Gestionnaire : **LiquidCrystal I2C** (Frank de Brabander)", "Ecran LCD I2C")
    if profile.display.startswith("oled_i2c"):
        add("Adafruit SSD1306", "Gestionnaire : **Adafruit SSD1306**", "Ecran OLED")
        add("Adafruit GFX Library", "Gestionnaire : **Adafruit GFX Library**", "Graphiques OLED")
    if "air_quality" in sensors:
        add("(aucune)", "MQ135 : lecture analogique native (`analogRead`)", "Qualite de l'air")
    if profile.access == "mfrc522":
        add("MFRC522", "Gestionnaire : **MFRC522** (GithubCommunity)", "Lecteur RFID RC522")
    if profile.access == "pn532":
        add("Adafruit PN532", "Gestionnaire : **Adafruit PN532**", "Lecteur NFC PN532")
    if profile.output == "neopixel_8":
        add("Adafruit NeoPixel", "Gestionnaire : **Adafruit NeoPixel**", "Ruban WS2812")
    return libs


def dependencies_bullets(profile: HardwareProfile) -> str:
    """Liste lisible pour l'interface (gros texte)."""
    libs = _profile_libraries(profile)
    lines = [
        "Arduino IDE → Croquis → Gerer les bibliotheques",
        "",
    ]
    n = 0
    for name, _install, why in libs:
        if name == "(aucune)":
            lines.append("• MQ135 : aucune lib (analogRead natif)")
            continue
        n += 1
        lines.append(f"{n}. {name}")
        lines.append(f"   → {why}")
    if n == 0 and not any(x[0] == "(aucune)" for x in libs):
        lines.append("Aucune bibliotheque externe requise.")
    return "\n".join(lines)


def generate_dependencies(profile: HardwareProfile) -> str:
    """Guide d'installation des bibliotheques Arduino IDE."""
    libs = _profile_libraries(profile)

    lines = [
        f"# Dependances Arduino — {profile.board_label()}",
        "",
        "Installez ces bibliotheques **avant** de compiler `stormer_generated.ino`.",
        "",
        "## Methode (Arduino IDE 2.x)",
        "",
        "1. Ouvrez **Arduino IDE**",
        "2. Menu **Croquis → Inclure une bibliotheque → Gerer les bibliotheques...**",
        "3. Recherchez le nom ci-dessous et cliquez **Installer**",
        "4. Recommencez pour chaque bibliotheque de la liste",
        "5. Branchez la carte, selectionnez **" + profile.board_label() + "** dans Outils → Type de carte",
        "6. Ouvrez `stormer_generated.ino` et cliquez **Verifier** (✓)",
        "",
        "## Bibliotheques requises pour votre configuration",
        "",
        "| Bibliotheque | Installation | Utilisee pour |",
        "|--------------|--------------|---------------|",
    ]
    for name, install, why in libs:
        lines.append(f"| **{name}** | {install} | {why} |")

    lines += [
        "",
        "## Toujours inclus (pas d'installation)",
        "",
        "- `Wire.h` — bus I2C",
        "- `SPI.h` — si RFID RC522 ou modules SPI",
        "",
        "## Fichiers Stormer (meme dossier)",
        "",
        "- `stormer_generated.ino` — code a televerser",
        "- `BRANCHEMENT.txt` — branchement detaille fil par fil",
        "- `DEPENDANCES.txt` — ce fichier",
        "",
        "## Depannage compilation",
        "",
        "- **LiquidCrystal_I2C** : essayez aussi `hd44780` si erreur d'adresse LCD",
        "- **DHT** : une seule lib DHT (Adafruit), pas deux en meme temps",
        "- **OLED** : adresse I2C `0x3C` par defaut dans le sketch",
        "",
    ]
    return "\n".join(lines)


def generate_readme(profile: HardwareProfile) -> str:
    """Fiche recapitulative exportee avec le profil."""
    from stormer.profile_info import profile_lines

    lines = [
        "# Stormer — Configuration materielle exportee",
        "",
        *profile_lines(profile),
        "",
        "## Fichiers",
        "",
        "1. **stormer_generated.ino** — televersez sur l'Arduino",
        "2. **BRANCHEMENT.txt** — plan des broches + branchement pas a pas",
        "3. **DEPENDANCES.txt** — bibliotheques a installer dans Arduino IDE",
        "",
        "## Ordre recommande",
        "",
        "1. Installez les bibliotheques (DEPENDANCES.txt)",
        "2. Branchez selon BRANCHEMENT.txt",
        "3. Televersez stormer_generated.ino",
        "4. Lancez Stormer sur le PC et connectez le port COM",
        "",
    ]
    return "\n".join(lines)


def _rfid_sketch_parts(profile: HardwareProfile, p: dict) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
    """Includes, defines, objects, setup, helpers, loop lines pour RFID."""
    if not profile.requires_rfid_unlock():
        helpers = ["bool systemUnlocked = true;", "void pollAccess() {}"]
        return [], [], [], [], helpers, []

    uid = uid_to_bytes(profile.rfid_uid)
    uid_lit = ", ".join(f"0x{b:02X}" for b in uid)
    defines = [f"#define AUTH_UID_LEN 4", f"#define USE_RFID_ACCESS"]
    objects: list[str] = []
    setup: list[str] = []
    helpers = [
        "bool systemUnlocked = false;",
        f"const byte AUTH_UID[{4}] = {{{uid_lit}}};",
    ]
    loop_pre: list[str] = ["  pollAccess();"]

    if profile.access == "mfrc522":
        includes = ["#include <SPI.h>", "#include <MFRC522.h>"]
        defines += [f"#define RFID_RST_PIN {p['rfid_rst']}", f"#define RFID_SS_PIN  {p['rfid_ss']}"]
        objects.append("MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);")
        setup += [
            "  SPI.begin();",
            "  rfid.PCD_Init();",
            "  Serial.println(\"# RFID RC522 actif — presentez la puce\");",
        ]
        helpers += [
            "bool uidMatches(byte* uid, byte len) {",
            "  if (len < AUTH_UID_LEN) return false;",
            "  for (byte i = 0; i < AUTH_UID_LEN; i++) if (uid[i] != AUTH_UID[i]) return false;",
            "  return true;",
            "}",
            "void pollAccess() {",
            "  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;",
            "  systemUnlocked = uidMatches(rfid.uid.uidByte, rfid.uid.size);",
            "  rfid.PICC_HaltA();",
            "  rfid.PCD_StopCrypto1();",
            "}",
        ]
    else:
        includes = ["#include <Wire.h>", "#include <Adafruit_PN532.h>"]
        defines.append("#define PN532_IRQ   -1")
        objects.append("Adafruit_PN532 nfc(PN532_IRQ, -1);")
        setup += [
            "  nfc.begin();",
            "  uint32_t v = nfc.getFirmwareVersion();",
            "  if (!v) Serial.println(\"# ERREUR PN532\");",
            "  else Serial.println(\"# NFC PN532 actif — presentez la puce\");",
            "  nfc.SAMConfig();",
        ]
        helpers += [
            "bool uidMatches(uint8_t* uid, uint8_t len) {",
            "  if (len < AUTH_UID_LEN) return false;",
            "  for (uint8_t i = 0; i < AUTH_UID_LEN; i++) if (uid[i] != AUTH_UID[i]) return false;",
            "  return true;",
            "}",
            "void pollAccess() {",
            "  uint8_t uid[] = {0,0,0,0,0,0,0};",
            "  uint8_t uidLen = 0;",
            "  if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLen, 80))",
            "    systemUnlocked = uidMatches(uid, uidLen);",
            "}",
        ]

    return includes, defines, objects, setup, helpers, loop_pre


def _led_sketch_parts(profile: HardwareProfile, p: dict) -> tuple[list[str], list[str], list[str], list[str], str]:
    """Includes, defines, setup, objects, updateLeds function."""
    noop = "void updateLeds(bool measuring) { (void)measuring; }"
    out = profile.output
    if out == "none":
        return [], [], [], [], noop

    includes: list[str] = []
    defines: list[str] = []
    setup: list[str] = []
    objects: list[str] = []

    if out == "status_3":
        defines += [
            f"#define LED_G {p['led_g']}",
            f"#define LED_O {p['led_o']}",
            f"#define LED_R {p['led_r']}",
        ]
        setup += [
            "  pinMode(LED_G, OUTPUT);",
            "  pinMode(LED_O, OUTPUT);",
            "  pinMode(LED_R, OUTPUT);",
            "  digitalWrite(LED_R, HIGH);",
        ]
        fn = (
            "void updateLeds(bool measuring) {"
            "  digitalWrite(LED_G, LOW); digitalWrite(LED_O, LOW); digitalWrite(LED_R, LOW);"
            "  if (!systemUnlocked) { digitalWrite(LED_R, HIGH); return; }"
            "  if (measuring) { digitalWrite(LED_O, HIGH); return; }"
            "  digitalWrite(LED_G, HIGH);"
            "}"
        )
        return includes, defines, setup, objects, fn

    if out == "rgb_1":
        defines += [
            f"#define LED_R_PIN {p['led_rgb_r']}",
            f"#define LED_G_PIN {p['led_rgb_g']}",
            f"#define LED_B_PIN {p['led_rgb_b']}",
        ]
        setup += [
            "  pinMode(LED_R_PIN, OUTPUT);",
            "  pinMode(LED_G_PIN, OUTPUT);",
            "  pinMode(LED_B_PIN, OUTPUT);",
        ]
        fn = (
            "void updateLeds(bool measuring) {"
            "  if (!systemUnlocked) { analogWrite(LED_R_PIN,255); analogWrite(LED_G_PIN,0); analogWrite(LED_B_PIN,0); return; }"
            "  if (measuring) { analogWrite(LED_R_PIN,0); analogWrite(LED_G_PIN,180); analogWrite(LED_B_PIN,0); return; }"
            "  analogWrite(LED_R_PIN,0); analogWrite(LED_G_PIN,255); analogWrite(LED_B_PIN,0);"
            "}"
        )
        return includes, defines, setup, objects, fn

    includes.append("#include <Adafruit_NeoPixel.h>")
    defines += [f"#define NEO_PIN {p['neopixel']}", "#define NEO_COUNT 8"]
    objects.append("Adafruit_NeoPixel pixels(NEO_COUNT, NEO_PIN, NEO_GRB + NEO_KHZ800);")
    setup.append("  pixels.begin(); pixels.show();")
    fn = (
        "void updateLeds(bool measuring) {"
        "  uint32_t c = pixels.Color(0,80,0);"
        "  if (!systemUnlocked) c = pixels.Color(80,0,0);"
        "  else if (measuring) c = pixels.Color(90,40,0);"
        "  for (int i=0;i<NEO_COUNT;i++) pixels.setPixelColor(i,c);"
        "  pixels.show();"
        "}"
    )
    return includes, defines, setup, objects, fn


def _boot_serial_line(pct: int, msg: str) -> str:
    return f'  Serial.println("# Boot [{pct:3d}%] {msg}");'


def _boot_helpers(has_lcd: bool, has_oled: bool) -> list[str]:
    helpers: list[str] = []
    if has_lcd:
        helpers.append(
            "void stormerBootBar(uint8_t pct, const char* label) {"
            "  lcd.clear();"
            "  lcd.setCursor(0, 0);"
            '  lcd.print(F(">> STORMER <<"));'
            "  lcd.setCursor(0, 1);"
            "  lcd.print(label);"
            "  delay(280);"
            "  lcd.setCursor(0, 1);"
            "  for (uint8_t c = 0; c < LCD_COLS; c++) lcd.print(' ');"
            "  lcd.setCursor(0, 1);"
            "  lcd.print('[');"
            "  uint8_t w = LCD_COLS > 2 ? LCD_COLS - 2 : 14;"
            "  uint8_t filled = (uint8_t)((uint16_t)w * pct / 100);"
            "  for (uint8_t i = 0; i < w; i++)"
            "    lcd.print(i < filled ? '#' : '-');"
            "  lcd.print(']');"
            "  delay(320);"
            "}"
        )
    if has_oled:
        helpers.append(
            "void stormerBootBar(uint8_t pct, const char* label) {"
            "  oled.clearDisplay();"
            "  oled.setTextSize(2);"
            "  oled.setCursor(10, 0);"
            '  oled.println(F("STORMER"));'
            "  oled.setTextSize(1);"
            "  oled.setCursor(0, 22);"
            "  oled.println(label);"
            "  oled.drawRect(4, 40, 120, 10, SSD1306_WHITE);"
            "  uint8_t fill = (uint8_t)((uint16_t)112 * pct / 100);"
            "  if (fill > 0) oled.fillRect(6, 42, fill, 6, SSD1306_WHITE);"
            "  oled.display();"
            "  delay(400);"
            "}"
        )
    return helpers


def _lcd_display_rows(
    lcd_rows: int,
    *,
    dht: str | None,
    has_bme: bool,
    has_air: bool,
    has_hygro: bool,
    has_rain: bool,
    gas_info: tuple[str, str] | None,
) -> list[tuple[int, str]]:
    """Lignes LCD : (numero_ligne, code lcd.print...)."""
    rows: list[tuple[int, str]] = []
    if dht:
        rows.append((0, 'lcd.print("T:"); lcd.print(temp,1); lcd.print(" H:"); lcd.print(hum,0);'))
    elif has_bme:
        rows.append((0, 'lcd.print("T:"); lcd.print(bmeT,1); lcd.print(" H:"); lcd.print(bmeH,0);'))

    if lcd_rows >= 4:
        r = 1
        if has_air:
            rows.append((r, 'lcd.print("Air:"); lcd.print(airVal); lcd.print(airAlert?"!":" ");'))
            r += 1
        if has_hygro:
            rows.append((r, 'lcd.print("Sol:"); lcd.print(soilPct); lcd.print("% "); lcd.print(soilAlert?"!":" ");'))
            r += 1
        if has_rain:
            rows.append((r, 'lcd.print("Pluie:"); lcd.print(rainPct); lcd.print("%");'))
        elif gas_info:
            key = "CO" if gas_info[0] == "PIN_MQ_CO" else "Gaz"
            rows.append((r, f'lcd.print("{key}:"); lcd.print(gasVal);'))
    else:
        parts: list[str] = []
        if has_air:
            parts.append('lcd.print("A:"); lcd.print(airVal);')
        if has_hygro:
            parts.append('lcd.print(" S:"); lcd.print(soilPct); lcd.print("%");')
        if has_rain:
            parts.append('lcd.print(" P:"); lcd.print(rainPct);')
        elif gas_info:
            key = "CO" if gas_info[0] == "PIN_MQ_CO" else "Gz"
            parts.append(f'lcd.print(" {key}:"); lcd.print(gasVal);')
        if parts:
            rows.append((1, "".join(parts)))
    return rows


def generate_sketch(profile: HardwareProfile) -> str:
    profile.ensure_rfid_uid()
    p = _pins(profile.board)
    sensors = _sensors(profile)
    dht = _dht_type(sensors)
    has_bme = "bme280" in sensors
    has_ds18 = "ds18b20" in sensors
    has_air = "air_quality" in sensors
    has_hygro = "hygro_soil" in sensors
    has_rain = "rain_sensor" in sensors
    gas_info = _gas_pin(sensors, p)
    disp = profile.display
    i2c_disp = disp.startswith("lcd_i2c") or disp.startswith("oled_i2c")
    has_lcd = disp.startswith("lcd_i2c")
    has_oled = disp.startswith("oled_i2c")
    lcd_cols = 20 if disp == "lcd_i2c_20x4" else 16
    lcd_rows = 4 if disp == "lcd_i2c_20x4" else 2
    oled_h = 32 if disp == "oled_i2c_128x32" else 64
    has_rfid = profile.requires_rfid_unlock()

    rfid_inc, rfid_def, rfid_obj, rfid_setup, rfid_helpers, rfid_loop = _rfid_sketch_parts(profile, p)
    led_inc, led_def, led_setup, led_obj, led_fn = _led_sketch_parts(profile, p)

    includes = ["#include <Wire.h>"]
    for inc in rfid_inc + led_inc:
        if inc not in includes:
            includes.append(inc)
    if dht:
        includes.append("#include <DHT.h>")
    if has_bme:
        includes += ["#include <Adafruit_Sensor.h>", "#include <Adafruit_BME280.h>"]
    if has_ds18:
        includes += ["#include <OneWire.h>", "#include <DallasTemperature.h>"]
    if has_lcd:
        includes.append("#include <LiquidCrystal_I2C.h>")
    if has_oled:
        includes += ["#include <Adafruit_GFX.h>", "#include <Adafruit_SSD1306.h>"]

    defines = ["#define BAUDRATE     9600", "#define INTERVAL_MS  2000", "#define USE_LCD_BEGIN"]
    defines.extend(rfid_def)
    defines.extend(led_def)
    if dht:
        defines += [f"#define DHT_PIN  {p['dht']}", f"#define DHT_TYPE {dht}"]
    if has_ds18:
        defines.append(f"#define DS18_PIN {p['ds18']}")
    if has_air:
        defines += [
            f"#define PIN_MQ_AIR    {p['mq_air']}",
            f"#define PIN_MQ_AIR_DO {_mq135_do_pin(p, sensors)}",
        ]
    if gas_info:
        defines += [
            f"#define {gas_info[0]} {gas_info[1]}",
            f"#define PIN_MQ_GAS_DO {_gas_do_pin(p, sensors, profile)}",
        ]
    if has_hygro:
        defines += [
            f"#define PIN_HYGRO    {p['hygro']}",
            f"#define PIN_HYGRO_DO {_hygro_do_pin(p, sensors, profile)}",
        ]
    if has_rain:
        defines.append(f"#define PIN_RAIN_DO {p['rain_do']}")
        if not i2c_disp:
            defines.append(f"#define PIN_RAIN_AN {p['rain_an']}")
    if has_lcd:
        defines += ["#define LCD_ADDR 0x27", f"#define LCD_COLS {lcd_cols}", f"#define LCD_ROWS {lcd_rows}"]
    if has_oled:
        defines += ["#define OLED_ADDR 0x3C", f"#define OLED_H  {oled_h}"]

    objects: list[str] = []
    objects.extend(rfid_obj)
    objects.extend(led_obj)
    setup = [
        "  Serial.begin(BAUDRATE);",
        "  delay(300);",
        _boot_serial_line(5, "Demarrage Stormer"),
        "  Wire.begin();",
        _boot_serial_line(10, "Bus I2C"),
    ]
    setup.extend(rfid_setup)
    setup.extend(led_setup)

    if has_lcd:
        objects.append("LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);")
        setup += [
            "#ifdef USE_LCD_BEGIN", "  lcd.begin();", "#else", "  lcd.init();", "#endif",
            "  lcd.backlight();",
            _boot_serial_line(18, "Ecran LCD"),
            '  stormerBootBar(18, "Ecran LCD");',
        ]
    if has_oled:
        objects.append("Adafruit_SSD1306 oled(128, OLED_H, &Wire, -1);")
        setup += [
            "  if (oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {",
            _boot_serial_line(18, "Ecran OLED"),
            '    stormerBootBar(18, "Ecran OLED");',
            "  }",
        ]

    if dht:
        objects.append("DHT dht(DHT_PIN, DHT_TYPE);")
        setup += [
            "  dht.begin();",
            _boot_serial_line(32, "Capteur DHT"),
            '  stormerBootBar(32, "DHT OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    if has_bme:
        objects.append("Adafruit_BME280 bme;")
        setup += [
            "  if (!bme.begin(0x76)) Serial.println(\"# ERREUR BME280\");",
            _boot_serial_line(36, "Capteur BME280"),
            '  stormerBootBar(36, "BME OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    if has_ds18:
        objects += [f"OneWire ow(DS18_PIN);", "DallasTemperature ds18(&ow);"]
        setup += [
            "  ds18.begin();",
            _boot_serial_line(40, "Sonde DS18B20"),
            '  stormerBootBar(40, "DS18 OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    if has_hygro:
        do = _hygro_do_pin(p, sensors, profile)
        setup += [
            "  pinMode(PIN_HYGRO_DO, INPUT);",
            f"  Serial.println(\"# FC-28 sol AO->{p['hygro']} DO->D{do}\");",
            _boot_serial_line(52, "Hygrometre sol"),
            '  stormerBootBar(52, "Sol OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    if has_rain:
        setup += [
            "  pinMode(PIN_RAIN_DO, INPUT);",
            _boot_serial_line(58, "Capteur pluie"),
            '  stormerBootBar(58, "Pluie OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    if gas_info:
        setup += [
            "  pinMode(PIN_MQ_GAS_DO, INPUT);",
            _boot_serial_line(62, "Capteur gaz"),
            '  stormerBootBar(62, "Gaz OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    if has_air:
        do_pin = _mq135_do_pin(p, sensors)
        setup += [
            "  pinMode(PIN_MQ_AIR_DO, INPUT);",
            f"  Serial.println(\"# MQ135 A0->{p['mq_air']} D0->D{do_pin} — prechauffer 2-3 min\");",
            _boot_serial_line(70, "MQ135 qualite air"),
            '  stormerBootBar(70, "MQ135 OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    if has_rfid:
        setup += [
            _boot_serial_line(82, "Lecteur RFID"),
            '  stormerBootBar(82, "RFID OK");' if (has_lcd or has_oled) else "",
        ]
        setup = [s for s in setup if s]
    setup += [
        _boot_serial_line(95, "Finalisation"),
        '  stormerBootBar(95, "Chargement...");' if (has_lcd or has_oled) else "",
        '  stormerBootBar(100, "Pret !");' if (has_lcd or has_oled) else "",
        "  delay(700);",
    ]
    setup = [s for s in setup if s]
    if has_lcd:
        setup.append("  lcd.clear();")
    if has_oled:
        setup.append("  oled.clearDisplay(); oled.display();")
    setup.append("  Serial.println(\"# Stormer pret\");")

    reads: list[str] = []
    serial: list[str] = []

    if dht:
        reads += ["  float hum = dht.readHumidity();", "  float temp = dht.readTemperature();",
                  "  if (isnan(hum)||isnan(temp)) { Serial.println(\"# ERREUR DHT\"); return; }"]
        serial += ['Serial.print("temp:"); Serial.print(temp,1);', 'Serial.print(",hum:"); Serial.print(hum,1);']
    if has_bme:
        reads += ["  float bmeT=bme.readTemperature();", "  float bmeH=bme.readHumidity();",
                  "  float bmeP=bme.readPressure()/100.0F;"]
        if not dht:
            serial += ['Serial.print("temp:"); Serial.print(bmeT,1);', 'Serial.print(",hum:"); Serial.print(bmeH,1);']
        serial.append('Serial.print(",press:"); Serial.print(bmeP,1);')
    if has_ds18:
        reads += ["  ds18.requestTemperatures();", "  float probe=ds18.getTempCByIndex(0);"]
        serial.append('Serial.print(",probe:"); Serial.print(probe,1);')
    if has_air:
        reads += [
            "  int airVal=analogRead(PIN_MQ_AIR);",
            "  int airAlert=(digitalRead(PIN_MQ_AIR_DO)==LOW)?1:0;",
        ]
        serial += [
            'Serial.print(",air:"); Serial.print(airVal);',
            'Serial.print(",air_alert:"); Serial.print(airAlert);',
        ]
    if has_hygro:
        reads += [
            "  int hygroRaw=analogRead(PIN_HYGRO);",
            "  int soilPct=constrain(map(hygroRaw,1023,0,0,100),0,100);",
            "  int soilAlert=(digitalRead(PIN_HYGRO_DO)==HIGH)?1:0;",
        ]
        serial += [
            'Serial.print(",soil:"); Serial.print(soilPct);',
            'Serial.print(",soil_alert:"); Serial.print(soilAlert);',
        ]
    if has_rain:
        if i2c_disp:
            reads += [
                "  int rainPct=(digitalRead(PIN_RAIN_DO)==LOW)?100:0;",
                "  int rainAlert=(digitalRead(PIN_RAIN_DO)==LOW)?1:0;",
            ]
            serial += [
                'Serial.print(",rain:"); Serial.print(rainPct);',
                'Serial.print(",rain_alert:"); Serial.print(rainAlert);',
            ]
        else:
            reads += [
                "  int rainRaw=analogRead(PIN_RAIN_AN);",
                "  int rainPct=constrain(map(rainRaw,1023,0,0,100),0,100);",
                "  int rainAlert=(digitalRead(PIN_RAIN_DO)==LOW)?1:0;",
            ]
            serial += [
                'Serial.print(",rain:"); Serial.print(rainPct);',
                'Serial.print(",rain_alert:"); Serial.print(rainAlert);',
            ]
    if gas_info:
        reads += [
            f"  int gasVal=analogRead({gas_info[0]});",
            "  int gasAlert=(digitalRead(PIN_MQ_GAS_DO)==LOW)?1:0;",
        ]
        key = "co" if gas_info[0] == "PIN_MQ_CO" else "gas"
        alert = "co_alert" if key == "co" else "gas_alert"
        serial += [
            f'Serial.print(",{key}:"); Serial.print(gasVal);',
            f'Serial.print(",{alert}:"); Serial.print(gasAlert);',
        ]

    disp_code: list[str] = []
    if has_lcd:
        lcd_layout = _lcd_display_rows(
            lcd_rows,
            dht=dht,
            has_bme=has_bme,
            has_air=has_air,
            has_hygro=has_hygro,
            has_rain=has_rain,
            gas_info=gas_info,
        )
        for row, code in lcd_layout:
            disp_code += [f"  lcd.setCursor(0,{row});", f"  {code} lcd.print(\"  \");"]
    if has_oled and (dht or has_bme or has_air or has_hygro or has_rain):
        oled_parts = ["  oled.clearDisplay();", "  oled.setTextSize(1);"]
        if dht:
            oled_parts.append(
                '  oled.setCursor(0, 0); oled.print("T:"); oled.print(temp,1);'
                ' oled.print(" H:"); oled.print(hum,0);'
            )
        elif has_bme:
            oled_parts.append(
                '  oled.setCursor(0, 0); oled.print("T:"); oled.print(bmeT,1);'
                ' oled.print(" H:"); oled.print(bmeH,0);'
            )
        oled_l2: list[str] = []
        if has_air:
            oled_l2.append('oled.print("A:"); oled.print(airVal);')
        if has_hygro:
            oled_l2.append('oled.print(" S:"); oled.print(soilPct); oled.print("%");')
        if has_rain:
            oled_l2.append('oled.print(" P:"); oled.print(rainPct);')
        if oled_l2:
            oled_parts.append(f"  oled.setCursor(0, 12); {' '.join(oled_l2)}")
        oled_parts.append("  oled.display();")
        disp_code += oled_parts

    rfid_note = ""
    if has_rfid:
        rfid_note = f"\n * RFID     : {profile.access_label()} — puce {profile.rfid_uid}"

    header = f"""/*
 * STORMER — genere pour {profile.board_label()}
 * Capteurs : {", ".join(profile.sensor_labels())}
 * Ecran    : {profile.display_label()}
 * LED      : {profile.output_label()}{rfid_note}
 *
 * COMMENT CA MARCHE :
 *  setup()  -> ecran de chargement LCD/OLED, puis capteurs
 *  loop()   -> verifie la puce RFID, lit capteurs si debloque
 *  Format   -> unlock:1,temp:23.5,hum:45.0 (lu par Stormer)
 */"""

    helpers = _boot_helpers(has_lcd, has_oled) + rfid_helpers + [led_fn]
    sensor_serial = list(serial)
    loop_body: list[str] = [
        "  if (millis()-lastRead<INTERVAL_MS) return;",
        "  lastRead=millis();",
        "",
    ]
    loop_body.extend(rfid_loop)
    loop_body.append("  updateLeds(true);")
    loop_body.append("")
    loop_body.append('  Serial.print("unlock:"); Serial.print(systemUnlocked ? 1 : 0);')
    if has_rfid:
        loop_body += [
            "  if (!systemUnlocked) {",
            "    Serial.println();",
            "    updateLeds(false);",
            "    return;",
            "  }",
            "",
        ]
    if reads:
        loop_body.append("\n".join(reads))
        loop_body.append("")
    for i, s in enumerate(sensor_serial):
        sep = 'Serial.print(","); ' if i == 0 else ""
        loop_body.append(f"  {sep}{s}")
    loop_body.append("  Serial.println();")
    loop_body.append("  updateLeds(false);")
    if disp_code:
        loop_body.append("\n" + "\n".join(disp_code))

    body = header + "\n\n" + "\n".join(includes) + "\n\n" + "\n".join(defines) + "\n\n"
    body += "\n".join(objects) + "\nunsigned long lastRead=0;\n\n"
    body += "\n".join(helpers) + "\n\n"
    body += "void setup() {\n" + "\n".join(setup) + "\n}\n\nvoid loop() {\n"
    body += "\n".join(loop_body) + "\n}\n"
    return body


EXPORT_FILES: list[tuple[str, str, str]] = [
    ("stormer_generated.ino", ".ino", "Code Arduino"),
    ("BRANCHEMENT.txt", ".txt", "Branchement"),
    ("DEPENDANCES.txt", ".txt", "Modules Arduino"),
    ("LISEZMOI.txt", ".txt", "Guide"),
]


def export_file_content(profile: HardwareProfile, filename: str) -> str:
    if filename.endswith(".ino"):
        return generate_sketch(profile)
    if filename == "BRANCHEMENT.txt":
        return generate_wiring(profile)
    if filename == "DEPENDANCES.txt":
        return generate_dependencies(profile)
    return generate_readme(profile)


def export_generated_files(profile: HardwareProfile) -> tuple[Path, Path, Path, Path]:
    out = export_dir()
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, _ext, _label in EXPORT_FILES:
        path = out / name
        path.write_text(export_file_content(profile, name), encoding="utf-8")
        paths.append(path)
    return paths[0], paths[1], paths[2], paths[3]
