/* ============================================================
 *  HidroSopó — Firmware del nodo sensor
 *  Placa: Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)
 *  Autor: Jose Alejandro Pulido Gómez — Uniagustiniana
 *  Licencia: MIT
 *
 *  Funciones:
 *   - Lee 3 sensores de humedad capacitivos, 2 DS18B20, SHT31 y pluviómetro
 *   - Alimenta los sensores por MOSFET solo durante la medición
 *   - Deep sleep entre ciclos; despierta por timer o por pulso de lluvia
 *   - Transmite por LoRa 915 MHz o por WiFi/HTTPS según configuración
 *   - Guarda en NVS los pulsos de lluvia para no perderlos entre reinicios
 * ============================================================ */

#include <Arduino.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_SHT31.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include "config.h"

#if TRANSPORTE == TRANSPORTE_LORA
  #include <RadioLib.h>
  SX1262 radio = new Module(PIN_LORA_CS, PIN_LORA_DIO1, PIN_LORA_RST, PIN_LORA_BUSY);
#else
  #include <WiFi.h>
  #include <HTTPClient.h>
  #include <WiFiClientSecure.h>
#endif

// ---------- Objetos globales ----------
OneWire oneWire(PIN_ONEWIRE);
DallasTemperature dsSensors(&oneWire);
Adafruit_SHT31 sht31 = Adafruit_SHT31();
Preferences prefs;

// ---------- Estado persistente en memoria RTC ----------
RTC_DATA_ATTR uint32_t contadorCiclos     = 0;
RTC_DATA_ATTR uint32_t pulsosLluvia       = 0;
RTC_DATA_ATTR uint32_t ultimoPulsoMs      = 0;
RTC_DATA_ATTR bool     primerArranque     = true;

// ============================================================
//  Utilidades
// ============================================================

void encenderSensores() {
  pinMode(PIN_MOSFET_SENSORES, OUTPUT);
  digitalWrite(PIN_MOSFET_SENSORES, HIGH);
  delay(T_ESTABILIZACION_MS);   // los capacitivos necesitan ~1.5 s
}

void apagarSensores() {
  digitalWrite(PIN_MOSFET_SENSORES, LOW);
}

/* Lee un ADC promediando N muestras y descartando los extremos.
   La mediana recortada evita que un pico de ruido arruine la lectura. */
uint16_t leerADCFiltrado(uint8_t pin, uint8_t n = 21) {
  uint16_t v[41];
  if (n > 41) n = 41;
  for (uint8_t i = 0; i < n; i++) { v[i] = analogRead(pin); delay(6); }
  // ordenamiento burbuja: n es pequeño, no vale la pena algo mejor
  for (uint8_t i = 0; i < n - 1; i++)
    for (uint8_t j = 0; j < n - 1 - i; j++)
      if (v[j] > v[j + 1]) { uint16_t t = v[j]; v[j] = v[j + 1]; v[j + 1] = t; }
  // promedio del 60% central
  uint8_t desde = n / 5, hasta = n - n / 5;
  uint32_t suma = 0;
  for (uint8_t i = desde; i < hasta; i++) suma += v[i];
  return suma / (hasta - desde);
}

float leerVoltajeBateria() {
  uint16_t raw = leerADCFiltrado(PIN_BATERIA, 11);
  // divisor 2:1, referencia 3.3 V, ADC de 12 bits
  return (raw / 4095.0f) * 3.3f * 2.0f * CAL_BATERIA;
}

/* ISR del pluviómetro. Antirrebote por tiempo: el reed switch
   rebota entre 20 y 80 ms; 150 ms es un margen seguro. */
void IRAM_ATTR isrLluvia() {
  uint32_t ahora = millis();
  if (ahora - ultimoPulsoMs > DEBOUNCE_LLUVIA_MS) {
    pulsosLluvia++;
    ultimoPulsoMs = ahora;
  }
}

// ============================================================
//  Lectura de sensores
// ============================================================

struct Medicion {
  uint16_t humedad_adc[3];
  float    temp_suelo[2];
  float    temp_aire;
  float    hum_aire;
  float    lluvia_mm;
  float    v_bateria;
  int16_t  rssi_ultimo;
  uint32_t ciclo;
};

Medicion tomarMedicion() {
  Medicion m = {};
  m.ciclo = contadorCiclos;

  encenderSensores();

  // --- Humedad de suelo (ADC1: obligatorio si el WiFi puede activarse) ---
  m.humedad_adc[0] = leerADCFiltrado(PIN_HUM_1);
  m.humedad_adc[1] = leerADCFiltrado(PIN_HUM_2);
  m.humedad_adc[2] = leerADCFiltrado(PIN_HUM_3);

  // --- Temperatura de suelo (DS18B20) ---
  dsSensors.begin();
  dsSensors.setResolution(12);
  dsSensors.requestTemperatures();
  m.temp_suelo[0] = dsSensors.getTempCByIndex(0);
  m.temp_suelo[1] = dsSensors.getTempCByIndex(1);
  // -127 = sensor desconectado
  if (m.temp_suelo[0] < -100) m.temp_suelo[0] = NAN;
  if (m.temp_suelo[1] < -100) m.temp_suelo[1] = NAN;

  // --- Temperatura y humedad del aire (SHT31) ---
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  if (sht31.begin(SHT31_ADDR)) {
    m.temp_aire = sht31.readTemperature();
    m.hum_aire  = sht31.readHumidity();
  } else {
    m.temp_aire = NAN;
    m.hum_aire  = NAN;
    Serial.println(F("[WARN] SHT31 no responde"));
  }

  apagarSensores();

  // --- Lluvia acumulada desde el último envío ---
  m.lluvia_mm = pulsosLluvia * MM_POR_PULSO;

  // --- Batería ---
  m.v_bateria = leerVoltajeBateria();

  return m;
}

// ============================================================
//  Serialización
// ============================================================

String construirPayload(const Medicion &m) {
  StaticJsonDocument<512> doc;
  doc["id"]  = NODO_ID;
  doc["tok"] = NODO_TOKEN;
  doc["c"]   = m.ciclo;

  JsonArray h = doc.createNestedArray("h");   // humedad ADC crudo
  for (int i = 0; i < 3; i++) h.add(m.humedad_adc[i]);

  JsonArray ts = doc.createNestedArray("ts"); // temp suelo
  for (int i = 0; i < 2; i++) ts.add(isnan(m.temp_suelo[i]) ? -999 : roundf(m.temp_suelo[i] * 10) / 10);

  doc["ta"]  = isnan(m.temp_aire) ? -999 : roundf(m.temp_aire * 10) / 10;
  doc["ha"]  = isnan(m.hum_aire)  ? -999 : roundf(m.hum_aire  * 10) / 10;
  doc["ll"]  = roundf(m.lluvia_mm * 100) / 100;
  doc["vb"]  = roundf(m.v_bateria * 100) / 100;

  String out;
  serializeJson(doc, out);
  return out;
}

// ============================================================
//  Transporte
// ============================================================

#if TRANSPORTE == TRANSPORTE_LORA

bool inicializarRadio() {
  int estado = radio.begin(LORA_FREQ, LORA_BW, LORA_SF, LORA_CR,
                           RADIOLIB_SX126X_SYNC_WORD_PRIVATE, LORA_POTENCIA_DBM);
  if (estado != RADIOLIB_ERR_NONE) {
    Serial.printf("[ERROR] LoRa init falló: %d\n", estado);
    return false;
  }
  radio.setCurrentLimit(140);
  return true;
}

bool enviar(const String &payload) {
  if (!inicializarRadio()) return false;

  for (uint8_t intento = 0; intento < MAX_REINTENTOS; intento++) {
    int estado = radio.transmit(payload);
    if (estado == RADIOLIB_ERR_NONE) {
      Serial.printf("[OK] LoRa TX (%d bytes)\n", payload.length());

      // Espera ACK del gateway. Si no llega, reintenta.
      String ack;
      radio.setDio1Action(nullptr);
      int rx = radio.receive(ack, 0, TIMEOUT_ACK_MS * 1000UL);
      if (rx == RADIOLIB_ERR_NONE && ack.indexOf("OK") >= 0) {
        Serial.println(F("[OK] ACK recibido"));
        radio.sleep();
        return true;
      }
      Serial.println(F("[WARN] sin ACK, reintentando"));
    } else {
      Serial.printf("[ERROR] TX falló: %d\n", estado);
    }
    // backoff exponencial con jitter, evita colisiones entre nodos
    delay((1 << intento) * 500 + random(0, 400));
  }
  radio.sleep();
  return false;
}

#else  // ---------- WiFi ----------

bool conectarWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < TIMEOUT_WIFI_MS) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();
  return WiFi.status() == WL_CONNECTED;
}

bool enviar(const String &payload) {
  if (!conectarWiFi()) {
    Serial.println(F("[ERROR] WiFi no conectó"));
    return false;
  }

  WiFiClientSecure cliente;
  cliente.setInsecure();   // para el piloto. En producción: cargar el certificado raíz.
  HTTPClient http;

  for (uint8_t intento = 0; intento < MAX_REINTENTOS; intento++) {
    http.begin(cliente, BACKEND_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(15000);
    int codigo = http.POST(payload);
    Serial.printf("[HTTP] %d\n", codigo);
    http.end();
    if (codigo >= 200 && codigo < 300) {
      WiFi.disconnect(true);
      return true;
    }
    // Render free tier tarda ~30 s en despertar: por eso el reintento largo
    delay((1 << intento) * 3000);
  }
  WiFi.disconnect(true);
  return false;
}

#endif

// ============================================================
//  Buffer persistente (para cuando el envío falla)
// ============================================================

void guardarEnBuffer(const String &payload) {
  prefs.begin("buffer", false);
  uint16_t n = prefs.getUShort("n", 0);
  if (n < MAX_BUFFER) {
    prefs.putString(String(n).c_str(), payload);
    prefs.putUShort("n", n + 1);
    Serial.printf("[BUF] guardado, %d pendientes\n", n + 1);
  } else {
    Serial.println(F("[BUF] lleno, se descarta el más antiguo"));
    // rotación simple: corre todo un lugar
    for (uint16_t i = 1; i < MAX_BUFFER; i++)
      prefs.putString(String(i - 1).c_str(), prefs.getString(String(i).c_str(), ""));
    prefs.putString(String(MAX_BUFFER - 1).c_str(), payload);
  }
  prefs.end();
}

void vaciarBuffer() {
  prefs.begin("buffer", false);
  uint16_t n = prefs.getUShort("n", 0);
  if (n == 0) { prefs.end(); return; }

  Serial.printf("[BUF] intentando enviar %d pendientes\n", n);
  uint16_t enviados = 0;
  for (uint16_t i = 0; i < n; i++) {
    String p = prefs.getString(String(i).c_str(), "");
    if (p.length() == 0) { enviados++; continue; }
    if (enviar(p)) { enviados++; delay(300); }
    else break;   // si falla uno, no insistas: se acabó la ventana
  }

  if (enviados == n) {
    prefs.clear();
    Serial.println(F("[BUF] vaciado completo"));
  } else {
    // compacta lo que queda al inicio
    uint16_t k = 0;
    for (uint16_t i = enviados; i < n; i++)
      prefs.putString(String(k++).c_str(), prefs.getString(String(i).c_str(), ""));
    prefs.putUShort("n", k);
    Serial.printf("[BUF] quedan %d pendientes\n", k);
  }
  prefs.end();
}

// ============================================================
//  Ciclo principal
// ============================================================

void irADormir() {
  Serial.println(F("[SLEEP] durmiendo..."));
  Serial.flush();

  // Despertar por timer
  esp_sleep_enable_timer_wakeup((uint64_t)INTERVALO_MIN * 60ULL * 1000000ULL);

  // Despertar por pulso del pluviómetro (flanco de bajada del reed)
  esp_sleep_enable_ext0_wakeup((gpio_num_t)PIN_LLUVIA, 0);

  apagarSensores();
  esp_deep_sleep_start();
}

void setup() {
  Serial.begin(115200);
  delay(80);

  esp_sleep_wakeup_cause_t causa = esp_sleep_get_wakeup_cause();

  // --- Si despertó por lluvia: cuenta el pulso y vuelve a dormir ---
  if (causa == ESP_SLEEP_WAKEUP_EXT0) {
    pulsosLluvia++;
    Serial.printf("[LLUVIA] pulso #%u (%.2f mm acumulados)\n",
                  pulsosLluvia, pulsosLluvia * MM_POR_PULSO);
    delay(DEBOUNCE_LLUVIA_MS);   // deja pasar el rebote antes de re-armar
    irADormir();
  }

  if (primerArranque) {
    Serial.println(F("\n=============================="));
    Serial.println(F(" HidroSopo - Nodo sensor"));
    Serial.printf(" ID: %s\n", NODO_ID);
    Serial.println(F("=============================="));
    primerArranque = false;
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);   // rango 0-3.3 V
  }

  pinMode(PIN_LLUVIA, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_LLUVIA), isrLluvia, FALLING);

  contadorCiclos++;

  Medicion m = tomarMedicion();

  Serial.printf("[MED] H:%u/%u/%u  Ts:%.1f/%.1f  Ta:%.1f  Ha:%.1f  Ll:%.2fmm  Bat:%.2fV\n",
                m.humedad_adc[0], m.humedad_adc[1], m.humedad_adc[2],
                m.temp_suelo[0], m.temp_suelo[1],
                m.temp_aire, m.hum_aire, m.lluvia_mm, m.v_bateria);

  // Protección de batería: si está muy baja, duerme largo y no transmite
  if (m.v_bateria < V_BATERIA_CRITICA && m.v_bateria > 1.0f) {
    Serial.println(F("[BAT] critica - modo ahorro extremo"));
    esp_sleep_enable_timer_wakeup(6ULL * 3600ULL * 1000000ULL);   // 6 horas
    apagarSensores();
    esp_deep_sleep_start();
  }

  String payload = construirPayload(m);
  Serial.println(payload);

  if (enviar(payload)) {
    pulsosLluvia = 0;    // solo se resetea si el dato quedó entregado
    vaciarBuffer();
  } else {
    guardarEnBuffer(payload);
    pulsosLluvia = 0;    // ya quedó registrado dentro del payload en buffer
  }

  irADormir();
}

void loop() {
  // No se usa: el nodo vive en deep sleep y todo pasa en setup()
}
