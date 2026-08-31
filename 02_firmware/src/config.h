/* ============================================================
 *  HidroSopó — Configuración del nodo
 *  Edita este archivo. No toques main.cpp salvo que sepas qué haces.
 * ============================================================ */
#ifndef CONFIG_H
#define CONFIG_H

// ---------- IDENTIDAD DEL NODO ----------
#define NODO_ID       "NODO-SUELO-01"
#define NODO_TOKEN    "cambiar_por_token_del_backend"

// ---------- TRANSPORTE ----------
#define TRANSPORTE_LORA  1
#define TRANSPORTE_WIFI  2
#define TRANSPORTE       TRANSPORTE_LORA   // <<< cambia aquí

// ---------- WiFi (solo si TRANSPORTE == TRANSPORTE_WIFI) ----------
#define WIFI_SSID        "RedDeLaFinca"
#define WIFI_PASS        "clave"
#define BACKEND_URL      "https://tu-backend.onrender.com/api/v1/telemetria"
#define TIMEOUT_WIFI_MS  20000

// ---------- LoRa ----------
// 915 MHz = banda ISM Región 2 (Américas). Verifica el cuadro de
// atribución de la ANE antes de operar en campo.
#define LORA_FREQ           915.0    // MHz
#define LORA_BW             125.0    // kHz
#define LORA_SF             9        // 7=rápido/corto, 12=lento/largo
#define LORA_CR             5        // coding rate 4/5
#define LORA_POTENCIA_DBM   20       // máx 22 en SX1262
#define TIMEOUT_ACK_MS      3000

// ---------- PINES (Heltec WiFi LoRa 32 V3 / ESP32-S3) ----------
#define PIN_HUM_1            1    // ADC1 - obligatorio ADC1 si el WiFi puede activarse
#define PIN_HUM_2            2
#define PIN_HUM_3            3
#define PIN_ONEWIRE          4    // DS18B20 (pull-up 4.7k a 3V3)
#define PIN_LLUVIA           5    // RTC_GPIO para wake desde deep sleep
#define PIN_MOSFET_SENSORES  6
#define PIN_BATERIA          7    // divisor 2:1
#define PIN_I2C_SDA          41
#define PIN_I2C_SCL          42

// SX1262 del Heltec V3 (no cambiar)
#define PIN_LORA_CS          8
#define PIN_LORA_DIO1        14
#define PIN_LORA_RST         12
#define PIN_LORA_BUSY        13

#define SHT31_ADDR           0x44

// ---------- TIEMPOS ----------
#define INTERVALO_MIN         15    // minutos entre mediciones
#define T_ESTABILIZACION_MS   1500  // los capacitivos necesitan ~1.5 s
#define DEBOUNCE_LLUVIA_MS    150
#define MAX_REINTENTOS        3

// ---------- PLUVIÓMETRO ----------
// Valor del cangilón. VERIFÍCALO: vierte 100 ml con jeringa y cuenta pulsos.
#define MM_POR_PULSO          0.28f

// ---------- CALIBRACIÓN ----------
#define CAL_BATERIA           1.000f   // ajusta comparando con multímetro
#define V_BATERIA_CRITICA     3.30f    // por debajo: modo ahorro extremo

// ---------- BUFFER ----------
#define MAX_BUFFER            120     // ~30 h de datos a 15 min

#endif
