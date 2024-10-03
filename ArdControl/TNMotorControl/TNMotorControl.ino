#include <Arduino.h>
#include "HAL/spi.h"
#include "HAL/gpio.h"
#include "peripherals/TMC5130.h"
#include "peripherals/TLE5012B.h"
#include "HAL/timer.h"
#include "callbacks.h"
#include "utils/dropin.h"
#include <UstepperS32.h>

#define SLOW 0
#define MEDIUM 1
#define FAST 2

const unsigned long DEFHeartBeatTime = 5000;
const int maxRPM = 500;
const int maxAcc = 2000;
const int inverted = 0;

int topPosition = 0;
bool calibrationFlag = false;
bool moveFlag = false;
bool calibrated = false;
UstepperS32 motor;

void setup(){
    Serial.begin(9600);
    motor.setup(mode = NORMAL, stepsPerRevolution = 200, pTerm = 10, iTerm = 0.2, dTerm = 0, dropinStepSize = 16, setHome = true, invert = inverted, runCurrent = 50, holdCurrent = 30);
    motor.setBrakeMode(COOLBRAKE);
    motor.setMaxAcceleration(maxAcc); //use an acceleration of 2000 fullsteps/s^2
    motor.setRPM(maxRPM);
    tStart = millis();  //begin polling timer
    heartBeat = millis();
    started = 0;
}

void loop(){
  while (started == 0) {
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

  tNow = millis();

  if(Serial.available()){handleSerial();}

  if(calibrationFlag == true && motor.getState(STANDSTILL) == true) {setHome();} //set the home position when calibration is finished

  if(moveFlag == true && motor.getState(POSITION_REACHED) == true) {moveFlag = false; Serial.println("LOG: Reached position");} //reset moveFlag when move is finished

  if((long)(tNow - heartBeat) >= (long)DEFHeartbeatTime) {reset();} //reset if no heartbeat for 5 seconds
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
        if (moveFlag == true) {Serial.println("LOG: Motor is already moving"); break;}
        else if (calibrationFlag == true) {Serial.println("LOG: Motor is calibrating"); break;}
        else if (calibrated == false) {Serial.println("LOG: Motor is not calibrated"); break;}
        else {Serial.println("LOG: Moving to position"); goToPos(); break;}
      case 'c': //calibrate
        Serial.println("LOG: Calibrating");
        setSpeedProfile(SLOW);
        motor.checkOritentation(10);
        motor.moveToEnd(dir=CW, rpm=50, threshold=4, timeOut=100000);
        calibrationFlag = true;
        break;
      case 'g': //get position
        Serial.println(motor.getPosition());
        break;
      case 't': //get status
        if (motor.getState(STANDSTILL) == true) {Serial.println("LOG: Motor is stopped");}
        else {Serial.println("LOG: Motor is moving");}
        if (motor.getState(POSITION_REACHED) == true) {Serial.println("LOG: Motor is at position");}
        else {Serial.println("LOG: Motor is not at position or position not set");}
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
  calibrationFlag = false;
  calibrated = true;
  topPosition = motor.getPosition();
  setSpeedProfile(FAST);
}

void goToPos(){
  if(Serial.available()){
    String positionStr = Serial.readStringUntil('\n');
    int position = (topPosition + positionStr.toInt());
    Serial.print("LOG: Moving to position: ");
    Serial.println(position);
    motor.movePosition(position);
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