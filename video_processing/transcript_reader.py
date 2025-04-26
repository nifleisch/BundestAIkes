import json
import re


def get_transcript_text(transcript_path: str) -> str:
    """
    Get the raw transcript text from the JSON file.
    
    Args:
        transcript_path (str): Path to the transcript JSON file
        
    Returns:
        str: The raw transcript text
    """
    with open(transcript_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["transcript"]


def find_sentence_timestamps(sentence: str, transcript_path: str) -> tuple:
    """
    Find the timestamps for a given sentence in the transcript.
    
    Args:
        sentence (str): The sentence to find
        transcript_path (str): Path to the transcript JSON file
        
    Returns:
        tuple: (start_time, end_time) or None if sentence not found
    """
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)
    
    sentence = sentence.strip()
    timestamps = transcript_data["timestamps"]
    
    snippet_texts = [snippet['text'] for snippet in timestamps]
    joined_text = ''.join(snippet_texts)
    joined_text = re.sub(r'\s+', ' ', joined_text)
    
    sentence = re.sub(r'\s+', ' ', sentence)
    idx = joined_text.find(sentence)
    if idx == -1:
        return None
    
    current_pos = 0
    start_time = None
    end_time = None
    
    for snippet in timestamps:
        snippet_text = snippet['text']
        snippet_length = len(snippet_text)# + 1
        
        if start_time is None and current_pos + snippet_length > idx:
            start_time = snippet['start']
        
        if start_time is not None and current_pos >= idx + len(sentence):
            end_time = snippet['end']
            break
        
        current_pos += snippet_length
    
    if end_time is None and start_time is not None:
        end_time = timestamps[-1]['end']
    
    return (max(start_time-5, 0), end_time+5) 