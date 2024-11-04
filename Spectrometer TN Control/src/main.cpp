#include <ModbusSerial.h>
#include <Arduino.h>

const int TxenPin = -1; // -1 disables the feature, change that if you are using an RS485 driver, this pin would be connected to the DE and /RE pins of the driver.

const byte SlaveId = 10;
// Modbus Registers Offsets (0-9999)
// const int Lamp1Coil = 0;
const int TTLCoil = 16;
const int testCoil = 19;
const int depressuriseCoil = 18;
const int resetCoil = 17;

const int SWITCH = 0; const int IN = 1; const int OUT = 2; const int VENT = 3; const int SHORT = 4;
const int LEDS[] = {32, 34, 36, 38, 40, 42, 44, 46};
const int VALVES[] = {8, 9, 10, 22, 52, 26, 28, 30};
const int test_led = 12;

const int valveCoil[] = {0, 1, 2, 3, 4, 5, 6, 7}; //coil addresses for valves

// status LEDs
const int STATUS_LEDS[] = {5, 6, 7, 11, 12, 13, 23, 50};

//default timings
const unsigned long pollTime = 500; //default time between pressure readings

//TTL Pins, T4 and T5 not working??
const int T1 = 25; const int T2 = 3; const int T3 = 4; const int T4 = 2; const int T5 = 24;

//Analog pins - pressure1 is external
const int Pressure1 = A1; const int Pressure2 = A2; const int Pressure3 = A3; const int Pressure4 = A4;

//VARIABLES
bool TTLState = 1; //TTL state
bool simpleTTL = 0; //simple TTL control, currently unreachable
bool serialConnected = 0; //serial connection state

float pressureInputs[4] = {0,0,0,0};  //container for pressure values from the analog pins

unsigned long tPoll = 0; //start time
unsigned long mbTimeout = 2000; //timeout length for no comms
unsigned long mbLast = 0; //time of last modbus command

#define MySerial Serial // define serial port used, Serial most of the time, or Serial1, Serial2 ... if available
const unsigned long Baudrate = 9600;

// ModbusSerial object
ModbusSerial mb (MySerial, SlaveId, TxenPin);

// # +--------------------------+---------+-----------------------------------------+
// # |         Coil/reg         | Address |                 Purpose                 |
// # +--------------------------+---------+-----------------------------------------+
// # | Valve coils              | 0-7     | 8 digital valve states (only 5 in use)  |
// # | Pressure Gauge Registers | 0-3     | Input registers for the pressure gauges |
// # | ,                        | ,       | Must be read with func code 4           |
// # | ,                        | ,       | Values not converted to bar             |
// # | TTL Coil                 | 16      | Used to enable/disable TTL control      |
// # | Reset Coil               | 17      | Used to reset the system from GUI       |
// # | depressurise Coil        | 18      | Used to depressurise system from GUI    |
// # +--------------------------+---------+-----------------------------------------+

void declarePins();
void initLEDs();
void addCoils();
void handleTTL();
void reset();
void setValves();
void setValve(int valve, int state);
void readPressure();
void updatePressureRegisters();
void depressurise();
float convertToBar(float pressure);
void setLED(int led, bool state);
void updateStatus();

void setup() {

    MySerial.begin (Baudrate); // works on all boards but the configuration is 8N1 which is incompatible with the MODBUS standard
    // prefer the line below instead if possible
    // MySerial.begin (Baudrate, MB_PARITY_EVEN);
    
    mb.config (Baudrate);
    mb.setAdditionalServerData("ValveController"); // for Report Server ID function (0x11)

    declarePins();
    initLEDs();
    addCoils();
    // Add Lamp1Coil register - Use addCoil() for digital outputs
    // mb.addCoil(Lamp1Coil);
    pinMode(test_led, OUTPUT);
}

void loop() {
    
    //check for timeout
    if(TTLState == false){  //only run the timer when not in TTL mode
        if(MySerial.available()>0){ //if there is serial activity and system is not in TTL mode
            //digitalWrite(test_led, HIGH);
            mbLast = millis(); //update mbLast
            serialConnected = true; //update serial connection state
        }
        else{
            //digitalWrite(test_led, LOW);
            if ((long)(millis() - mbLast) > (long)(mbTimeout)){reset(); serialConnected = false;}    //If no serial activity for longer than mbTimeout, declare disconnection
        }
    }
    

    // Call once inside loop() - all magic here
    mb.task();

    // Attach LedPin to Lamp1Coil register
    // digitalWrite (13, mb.Coil (Lamp1Coil));

    if (mb.coil(TTLCoil) == true){
        handleTTL();
        TTLState = true;
    }
    else{
        if (TTLState == true){mbLast = millis();TTLState = false;serialConnected = true;}  //If system was in TTL mode, update mbLast and TTLState

        //check for depressurise command
        if(mb.coil(depressuriseCoil) == 1){depressurise();} //check for depressurise command

        //check for reset command   
        if(mb.coil(resetCoil) == 1){reset();} //check for reset command   

        setValves(); //set valves based on coil values  
    }

    if((long)(millis() - tPoll) > (long)pollTime){ //if it's time to poll the pressure sensors
        tPoll = millis(); //update tPoll
        //read pressure sensors
        readPressure();
        updatePressureRegisters();

        //if(convertToBar(pressureInputs[2]) > 1000){depressurise();} //if pressure is too high, vent
    }

    updateStatus(); //update status LEDs
}

void declarePins(){
    //set valve pins as outputs
    for (int i = 0; i < 8; i++)
    {
        pinMode(VALVES[i], OUTPUT);
    }

    //set LED pins as outputs
    for (int i = 0; i < 8; i++)
    {
        pinMode(LEDS[i], OUTPUT);
    }

    //set status LED pins as outputs
    for (int i = 0; i < 8; i++)
    {
        pinMode(STATUS_LEDS[i], OUTPUT);
    }

    //set TTL pins as inputs
    pinMode(T1, INPUT);
    pinMode(T2, INPUT);
    pinMode(T3, INPUT);
    pinMode(T4, INPUT);
    pinMode(T5, INPUT);

    //analog pins as inputs
    pinMode(Pressure1, INPUT);
    pinMode(Pressure2, INPUT);
    pinMode(Pressure3, INPUT);
    pinMode(Pressure4, INPUT);
}

void initLEDs(){
    //set all valves to off
    for (int i = 0; i < 8; i++)
    {
        setValve(i, 0);
    }
}

void addCoils(){
    //add coils for valves
    for (int i = 0; i < 8; i++)
    {
        mb.addCoil(valveCoil[i], false);
    }

    mb.addCoil(TTLCoil, true);
    mb.addCoil(testCoil, false);
    mb.addCoil(resetCoil, 0);
    mb.addCoil(depressuriseCoil, 0);

    for (int i = 0; i < 4; i++){
        mb.addIreg(i, 0);
    }
}

void handleTTL(){
  if (simpleTTL == 1){ //simple TTL control, currently unreachable
    //set valves based on TTL inputs
    setValve(IN, digitalRead(T1));
    setValve(OUT, digitalRead(T2));
    setValve(SHORT, digitalRead(T3));
    setValve(VENT, digitalRead(T4));
    setValve(SWITCH, digitalRead(T5));
  }
  else
  {
    int combinedState = (digitalRead(T4) << 3) | (digitalRead(T3) << 2) | (digitalRead(T2) << 1) | digitalRead(T1);
    switch(combinedState){
      //TODO Add more cases as needed
      case 0:
        setValve(IN, 0);
        setValve(OUT, 0);
        setValve(SWITCH, 0);
        setValve(VENT, 0);
        setValve(SHORT, 0);
        break;
      default:
        //Serial.println("LOG: Invalid TTL input");
        break;
    }
  }
}

void setValve(int valve, int state) //sets the valve & corresponding LED to on or off
{
  digitalWrite(VALVES[valve], state); //set the valve to the desired state
  digitalWrite(LEDS[valve], state);  //set the corresponding valve LED to the same state
  //Serial.println("LOG: Valve " + String(valve+1) + " set to " + String(state));
}

void reset(){
    //default to TTL control
    TTLState = true;
    mb.setCoil(TTLCoil, true);
    mb.setCoil(resetCoil, 0);
    for (int i = 0; i < 8; i++) {
        mb.setCoil(valveCoil[i], 0);
    }
    setValve(SWITCH, 0);
    setValve(IN, 0);
    setValve(OUT, 0);
    setValve(VENT, 0);
    setValve(SHORT, 0);
}

void setValves(){
    //set valves based on coil values
    for (int i = 4; i >= 0; i--)
    {
        setValve(i, mb.coil(valveCoil[i]));
    }
}

void readPressure(){
    pressureInputs[0] = analogRead(Pressure1);
    pressureInputs[1] = analogRead(Pressure2);
    pressureInputs[2] = analogRead(Pressure3);
    pressureInputs[3] = analogRead(Pressure4);
}

void updatePressureRegisters(){
    mb.setIreg(0, pressureInputs[0]);
    mb.setIreg(1, pressureInputs[1]);
    mb.setIreg(2, pressureInputs[2]);
    mb.setIreg(3, pressureInputs[3]);
}

void depressurise(){
    //depressurise the system
    Serial.println("LOG: Depressurising system");
    if(convertToBar(analogRead(Pressure3)) > 0.1){
        setValve(SWITCH, 0);
        setValve(IN, 0);
        setValve(OUT, 1);
        setValve(VENT, 0);
        setValve(SHORT, 1);
        unsigned long startTime = millis();
        while (convertToBar(analogRead(Pressure3)) > 0.1) {
            if ((long)(millis() - startTime) > 5000) {      //timeout, break loop
                break;
            }
            delay(50);
        }
        setValve(SHORT, 0);
        setValve(OUT, 0);
    }
    else{
        setValve(SWITCH, 0);
        setValve(IN, 0);
        setValve(OUT, 0);
        setValve(VENT, 0);
        setValve(SHORT, 0);
    }
    mb.setCoil(depressuriseCoil, 0);  
}

float convertToBar(float pressure){
    return (pressure-203.53)/0.8248/100;
}

void updateStatus(){
  //update status LEDs
  setLED(0, Serial); //LED 1 indicates serial communication
  setLED(1, TTLState); //LED 2 indicates TN control
  setLED(2, digitalRead(VALVES[SHORT])); //LED 4 indicates NN valve state - venting???
  //expand with more LEDs when they have a purpose
}

void setLED(int led, bool state){
  digitalWrite(STATUS_LEDS[led], state);
}