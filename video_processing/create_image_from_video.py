import argparse
import cv2
import os
import mediapipe as mp
import numpy as np
import math
import datetime

# --- Constants for Eye Aspect Ratio ---
# Threshold: Adjust this value based on testing; higher means eyes must be wider open.
EAR_THRESHOLD = 0.20
# Indices for facial landmarks for left and right eyes based on Mediapipe Face Mesh
# https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
LEFT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
# Points for EAR calculation (top, bottom, left, right corners)
# Left eye: top, bottom, left_corner, right_corner
LEFT_EAR_POINTS = [386, 374, 263, 362]
# Right eye: top, bottom, left_corner, right_corner
RIGHT_EAR_POINTS = [159, 145, 133, 33]
# --------------------------------------

def calculate_ear(eye_landmarks, frame_shape):
    """Calculates the Eye Aspect Ratio (EAR) for a single eye."""
    try:
        # Get pixel coordinates from normalized landmarks
        p1 = (eye_landmarks[0].x * frame_shape[1], eye_landmarks[0].y * frame_shape[0]) # Vertical point 1 (Top)
        p2 = (eye_landmarks[1].x * frame_shape[1], eye_landmarks[1].y * frame_shape[0]) # Vertical point 2 (Bottom)
        p3 = (eye_landmarks[2].x * frame_shape[1], eye_landmarks[2].y * frame_shape[0]) # Horizontal point 1 (Left corner)
        p4 = (eye_landmarks[3].x * frame_shape[1], eye_landmarks[3].y * frame_shape[0]) # Horizontal point 2 (Right corner)

        # Euclidean distance
        vertical_dist = math.dist(p1, p2)
        horizontal_dist = math.dist(p3, p4)

        if horizontal_dist == 0:
            return 0.0

        ear = vertical_dist / horizontal_dist
        return ear
    except Exception as e:
        print(f"Error calculating EAR: {e}")
        return 0.0


def extract_frame(video_path, quote):
    """
    Loads a video, finds the first frame with open eyes, adds quote text.

    Args:
        video_path (str): Path to the video file.
        quote (str): The quote to add to the frame.

    Returns:
        numpy.ndarray: The extracted video frame with quote, or None if not found/error.
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return None

    # Initialize Mediapipe Face Mesh
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1, # Assume one primary face
        refine_landmarks=True, # Get finer landmarks for eyes
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    selected_frame = None
    frame_count = 0
    max_frames_to_check = 1500 # Limit frames to check to avoid long processing

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Reached end of video or cannot read frame.")
            break

        frame_count += 1
        if frame_count > max_frames_to_check:
            print(f"Stopped processing after checking {max_frames_to_check} frames.")
            break

        # Convert BGR frame to RGB for Mediapipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Process the frame
        results = face_mesh.process(rgb_frame)

        eyes_open = False
        if results.multi_face_landmarks:
            # Assume only one face detected (max_num_faces=1)
            face_landmarks = results.multi_face_landmarks[0]
            landmarks = face_landmarks.landmark
            frame_shape = frame.shape # (h, w, c)

            # Extract specific eye landmark points for EAR calculation
            try:
                left_eye_lm = [landmarks[i] for i in LEFT_EAR_POINTS]
                right_eye_lm = [landmarks[i] for i in RIGHT_EAR_POINTS]

                # Calculate EAR for both eyes
                left_ear = calculate_ear(left_eye_lm, frame_shape)
                right_ear = calculate_ear(right_eye_lm, frame_shape)

                # Average EAR or check both eyes
                avg_ear = (left_ear + right_ear) / 2.0

                # Check if eyes are open based on threshold
                if avg_ear > EAR_THRESHOLD:
                    eyes_open = True
                    print(f"Frame {frame_count}: Eyes detected as open (EAR: {avg_ear:.2f})")

            except IndexError:
                 print(f"Frame {frame_count}: Could not extract all required landmarks.")
            except Exception as e:
                 print(f"Frame {frame_count}: Error processing landmarks: {e}")


        if eyes_open:
            selected_frame = frame.copy() # Keep a copy of the selected frame
            break # Exit loop once a suitable frame is found

    # Release resources
    cap.release()
    face_mesh.close()

    if selected_frame is None:
        print("Could not find a frame with open eyes within the checked range.")
        return None

    # --- Add quote text to the selected frame ---
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (255, 255, 255)  # White color in BGR
    thickness = 2 # Made thickness slightly bolder
    line_type = cv2.LINE_AA

    (h, w) = selected_frame.shape[:2]
    text_position = (int(w * 0.05), int(h * 0.95)) # Bottom-left

    # Add background rectangle for better text visibility (optional)
    (text_w, text_h), _ = cv2.getTextSize(quote, font, font_scale, thickness)
    padding = 10
    rect_start = (text_position[0] - padding, text_position[1] - text_h - padding)
    rect_end = (text_position[0] + text_w + padding, text_position[1] + padding)
    # Draw semi-transparent rectangle
    overlay = selected_frame.copy()
    cv2.rectangle(overlay, rect_start, rect_end, (0, 0, 0), -1) # Black background
    alpha = 0.5 # Transparency factor
    cv2.addWeighted(overlay, alpha, selected_frame, 1 - alpha, 0, selected_frame)

    # Put the text on top of the rectangle
    cv2.putText(selected_frame, quote, text_position, font, font_scale, color, thickness, line_type)
    # -------------------------------------------

    print(f"Successfully extracted frame {frame_count} with open eyes and added quote.")
    return selected_frame

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract a frame from a video.')
    parser.add_argument('video_path', type=str, help='Path to the video file.')
    parser.add_argument('quote', type=str, help='A quote associated with the video.')
    parser.add_argument('--output_dir', type=str, default='img/output', help='Directory to save the extracted frame (default: img/output).')

    args = parser.parse_args()

    # Call the function to extract the frame
    extracted_frame = extract_frame(args.video_path, args.quote)

    if extracted_frame is not None:
        # Ensure the output directory exists
        os.makedirs(args.output_dir, exist_ok=True)

        # Create a timestamp string
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Get base video filename without extension
        video_basename = os.path.splitext(os.path.basename(args.video_path))[0]
        # Construct filename: videoname_timestamp_frame.jpg
        output_filename = os.path.join(args.output_dir, f"{video_basename}_{timestamp}_frame.jpg")

        # Save the frame
        try:
            cv2.imwrite(output_filename, extracted_frame)
            print(f"Frame successfully saved as {output_filename}")
        except Exception as e:
            print(f"Error saving frame: {e}")
            print("Failed to save frame.")
    else:
        print("Failed to extract frame.")
