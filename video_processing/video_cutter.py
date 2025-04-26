import subprocess


def cut_video_clip(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    Cut a segment from a video file.
    
    Args:
        input_path (str): Path to the input video file
        output_path (str): Path to save the cut clip
        start_time (float): Start time in seconds
        end_time (float): End time in seconds
    """
    duration = end_time - start_time
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i", input_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-c:v", "copy",  # Copy the video without re-encoding
        "-c:a", "copy",  # Copy the audio without re-encoding
        output_path
    ]
    
    print(f"Cutting clip from {start_time}s to {end_time}s into {output_path}")
    subprocess.run(cmd, check=True) 