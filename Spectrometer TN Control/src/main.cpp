#include <Arduino.h>

//CONSTANTS

//Pin values taken from communication from Chris Rhodes
//5 valves - IN, OUT, SHORT, NN, SWITCH - 42, 44 and 46 unused
//V1 = SWITCH, V2 = IN, V3 = OUT, V4 = NN, V5 = SHORT
//TODO check with James about which valve is which
//const int IN = 0; const int OUT = 1; const int SHORT = 2; const int NN = 3; const int SWITCH = 4;
const int SWITCH = 0; const int IN = 1; const int OUT = 2; const int VENT = 3; const int SHORT = 4;
const int LEDS[] = {32, 34, 36, 38, 40, 42, 44, 46};
const int VALVES[] = {8, 9, 10, 22, 52, 26, 28, 30};

// status LEDs
const int STATUS_LEDS[] = {5, 6, 7, 11, 12, 13, 23, 50};

//default timings
const unsigned long DEFPollTime = 500; //default time between pressure readings
const unsigned long DEFPressureTime = 3000; //default time required to build pressure before bubbling

//TTL Pins, T4 and T5 not working??
const int T1 = 25; const int T2 = 3; const int T3 = 4; const int T4 = 2; const int T5 = 24;

//Analog pins - pressure4 is external
const int Pressure1 = A0; const int Pressure2 = A2; const int Pressure3 = A4; const int Pressure4 = A6;

const int maxLength = 9; //maximum number of steps in a sequence

//VARIABLES
bool TNcontrol = 0; //TerraNova control - allows valves to be controlled by TTL signals
bool pressureLog = 0; //log pressure values
bool TTLControl = 0; //TTL control toggle
bool decodeFlag = 0; //flag to decode a sequence
bool execFlag = 0; //flag to execute a sequence
bool simpleTTL = 0; //simple TTL control toggle - unused

int pressureInputs[4] = {0,0,0,0};  //container for pressure values from the analog pins

int pollTime = DEFPollTime; //time between pressure readings
int pressureTime = DEFPressureTime; //time required to build pressure before bubbling
size_t currentStepIndex = 0; //current step in the sequence

unsigned long tNow = 0; //current time
unsigned long tStart = 0; //start time
unsigned long tStepStart = 0; //start time of a step
unsigned long heartBeat = 0; //time of last heartbeat

String sequence = ""; //sequence to be decoded

struct Step {
  char type; //type of step - 'b' for bubble, 'd' for delay, 'n' for alt bubble
  unsigned long length; //length of step in ms
};

Step sequenceSteps[maxLength]; //array to hold the steps in the sequence

char validTypes[3] = {'b', 'd', 'n'};

//FUNCTIONS
void declarePins();

void initOutput();

void updateStatus();

void handleSerial();

void handleTTL();

void readPressure();

void setValve(int valve, int state);

void setLED(int led, int state);

void decodeSequence();

void processStoredSequence();

void processStep(char stepType);

void closeValves();

void reset();

bool isValidType(char type);

void setup() {
  // put your setup code here, to run once:
  declarePins();
  initOutput(); //set all valves and LEDs to off & flash status LEDs
  tStart = millis();  //begin polling timer
  Serial.begin(9600); //Open serial communication
}

void loop() {
  // put your main code here, to run repeatedly:
  tNow = millis();

  updateStatus();

  if(Serial.available()){handleSerial();}

  if(decodeFlag == 1){decodeSequence();}

  if(execFlag == 1){processStoredSequence();}

  if(TTLControl == 1){handleTTL();}

  if(tNow - tStart >= pollTime){readPressure(); tStart = tNow;}
  
  //need to reset if no serial signal for certain time
  if(tNow - heartBeat > 5000){reset();}
}

void declarePins()
{
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

void initOutput(){
  //set all valves to off
  for (int i = 0; i < 8; i++)
  {
    setValve(i, 0);
  }

  //flash status LEDs to show that the system is ready
  for (int i = 0; i < 8; i++)
  {
    setLED(i, 1);
  }

  delay(200);

  //set all status LEDs to off
  for (int i = 0; i < 8; i++)
  {
    setLED(i, 0);
  }

  //Initial heartbeat in case the first one is missed due to the initialisation delay
  Serial.println("HEARTBEAT_ACK");  //Heartbeat response
}

void setLED(int led, int state) //sets status LEDs to on or off
{
  digitalWrite(STATUS_LEDS[led], state);
}

void setValve(int valve, int state) //sets the valve & corresponding LED to on or off
{
  digitalWrite(VALVES[valve], state); //set the valve to the desired state
  digitalWrite(LEDS[valve], state);  //set the corresponding valve LED to the same state
  Serial.println("LOG: Valve " + String(valve+1) + " set to " + String(state));
}

void handleSerial()
{
  char input = Serial.read();
  if (isAlpha(input))
  {
    if (TNcontrol == 1)     //If TN control is enabled
    {
      switch(input){
        case 'y': 
          Serial.println("HEARTBEAT_ACK");  //Heartbeat response
          heartBeat = millis(); //update the heartbeat time
          break;
        case 'i':   //Decode a sequence input
          decodeFlag = 1; // Set the flag to indicate a new sequence is ready to be decoded
          break;
        case 'R':   //Execute the current loaded sequence
          execFlag = 1; // Set the machine ready flag to true
          pressureLog = 1; // Enable pressure logging when a sequence is running
          break;
        case 'm':   //Switch to manual control (TN = 0)
          TNcontrol = 0;
          break;
        case 'M':   //Switch to manual control (TN = 0)
          Serial.println("LOG: Already in auto control mode");
          break;
        case 'K':   //Enable pressure logging
          pressureLog = 1;
          break;
        case 'k':   //Disable pressure logging
          pressureLog = 0; 
          break;
        case 'T':   //Enable TTL control
          simpleTTL = 1;
          pressureLog = 1;  //Enable pressure logging when TTL control is enabled
          break;
        case 't':   //Disable TTL control
          simpleTTL = 0;
          break;
        case 's':   //Reset the system
          reset();
          break;
        default:
          Serial.println("LOG: Invalid input");  //Invalid input
          break;
      }
    }
    else                    //If TN control is disabled
    {
      switch(input){
        case 'y': 
          Serial.println("HEARTBEAT_ACK");  //Heartbeat response
          heartBeat = millis(); //update the heartbeat time
          break;
        case 'K':   //Enable pressure logging
          pressureLog = 1;
          break;
        case 'k':   //Disable pressure logging
          pressureLog = 0; 
          break;
        case 'M':   //Switch to spec'r control (TN = 1)
          TNcontrol = 1;
          break;
        case 'm':   //Switch to manual control (TN = 0)
          Serial.println("LOG: Already in manual control mode");
          break;
        case 'Z':   //Turn on short valve
          setValve(SHORT, 1);
          break;
        case 'z':   //Turn off short valve
          setValve(SHORT, 0);
          break;
        case 'C':   //Turn on INLET valve
          setValve(IN, 1);
          break;
        case 'c':   //Turn off INLET valve
          setValve(IN, 0);
          break;
        case 'V':   //Turn on OUTLET valve
          setValve(OUT, 1);
          break;
        case 'v':   //Turn off OUTLET valve
          setValve(OUT, 0);
          break;
        case 'X':   //Turn on VENT valve
          setValve(VENT, 1);
          break;
        case 'x':   //Turn off VENT valve
          setValve(VENT, 0);
          break;
        case 'H':   //Turn on SWITCH valve
          setValve(SWITCH, 1);
          break;
        case 'h':   //Turn off SWITCH valve
          setValve(SWITCH, 0);
          break;
        case 's':   //Reset the system
          reset();
          break;
        default:
          Serial.println("LOG: Invalid input");  //Invalid input
          break;
      }
    }
  }
  else
  {
    Serial.println("LOG: Invalid input, not a letter");  //Invalid input
  }
}

void decodeSequence() //decode the sequence input
{
  if (execFlag == 1) //if a sequence is potentially running, do not load a new sequence
  {
    Serial.println("SEQ: False"); //send a false sequence response
    Serial.println("LOG: Sequence already running, please wait for current sequence to end before loading a new one");
    decodeFlag = 0;
    return; //exit the function to avoid loadning new sequence

    /* //ALTERNATE CODE, load new sequence anyway and overwrite the current one
    Serial.println("Sequence already running, cancelling current sequence and loading new one");
    memset(sequenceSteps, 0, sizeof(sequenceSteps));
    currentStepIndex = 0;
    execFlag = false; // Set the machine ready flag to false due to cancelling the current sequence
    closeValves();  // Close all valves for safety
    */
  }
  //decode the sequence
  if (Serial.available() > 0) {
    sequence = Serial.readStringUntil('\n'); // Read the entire input until newline
    decodeFlag = 0; // initialise the decode flag

    size_t i = 0;   // Unsigned int to avoid warning
    int stepIndex = 0;
    while (i < sequence.length()) {
      char stepType = sequence[i];  // Read the step type
      if (isValidType(stepType)) { // Check if the step type is valid
        i++;
        String stepLengthStr = "";
        while (i < sequence.length() && isDigit(sequence[i])) { // Read the step length until another type is found
          stepLengthStr += sequence[i];
          i++;
        }

        if (stepIndex >= maxLength) { // Check if the sequence is too long
          Serial.println("LOG: Sequence too long, only first 9 steps will be executed");
          break;
        }
        else{
          int stepLength = stepLengthStr.toInt(); // Convert the step length to an integer
          sequenceSteps[stepIndex] = {stepType, static_cast<unsigned long>(stepLength)}; // Store the step in the list
          stepIndex++;
        }
      }
      else {
        Serial.println("LOG: Invalid step type in sequence");
        Serial.println("SEQ: False"); //send a false sequence response
        decodeFlag = 0;
        break;
      }
    }
    Serial.println("SEQ: True"); //send a true sequence response
    decodeFlag = 1; // Set the flag to indicate sequence has been decoded
  }
  else
  {
    Serial.println("SEQ: False"); //send a false sequence response
    Serial.println("LOG: Expected sequence input, but none received");
    decodeFlag = 0;
  }
}

void processStoredSequence() {  // Process the loaded sequence
  if (sequenceSteps[0].length == 0) { // Check if the sequence is empty
    Serial.println("LOG: Sequence is empty, nothing to process.");
    execFlag = false; // Set the machine ready flag to false due to an empty sequence
    return; // Exit the function if the sequence is empty
  }
  pressureLog = 1; // Ensure pressure logging enabled when a sequence is running
  if (currentStepIndex < sizeof(sequenceSteps) / sizeof(sequenceSteps[0]) && sequenceSteps[currentStepIndex].length > 0) {
    Step& step = sequenceSteps[currentStepIndex];
    if (tNow - tStepStart >= step.length) { // Check if the current step has been processed
      processStep(step.type);
      tStepStart = tNow; // Reset the start time for the next step
      currentStepIndex++; // Move to the next step
    }
  } else {
    // All steps processed, reinitialise the state
    closeValves();  // Close all valves for safety
    memset(sequenceSteps, 0, sizeof(sequenceSteps));
    currentStepIndex = 0;
    execFlag = false; // Set the machine ready flag to false after processing all steps
  }
}

void processStep(char stepType) { // Process a step based on the type
  switch (stepType) {
    case 'b':
      // Handle bubble step
      setValve(IN, 1);
      setValve(OUT, 1);
      setValve(SWITCH, 0);
      break;
    case 'd':
      // Handle delay step
      setValve(IN, 0);
      setValve(OUT, 0);
      setValve(SWITCH, 0);
      break;
    case 'n':
      // Handle alt bubble step
      Serial.println("LOG: Alt bubble step not implemented");
      break;
    // Add more cases as needed
    default:
      Serial.println("LOG: Unknown step type");
      break;
  }
}

void readPressure() //read pressure values from the analog pins
{
  //read pressure values
  pressureInputs[0] = analogRead(Pressure1);
  pressureInputs[1] = analogRead(Pressure2);
  pressureInputs[2] = analogRead(Pressure3);
  pressureInputs[3] = analogRead(Pressure4);

  if (pressureLog == 1){
    //build the pressure return string the way James has been using so far
    String pressureReturn = "P ";
    for (int i = 0; i < sizeof(pressureInputs) / sizeof(pressureInputs[0]); i++)
    {
      pressureReturn += String(pressureInputs[i]);
      pressureReturn += " ";
    }
    for (int i = 0;i < sizeof(VALVES) / sizeof(VALVES[0]); i++)
    {
      pressureReturn += String(digitalRead(VALVES[i]));
      pressureReturn += " ";
    }
    pressureReturn += "C";
    Serial.println(pressureReturn);
  }
}

void closeValves(){ //safety function run at the end of a sequence
  //close all valves
  for (int i = 0; i < sizeof(VALVES) / sizeof(VALVES[0]); i++)
  {
    setValve(i, 0);
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
        Serial.println("LOG: Invalid TTL input");
        break;
    }
  }
}

void reset(){
  //reset the system
  memset(sequenceSteps, 0, sizeof(sequenceSteps));
  currentStepIndex = 0;
  execFlag = 0;
  decodeFlag = 0;
  simpleTTL = 0;
  TNcontrol = 0;
  pressureLog = 0;
  closeValves();
  tStart = millis();
}

void updateStatus(){
  //update status LEDs
  setLED(0, Serial); //LED 1 indicates serial communication
  setLED(1, TNcontrol); //LED 2 indicates TN control
  setLED(2, pressureLog); //LED 3 indicates pressure logging
  setLED(3, digitalRead(VALVES[VENT])); //LED 4 indicates NN valve state
  //expand with more LEDs when they have a purpose
}

bool isValidType(char type) { // Check if the step type is valid
  for (int i = 0; i < sizeof(validTypes) / sizeof(validTypes[0]); i++) {
    if (type == validTypes[i]) {
      return true;
    }
  }
  return false;
}
