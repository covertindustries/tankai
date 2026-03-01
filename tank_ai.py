# =========================
# IMPORTS
# =========================

from gpiozero import Motor, DistanceSensor
from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import signal
import sys
import subprocess


# =========================
# MOTOR SETUP
# =========================

left_motor = Motor(forward=24, backward=23)
right_motor = Motor(forward=5, backward=6)

MAX_SPEED = 0.20
TURN_SPEED = 0.15
STOP_DISTANCE = 15  # cm


# =========================
# ULTRASONIC SETUP
# =========================

sensor = DistanceSensor(echo=22, trigger=27, max_distance=4)


# =========================
# CAMERA SETUP
# =========================

picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()


# =========================
# YOLO MODEL (Nano)
# =========================

model = YOLO("yolov8n.pt")


# =========================
# CLEAN SHUTDOWN
# =========================

def shutdown(signal_received=None, frame=None):
    left_motor.stop()
    right_motor.stop()
    cv2.destroyAllWindows()
    print("\nShutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)


# =========================
# START MESSAGE
# =========================

print("\n--- TANK AI MODE STARTED ---")
print("W = Forward")
print("S = Backward")
print("A = Left")
print("D = Right")
print("Q = Quit")
print("----------------------------\n")


# =========================
# SPEECH / DETECTION STATE
# =========================

# Use espeak to say the phrase (common on Raspberry Pi).
# This will be launched asynchronously so the loop isn't blocked.
dog_seen = False


# =========================
# MAIN LOOP (NON-BLOCKING)
# =========================

while True:

    # Capture frame
    frame = picam2.capture_array()

    # Flip camera (mounted upside down)
    frame = cv2.flip(frame, -1)

    # Run YOLO (lightweight settings for Pi)
    results = model(frame, imgsz=320, conf=0.4, verbose=False)
    annotated_frame = results[0].plot()

    # Check if a 'dog' was detected in this frame
    dog_present = False
    try:
        cls_tensor = results[0].boxes.cls  # class indices
        # convert tensor/array to iterable of ints
        if hasattr(cls_tensor, "cpu"):
            cls_arr = cls_tensor.cpu().numpy()
        elif hasattr(cls_tensor, "numpy"):
            cls_arr = cls_tensor.numpy()
        else:
            cls_arr = list(cls_tensor)
        for c in cls_arr:
            if model.names.get(int(c), "") == "dog":
                dog_present = True
                break
    except Exception:
        dog_present = False

    # If dog appears (transition from not-seen to seen), speak once
    if dog_present and not dog_seen:
        try:
            subprocess.Popen(["espeak", "Hello Pepe"])
        except Exception:
            # if espeak isn't available, ignore the error silently
            pass
        dog_seen = True
    elif not dog_present and dog_seen:
        # reset so we can speak again next time a dog appears
        dog_seen = False

    # Get ultrasonic distance
    distance_cm = sensor.distance * 100

    # Overlay distance
    cv2.putText(
        annotated_frame,
        f"Distance: {distance_cm:.1f} cm",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    # Auto brake if too close
    if distance_cm < STOP_DISTANCE:
        left_motor.stop()
        right_motor.stop()
        cv2.putText(
            annotated_frame,
            "AUTO BRAKE!",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

    # Show frame
    cv2.imshow("Tank AI Vision", annotated_frame)

    # Non-blocking key input
    key = cv2.waitKey(1) & 0xFF

    if key == ord('w') and distance_cm >= STOP_DISTANCE:
        left_motor.forward(MAX_SPEED)
        right_motor.forward(MAX_SPEED)

    elif key == ord('s'):
        left_motor.backward(MAX_SPEED)
        right_motor.backward(MAX_SPEED)

    elif key == ord('a'):
        left_motor.backward(TURN_SPEED)
        right_motor.forward(TURN_SPEED)

    elif key == ord('d'):
        left_motor.forward(TURN_SPEED)
        right_motor.backward(TURN_SPEED)

    elif key == ord('q'):
        shutdown()

    else:
        left_motor.stop()
        right_motor.stop()