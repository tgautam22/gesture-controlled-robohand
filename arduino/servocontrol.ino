#include <Servo.h>   // library used to control servo motors

// create an array to store 5 servo objects
Servo servos[5];

// pins where each servo signal wire is connected
// order: Thumb, Index, Middle, Ring, Pinky
int pins[5] = {3, 5, 9, 6, 10};

// servo positions when finger is open
int OPEN_POS[5]   = {180, 180, 180, 180, 180};

// servo positions when finger is closed
int CLOSED_POS[5] = {10, 10, 10, 10, 10};


void setup() {
  // start serial communication with the PC
  Serial.begin(115200);

  // attach each servo to its pin
  // move all servos to open position at startup
  for (int i = 0; i < 5; i++) {
    servos[i].attach(pins[i]);   // tell servo which pin it uses
    servos[i].write(OPEN_POS[i]); // start with hand open
  }
}

void loop() {
  // if no data is coming in, do nothing
  if (!Serial.available()) return;

  // read one full line from Python (ex: "1,0,1,1,0")
  String line = Serial.readStringUntil('\n');

  // remove any extra spaces or newline characters
  line.trim();

  // array to store parsed finger states
  int state[5];

  // index for which finger we are filling
  int idx = 0;

  // starting index of the current number in the string
  int start = 0;

  // loop through the entire string
  for (int i = 0; i <= line.length(); i++) {

    // when we hit a comma or the end of the string
    if (i == line.length() || line.charAt(i) == ',') {

      // convert substring to integer (0 or 1)
      state[idx++] = line.substring(start, i).toInt();

      // move start to the next number
      start = i + 1;

      // stop if we already read 5 values
      if (idx >= 5) break;
    }
  }

  // if we did not receive exactly 5 values, ignore this line
  if (idx != 5) return;

  // move each servo based on its state
  for (int i = 0; i < 5; i++) {

    // if value is 1, open the finger
    if (state[i] == 1)
      servos[i].write(OPEN_POS[i]);

    // if value is 0, close the finger
    else
      servos[i].write(CLOSED_POS[i]);
  }
}
