# import moviepy.editor as mp
from moviepy import *
import whisper
import os
import tempfile
import math # Import math for ceiling function if needed for positioning
import argparse

# Ensure ffmpeg is installed and accessible in the system PATH.
# You might need to install it separately (e.g., `brew install ffmpeg` on macOS, `sudo apt update && sudo apt install ffmpeg` on Debian/Ubuntu).
def create_captions(video_path: str, output_directory: str = None) -> str:
    """
    Generates captions for a video, highlighting the currently spoken word,
    and returns the path to the new video file.

    Args:
        video_path: Path to the input MP4 video file.
        output_directory: Optional directory to save the output video. 
                          Defaults to the same directory as the input video.

    Returns:
        The path to the newly created video file with captions.

    Raises:
        FileNotFoundError: If the input video file does not exist.
        Exception: If any error occurs during transcription or video processing.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    print(f"Loading video: {video_path}")
    video = VideoFileClip(video_path)
    audio_path = None
    final_clip = None
    caption_clips = []

    try:
        # 1. Extract Audio
        print("Extracting audio...")
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
            audio_path = tmp_audio.name
        video.audio.write_audiofile(audio_path, codec='mp3')
        print(f"Audio extracted to: {audio_path}")

        # 2. Transcribe using Whisper
        print("Loading Whisper model (base)...")
        # Using the 'base' model for speed. Options: tiny, base, small, medium, large
        model = whisper.load_model("base")
        print("Starting transcription (this may take a while)...")
        result = model.transcribe(audio_path, word_timestamps=True)
        print("Transcription complete.")

        # 3. Create TextClips for each word
        print("Generating caption clips (single word highlight)...")
        highlight_color = 'yellow'
        fontsize = int(max(24, int(video.h * 0.04))) # Dynamic fontsize
        font = 'Arial' 
        stroke_color = 'black'
        stroke_width = max(1, int(fontsize * 0.05))
        
        # Position near bottom center
        text_position = ('center', video.h - fontsize * 1.5) 

        if "segments" not in result or not result["segments"]:
             print("Warning: No segments found in transcription. Skipping caption generation.")
             return video_path

        all_words = []
        for segment in result["segments"]:
            segment_words = segment.get('words')
            if segment_words and isinstance(segment_words, list):
                 all_words.extend(segment_words)

        if not all_words:
            print("Warning: No words with timestamps found in transcription. Skipping caption generation.")
            return video_path

        total_words_processed = 0
        for word_info in all_words:
            # Basic validation for word_info structure
            if not isinstance(word_info, dict) or not all(k in word_info for k in ["word", "start", "end"]):
                print(f"Warning: Skipping invalid word data: {word_info}")
                continue
            
            word_text = word_info["word"].strip()
            if not word_text:
                 continue # Skip empty words

            start_time = word_info["start"]
            end_time = word_info["end"]
            # Ensure duration is positive, minimum 0.05s
            duration = max(0.05, end_time - start_time)

            # Create the text clip for the highlighted word
            # Using method='caption' which is generally more reliable than pango
            try:
                 txt_clip = TextClip(
                    #  text=word_text,
                    #  fontsize=fontsize,
                     text=word_text,
                     font_size=fontsize,
                     color=highlight_color, 
                     font=font,
                     stroke_color=stroke_color,
                     stroke_width=stroke_width,
                     method='caption',
                     size=(600, None)
                    #  method='pillow',
                    #  align='center'
                 )
            except Exception as clip_err:
                 print(f"\\n** ERROR creating TextClip for word '{word_text}': {clip_err} **")
                 # Decide if you want to skip the word or raise the error
                 # raise clip_err 
                 continue # Skip this word if clip creation fails

            # Set timing and position
            txt_clip = (txt_clip
                        .with_start(start_time)
                        .with_duration(duration)
                        .with_position(text_position))

            caption_clips.append(txt_clip)
            total_words_processed += 1

        # Check if any clips were generated
        if not caption_clips:
             print("Warning: No caption clips were generated.")
             return video_path

        print(f"Generated {len(caption_clips)} caption clips for {total_words_processed} words.")

        # 4. Composite captions onto the original video
        print("Compositing video and captions...")
        final_clip = CompositeVideoClip([video, *caption_clips])

        # 5. Define output path
        base, ext = os.path.splitext(os.path.basename(video_path))
        output_filename = f"{base}_captioned.mp4" # Use .mp4 extension

        if output_directory:
            if not os.path.isdir(output_directory):
                os.makedirs(output_directory)
            output_path = os.path.join(output_directory, output_filename)
        else:
             print(output_directory)
             output_path = os.path.join(os.path.dirname(video_path), output_filename)


        # 6. Write the final video
        print(f"Writing final video to: {output_path}...")
        final_clip.write_videofile(
            output_path,
            codec='libx264',      # Common, high-compatibility codec
            audio_codec='aac',    # Common audio codec
            temp_audiofile=f'{os.path.splitext(output_path)[0]}-temp-audio.m4a', # Explicit temp audio file
            remove_temp=True,
            threads=os.cpu_count() or 4, # Use available cores
            fps=video.fps,        # Maintain original FPS
            preset='medium',      # Balance between speed and quality/size ('ultrafast', 'medium', 'slow')
            logger='bar'          # Show progress bar
        )
        print("Video writing complete.")

        # 7. Return the output path
        return output_path

    except Exception as e:
        print(f"An error occurred: {e}")
        # Re-raise the exception after cleanup attempt
        raise e

    finally:
        # 8. Cleanup
        print("Cleaning up resources...")
        # Close clips to release resources
        if video:
            video.close()
        if final_clip:
            final_clip.close()
        for clip in caption_clips:
            if clip:
                clip.close()
        # Remove temporary audio file
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Removed temporary audio file: {audio_path}")
            except OSError as ose:
                print(f"Warning: Could not remove temporary audio file {audio_path}: {ose}")
        print("Cleanup finished.")

# Example usage (optional, for testing - uncomment and provide a real path)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate word-highlighted captions for a video.")
    parser.add_argument("video_path", help="Path to the input MP4 video file.")
    parser.add_argument("output_dir", help="Directory to save the output captioned video.")
    
    args = parser.parse_args()

    input_video = args.video_path
    output_directory = args.output_dir

    if not os.path.exists(input_video):
        print(f"Error: Input video file not found at '{input_video}'. Please provide a valid path.")
    else:
        try:
            print("--- Starting Caption Generation ---")
            captioned_video_path = create_captions(input_video, output_directory)
            print("--- Caption Generation Successful ---")
            print(f"Output video saved to: {captioned_video_path}")
        except FileNotFoundError as fnf_error:
            print(f"Error: {fnf_error}")
        except Exception as e:
            print(f"An unexpected error occurred during caption generation: {e}")
            import traceback
            traceback.print_exc() # Print detailed traceback for debugging
