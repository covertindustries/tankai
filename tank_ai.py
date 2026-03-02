"""
Tank AI — Raspberry Pi tank robot with vision and obstacle avoidance.

This script runs a small tank robot that:
  - Uses the camera and YOLO to detect objects (e.g. dogs); says "Hello Pepe" once when a dog appears.
  - Records a video clip to the "recordings" folder while a dog is in the scene (saved when they leave).
  - Uses an ultrasonic sensor to measure distance and auto-brakes when too close to obstacles.
  - Lets you drive with the keyboard: W/S = forward/back, A/D = turn left/right, Q = quit.

Hardware: Raspberry Pi with GPIO motors, Picamera2, ultrasonic (HC-SR04-style) sensor.
Press Ctrl+C or Q to stop motors and exit cleanly.
"""
# Run with: source tankai/bin/activate && python3 tank_ai.py

# =========================
# IMPORTS
# =========================

import os
from dotenv import load_dotenv

# Load .env from the script directory so it's found when run from any cwd
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from gpiozero import Motor, DistanceSensor
from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import signal
import sys
import subprocess
import time
from datetime import datetime

from notifications.whatsapp import notify_recording_saved


# =========================
# MOTOR SETUP
# =========================
# GPIO pins: left wheel (24/23), right wheel (5/6). Speed values are 0–1.

left_motor = Motor(forward=24, backward=23)
right_motor = Motor(forward=5, backward=6)

MAX_SPEED = 0.20      # Forward/backward speed (kept low for safety)
TURN_SPEED = 0.15     # Speed when turning in place
STOP_DISTANCE = 15    # cm — if closer than this, we auto-brake and block forward


# =========================
# ULTRASONIC SETUP
# =========================
# HC-SR04-style sensor: echo=22, trigger=27. max_distance is in meters.

sensor = DistanceSensor(echo=22, trigger=27, max_distance=4)


# =========================
# CAMERA SETUP
# =========================
# Picamera2 at 640x480 RGB for YOLO and the on-screen preview.

picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()


# =========================
# YOLO MODEL (Nano)
# =========================
# yolov8n.pt is the lightweight model for Pi; detects COCO classes (person, dog, etc.).

model = YOLO("yolov8n.pt")


# =========================
# CLEAN SHUTDOWN
# =========================
# Stop motors and close OpenCV window on Ctrl+C or Q.

def shutdown(signal_received=None, frame=None):
    """Stop both motors, close the camera preview window (if any), and exit."""
    global video_writer
    left_motor.stop()
    right_motor.stop()
    if video_writer is not None:
        video_writer.release()
        video_writer = None
    if not HEADLESS:
        cv2.destroyAllWindows()
    print("\nShutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)


# =========================
# DISPLAY / HEADLESS
# =========================
# No DISPLAY (e.g. SSH) or HEADLESS=1: skip cv2.imshow so the app runs without a GUI.
# Detection, recording, motors and WhatsApp still work; keyboard control needs a display.

HEADLESS = os.environ.get("HEADLESS", "").strip() == "1" or not os.environ.get("DISPLAY", "").strip()

# =========================
# START MESSAGE
# =========================

print("\n--- TANK AI MODE STARTED ---")
if HEADLESS:
    print("(headless — no display; detection, recording & notifications only)")
else:
    print("W = Forward   S = Backward   A = Left   D = Right   Q = Quit")
print("Dog in scene → records to ./recordings/ (saved when dog leaves)")
print("----------------------------\n")


# =========================
# EVENT RECORDING (DOG IN SCENE)
# =========================
# When a dog is detected, we record video to this folder. One clip per "dog appearance";
# recording starts when the dog enters the frame and stops when they leave.

RECORDINGS_DIR = "recordings"
RECORD_FPS = 10  # Frames per second in the saved video (loop isn't fixed FPS, this is for playback)

# Create recordings directory if it doesn't exist
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# =========================
# SPEECH / DETECTION STATE
# =========================
# dog_seen: have we already said "Hello Pepe" for the current dog? Used so we speak
# only once when a dog first appears, not every frame. Reset when the dog leaves the frame.

dog_seen = False
video_writer = None  # cv2.VideoWriter; active while dog is in scene
current_recording_path = None  # path of the clip being recorded (for notification on save)


# =========================
# MAIN LOOP (NON-BLOCKING)
# =========================
# Each iteration: capture image → run YOLO → check for dog → update distance → handle keys.
# cv2.waitKey(1) keeps the loop responsive so we don't block on input.

while True:

    # --- Capture and preprocess ---
    frame = picam2.capture_array()
    frame = cv2.flip(frame, -1)  # Camera is mounted upside down; flip so image is right-side up

    # --- Object detection ---
    # imgsz=320, conf=0.4: smaller input and confidence threshold for faster runs on Pi
    results = model(frame, imgsz=320, conf=0.4, verbose=False)
    annotated_frame = results[0].plot()  # Draw bounding boxes on the frame for display

    # --- Dog detection: get class IDs from this frame ---
    # YOLO returns class indices (ints); model.names maps index → name (e.g. 16 → "dog")
    dog_present = False
    try:
        cls_tensor = results[0].boxes.cls
        # Handle both PyTorch tensors and numpy arrays (depends on YOLO/device)
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

    # --- Speak once when dog first appears ---
    # On transition from no-dog to dog: run espeak in background (Popen), set dog_seen.
    # When dog leaves frame: clear dog_seen so we'll speak again next time we see a dog.
    if dog_present and not dog_seen:
        try:
            subprocess.Popen(["espeak", "Hello Pepe"])  # Non-blocking; doesn't wait for speech to finish
        except Exception:
            pass  # espeak may not be installed; ignore
        dog_seen = True
    elif not dog_present and dog_seen:
        dog_seen = False

    # --- Ultrasonic distance (sensor.distance is in meters) ---
    distance_cm = sensor.distance * 100

    # --- Draw distance and warnings on the image ---
    cv2.putText(
        annotated_frame,
        f"Distance: {distance_cm:.1f} cm",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    # --- Auto-brake when obstacle is too close ---
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

    # --- Record video while dog is in scene ---
    # Write after overlays so the saved clip includes distance and "AUTO BRAKE!" if shown.
    if dog_present:
        if video_writer is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            current_recording_path = os.path.join(RECORDINGS_DIR, f"dog_{timestamp}.avi")
            h, w = annotated_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")  # MJPG works well on Pi
            video_writer = cv2.VideoWriter(current_recording_path, fourcc, RECORD_FPS, (w, h))
            print(f"Recording: {current_recording_path}")
        video_writer.write(annotated_frame)
    elif video_writer is not None:
        saved_path = current_recording_path  # capture before clearing
        video_writer.release()
        video_writer = None
        current_recording_path = None
        print("Recording saved.")
        notify_recording_saved(saved_path)

    # --- Show annotated frame (boxes + distance + "AUTO BRAKE!" if active) ---
    if HEADLESS:
        key = -1
        time.sleep(0.01)  # avoid busy loop when no window
    else:
        cv2.imshow("Tank AI Vision", annotated_frame)
        key = cv2.waitKey(1) & 0xFF

    # Forward only if not in auto-brake range (safety)
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

    # No key pressed (or key not handled): stop motors so tank doesn't keep moving
    else:
        left_motor.stop()
        right_motor.stop()