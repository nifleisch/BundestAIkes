import os
import json
import re
from mutagen.mp3 import MP3
import openai
import assemblyai as aai


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by removing punctuation and extra spaces.
    
    Args:
        text (str): Text to normalize
        
    Returns:
        str: Normalized text
    """
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def transcribe_audio(mp3_path: str, openai_key: str, chunk_duration: int = 1400) -> str:
    """
    Transcribe audio file using OpenAI Whisper.
    If the transcript JSON already exists, skip the transcription process.
    
    Args:
        mp3_path (str): Path to the MP3 file
        openai_key (str): OpenAI API key
        chunk_duration (int): Duration of each chunk in seconds
        
    Returns:
        str: Path to the generated transcript JSON file
    """
    # Create output directory
    transcript_dir = os.path.join("intermediate", "transcript")
    os.makedirs(transcript_dir, exist_ok=True)
    
    output_json_path = os.path.join(transcript_dir, "full_transcript_verbose.json")
    
    # Skip if transcript already exists
    if os.path.exists(output_json_path):
        print(f"Transcript already exists at {output_json_path}, skipping transcription")
        return output_json_path
    
    openai.api_key = openai_key
    
    # Get total duration of the MP3 file
    audio = MP3(mp3_path)
    total_duration = int(audio.info.length)
    
    # Generate chunking commands
    chunk_paths = []
    for start_time in range(0, total_duration, chunk_duration):
        chunk_name = f"chunk_{(start_time // chunk_duration + 1):0{3}d}.mp3"
        output_path = os.path.join(transcript_dir, chunk_name)
        actual_duration = min(chunk_duration, total_duration - start_time)
        os.system(f"sox \"{mp3_path}\" \"{output_path}\" trim {start_time} {actual_duration}")
        chunk_paths.append(output_path)
    
    print("Audio splitting complete!")
    
    all_segments = []
    
    for i, path in enumerate(chunk_paths):
        print(f"Transcribing {path}...")
        with open(path, "rb") as audio_file:
            result = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                prompt="Write the transcript for the following interview to text"
            )
            
            # Add chunk offset to segment times
            chunk_offset = i * chunk_duration
            for segment in result.segments:
                segment.start += chunk_offset
                segment.end += chunk_offset
                all_segments.append(segment)
    
    timestamps_data = [{
        "start": seg.start,
        "end": seg.end,
        "text": seg.text
    } for seg in all_segments]
    
    transcript_text = "".join(seg.text for seg in all_segments)
    
    full_result = {
        "transcript": transcript_text,
        "timestamps": timestamps_data
    }
    
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(full_result, f, indent=2, ensure_ascii=False)
    
    print(f"Transcription complete! Saved full verbose JSON to {output_json_path}")
    return output_json_path


def get_word_level_timestamps(mp4_path: str, assemblyai_key: str, sentence: str) -> tuple:
    """
    Get exact word-level timestamps for a sentence in a video.
    Uses flexible matching to find the sentence in the transcript.
    
    Args:
        mp4_path (str): Path to the MP4 file
        assemblyai_key (str): AssemblyAI API key
        sentence (str): The sentence to find timestamps for
        
    Returns:
        tuple: (start_time, end_time) in seconds, or None if sentence not found
    """
    # Convert MP4 to MP3 if needed
    mp3_path = os.path.splitext(mp4_path)[0] + ".mp3"
    if not os.path.exists(mp3_path):
        from video_processing.audio_converter import convert_to_mp3
        mp3_path = convert_to_mp3(mp4_path)
    
    # Get word-level transcript
    aai.settings.api_key = assemblyai_key
    config = aai.TranscriptionConfig(language_code="de")
    transcriber = aai.Transcriber(config=config)
    
    future = transcriber.transcribe_async(mp3_path)
    transcript = future.result(timeout=600)
    
    if transcript.status != "completed":
        raise RuntimeError(f"Transcription error: {transcript.error}")
    
    # Normalize the target sentence
    target_words = normalize_text(sentence).split()
    target_text = ' '.join(target_words)
    
    # Get all words and their timestamps
    words = transcript.words
    normalized_words = [normalize_text(w.text) for w in words]
    
    # Try to find the sentence using a sliding window
    best_match = None
    best_match_score = 0
    window_size = len(target_words)
    
    for i in range(len(words) - window_size + 1):
        # Get the current window of words
        current_words = normalized_words[i:i + window_size]
        current_text = ' '.join(current_words)
        
        # Calculate match score (number of matching words)
        matching_words = sum(1 for w1, w2 in zip(target_words, current_words) if w1 == w2)
        match_score = matching_words / len(target_words)
        
        # If we find a better match, update best_match
        if match_score > best_match_score:
            best_match_score = match_score
            best_match = (i, i + window_size - 1)
    
    # If we found a good enough match (at least 70% of words match)
    if best_match and best_match_score >= 0.7:
        start_idx, end_idx = best_match
        start_time = words[start_idx].start / 1000.0  # Convert ms to seconds
        end_time = words[end_idx].end / 1000.0  # Convert ms to seconds
        return (max(start_time - 0.5, 0), end_time + 0.5)  # Add small buffer
    
    return None 