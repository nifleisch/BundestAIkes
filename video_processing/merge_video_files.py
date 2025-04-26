from moviepy.editor import VideoFileClip, concatenate_videoclips
from typing import List
import os
import argparse
from datetime import datetime

def concat_video_files(*video_files: str, output_path_override: str = None) -> str:
    """
    Concatenates multiple MP4 video files into a single video file.
    
    Args:
        *video_files: Variable number of paths to MP4 video files
        output_path_override: Optional path to save the output video file. 
                              If None, defaults to 'img/videos/concatenated_YYYYMMDD_HHMMSS.mp4'.
        
    Returns:
        str: Path to the concatenated output video file
        
    Raises:
        ValueError: If no video files are provided or if any file doesn't exist
    """
    if not video_files:
        raise ValueError("At least one video file must be provided")
    
    # Check if all files exist
    for file_path in video_files:
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
    
    # Load all video clips
    video_clips = [VideoFileClip(file_path) for file_path in video_files]
    
    # Concatenate the clips
    final_clip = concatenate_videoclips(video_clips)
    
    # Determine output path
    if output_path_override:
        output_path = output_path_override
        output_dir = os.path.dirname(output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "img/videos"
        output_path = os.path.join(output_dir, f"concatenated_{timestamp}.mp4")
    
    # Ensure output directory exists
    if output_dir: # Check if output_dir is not empty (protects against saving in root)
        os.makedirs(output_dir, exist_ok=True)
    
    # Write the result to a file
    final_clip.write_videofile(output_path)
    
    # Close all clips to free up resources
    for clip in video_clips:
        clip.close()
    final_clip.close()
    
    return output_path

# Added main execution block for command-line usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concatenate multiple MP4 video files.")
    parser.add_argument("video_files", 
                        metavar="VIDEO_FILE", 
                        type=str, 
                        nargs='+', 
                        help="Paths to the input MP4 video files")
    parser.add_argument("-o", "--output", 
                        type=str, 
                        help="Path for the output concatenated MP4 file (defaults to img/videos/concatenated_TIMESTAMP.mp4)")

    args = parser.parse_args()

    try:
        output_file = concat_video_files(*args.video_files, output_path_override=args.output)
        print(f"Successfully concatenated videos to: {output_file}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
