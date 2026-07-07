"""Profil materiel Stormer — sauvegarde et chargement."""



from __future__ import annotations



import json

import secrets

from dataclasses import asdict, dataclass, field



from stormer.paths import config_path as _config_path



CONFIG_PATH = _config_path()



# ── Cartes Arduino supportees ───────────────────────────────

BOARDS = {

    "uno": "Arduino Uno R3",

    "nano": "Arduino Nano (ATmega328)",

    "mega": "Arduino Mega 2560",

    "leonardo": "Arduino Leonardo",

    "micro": "Arduino Micro",

    "pro_mini": "Arduino Pro Mini 5V",

    "due": "Arduino Due",

    "esp32": "ESP32 DevKit (WiFi/BLE)",

}



# ── Capteurs supportes ──────────────────────────────────────

SENSORS = {

    "dht11": "DHT11 — temperature + humidite",

    "dht22": "DHT22 / AM2302 — plus precis",

    "bme280": "BME280 — temp. + humidite + pression (I2C)",

    "ds18b20": "DS18B20 — sonde temperature (1-Wire)",

    "air_quality": "MQ135 — qualite de l'air",

    "gas_mq2": "MQ2 — gaz inflammables / fumee",

    "gas_mq5": "MQ5 — gaz naturel / GPL",

    "gas_mq7": "MQ7 — monoxyde de carbone (CO)",

    "hygro_soil": "Module hygrometre sol (FC-28 / YL-69)",

    "rain_sensor": "Module detecteur de pluie (FC-37 / YD-R804)",

}



# ── Ecrans ──────────────────────────────────────────────────

DISPLAYS = {

    "none": "Aucun ecran",

    "lcd_i2c_16x2": "LCD 16x2 I2C (PCF8574)",

    "lcd_i2c_20x4": "LCD 20x4 I2C",

    "oled_i2c_128x64": "OLED 128x64 I2C (SSD1306)",

    "oled_i2c_128x32": "OLED 128x32 I2C",

    "tft_ili9341": "Ecran TFT ILI9341 (SPI)",

}



# ── Modules sans fil / communication ────────────────────────

WIRELESS = {

    "none": "Aucun",

    "rf433_tx": "Emetteur 433 MHz (DATA)",

    "rf433_rx": "Recepteur 433 MHz (DATA)",

    "cc1101": "CC1101 433 MHz (SPI)",

    "nrf24l01": "NRF24L01 2.4 GHz (SPI)",

    "hc12": "Module HC-12 433 MHz (Serial)",

    "hc05": "Bluetooth HC-05 / HC-06 (Serial)",

    "esp8266_shield": "Shield ESP8266 (Serial)",

}



# ── Acces / deverrouillage RFID ─────────────────────────────

ACCESS = {

    "none": "Aucun — systeme toujours debloque",

    "mfrc522": "Lecteur RFID RC522 (SPI) — puce autorisee requise",

    "pn532": "Lecteur NFC PN532 (I2C) — puce autorisee requise",

}



# ── Sorties LED ─────────────────────────────────────────────

OUTPUTS = {

    "none": "Aucune LED",

    "status_3": "3 LED status (vert / orange / rouge)",

    "rgb_1": "LED RGB 3 couleurs (R / G / B)",

    "neopixel_8": "Ruban NeoPixel 8 LED (WS2812)",

}



# Capteurs exclusifs DHT (un seul actif)

_DHT_KEYS = {"dht11", "dht22"}





def generate_rfid_uid() -> str:

    """UID RFID pre-genere (4 octets hex)."""

    return ":".join(f"{secrets.randbelow(256):02X}" for _ in range(4))





def uid_to_bytes(uid: str) -> list[int]:

    parts = [p.strip() for p in uid.replace("-", ":").split(":") if p.strip()]

    if len(parts) != 4:

        return [0xA1, 0xB2, 0xC3, 0xD4]

    return [int(p, 16) for p in parts]





@dataclass

class HardwareProfile:

    board: str = "uno"

    sensors: list[str] = field(default_factory=lambda: ["dht11"])

    display: str = "lcd_i2c_16x2"

    wireless: str = "none"

    access: str = "none"

    output: str = "none"

    rfid_uid: str = ""

    setup_complete: bool = False



    def board_label(self) -> str:

        return BOARDS.get(self.board, self.board)



    def sensor_labels(self) -> list[str]:

        return [SENSORS.get(s, s) for s in self.sensors]



    def display_label(self) -> str:

        return DISPLAYS.get(self.display, self.display)



    def wireless_label(self) -> str:

        return WIRELESS.get(self.wireless, self.wireless)



    def access_label(self) -> str:

        return ACCESS.get(self.access, self.access)



    def output_label(self) -> str:

        return OUTPUTS.get(self.output, self.output)



    def requires_rfid_unlock(self) -> bool:

        return self.access in ("mfrc522", "pn532")



    def normalized_sensors(self) -> list[str]:

        """Un seul DHT : DHT22 prioritaire."""

        s = list(self.sensors)

        if "dht11" in s and "dht22" in s:

            s.remove("dht11")

        return s



    def ensure_rfid_uid(self) -> None:

        if self.requires_rfid_unlock() and not self.rfid_uid:

            self.rfid_uid = generate_rfid_uid()





def load_profile() -> HardwareProfile:

    if not CONFIG_PATH.exists():

        return HardwareProfile()

    try:

        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

        allowed = HardwareProfile.__dataclass_fields__

        profile = HardwareProfile(**{k: v for k, v in data.items() if k in allowed})

        # Migration anciennes configs

        if profile.display == "lcd_i2c":

            profile.display = "lcd_i2c_16x2"

        if profile.display == "oled_i2c":

            profile.display = "oled_i2c_128x64"

        if profile.sensors and "gas" in profile.sensors:

            profile.sensors = [("gas_mq2" if x == "gas" else x) for x in profile.sensors]

        if profile.wireless == "rf433":

            profile.wireless = "rf433_tx"

        profile.ensure_rfid_uid()

        return profile

    except (json.JSONDecodeError, TypeError):

        return HardwareProfile()





def save_profile(profile: HardwareProfile) -> None:

    profile.ensure_rfid_uid()

    profile.setup_complete = True

    CONFIG_PATH.write_text(

        json.dumps(asdict(profile), indent=2, ensure_ascii=False), encoding="utf-8"

    )





def is_first_run() -> bool:

    return not load_profile().setup_complete

