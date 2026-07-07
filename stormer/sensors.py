"""Registre des capteurs — cles serie, affichage UI et lien profil materiel."""

from __future__ import annotations

from stormer.setup_config import HardwareProfile

# Sorties serie generees par type de capteur dans le profil
PROFILE_OUTPUTS: dict[str, list[str]] = {
    "dht11": ["temp", "hum"],
    "dht22": ["temp", "hum"],
    "bme280": ["temp", "hum", "press"],
    "ds18b20": ["probe"],
    "air_quality": ["air", "air_alert"],
    "gas_mq2": ["gas", "gas_alert"],
    "gas_mq5": ["gas", "gas_alert"],
    "gas_mq7": ["co", "co_alert"],
    "hygro_soil": ["soil", "soil_alert"],
    "rain_sensor": ["rain", "rain_alert"],
}

# Metadonnees pour l'interface et l'IA
SENSOR_META: dict[str, dict[str, str]] = {
    "temp": {"title": "Temperature", "display": "Temperature", "unit": "°C", "color": "#f59e0b"},
    "hum": {"title": "Humidite air", "display": "Humidite air", "unit": "%", "color": "#06b6d4"},
    "press": {"title": "Pression", "display": "Pression", "unit": "hPa", "color": "#8b5cf6"},
    "probe": {"title": "Sonde", "display": "Sonde DS18B20", "unit": "°C", "color": "#f97316"},
    "air": {
        "title": "Qualite air",
        "display": "Qualite air (MQ135)",
        "unit": "/1023",
        "color": "#a855f7",
    },
    "air_alert": {"title": "Alerte air", "display": "Alerte MQ135 (D0)", "unit": "", "color": "#ef4444"},
    "gas": {"title": "Gaz", "display": "Gaz", "unit": "", "color": "#eab308"},
    "gas_alert": {"title": "Alerte gaz", "display": "Alerte MQ2/5 (D0)", "unit": "", "color": "#ef4444"},
    "co": {"title": "CO", "display": "Monoxyde de carbone", "unit": "", "color": "#ef4444"},
    "co_alert": {"title": "Alerte CO", "display": "Alerte MQ7 (D0)", "unit": "", "color": "#dc2626"},
    "soil": {
        "title": "Humidite sol",
        "display": "Humidite sol (FC-28)",
        "unit": "%",
        "color": "#84cc16",
    },
    "soil_alert": {"title": "Alerte sol", "display": "Sol trop sec (D0)", "unit": "", "color": "#ea580c"},
    "rain": {"title": "Pluie", "display": "Pluie", "unit": "", "color": "#6366f1"},
    "rain_alert": {"title": "Alerte pluie", "display": "Pluie detectee (D0)", "unit": "", "color": "#4f46e5"},
}

# Priorite d'affichage dans le header et le panneau IA
DISPLAY_ORDER = [
    "temp", "hum", "soil", "soil_alert", "rain", "rain_alert",
    "press", "probe", "air", "air_alert", "gas", "gas_alert", "co", "co_alert",
]


def meta(key: str) -> dict[str, str]:
    k = key.lower()
    if k in SENSOR_META:
        return SENSOR_META[k]
    return {"title": k.capitalize(), "display": k.capitalize(), "unit": "", "color": "#3b82f6"}


def expected_keys(profile: HardwareProfile | None) -> list[str]:
    if not profile or not profile.sensors:
        return ["temp", "hum"]
    keys: list[str] = []
    seen: set[str] = set()
    for sensor in profile.normalized_sensors():
        for key in PROFILE_OUTPUTS.get(sensor, []):
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return sorted(keys, key=lambda k: DISPLAY_ORDER.index(k) if k in DISPLAY_ORDER else 99)


def value_hint(key: str, value: float) -> str:
    """Legende courte affichee sous la valeur ou dans le terminal."""
    k = key.lower()
    if k == "air":
        if value >= 700:
            return "air pur"
        if value >= 400:
            return "correct"
        if value >= 150:
            return "moyen"
        return "air charge"
    if k == "soil":
        if value >= 60:
            return "humide"
        if value >= 35:
            return "moyen"
        return "sec"
    if k.endswith("_alert"):
        return "alarme active" if value >= 1 else "normal"
    if k == "rain":
        if value >= 70:
            return "forte pluie"
        if value >= 35:
            return "pluie"
        if value >= 10:
            return "humide"
        return "sec"
    if k == "gas" or k == "co":
        if value >= 700:
            return "faible"
        if value >= 300:
            return "moyen"
        return "eleve"
    return ""


def format_live(key: str, value: float) -> str:
    k = key.lower()
    if k.endswith("_alert") or k == "air_alert":
        return "ALERTE" if value >= 1 else "OK"
    if k == "rain":
        if value >= 70:
            return "Forte"
        if value >= 35:
            return "Pluie"
        if value >= 10:
            return "Humide"
        return "Sec"
    if meta(k)["unit"] == "°C":
        return f"{value:.1f}"
    if meta(k)["unit"] == "%":
        return f"{value:.0f}"
    return f"{value:.0f}"


_ALERT_SHORT: dict[str, str] = {
    "soil_alert": "sol",
    "air_alert": "air",
    "rain_alert": "pluie",
    "gas_alert": "gaz",
    "co_alert": "co",
}


def _terminal_measure(key: str, value: float) -> str | None:
    """Fragment court pour une mesure (hors alertes)."""
    k = key.lower()
    if k == "temp":
        return f"{value:.1f}°C"
    if k == "hum":
        return f"{value:.0f}%"
    if k == "soil":
        hint = value_hint(k, value)
        if hint == "sec":
            return f"sol {value:.0f}% sec"
        if hint == "humide":
            return f"sol {value:.0f}% hum"
        return f"sol {value:.0f}%"
    if k == "air":
        hint = value_hint(k, value)
        if hint == "air charge":
            return f"air {value:.0f} charge"
        if hint == "air pur":
            return f"air {value:.0f} pur"
        return f"air {value:.0f}"
    if k == "press":
        return f"{value:.0f} hPa"
    if k == "probe":
        return f"sonde {value:.1f}°C"
    if k == "rain":
        return f"pluie {format_live(k, value).lower()}"
    if k in {"gas", "co"}:
        return f"{k} {value:.0f}"
    return None


def format_terminal_line(values: dict[str, float]) -> str:
    """Ligne terminal compacte : tout visible d'un coup d'oeil."""
    ordered = sorted(
        values.keys(),
        key=lambda k: DISPLAY_ORDER.index(k) if k in DISPLAY_ORDER else 99,
    )
    parts: list[str] = []
    alerts: list[str] = []

    for key in ordered:
        if key == "unlock":
            continue
        value = values[key]
        if key.endswith("_alert"):
            if value >= 1:
                alerts.append(_ALERT_SHORT.get(key, key.replace("_alert", "")))
            continue
        chunk = _terminal_measure(key, value)
        if chunk:
            parts.append(chunk)

    line = " · ".join(parts)
    if alerts:
        flags = " ".join(f"!{a}" for a in alerts)
        line = f"{line} · {flags}" if line else flags
    return line


def format_forecast(key: str, value: float, unit: str) -> str:
    k = key.lower()
    if k == "rain":
        if value >= 70:
            return "+++"
        if value >= 35:
            return "++"
        if value >= 10:
            return "+"
        return "—"
    if unit == "°C":
        return f"{value:.0f}°"
    if unit == "%":
        return f"{value:.0f}%"
    if unit:
        return f"{value:.0f}{unit}"
    return f"{value:.0f}"


def is_climate_key(key: str) -> bool:
    k = key.lower()
    return k in {"temp", "hum", "soil", "rain", "press", "probe"}


def prediction_kind(key: str) -> str:
    k = key.lower()
    if k == "temp" or k == "probe":
        return "temp"
    if k in {"hum", "soil", "rain"}:
        return "percent"
    return "generic"
