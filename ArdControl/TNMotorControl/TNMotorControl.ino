#include <Arduino.h>
#include "callbacks.h"

#include <UstepperS32.h>

#define SLOW 0
#define MEDIUM 1
#define FAST 2

const int stepMult = 25600;
const unsigned long DEFHeartBeatTime = 5000;
const int maxRPM = 50;
const int maxAcc = 2000;
const int maxVel = 50;
const int inverted = 0;
const int UP = 1;
const int DOWN = -1;

int topPosition = 0;
bool started = false;
bool calibrationFlag = false;
bool moveFlag = false;
bool calibrated = false;
unsigned long tNow = 0;
unsigned long heartBeat = 0;
unsigned long tStart = 0;
unsigned long tStall = 0;
//UstepperS32 motor;
int dir = 0;
int stallVal = 0;
bool doOnce = true;

void setup(){
    motor = UstepperS32(2000, 200);
    Serial.begin(9600);
    motor.setup(NORMAL, 200, 10, 0.2, 0.0, 16, true, 0, 80, 40);
    motor.setBrakeMode(COOLBRAKE);
    motor.setMaxAcceleration(maxAcc); //use an acceleration of 2000 fullsteps/s^2
    motor.setRPM(maxRPM);
    motor.setMaxVelocity(maxVel);
    //motor.encoder.encoderStallDetectEnable = 1;
    tStart = millis();  //begin polling timer
    heartBeat = millis();
    started = 0;
    dir = 0;
    motor.stop();
}

void loop(){
  //motor.stop();
  while (started == 0) {
    calibrationFlag = false;
    // Wait for the system to be started
    if (Serial.available() > 0) {
      char input = Serial.read();
      Serial.print("LOG: Received input: ");
      Serial.println(input);
      if (input == 'S') {
        started = 1;
        Serial.println("LOG: System started");
        heartBeat = millis(); // Update the heartbeat time
      }
    }
  }

  if (doOnce = true){
    int steps = 10000;
    motor.moveSteps(steps * UP);
    doOnce = false;
  }

  tNow = millis();

  if(Serial.available()){handleSerial();}

  //if(calibrationFlag == true && motor.getMotorState(STALLGUARD2) == true) {setHome();} //set the home position when calibration is finished

  //if(moveFlag == true && motor.getMotorState(POSITION_REACHED) == true) {moveFlag = false; Serial.println("LOG: Reached position");} //reset moveFlag when move is finished

  if((long)(tNow - heartBeat) >= (long)DEFHeartBeatTime) {reset();} //reset if no heartbeat for 5 seconds
  //motor.disableStallguard();
  if((long)(tNow - tStall) >= (long)1000){
    tStall = millis();
    stallVal += 1;
    //motor.disableStallguard();
    if(motor.driver.getVelocity() < 0.01){
      Serial.print("LOG: Stall detected at sens ");
      Serial.println(stallVal);
    }
    else{  
      motor.enableStallguard(stallVal, true, maxRPM);
      Serial.print("LOG: STALLVAL IS NOW ");
      Serial.println(stallVal);
      int steps = 10000;
      motor.moveSteps(steps * UP);
    }    
  }
  
  
  /*
  if (motor.driver.getVelocity() < 0){
    Serial.println("LOG: Velocity too low");
    reset();
  }
  */
}

void handleSerial(){
  char input = Serial.read();
  if (isAlpha(input))
  {
    switch(input)
    {
      case 's': //stop
        Serial.println("LOG: Shutting down motor");
        reset();
        break;
      case 'y': //heartbeat
        Serial.println("HEARTBEATACK");
        heartBeat = millis();
        break;
      case 'p': //move to position
      /*
        if (moveFlag == true) {Serial.println("LOG: Motor is already moving"); break;}
        else if (calibrationFlag == true) {Serial.println("LOG: Motor is calibrating"); break;}
        else if (calibrated == false) {Serial.println("LOG: Motor is not calibrated"); break;}
        else {Serial.println("LOG: Moving to position"); goToPos(); break;}
        */
        Serial.println("LOG: Moving to position"); 
        goToPos();
        break;
      case 'c': //calibrate
        Serial.println("LOG: Calibrating");
        Serial.println("yes");
        //setSpeedProfile(MEDIUM);
        motor.checkOrientation(10);
        motor.enableStallguard(4, true, maxVel);
        motor.runContinous(1);
        Serial.println("LOG: Got past calibr");
        calibrationFlag = true;
        break;
      case 'g': //get position
        Serial.println(motor.driver.getPosition());
        break;
      case 't': //get status
        if (motor.getMotorState(STANDSTILL) == true) {Serial.println("LOG: Motor is stopped");}
        else {Serial.println("LOG: Motor is moving");}
        if (motor.getMotorState(POSITION_REACHED) == true) {Serial.println("LOG: Motor is at position");}
        else {Serial.println("LOG: Motor is not at position or position not set");}
        //Serial.println(motor.driver.readRegister(STANDSTILL));
        //Serial.println(motor.driver.readRegister(POSITION_REACHED));
        break;
      default:
        Serial.println("LOG: Invalid input");
        break;
    }
  }
}

void reset(){ //called when error - stop hard
  motor.stop(HARD);
  started = 0;
  calibrated = 0;
}

void setHome(){
  Serial.println("Set home");
  calibrationFlag = false;
  calibrated = true;
  topPosition = motor.driver.getPosition();
  setSpeedProfile(FAST);
  //motor.clearStall();
  //motor.disableStallguard();
}

void goToPos(){
  String positionStr = Serial.readStringUntil('\n');
  if (positionStr.length() > 0){
    float position = (positionStr.toInt());
    Serial.print("LOG: Moving to position: ");
    Serial.println(position);
    motor.moveSteps(position);
    // motor.driver.setDeceleration((uint16_t)(2000));
  	// motor.driver.setAcceleration((uint16_t)(2000));
	  // motor.driver.setVelocity((uint32_t)(50));

    // motor.driver.setPosition(position);
    moveFlag = true;
  }
  else{
    Serial.println("LOG: No position given");
  }
}

void setSpeedProfile(int speed){
  if (speed == 0){  //slow setting
    motor.setRPM(200);
    motor.setMaxAcceleration(1500);
  }
  else if (speed == 1){ //medium setting
    motor.setRPM(350);
    motor.setMaxAcceleration(1750);
  }
  else if (speed == 2){ //fast setting
    motor.setRPM(500);
    motor.setMaxAcceleration(2000);
  }
  else{
    Serial.println("LOG: Invalid speed setting, defaulting to slow");
    motor.setRPM(200);
    motor.setMaxAcceleration(1500);
  }
}

void stop(){
  motor.stop(HARD);
}