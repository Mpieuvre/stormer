"""Configuration globale de l'application Stormer."""

APP_NAME = "Stormer"
APP_VERSION = "1.0.0"
DEFAULT_BAUDRATE = 9600
SERIAL_TIMEOUT = 0.1
MAX_TERMINAL_LINES = 5000
PREDICTION_HOURS = 6
MEASURE_INTERVAL_SEC = 2

# Mots-cles pour detecter automatiquement une carte Arduino
ARDUINO_VID_PIDS = {
    (0x2341, 0x0043),
    (0x2341, 0x0001),
    (0x2341, 0x0243),
    (0x2A03, 0x0043),
    (0x2341, 0x0010),
    (0x2341, 0x0042),
    (0x2341, 0x8036),
    (0x2341, 0x8037),
    (0x1A86, 0x7523),
    (0x1A86, 0x5523),
    (0x10C4, 0xEA60),
    (0x0403, 0x6001),
}
