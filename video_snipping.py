import os
import json
from mutagen.mp3 import MP3
import openai
from moviepy import VideoFileClip
import subprocess
import re
import assemblyai as aai


def get_transcript_from_mp4(mp4_path,mp3_path,transcript_path,openai_key):
    mp4_to_mp3(mp4_path,mp3_path)
    get_transcript_from_mp3(mp3_path,transcript_path,key = openai_key)










def mp4_to_mp3(input_path: str, output_path: str):
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-q:a", "0",
        "-map", "a",
        output_path,
        "-y"  # Overwrite output if exists
    ]
    subprocess.run(cmd, check=True)

def cut_mp4_clip(input_mp4_path, output_mp4_path, start_time, end_time):
    """
    Cut a segment from an MP4 file.

    Args:
        input_mp4_path (str): Path to the original MP4 file.
        output_mp4_path (str): Path to save the cut clip.
        start_time (float): Start time in seconds.
        end_time (float): End time in seconds.
    """
    duration = end_time - start_time
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i", input_mp4_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-c:v", "copy",  # Copy the video without re-encoding
        "-c:a", "copy",  # Copy the audio without re-encoding
        output_mp4_path
    ]

    print(f"Cutting clip from {start_time}s to {end_time}s into {output_mp4_path}")
    subprocess.run(cmd, check=True)

def cut_mp3_clip(input_mp3_path, output_mp3_path, start_time, end_time):
    """
    Cut a segment from an MP3 file.

    Args:
        input_mp3_path (str): Path to the original MP3 file.
        output_mp3_path (str): Path to save the cut clip.
        start_time (float): Start time in seconds.
        end_time (float): End time in seconds.
    """
    duration = end_time - start_time
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i", input_mp3_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-c", "copy",  # Copy audio without re-encoding
        output_mp3_path
    ]

    print(f"Cutting clip from {start_time}s to {end_time}s into {output_mp3_path}")
    subprocess.run(cmd, check=True)

def find_sentence_timestamps(sentence, transcript_data):
    # Prepare
    sentence = sentence.strip()
    timestamps = transcript_data["timestamps"]
    
    # Build a flat list of all texts and remember the mapping to timestamps
    snippet_texts = [snippet['text'] for snippet in timestamps]
    
    # Join all snippets together with a separator (to simulate the full transcript)
    joined_text = ''.join(snippet_texts)
    joined_text = re.sub(r'\s+', ' ', joined_text)

    sentence = re.sub(r'\s+', ' ', sentence)
    # Find where the sentence appears in the joined text
    idx = joined_text.find(sentence)
    if idx == -1:
        return None  # Sentence not found

    # Now map character positions back to snippets
    current_pos = 0
    start_time = None
    end_time = None
    
    for snippet in timestamps:
        snippet_text = snippet['text']
        snippet_length = len(snippet_text) + 1  # +1 because we added a space between snippets
        
        if start_time is None and current_pos + snippet_length > idx:
            start_time = snippet['start']
        
        if start_time is not None and current_pos >= idx + len(sentence):
            end_time = snippet['end']
            break
        
        current_pos += snippet_length
    
    # If end_time wasn't found exactly, take it from the last matched snippet
    if end_time is None and start_time is not None:
        end_time = timestamps[-1]['end']
    
    return (max(start_time-30,0), end_time+30)


def get_transcript_from_mp3(mp3_file_path,output_dir,key,chunk_duration=1400):
    openai.api_key = key 
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get total duration of the MP3 file
    audio = MP3(mp3_file_path)
    total_duration = int(audio.info.length)

    # Generate chunking commands
    chunk_paths = []
    for start_time in range(0, total_duration, chunk_duration):
        chunk_name = f"chunk_{(start_time // chunk_duration + 1):0{3}d}.mp3"
        output_path = os.path.join(output_dir, chunk_name)
        actual_duration = min(chunk_duration, total_duration - start_time)
        os.system(f"sox \"{mp3_file_path}\" \"{output_path}\" trim {start_time} {actual_duration}")
        chunk_paths.append(output_path)

    print("Audio splitting complete!")

    all_segments = []
    current_time_offset = 0.0  # How much total time has passed

    for path in chunk_paths:
        print(f"Transcribing {path}...")
        with open(path, "rb") as audio_file:
            result = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                prompt="Write the transcript for the following interview to text"
            )
            
            # Shift the start and end times
            for segment in result.segments:
                segment.start += current_time_offset
                segment.end += current_time_offset
                all_segments.append(segment)
            
            # Update the offset for the next chunk
            if result.segments:
                current_time_offset = all_segments[-1].end
                print(f"Updated time offset: {current_time_offset}")

    # Convert segments into simple dicts for JSON saving
    timestamps_data = [{
        "start": seg.start,
        "end": seg.end,
        "text": seg.text
    } for seg in all_segments]

    # Build final transcript text
    transcript_text = "".join(seg.text for seg in all_segments)

    # Save the full verbose JSON
    full_result = {
        "transcript": transcript_text,
        "timestamps": timestamps_data
    }
    output_json_path = os.path.join(output_dir, "full_transcript_verbose.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(full_result, f, indent=2, ensure_ascii=False)

    print(f"Transcription complete! Saved full verbose JSON to {output_json_path}")
    return full_result

def get_word_level_transcript(key_assembly, audio_file_path):
    aai.settings.api_key = key_assembly

    config = aai.TranscriptionConfig(language_code="de")
    transcriber = aai.Transcriber(config=config)

    # Submit job asynchronously
    future = transcriber.transcribe_async(audio_file_path)

    # Do other work here...

    # Wait for completion (timeout in seconds)
    transcript = future.result(timeout=600)

    if transcript.status == "completed":
        for word in transcript.words:
            print(f"{word.text}: {word.start}–{word.end}ms ({word.confidence*100:.1f}%)")
    else:
        raise RuntimeError(f"Transcription error: {transcript.error}")