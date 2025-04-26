from moviepy.editor import VideoFileClip, concatenate_videoclips
from typing import List
import os

def concat_video_files(*video_files: str) -> str:
    """
    Concatenates multiple MP4 video files into a single video file.
    
    Args:
        *video_files: Variable number of paths to MP4 video files
        
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
    
    # Generate output filename
    output_path = "concatenated_output.mp4"
    
    # Write the result to a file
    final_clip.write_videofile(output_path)
    
    # Close all clips to free up resources
    for clip in video_clips:
        clip.close()
    final_clip.close()
    
    return output_path
