double runCurrent = 100; // Motor run current, % of maximum
double holdCurrent = 10;  // Motor hold current, % of maximum
double brakeCurrent = 10;
float maxAcceleration = 23250; //23250 Motor acceleration, steps/s^2
float maxDeceleration = 23250; //23250 Motor deceleration, steps/s^2
int maxVelocity = 6500; //6500
int contVelocity = 1000;
int stallSensitivity = 0; // Stall sensitivity, arbitrary (-64 to 63, lower number = higher sensitivity)

// Motor standby parameters
double standby_runCurrent = 0;
double standby_holdCurrent = 0;
float standby_maxAcceleration = 0;
float standby_maxDeceleration = 0;
int standby_maxVelocity = 0;

// Position definitions
int mmSteps = 6400;     //steps in 1 mm
int topPosition = -1;
int currentPosition;
int downPosition;
int downValue = 2475000;
int sixmTPosition;
int sixmTValue = 1190700; //2475000 - 1284300
int upPosition;
int upValue = 100000;
int setPosition;
int mapPositions;
int curPos;
int newPos;


//misc
bool contFlag;
bool movingFlag;
unsigned long startTime;
unsigned long endTime;
bool motorState1 = 0; //pos reached
bool motorState2;     //vel.
bool motorState3;     //standstill
bool prevMotorS1 = 0;

void setup() {
  //stepper.setup(NORMAL, 200);				     // Initialize uStepper S32
  Serial.begin(9600);
//  Serial.println("Initialising motor, finding top position!");
  //stepper.moveToEnd(CW, 50, stallSensitivity);  // Find top reference position
  topPosition = //stepper.getPosition();  // Set top reference position
//  Serial.print("Top position: "); 
  Serial.println(topPosition);  // Print top reference position
  calculatePositions(topPosition);

  /*upPosition = topPosition - 100000;
    setPosition = upPosition;*/
  //stepper.movePosition(upPosition);

  //stepper.setCurrent(runCurrent);	              // Set motor run current
  //stepper.setHoldCurrent(holdCurrent);          // Set motor hold current
  //stepper.setMaxAcceleration(maxAcceleration);  // Set maximum acceleration of motor
  //stepper.setMaxDeceleration(maxDeceleration);  // Set maximum deceleration of motor
  //stepper.setBrakeMode(COOLBRAKE);
  //stepper.setMaxVelocity(maxVelocity);          // Set maximum velocity of motor
}

void loop() {
  motorState1 = //stepper.getMotorState(POSITION_REACHED);
  motorState2 = //stepper.getMotorState(VELOCITY_REACHED);
  motorState3 = //stepper.getMotorState(STANDSTILL);
  curPos = 0;//stepper.getPosition();
  /*  Serial.print(motorState1);    Serial.print(motorState2);  Serial.println(motorState3);*/
  char input;
  input = Serial.read();
  if (input == 'u' || input == 'd') {
    contFlag = 1;
    //movingFlag = 1;
    //stepper.setMaxVelocity(contVelocity);
    Serial.println("low vel.");
  } else {
    contFlag = 0;
    //stepper.setMaxVelocity(maxVelocity);
    //reset velocity
  }
  while (contFlag == 1 && Serial.available() == 0) {
    curPos = //stepper.getPosition();
    Serial.println(curPos);
    if ((curPos > upPosition) || (curPos < downPosition)) {//dir == 1 && .... dir == 0 &&
      Serial.println("Motor will crash!");
      //stepper.stop(HARD);
      contFlag = 0;
      movingFlag = 0;
    }
  }

  ////  timer /////
  if (motorState1 && !prevMotorS1) {
    // Motor state just turned true, start the timer
    startTime = millis();
  } else if (!motorState1 && prevMotorS1) {
    // Motor state just turned false, stop the timer
    unsigned long elapsedTime = millis() - startTime;
    //Serial.print("Motor was on for: ");    Serial.print(elapsedTime);  Serial.println(" milliseconds");
  }
  prevMotorS1 = motorState1;  // Update the previous motor state

  //these two might want to go a bit slower
  switch (input) {
    case 'u': // Move upwards continuously
      contRotation(1);
      break;
    case 'd': // Move downwards continuously
      contRotation(0);
      break;
    case 's': // Stop
      //stepper.stop(HARD);
      Serial.println("Stop!");
      curPos = //stepper.getPosition();
      //Serial.print("Current position: ");
      Serial.println(curPos);
      break;

    case 'e': // Shutdown. requires reinitialisation code 'i' to reset.
      shutdownMotor();
      break;
    case 'm': // Perform field map
      fieldMap();
      break;
    case 'c': // Calibrate positions
      calibrateMotor();
      break;
    case 'p':             //position motor; position determined by next character in.
      movingFlag = 1;
      positionMotor();    //will want to include relative up & down commands.
      break;
    case 'r': // Read position
      curPos = //stepper.getPosition();
      Serial.println(curPos);
      break;
    // Move upwards by 5 mm
    case 'y':
      //Serial.println("Moving upwards by 5 mm!");
      bumpMotor(5);
      break;
    case 'z': // Move downwards by 5 mm
      //Serial.println("Moving downwards by 5 mm!");
      bumpMotor(-5);
      break;
    case 'b':
      //movingFlag = 1;
      bumpMotor(0);
      break;
    case 'i':
      queryMotor();
      break;
  }
}

/*///////////////////////////////////////////////////////////////////////////////////////////////////////
  //           ______   _    _   _   _    _____   _______   _____    ____    _   _    _____
  //          |  ____| | |  | | | \ | |  / ____| |__   __| |_   _|  / __ \  | \ | |  / ____|
  //    ____  | |__    | |  | | |  \| | | |         | |      | |   | |  | | |  \| | | (___    ____
  //   |____| |  __|   | |  | | | . ` | | |         | |      | |   | |  | | | . ` |  \___ \  |____|
  //          | |      | |__| | | |\  | | |____     | |     _| |_  | |__| | | |\  |  ____) |
  //          |_|       \____/  |_| \_|  \_____|    |_|    |_____|  \____/  |_| \_| |_____/
  //
  //////////////////////////////////////////////////////////////////////////////////////////////////./*/


//////////
void calibrateMotor() {
  //////////
  ////stepper.setCurrent(runCurrent);         // Set motor run current
  //stepper.setHoldCurrent(holdCurrent);   // Set motor hold current
  //stepper.setMaxAcceleration(maxAcceleration);  // Set maximum acceleration of motor
  //stepper.setMaxDeceleration(maxDeceleration);  // Set maximum deceleration of motor
  //stepper.setBrakeMode(COOLBRAKE);
  //stepper.setMaxVelocity(maxVelocity); // Set maximum velocity of motor

  //Serial.println("Finding top position!");
  //stepper.moveToEnd(CW, 50, stallSensitivity);
  topPosition = 0;//stepper.getPosition();
  calculatePositions(topPosition);
  //Serial.print("Top position: ");
  Serial.println(topPosition);
  upPosition = topPosition - upValue;
  //stepper.movePosition(upPosition);
}

/////////////////////////
void positionMotor() {
  //////////////////////
  char nextin;
  //if testing - first char is 'p'
  nextin = Serial.read();
  switch (nextin) {
    case 'b': // Sample to down position
      //Serial.println("Sample down!");
      downPosition = topPosition - downValue;
      setPosition = downPosition;
      //stepper.movePosition(setPosition);
      break;

    case 'p': // Sample to 6 mT position
      //Serial.println("6 mT position!");
      sixmTPosition = topPosition - sixmTValue;
      setPosition = sixmTPosition;
      //stepper.movePosition(setPosition);
      break;

    case 't': // Sample to top
      //Serial.println("Sample up!");
      upPosition = topPosition - upValue;
      setPosition = upPosition;
      //stepper.movePosition(setPosition);
      break;

    case 'a': {
        int testPos1 = downPosition + 1500000;
        //stepper.movePosition(testPos1);
        break;
      }

    case 's': {
        int testPos2 = downPosition + 1750000;
        //stepper.movePosition(testPos2);
        break;
      }

    case 'd': {
        int testPos3 = downPosition + 2000000;
        //stepper.movePosition(testPos3);
        break;
      }

    case 'f': {
        int testPos4 = downPosition + 2250000;
        //stepper.movePosition(testPos4);
        break;
      }
  }
}
///////////////////////
void fieldMap() {
  /////////////////////
  //Serial.println("Performing field map!");
  downPosition = topPosition - downValue;
  setPosition = downPosition;
  //stepper.movePosition(setPosition);
  delay(5000);
  //currentPosition = //stepper.getPosition();
  //Serial.println(currentPosition);

  mapPositions = 75;
  for (int i = 0; i < mapPositions; i++) {
    delay(5000);
    //stepper.moveAngle(225);
    curPos = //stepper.getPosition();
    Serial.println(curPos);
  }
}
/////////////////////////
void shutdownMotor() {
  ///////////////////////
 // Serial.println("Shutting down!");
  upPosition = topPosition - 100000;
  setPosition = upPosition;
  //stepper.movePosition(setPosition);
  delay(10000);

  //stepper.setCurrent(standby_runCurrent);                // Set motor standby run current
  //stepper.setHoldCurrent(standby_holdCurrent);          // Set motor standby hold current
  //stepper.setMaxAcceleration(standby_maxAcceleration);  // Set standby maximum acceleration of motor
  //stepper.setMaxDeceleration(standby_maxDeceleration);  // Set standby maximum deceleration of motor
  //stepper.setBrakeMode(FREEWHEELBRAKE);
  //stepper.setMaxVelocity(standby_maxVelocity); // Set standby maximum velocity of motor
}
////////////////////
void calculatePositions(int topPosition) {
  ///////////////////
  downPosition = topPosition - downValue;
  sixmTPosition = topPosition - sixmTValue;
  upPosition  = topPosition - upValue;
}


/////////////////////////
void bumpMotor(int distance) {
  ///////////////////////
  curPos = 0;//stepper.getPosition();
  //Serial.println(distance);
  //Serial.println(curPos);

  if (distance == 0) {
    String nextin;
    // Serial.read();
    if (Serial.available() > 0) {
      nextin = Serial.readStringUntil('\n'); // Read the input string until a newline character
      //Serial.println(nextin);
      distance = nextin.toInt(); // Convert the input string to an integer
      Serial.println(distance);
    }
  }
  int  toMove = (distance * mmSteps);
  newPos = curPos + toMove;
  if (newPos > topPosition || newPos < downPosition) {
    //Serial.println("Motor will crash!");
    return;
  }
  //stepper.movePosition(newPos); //      //stepper.moveAngle(-225);
}



///////////////////////
void queryMotor() {
  ////////////////
  char nextin;
  //if testing - first char is 'i'
  nextin = Serial.read();
  switch (nextin) {
    case 'a':
      Serial.println(maxAcceleration);
      break;
    case 'b':
      Serial.println(downPosition);
      break;
    case 'c':
      curPos = //stepper.getPosition();
      Serial.println(curPos);
      break;
    case 'p':
      Serial.println(sixmTPosition);
      break;
    case 't':
      Serial.println(topPosition);
      break;
    case 'u':
      Serial.println(upPosition);
      break;
    case 'v':
      Serial.println(maxVelocity);
      break;
  }
}


/////////////////
void contRotation(bool dir) { //1 is up and dir 0 is down
  /////
  String dirtext;
  if (dir == 1) {
    dirtext = "up";
  }  else {
    dirtext = "down";
  }

  //stepper.runContinous(dir);
  Serial.print("Moving "); Serial.println(dirtext);
  contFlag = 1;
  //movingFlag = 1;
  Serial.read();
  while (contFlag == 1 && Serial.available() == 0) {

    curPos = //stepper.getPosition();
    Serial.println(curPos);

    if ((dir == 1 && curPos > upPosition) || (dir == 0 && curPos < downPosition)) {
      //Serial.println("Motor will crash!");
      //stepper.stop(HARD);
      contFlag = 0;
      movingFlag = 0;
     
    }
  }
}





/*
  //-------- _+@      _~@            __@     ~#@       __~@                                         __~@
  //----- _`\<,_    _`\<,_         _`\<,_  _`\<,_    _`\<,_                                        _`\<,_
  //---- (*)/ (*)  (*)/ (*)      (*)/ (*) (O)/ (*)  (*)/ ( )                                     (*)/ ( )
  //~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
