#include <Servo.h>

// Pins
#define TRIGGER_PIN 2
#define ECHO_PIN 3
#define RED_LED_PIN 4
#define BLUE_LED_PIN 5
#define SERVO_PIN 6
#define BUZZER_PIN 11

// Gate positions
#define GATE_CLOSED_POS 0
#define GATE_OPEN_POS 180

// Alert types
enum AlertType {
  NONE,
  PAYMENT_PENDING,
  TAMPERING
};

AlertType currentAlert = NONE;

// Timing variables
unsigned long alertStartTime = 0;
unsigned long lastBlinkTime = 0;
unsigned long lastBeepTime = 0;
unsigned long lastDistanceSendTime = 0;

// Alert timing configs
#define BLINK_INTERVAL_PAYMENT 300
#define BEEP_INTERVAL_PAYMENT 1000
#define BEEP_DURATION_PAYMENT 200

#define BLINK_INTERVAL_TAMPER 150
#define BEEP_INTERVAL_TAMPER 700
#define BEEP_DURATION_TAMPER 150

#define DISTANCE_SEND_INTERVAL 200

// Objects
Servo barrierServo;
bool isGateOpen = false;

void setup() {
  Serial.begin(9600);
  
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(BLUE_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  barrierServo.attach(SERVO_PIN);
  closeGateAction();

  digitalWrite(BUZZER_PIN, LOW);

  Serial.println("MSG:Gate Controller Ready.");
  Serial.println("MSG:Commands: '0'-Close, '1'-Open, '2'-PaymentAlert, '3'-TamperAlert, 'S'-StopAlert, 'B'-Test Buzzer");
}

void loop() {
  handleSerialCommands();
  handleAlerts();
  sendDistanceData();
}

void handleSerialCommands() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    Serial.print("MSG:Received command: ");
    Serial.println(cmd);

    switch (cmd) {
      case '0':
        stopAlertAction();
        closeGateAction();
        break;

      case '1':
        stopAlertAction();
        openGateAction();
        break;

      case '2':
        startAlert(PAYMENT_PENDING);
        break;

      case '3':
        startAlert(TAMPERING);
        break;

      case 'S':
        stopAlertAction();
        updateLEDState();
        break;

      case 'B':
        testBuzzer();
        break;

      default:
        Serial.println("MSG:Unknown command.");
        break;
    }
  }
}

void openGateAction() {
  barrierServo.write(GATE_OPEN_POS);
  isGateOpen = true;
  updateLEDState();
  Serial.println("MSG:Gate Opened");
}

void closeGateAction() {
  barrierServo.write(GATE_CLOSED_POS);
  isGateOpen = false;
  updateLEDState();
  Serial.println("MSG:Gate Closed");
}

void updateLEDState() {
  if (currentAlert == NONE) {
    if (isGateOpen) {
      digitalWrite(BLUE_LED_PIN, HIGH);
      digitalWrite(RED_LED_PIN, LOW);
    } else {
      digitalWrite(RED_LED_PIN, HIGH);
      digitalWrite(BLUE_LED_PIN, LOW);
    }
  }
}

void startAlert(AlertType type) {
  currentAlert = type;
  alertStartTime = millis();
  lastBlinkTime = millis();
  lastBeepTime = millis();

  Serial.print("MSG:ALERT STARTED: ");
  if (type == PAYMENT_PENDING) Serial.println("Payment Pending");
  if (type == TAMPERING) Serial.println("Tampering Detected");
}

void stopAlertAction() {
  if (currentAlert != NONE) {
    currentAlert = NONE;
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(BLUE_LED_PIN, LOW);
    Serial.println("MSG:Alert Stopped.");
  }
}

void handleAlerts() {
  if (currentAlert == NONE) return;

  unsigned long currentTime = millis();

  int blinkInterval, beepInterval, beepDuration;
  if (currentAlert == PAYMENT_PENDING) {
    blinkInterval = BLINK_INTERVAL_PAYMENT;
    beepInterval = BEEP_INTERVAL_PAYMENT;
    beepDuration = BEEP_DURATION_PAYMENT;
  } else {
    blinkInterval = BLINK_INTERVAL_TAMPER;
    beepInterval = BEEP_INTERVAL_TAMPER;
    beepDuration = BEEP_DURATION_TAMPER;
  }

  // Blink red LED
  if (currentTime - lastBlinkTime >= blinkInterval) {
    lastBlinkTime = currentTime;
    digitalWrite(RED_LED_PIN, !digitalRead(RED_LED_PIN));
    digitalWrite(BLUE_LED_PIN, LOW); // turn off blue during alert
  }

  // Beep buzzer (blocking delay to ensure audible beep)
  if (currentTime - lastBeepTime >= beepInterval) {
    lastBeepTime = currentTime;
    digitalWrite(BUZZER_PIN, HIGH);
    delay(beepDuration);
    digitalWrite(BUZZER_PIN, LOW);
  }
}

void testBuzzer() {
  Serial.println("MSG:Testing Buzzer...");
  digitalWrite(BUZZER_PIN, HIGH);
  delay(500); // 500ms beep
  digitalWrite(BUZZER_PIN, LOW);
}

float getDistanceCm() {
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 25000); // 25ms timeout (~4m)
  if (duration == 0) return 999.99; // No echo

  float distance_cm = (duration * 0.0343) / 2.0;
  return distance_cm;
}

void sendDistanceData() {
  if (millis() - lastDistanceSendTime >= DISTANCE_SEND_INTERVAL) {
    lastDistanceSendTime = millis();
    float distance = getDistanceCm();
    Serial.print("DIST:");
    Serial.println(distance, 2);
  }
}
