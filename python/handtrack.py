import cv2              # used to read camera frames and draw on them
import math             # math functions like acos and degrees
import time             # used for delays and timing calibration
import serial           # used to talk to Arduino over USB
import numpy as np      # used for vector and distance calculations
import mediapipe as mp  # Google hand tracking library
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# set up serial communication
PORT = "COM3"           # COM port where Arduino is connected
BAUD = 115200           # Arduino baud rate
ser = serial.Serial(PORT, BAUD, timeout=0)
time.sleep(2)           # give Arduino time to reset


# colors used when drawing on the camera frame
# OpenCV uses BGR, not RGB
BLUE = (255, 0, 0)
YELLOW = (0, 255, 255)
RED = (0, 0, 255)

# landmark index pairs that form the hand skeleton
# each pair means "draw a line between these two points"
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),        # thumb
    (0,5),(5,6),(6,7),(7,8),        # index
    (5,9),(9,10),(10,11),(11,12),   # middle
    (9,13),(13,14),(14,15),(15,16), # ring
    (13,17),(17,18),(18,19),(19,20),# pinky
    (0,17)                          # palm base
]


# calculates the angle at point b using points a, b, and c
# this is used to measure finger bending
def angle(a, b, c):
    # vector from b to a
    ba = np.array([a.x - b.x, a.y - b.y, a.z - b.z])

    # vector from b to c
    bc = np.array([c.x - b.x, c.y - b.y, c.z - b.z])

    # cosine of the angle using dot product
    cosang = np.dot(ba, bc) / ((np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-6)

    # clamp value so acos does not crash
    cosang = np.clip(cosang, -1, 1)

    # convert angle from radians to degrees
    return math.degrees(math.acos(cosang))


# calculates straight-line distance between two landmarks
def dist(a, b):
    return math.sqrt(
        (a.x - b.x)**2 +
        (a.y - b.y)**2 +
        (a.z - b.z)**2
    )


# estimates the center of the palm
# uses wrist, index base, and pinky base
def palm_center(hand):
    x = (hand[0].x + hand[5].x + hand[17].x) / 3
    y = (hand[0].y + hand[5].y + hand[17].y) / 3
    z = (hand[0].z + hand[5].z + hand[17].z) / 3

    # simple object to store x, y, z
    class P: pass
    p = P()
    p.x = x
    p.y = y
    p.z = z
    return p


# keeps a value between 0 and 1
# useful for normalized values
def clamp01(v):
    return max(0.0, min(1.0, v))


# mediapipe setup
BaseOptions = python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

# configure the hand detector
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="hand_landmarker.task"),
    running_mode=VisionRunningMode.VIDEO,  # video mode needs timestamps
    num_hands=1                            # only track one hand
)

# create the detector object
detector = HandLandmarker.create_from_options(options)


# open the webcam (0 = default camera)
cap = cv2.VideoCapture(0)


# calibration timing
STAGE_TIME = 5.0         # seconds per calibration step
stage = "WAIT"           # current calibration stage
stage_start = 0          # time when stage started

# store finger angles when hand is open
open_vals = [0, 0, 0, 0]

# store finger angles when hand is closed
closed_vals = [0, 0, 0, 0]

# thumb uses distance instead of angle
thumb_open = 0.0
thumb_closed = 0.0

# values sent to Arduino
# 1 = finger open, 0 = finger closed
finger_state = [1, 1, 1, 1, 1]  # thumb, index, middle, ring, pinky


# main loop
while True:
    # read a frame from the camera
    ret, frame = cap.read()
    if not ret:
        break

    # get image height and width
    h, w, _ = frame.shape

    # convert frame to RGB (mediapipe expects RGB)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # wrap image for mediapipe
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    # timestamp in milliseconds (required by mediapipe video mode)
    ts = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)

    # run hand detection
    result = detector.detect_for_video(mp_image, ts)

    # show instruction before calibration starts
    if stage == "WAIT":
        cv2.putText(
            frame,
            "PRESS 'S' TO START CALIBRATION",
            (40, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            RED,
            2
        )

    # if a hand was detected
    if result.hand_landmarks:
        hand = result.hand_landmarks[0]

        # draw hand skeleton lines
        for a, b in HAND_CONNECTIONS:
            x1, y1 = int(hand[a].x * w), int(hand[a].y * h)
            x2, y2 = int(hand[b].x * w), int(hand[b].y * h)
            cv2.line(frame, (x1, y1), (x2, y2), BLUE, 2)

        # draw each landmark as a dot
        for lm in hand:
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (x, y), 4, BLUE, -1)

        # calculate finger bend angles (index to pinky)
        angles = [
            angle(hand[5], hand[6], hand[7]),
            angle(hand[9], hand[10], hand[11]),
            angle(hand[13], hand[14], hand[15]),
            angle(hand[17], hand[18], hand[19])
        ]

        # calculate thumb distance from palm
        palm = palm_center(hand)
        thumb_val = dist(hand[4], palm) / (dist(hand[5], hand[17]) + 1e-6)

        # calibration stages
        if stage in ["OPEN", "CLOSED"]:
            elapsed = time.time() - stage_start

            # choose text based on stage
            text = "KEEP HAND OPEN" if stage == "OPEN" else "MAKE A FIST"

            cv2.putText(
                frame,
                f"{text} ({STAGE_TIME - elapsed:0.1f}s)",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                RED,
                2
            )

            # save values depending on stage
            if stage == "OPEN":
                open_vals = angles.copy()
                thumb_open = thumb_val
            else:
                closed_vals = angles.copy()
                thumb_closed = thumb_val

            # move to next stage when time is up
            if elapsed >= STAGE_TIME:
                stage = "CLOSED" if stage == "OPEN" else "DONE"
                stage_start = time.time()

        # after calibration is complete
        if stage == "DONE":
            curls = []

            # normalize curl for each finger
            for i in range(4):
                curl = (open_vals[i] - angles[i]) / (open_vals[i] - closed_vals[i] + 1e-6)
                curls.append(clamp01(curl))

            # normalize thumb curl
            thumb_curl = clamp01(
                (thumb_open - thumb_val) /
                (thumb_open - thumb_closed + 1e-6)
            )

            # combine thumb and fingers
            values = [thumb_curl] + curls

            # convert curl values to binary open/closed
            for i in range(5):
                finger_state[i] = 1 if values[i] < 0.5 else 0

            # send finger states to Arduino
            msg = ",".join(str(v) for v in finger_state) + "\n"
            ser.write(msg.encode())

            # draw palm center
            pcx, pcy = int(palm.x * w), int(palm.y * h)
            cv2.circle(frame, (pcx, pcy), 6, YELLOW, -1)

            # show live curl values on screen
            cv2.putText(
                frame,
                f"T:{values[0]:.2f} I:{values[1]:.2f} M:{values[2]:.2f} R:{values[3]:.2f} P:{values[4]:.2f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                BLUE,
                2
            )

    # show camera window
    cv2.imshow("Hand to Servo Control", frame)

    # keyboard input
    key = cv2.waitKey(1) & 0xFF

    # quit program
    if key == ord('q'):
        break

    # start calibration
    if key == ord('s') and stage == "WAIT":
        stage = "OPEN"
        stage_start = time.time()


# release camera and close everything
cap.release()
ser.close()
cv2.destroyAllWindows()
