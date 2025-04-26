import argparse
import cv2
import os
import mediapipe as mp
import numpy as np
import math
import datetime
import json
import openai
from PIL import Image, ImageDraw, ImageFont

# --- Font Settings (User might need to adjust FONT_PATH) ---
# Ensure the font file supports German characters (e.g., Arial, Verdana, DejaVuSans)
# Common paths:
# macOS: /System/Library/Fonts/Supplemental/Arial Unicode.ttf
# Linux: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
# Windows: C:/Windows/Fonts/arial.ttf
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf" # <-- ADJUST THIS PATH IF NEEDED
FONT_SIZE = 25 # Reduced font size from 40
# -----------------------------------------------------------

# --- Helper function for text wrapping by pixel width ---
def wrap_text_by_width(text, font, max_width, draw):
    """Wraps text to fit within a specific pixel width."""
    lines = []
    if not text:
        return lines

    words = text.split()
    current_line = ""

    for word in words:
        # Check width of potential new line
        test_line = f"{current_line} {word}".strip()
        # Use textbbox for more accurate width calculation
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line = test_line
        else:
            # Add the previous line if it wasn't empty
            if current_line:
                lines.append(current_line)
            # Start new line with the current word
            current_line = word
            # Check if the single word itself is too long (optional: could split the word)
            bbox = draw.textbbox((0, 0), current_line, font=font)
            word_width = bbox[2] - bbox[0]
            if word_width > max_width:
                # Handle very long words if necessary (e.g., hyphenate or just let it overflow)
                print(f"Warning: Word '{word}' is wider than max_width.")

    # Add the last line
    if current_line:
        lines.append(current_line)

    return lines
# ---------------------------------------------------------

# --- Constants for Eye Aspect Ratio ---
# Threshold: Adjust this value based on testing; higher means eyes must be wider open.
EAR_THRESHOLD = 0.32
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

# NOTE: Ensure OPENAI_API_KEY environment variable is set.
openai.api_key = os.getenv("OPENAI_API_KEY")

def find_quotes_recursively(data):
    """Recursively searches for 'quote' keys in nested JSON data (dicts/lists)."""
    quotes = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'quote' and isinstance(value, str):
                quotes.append(value)
            else:
                quotes.extend(find_quotes_recursively(value))
    elif isinstance(data, list):
        for item in data:
            quotes.extend(find_quotes_recursively(item))
    return quotes

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


def extract_frame(video_path, json_path):
    """
    Loads a video, finds the first frame with open eyes, reads spoken text from
    a potentially nested JSON file by finding all 'quote' keys, generates a catchy
    quote using OpenAI, and adds it to the frame.

    Args:
        video_path (str): Path to the video file.
        json_path (str): Path to the .json file containing potentially nested quotes.

    Returns:
        numpy.ndarray: The extracted video frame with quote, or None if not found/error.
    """
    # --- Read spoken text from JSON file (recursive search) ---
    spoken_text = ""
    try:
        with open(json_path, 'r') as f:
            # Load the entire file as a single JSON object
            data = json.load(f)
            # Recursively find all quotes
            all_quotes = find_quotes_recursively(data)
            if all_quotes:
                spoken_text = " ".join(all_quotes) # Concatenate quotes
            else:
                print(f"Warning: No 'quote' keys found in {json_path}")
                return None # Or handle differently if needed

    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_path}. Is it valid JSON?")
        return None
    except Exception as e:
        print(f"Error reading or processing JSON file {json_path}: {e}")
        return None
    # --- Generate catchy quote using OpenAI ---
    catchy_quote = "Video Thumbnail" # Default fallback
    if spoken_text and openai.api_key:
        try:
            # prompt = f"Gib mir einen eingängigen und polarisierenden Satz auf Deutsch (max. 10 Wörter), der sich aus diesem Text ergibt: {spoken_text}." # Old German prompt
            prompt = f"Gib mir einen eingängigen und polarisierenden Satz auf Deutsch (max. 8 Wörter), der sich aus diesem Text ergibt: {spoken_text}." # New German prompt (max 8 words)
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo", # Or another suitable model like gpt-4
                messages=[
                    {"role": "system", "content": "Du bist ein Assistent, der eingängige und polarisierende Video-Thumbnail-Titel auf Deutsch mit maximal 8 Wörtern erstellt." }, # Updated German system message
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20, # Reduced max_tokens slightly for shorter output
                temperature=0.8,
                n=1,
                stop=None,
            )
            if response.choices:
                catchy_quote = response.choices[0].message.content.strip().strip('"')
                print(f"Generated catchy quote: {catchy_quote}")
            else:
                 print("Warning: OpenAI did not return a quote.")

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            print("Using default quote.")
    elif not openai.api_key:
        print("Warning: OPENAI_API_KEY not set. Using default quote.")
    else:
        print("Using default quote as no spoken text was found.")


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

    # --- Add quote text to the selected frame using Pillow ---
    try:
        # Convert OpenCV BGR image to Pillow RGB image
        pil_image = Image.fromarray(cv2.cvtColor(selected_frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # Load the TrueType font
        try:
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        except IOError:
            print(f"Error: Font file not found at {FONT_PATH}. Using default font (may not support special chars).")
            # Fallback to a default Pillow font if TTF fails (limited character support)
            try:
                font = ImageFont.load_default()
                # Adjust size for default font if needed
                # font = ImageFont.truetype("some_fallback.ttf", FONT_SIZE) # Alternative fallback
            except Exception as e:
                 print(f"Could not load default font: {e}")
                 # If default font fails, we might have to skip text drawing or raise error
                 # For now, let's proceed without guaranteed text support
                 font = None

        if font:
            color = (255, 255, 255)  # White color in RGB for Pillow
            background_color = (0, 0, 0) # Black background
            alpha_blend = 0.5 # Transparency for background

            (h, w) = selected_frame.shape[:2]
            max_text_width = w * 0.75 # Max width for text lines
            padding = 10

            # Wrap the text
            wrapped_lines = wrap_text_by_width(catchy_quote, font, max_text_width, draw)
            if not wrapped_lines:
                 print("Warning: Text wrapping resulted in no lines.")
                 return selected_frame # Or handle error

            # Calculate line height and total text block height
            # Use a sample character or the first line for line height
            line_bbox = draw.textbbox((0,0), wrapped_lines[0], font=font)
            line_height = line_bbox[3] - line_bbox[1]
            line_spacing_factor = 1.2 # Add a little space between lines
            total_text_height = len(wrapped_lines) * line_height * line_spacing_factor - (line_height * (line_spacing_factor - 1)) # Subtract extra spacing after last line

            # Calculate dimensions of the widest line for the background
            max_line_width = 0
            for line in wrapped_lines:
                line_bbox = draw.textbbox((0, 0), line, font=font)
                line_width = line_bbox[2] - line_bbox[0]
                if line_width > max_line_width:
                    max_line_width = line_width

            # Position text block at bottom-left with padding
            text_x = int(w * 0.05)
            # Adjust y based on total block height
            text_y = int(h * 0.95) - total_text_height

            # Draw semi-transparent background rectangle based on wrapped text dimensions
            rect_x0 = text_x - padding
            rect_y0 = text_y - padding
            rect_x1 = text_x + max_line_width + padding
            rect_y1 = text_y + total_text_height + padding

            # Create a separate layer for the rectangle for transparency
            rect_layer = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
            rect_draw = ImageDraw.Draw(rect_layer)
            rect_draw.rectangle(
                [rect_x0, rect_y0, rect_x1, rect_y1],
                fill=(*background_color, int(255 * alpha_blend)) # Add alpha to background color
            )
            # Composite the rectangle layer onto the image
            pil_image = Image.alpha_composite(pil_image.convert('RGBA'), rect_layer).convert('RGB')

            # Recreate draw object for the composited image before drawing text
            draw = ImageDraw.Draw(pil_image)

            # Draw the wrapped text line by line
            current_y = text_y
            for line in wrapped_lines:
                draw.text((text_x, current_y), line, font=font, fill=color)
                current_y += line_height * line_spacing_factor # Move y down for next line

            # Convert Pillow RGB image back to OpenCV BGR image
            selected_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        else:
            print("Skipping text drawing due to font loading issues.")

    except ImportError:
        print("Error: Pillow library not installed. Cannot draw text with UTF-8 support.")
        print("Please install Pillow: pip install Pillow")
        # Optionally fallback to cv2.putText here, warning about potential character issues
        # For now, we just skip if Pillow isn't there or font fails badly
    except Exception as e:
        print(f"Error during text drawing with Pillow: {e}")
        # Decide how to handle this - skip text? return None?

    print(f"Successfully extracted frame {frame_count} with open eyes and added quote.")
    return selected_frame

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract a frame from a video.')
    parser.add_argument('video_path', type=str, help='Path to the video file.')
    parser.add_argument('json_path', type=str, help='Path to the .json file containing potentially nested quotes.')
    parser.add_argument('--output_dir', type=str, default='img/output', help='Directory to save the extracted frame (default: img/output).')

    args = parser.parse_args()

    # Call the function to extract the frame
    extracted_frame = extract_frame(args.video_path, args.json_path)

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
