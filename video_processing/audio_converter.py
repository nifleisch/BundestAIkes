import os
import subprocess


def convert_to_mp3(input_path: str) -> str:
    """
    Convert MP4 file to MP3 format.
    If the MP3 file already exists, skip the conversion.
    
    Args:
        input_path (str): Path to the input MP4 file
        
    Returns:
        str: Path to the generated MP3 file
    """
    mp3_path = os.path.splitext(input_path)[0] + ".mp3"
    
    # Skip if MP3 already exists
    if os.path.exists(mp3_path):
        print(f"MP3 file already exists at {mp3_path}, skipping conversion")
        return mp3_path
    
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-q:a", "0",
        "-map", "a",
        mp3_path,
        "-y"  # Overwrite output if exists
    ]
    subprocess.run(cmd, check=True)
    
    return mp3_path 