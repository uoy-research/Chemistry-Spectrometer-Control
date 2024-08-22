////////////////////////////////////////
//define variables
////////////////////////////////////////

//if you're working on this code and you're not me, i'm so sorry
//actually even if you are me i'm sorry.
//if you're new to arduino Alastair Robinson made some fantastic examples that'll drop you in a little more gently than this big lump.
//if you have any questions please ask :)

//variables you might want to change
int pollTime = 500;       //time between pressure reads
int pressureTime = 3000;  //time the outlet valve is closed to pressurise the cell before 'open' bubbling starts.
int simpleTTL = 0;

//
String pollTimeS;
int bubbleT, seqT, leadT, reps;
String bubbleTS, seqTS, leadTS, repsS;

//pin-specific variables
int outLEDIn = 32;
int oLI = outLEDIn;
int outLEDOut = 34;
int oLO = outLEDOut;
int outLEDshort = 36;   //sets pin number for LED outputs
int oLS = outLEDshort;  //contraction. used throughout
int outLEDNN = 38;
int oLN = outLEDNN;
int outLEDopH = 40;
int oLH = outLEDopH;
int V6 = 42;
int V7 = 44;
int V8 = 46;
int inMon = 0;
int outMon = 0;
int ophMon = 0;
int n2Mon = 0;
int shortMon = 0;
int T1n, T1b, T2n, T2b, T3n, T3b, T4n, T4b, T5n, T5b;
String inMo, outMo, ophMo, n2Mo, shortMo;
char startup = 'z';
//
int outValveIn = 8;
int oVI = outValveIn;
int outValveOut = 9;
int oVO = outValveOut;
int outValveShort = 10;
int oVS = outValveShort;  //pin nos for valve triggers
int outValveNN = 22;      //inclusing contractions. if you need to add both will work
int oVN = outValveNN;
int outValveopH = 52;
int oVH = outValveopH;
int startupint;
//
int T1 = 2;  //0x10
int T2 = 3;  //0x20
int T3 = 4;  //0x08

//these two aren't working
int T4 = 51;
int T5 = 53;
//
int S1 = 5;  //pin numbers for LED status indicators
int S2 = 6;
int S3 = 7;
int S4 = 11;
int S5 = 12;
int S6 = 13;
int S7 = 23;
int S8 = 50;
//
bool TNcontrol = 1;      //Terranova control: when true valves are triggered by TTL pulses
bool PrintPressure = 0;  //sends presure readings over serial port
//
int vA1 = 0;
int vA2 = 0;  //voltage from analog pin
int vA3 = 0;
int vA4 = 0;
//
String prOut;  //the string that gives the pressure readings over serial
int pCount;
unsigned long tNow;
unsigned long tSt = 0;
String parameters;
int zeroTime;
int fillTime;


//Variables for spinsolver
String test, stepsStr, durationStr, sequence;
int steps, duration, acStepDur;
char stepType;
int stepno = 0;
int exec[9][2] = {
  { 0, 0 },
  { 0, 0 },
  { 0, 0 },
  { 0, 0 },
  { 0, 0 },
  { 0, 0 },
  { 0, 0 },
  { 0, 0 },
  { 0, 0 },
};
int steplocator = 1;
int seqLen;

//////////////////////////////////////////
void setup() {
  //////////////////////////////////////////
  // put your setup code here, to run once:
  DeclarePins();  //declares the pin numbers to the arduino
  //statements like these run a separate function stated after LOOP.
  AllTheLights();

  Serial.begin(9600);   //opens the serial port at 9600baud (9600 bits/second)
  digitalWrite(S2, 1);  //TNcontrol is on by default
  digitalWrite(S3, 1);  //Print pressure is on  by default
  tSt = millis();
}
//////////////////////////////////////////
void loop() {
  //////////////////////////////////////////
  // this loop runs forever til you turn the arduino off.
  //i apologise in advance for anyone who has to update it, but at least it's not LabView
  //-James

  tNow = millis();

  HandleSerial();

  TTLFunction();

  pressureFunction();

}  //end of the repeated code loop


/*///////////////////////////////////////////////////////////////////////////////////////////////////////
  //           ______   _    _   _   _    _____   _______   _____    ____    _   _    _____
  //          |  ____| | |  | | | \ | |  / ____| |__   __| |_   _|  / __ \  | \ | |  / ____|
  //    ____  | |__    | |  | | |  \| | | |         | |      | |   | |  | | |  \| | | (___    ______
  //   |____| |  __|   | |  | | | . ` | | |         | |      | |   | |  | | | . ` |  \___ \  |______|
  //          | |      | |__| | | |\  | | |____     | |     _| |_  | |__| | | |\  |  ____) |
  //          |_|       \____/  |_| \_|  \_____|    |_|    |_____|  \____/  |_| \_| |_____/
  //
  //////////////////////////////////////////////////////////////////////////////////////////////////./*/



//////////////////////////////////////////
void HandleSerial() {
  ////////////////////////////////////////

  char input;             //defines a character variable called input
  input = Serial.read();  //this variable is read off the serial port.

  switch (input) {        //depending on *input*, do the following:
    /////////////////////////
    //manual,auto control functions
    //////////////////////////
    case 'i':
      //Serial.println("spinsolving");
        //Serial.println(input);
      digitalWrite(S4, HIGH);
      spinsolver(exec);
      //Serial.println("spinsolved");
      break;
    case 'R':
      ssexecute(exec);
      digitalWrite(S4, HIGH);
      delay(5000);
      digitalWrite(S4, LOW);
      break;


    case 'M':               //Capital M for auto(spec'r) control. lc *m* for manual control.
      TNcontrol = 1;        //Tells this code whether we're doing manual or auto (used later in IF statements)
      pCount = 0;           //we'll come to pCount later.
      digitalWrite(S2, 1);  //S2 is on when we're running in auto.
      // FullTTL();
      break;
    case 'm':  //activates manual control
      TNcontrol = 0;
      pCount = 0;
      digitalWrite(S2, 0);
    case 'K':             //turns on the plotting and the valve logging.
      PrintPressure = 1;  //how we log comes later.
      digitalWrite(S3, 1);
      break;
    case 'k':  //turns the logging off.
      PrintPressure = 0;
      digitalWrite(S3, 0);
      break;
      if (TNcontrol == 0) {      //when in manual mode:
        case 'Z':                //capital letters for on, l/c for off
          VLWrite(oVS, oLS, 1);  //turns on the short valve and the short LED.
          shortMon = 1;          //logs the valve state
          break;                 //this valve sytate is printed next to the pressures.
        case 'z':
          VLWrite(oVS, oLS, 0);
          shortMon = 0;
          break;
        case 'C':
          VLWrite(oVI, oLI, 1);
          inMon = 1;
          break;
        case 'c':
          VLWrite(oVI, oLI, 0);
          inMon = 0;
          break;
        case 'V':
          VLWrite(oVO, oLO, 1);
          outMon = 1;
          break;
        case 'v':
          VLWrite(oVO, oLO, 0);
          outMon = 0;
          break;
        case 'H':
          VLWrite(oVH, oLH, 1);
          ophMon = 1;
          break;
        case 'h':
          VLWrite(oVH, oLH, 0);
          ophMon = 0;
          break;
        case 'X':
          digitalWrite(S4, 1);
          VLWrite(oVN, oLN, 1);
          break;
        case 'x':
          digitalWrite(S4, 0);
          VLWrite(oVN, oLN, 0);
          break;
      }  //end of the manual control operation part of the code.
  }
}

//////////////////////////////////////////
void TTLFunction() {
  ////////////////////////////////////////
  if (simpleTTL == 0 && TNcontrol == 1) {
    /*
      functions we need:
      pressurise into bubble
      drain cell
      gas switch
    */
    // start of the auto control section
    T3n = digitalRead(T3);  //usually does oph        0x20
    T2n = digitalRead(T2);  //usually does inlet      0x08
    T1n = digitalRead(T1);  //usually does short      0x??
    T5n = digitalRead(T5);  //usually does outlet     0x10
    T4n = digitalRead(T4);  //usually does outlet     0x10

    /* Serial.println(T1n);
      Serial.println(T5n);
      Serial.println(T4n);
      Serial.println(T3n);*/

    int TTLcode = TTLByter(T1n, T2n, T3n, T4n, T5n);
    /*        Serial.println(TTLcode);
        Serial.println("-------");*/
    TTLCases(TTLcode);
  }


  if (simpleTTL == 1 && TNcontrol == 1) {
    //start of the auto control section
    //second 0x10
    T1n = digitalRead(T1);
    VLWrite(oVI, oLI, T1n);
    shortMon = T1n;
    //third 0x20
    T2n = digitalRead(T2);
    VLWrite(oVO, oLO, T2n);
    inMon = T2n;
    //first, 0x08
    T3n = digitalRead(T3);   // T(TL trigger pin) 3 n(ew)/b(oolean)
    VLWrite(oVH, oLH, T3n);  //reads the input from the arduino pin connected to the (third) pin as defined above
    ophMon = T3n;

    //this one flips the h2 supply from thermal to para.
    ///T4 and T5 not currwntly working
    T4n = digitalRead(T4);
    VLWrite(oVN, oLN, T4n);
    inMon = T2n;
    T5n = digitalRead(T5);
    VLWrite(oVS, oLS, T5n);
    outMon = T5n;
  }
}

/////////////////////////////////////////
void pressureFunction() {
  ///////////////////////////////////////

  //  Serial.println(tNow);     //put this in if you need to see if the system is chugging when running the code. it slows the printing speed though so not entirely accurate
  if (PrintPressure == 1) {  //if we're recording valves and pressures:
    pCount = pCount + 1;     //add one to pcount. this slows the print frequency without slowing the operation frequency.
    if (tNow - tSt >= pollTime) {
      tSt = tNow;            //after we print reset the timer.
      vA1 = analogRead(A0);  //gets the pressures.
      vA2 = analogRead(A2);
      vA3 = analogRead(A4);
      vA4 = analogRead(A6);
      //vA4 = analogRead(A4);               //can be in if/when we get more pressure gauges.
      String vsA1 = String(vA1);  //makes the recorded pressure integer into a string, bc can't concactenate integers into compound strings.
      String vsA2 = String(vA2);  //this might actually be redundant?
      String vsA3 = String(vA3);
      String vsA4 = String(vA4);
      String ophMo = String(ophMon);
      String inMo = String(inMon);  //does the same with the valve state indicator
      String outMo = String(outMon);
      String n2Mo = String(n2Mon);
      String shortMo = String(shortMon);
      prOut = "P " + vsA1 + ' ' + vsA2 + ' ' + vsA3 + ' ' + vsA4 + ' ' + ophMon + ' ' + inMo + ' ' + outMo + ' ' + n2Mon + ' ' + shortMo + 'C';  //prints the pressures, followed  y the valve states separated by a space for
      Serial.println(prOut);
      //prints a string of the read voltages concactenated with splitting letters to allow matlab to differentiate pressure from each pin. P100D100T100Q.
      //we can add extra pressures read off to the end of the string
    }
  }
}
//////////////////////////////////////////
void VLWrite(int valve, int LED, int power) {
  ////////////////////////////////////////

  // turns on valve and led
  if (power == 1) {
    digitalWrite(valve, HIGH);
    digitalWrite(LED, HIGH);
  } else {
    digitalWrite(valve, LOW);
    digitalWrite(LED, LOW);
  }
}

///////////////////////////////////////

int TTLByter(int T1n, int T2n, int T3n, int T4n, int T5n) {

  //////////////////////////////////////*/
  byte result;
  int a, s, d, f;
  a = s = d = f = 0;
  if (T1n == 1) {  //0x10
    a = 1;
  }
  if (T2n == 1) {  //0x20
    s = 2;
  }
  if (T3n == 1) {  //0x08
    d = 4;
  }
  if (T4n == 1) {
    f = 8;
  }
  result = a + s + d + f;
  return result;
}


/////////////////////////////////////////
void TTLCases(int input) {
  ///////////////////////////////////////

  if (input != 1 && input != 7) {
    fillTime = 0;
    //these two code require a fixed delay after which a second step occurs. The timing used is fillTime (set at top)
    //fillTime resets whenever a different case other than the two-step cases is running. To run the back-to-back, add in a +111 pulse or +000 gap
  }

  switch (input) {
    case 0:  //000
      VLWrite(oVI, oLI, 0);
      inMon = 0;
      VLWrite(oVH, oLH, 0);
      ophMon = 0;
      VLWrite(oVO, oLO, 0);
      outMon = 0;
      break;
    //cell filling & bubbling
    case 1:  //001          //0x10 only
      VLWrite(oVI, oLI, 1);
      inMon = 1;
      VLWrite(oVH, oLH, 0);
      ophMon = 0;
      if (fillTime == 0) {
        zeroTime = millis();
      }
      fillTime = millis() - zeroTime + 1;
      if (fillTime >= pressureTime) {
        VLWrite(oVO, oLO, 1);
        outMon = 1;
      } else {
        VLWrite(oVO, oLO, 0);
      }
      break;

    //open bubbling. pH2 flow through cell.
    case 2:  //010          //0x20 only
      VLWrite(oVI, oLI, 1);
      inMon = 1;
      VLWrite(oVH, oLH, 0);
      ophMon = 0;
      VLWrite(oVO, oLO, 1);
      outMon = 1;
      break;

    //cell filling. opens in. Used to open H2 too - will need to in future
    case 3:  //011
      VLWrite(oVI, oLI, 1);
      inMon = 1;
      VLWrite(oVH, oLH, 0);
      ophMon = 0;
      VLWrite(oVO, oLO, 0);
      outMon = 0;
      break;
    //draining
    case 4:  //100          //0x08 only
      VLWrite(oVI, oLI, 0);
      inMon = 0;
      VLWrite(oVH, oLH, 0);
      ophMon = 0;
      VLWrite(oVO, oLO, 1);
      outMon = 1;
      break;

    //N2 flushout        //0x10 and 0x08 = 0x18 t
    case 5:  //101
      VLWrite(oVI, oLI, 1);
      inMon = 1;
      VLWrite(oVH, oLH, 1);
      ophMon = 1;
      VLWrite(oVO, oLO, 1);
      outMon = 1;
      break;

    case 6:  //110          //currently not doing anything.
      VLWrite(oVI, oLI, 0);
      inMon = 0;
      VLWrite(oVH, oLH, 0);
      ophMon = 0;
      VLWrite(oVO, oLO, 0);
      outMon = 0;
      break;

    case 7:  //111            //currently not doing anything.
      VLWrite(oVI, oLI, 0);
      inMon = 0;
      VLWrite(oVH, oLH, 0);
      ophMon = 0;
      VLWrite(oVO, oLO, 0);
      outMon = 0;
      break;
  }
}
///////////////////////////////////////////
void DeclarePins() {
  /////////////////////////////////////////

  pinMode(outLEDshort, OUTPUT);  //sets the corresponding pins to input or output
  pinMode(outLEDNN, OUTPUT);     //in theory i think these arent needed but arduino can get fussy when you don't declare
  pinMode(outLEDopH, OUTPUT);
  pinMode(outLEDIn, OUTPUT);
  pinMode(outLEDOut, OUTPUT);
  pinMode(V6, OUTPUT);
  pinMode(V7, OUTPUT);
  pinMode(V8, OUTPUT);

  pinMode(outValveShort, OUTPUT);
  pinMode(outValveNN, OUTPUT);
  pinMode(outValveopH, OUTPUT);
  pinMode(outValveIn, OUTPUT);
  pinMode(outValveOut, OUTPUT);

  pinMode(T1, INPUT);
  pinMode(T2, INPUT);
  pinMode(T3, INPUT);
  pinMode(T4, INPUT);
  pinMode(T5, INPUT);

  pinMode(S1, OUTPUT);
  pinMode(S2, OUTPUT);
  pinMode(S3, OUTPUT);
  pinMode(S4, OUTPUT);
  pinMode(S5, OUTPUT);
  pinMode(S6, OUTPUT);
  pinMode(S7, OUTPUT);
  pinMode(S8, OUTPUT);
}
///////////////////////////////
void AllTheLights() {
  ///////////////////////////////

  //this turns all the lights on briefly as the arduino starts up.
  digitalWrite(S1, HIGH);
  digitalWrite(S2, HIGH);
  digitalWrite(S3, HIGH);
  digitalWrite(S4, HIGH);
  digitalWrite(S5, HIGH);
  digitalWrite(S6, HIGH);
  digitalWrite(S7, HIGH);
  digitalWrite(S8, HIGH);
  digitalWrite(outLEDshort, HIGH);
  digitalWrite(outLEDNN, HIGH);
  digitalWrite(outLEDopH, HIGH);
  digitalWrite(outLEDIn, HIGH);
  digitalWrite(outLEDOut, HIGH);
  digitalWrite(V6, HIGH);
  digitalWrite(V7, HIGH);
  digitalWrite(V8, HIGH);

  delay(200);

  digitalWrite(S1, LOW);
  digitalWrite(S2, LOW);
  digitalWrite(S3, LOW);
  digitalWrite(S4, LOW);
  digitalWrite(S5, LOW);
  digitalWrite(S6, LOW);
  digitalWrite(S7, LOW);
  digitalWrite(S8, LOW);
  digitalWrite(outLEDshort, LOW);
  digitalWrite(outLEDNN, LOW);
  digitalWrite(outLEDopH, LOW);
  digitalWrite(outLEDIn, LOW);
  digitalWrite(outLEDOut, LOW);
  digitalWrite(V6, LOW);
  digitalWrite(V7, LOW);
  digitalWrite(V8, LOW);
}





void spinsolver(int exec[9][2]) {
  Serial.println("active");
  //if (Serial.available() > 0) {

  sequence = Serial.readString();
  Serial.println(sequence);
  //Serial.readString();
  //while (Serial.available() == 0) {
  //}
  //sequence = (Serial.readString());
  Serial.println("string loaded");
    digitalWrite(S6, HIGH);
  //decompile the string into an array of command steps
  stepsStr = sequence.substring(0);
  steps = stepsStr.toInt();
  //String stepsStr = String(steps);
  Serial.println(stepsStr);

  //for (int i = 0; i < steps; i++) {
  int steplocator = sequence.indexOf('s');
  int seqLen = sequence.length();
  int start = steplocator + 1;
  stepno = 0;
  Serial.print("seq length is: ");
  Serial.println(seqLen);
  //for position in string x
  for (int x = (steplocator + 1); x < seqLen; x++) {

    //read each position in the string.
    //once a character is reached, step is complete. calculated here and loaded into exec matrix
    if (isAlpha(sequence.charAt(x))) {
      int end = x;
      durationStr = sequence.substring(start, end);
      int stepDur = durationStr.toInt();
      acStepDur = stepDur * 100;
      exec[stepno][0] = acStepDur;


      //Serial.println(stepno);
      //character declares what type of step to process. processed here and loaded into exec matrix
      char StepType = sequence.charAt(x);
      start = x + 1;
      if (StepType == 'b') {
        //load bubbling step into executable
        exec[stepno][1] = 1;

        //use these lines here and down if you need to dsebug this part of the program
        //Serial.print("step " + stepno);
        //Serial.print(" bubbling for ");
        //Serial.println(acStepDur);
      }
      if (StepType == 'd') {
        //load delay time step into executable
        exec[stepno][1] = 2;
        /*Serial.print("step " + stepno);
        Serial.print(" delay for ");
        Serial.println(acStepDur);*/
      }
      if (StepType == 'n') {
        //load alt bubble time step into executable
        exec[stepno][1] = 3;
      }
      stepno = stepno + 1;
    }
  }
  //Serial.print(steps);  /*for (int i = 0; i < steps; i++) { /*if (execType[i] != 0)   {Serial.print(execType[i]);Serial.print(" "); Serial.println(execTime[i]);*/}
  //}
  return (exec);
  Serial.print("sequence loaded: ");
  Serial.println(sequence);
  digitalWrite(S7, HIGH);
}

void ssexecute(int executable[9][2]) {

  //theres probably a better/cleverer way of doing this which allows continuous pressure logging through the bubbling steps but i'm not going to try and do that now.
  //it would also be better bc it would allow creation of an emergency shutdown mid bubble
  //as it stands if you need to shut down, pulling the power out is pretty effective.
  if (executable[0][0] != 0 && executable[0][0] != 0) {
    for (int i = 0; i < 10; i++) {
      int time = executable[i][0];
      int type = executable[i][1];
      if (type == 0) {
        //Serial.println("ard. seq. done");
        break;
      }
      if (type == 1) {
        VLWrite(oVI, oLI, 1);
        inMon = 1;
        VLWrite(oVH, oLH, 0);
        ophMon = 0;
        VLWrite(oVO, oLO, 1);
        outMon = 1;

        //this is a les sthan ideal way of doing  things because it stops all code execution during the bubbling time
        delay(time);

        VLWrite(oVI, oLI, 0);
        inMon = 0;
        VLWrite(oVH, oLH, 0);
        ophMon = 0;
        VLWrite(oVO, oLO, 0);
        outMon = 0;

        //Serial.print("bubbling ");
        //Serial.println(i);
      }
      if (type == 2) {
        VLWrite(oVI, oLI, 0);
        inMon = 0;
        VLWrite(oVH, oLH, 0);
        ophMon = 0;
        VLWrite(oVO, oLO, 0);
        outMon = 0;
        delay(time);
      }
    }
  }
}


//-------- _+@      _~@       __@        ~#@       __~@                                                         __~@
//----- _`\<,_    _`\<,_    _`\<,_     _`\<,_    _`\<,_                                                       _`\<,_
//---- (*)/ (*)  (*)/ (*)  (*)/ (*)  (O)/ (*)  (*)/ ( )                                                     (*)/ ( )
//~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
