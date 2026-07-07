/*
 * Stormer — Arduino Uno R3
 * Capteur : DHT11 (température + humidité)
 * Affichage : écran LCD 16x2 I2C (PCF8574)
 *
 * ── BRANCHEMENT ──────────────────────────────────────────
 *
 *  Alimentation : tout en 5V (broche 5V de l'Uno, PAS la broche 3.3V)
 *
 *  DHT11 (broche DATA)  →  Pin 2  (D2)
 *  DHT11 VCC            →  5V
 *  DHT11 GND            →  GND
 *
 *  Écran I2C SDA        →  A4  (SDA — fil I2C obligatoire sur Uno)
 *  Écran I2C SCL        →  A5  (SCL — fil I2C obligatoire sur Uno)
 *  Écran VCC            →  5V
 *  Écran GND            →  GND
 *
 * ── LIBRAIRIES ARDUINO IDE ───────────────────────────────
 *  Outils → Gérer les bibliothèques → installer :
 *    • "DHT sensor library"        (Adafruit)
 *    • "Adafruit Unified Sensor"   (dépendance Adafruit)
 *    • "LiquidCrystal I2C"         (Frank de Brabander ou fmalpartida)
 *
 * ── FORMAT ENVOYÉ AU PC (Stormer) ────────────────────────
 *  temp:23.5,hum:45.0
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

// ── Configuration ─────────────────────────────────────────
#define DHT_PIN      2
#define DHT_TYPE     DHT11

#define LCD_COLS     16
#define LCD_ROWS     2
#define LCD_ADDR     0x27       // Essayer 0x3F si l'écran reste vide
#define INTERVAL_MS  2000       // DHT11 : min ~1 s entre deux lectures

#define USE_LCD_BEGIN   // Commentez si erreur "no member begin"

// ── Objets ────────────────────────────────────────────────
DHT dht(DHT_PIN, DHT_TYPE);
LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);

unsigned long lastRead = 0;
bool lcdOk = false;

struct BootStep {
  const char *title;
  const char *subtitle;
  byte progress;      // 0-100
  unsigned int ms;    // durée de l'étape
};

// ── LCD helpers ───────────────────────────────────────────
void startLcd() {
#ifdef USE_LCD_BEGIN
  lcd.begin();
#else
  lcd.init();
#endif
  lcd.backlight();
}

void lcdLine(byte row, const char *text) {
  lcd.setCursor(0, row);
  lcd.print(text);
  byte len = 0;
  while (text[len] != '\0') len++;
  for (byte i = len; i < LCD_COLS; i++) {
    lcd.print(' ');
  }
}

void showProgressBar(byte row, byte percent) {
  lcd.setCursor(0, row);
  lcd.print('[');
  byte filled = map(percent, 0, 100, 0, 10);
  for (byte i = 0; i < 10; i++) {
    lcd.print(i < filled ? '#' : '-');
  }
  lcd.print(']');
}

void runStartupAnimation() {
  const BootStep steps[] = {
    {"  >> STORMER <<", "Demarrage...",      10,  500},
    {"Calibration",     "Capteur DHT11",     25,  700},
    {"Init capteurs",   "Lecture test...",   40,  800},
    {"Liaison serie",   "Port COM actif",    55,  600},
    {"Televersement",   "Envoi data PC",     70,  700},
    {"App Stormer",     "Ouverture...",      85,  700},
    {"   PRET !",        "Acquisition ON",   100, 900},
  };
  const byte stepCount = sizeof(steps) / sizeof(steps[0]);

  lcd.clear();

  for (byte s = 0; s < stepCount; s++) {
    lcdLine(0, steps[s].title);
    lcdLine(1, steps[s].subtitle);
    delay(180);

    unsigned int elapsed = 180;
    int startProg = (int)steps[s].progress - 15;
    if (startProg < 0) startProg = 0;

    while (elapsed < steps[s].ms) {
      showProgressBar(1, map(elapsed, 0, steps[s].ms, startProg, steps[s].progress));
      delay(80);
      elapsed += 80;
    }

    showProgressBar(1, steps[s].progress);
    delay(120);
  }

  // Flash final
  for (byte i = 0; i < 2; i++) {
    lcdLine(0, "   STORMER OK  ");
    lcdLine(1, "================");
    delay(200);
    lcdLine(0, "  Acquisition  ");
    lcdLine(1, "   en cours    ");
    delay(200);
  }

  lcd.clear();
}

// ── Setup ─────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);
  dht.begin();

  Wire.begin();
  startLcd();
  lcdOk = true;

  runStartupAnimation();

  // Test rapide DHT11 pendant l'anim (lecture silencieuse)
  dht.readHumidity();
  dht.readTemperature();

  Serial.println("# Stormer Uno R3 — DHT11 pret");
}

// ── Loop ──────────────────────────────────────────────────
void loop() {
  if (millis() - lastRead < INTERVAL_MS) {
    return;
  }
  lastRead = millis();

  float humidity    = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("# ERREUR: lecture DHT11 echouee");
    if (lcdOk) {
      lcd.clear();
      lcdLine(0, "DHT11 ERREUR");
      lcdLine(1, "Verif. cablage");
    }
    return;
  }

  if (lcdOk) {
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(temperature, 1);
    lcd.print(" C  H:");
    lcd.print(humidity, 0);
    lcd.print("% ");
    lcd.print("    ");

    lcd.setCursor(0, 1);
    lcd.print("Brut T=");
    lcd.print(temperature, 1);
    lcd.print(" H=");
    lcd.print(humidity, 0);
    lcd.print("   ");
  }

  Serial.print("temp:");
  Serial.print(temperature, 1);
  Serial.print(",hum:");
  Serial.println(humidity, 1);
}

// ── Debug I2C (appel manuel si besoin) ────────────────────
void scanI2C() {
  Serial.println("# Scan I2C — adresses detectees :");
  byte count = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("#   0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      count++;
    }
  }
  if (count == 0) {
    Serial.println("#   (aucune — verifier SDA=A4, SCL=A5)");
  }
}
