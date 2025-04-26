import argparse
import os
import json
import shutil

import dotenv

from video_processing.audio_converter import convert_to_mp3
from video_processing.transcriber import transcribe_audio, get_word_level_timestamps
from video_processing.transcript_reader import get_transcript_text, find_sentence_timestamps
from video_processing.video_cutter import cut_video_clip
from text_mining.extract_topics import extract_topics
from text_mining.extract_speeches import extract_speeches
from text_mining.extract_statements import extract_statements
from text_mining.score_statements import score_statements
from text_mining.create_topic_collections import create_topic_collections
from text_mining.create_dialogues import create_dialogues
from text_mining.extract_responses import extract_responses
from text_mining.score_dialogues import score_dialogues


def create_shorts_from_collections(input_video_path: str, transcript_path: str):
    """
    Create video shorts from topic collections using a two-step cutting process:
    1. Rough cut using sentence-level timestamps
    2. Precise cut using word-level timestamps
    
    Args:
        input_video_path (str): Path to the input video file
        transcript_path (str): Path to the transcript JSON file
    """
    # Create shorts_draft directory
    shorts_draft_dir = os.path.join("intermediate", "shorts_draft")
    os.makedirs(shorts_draft_dir, exist_ok=True)
    
    # Get all topic collection files
    topic_collections_dir = os.path.join("intermediate", "topic_collections")
    for collection_file in os.listdir(topic_collections_dir):
        if not collection_file.endswith(".jsonl"):
            continue
            
        # Create topic-specific directory
        topic_name = os.path.splitext(collection_file)[0]
        topic_dir = os.path.join(shorts_draft_dir, topic_name)
        os.makedirs(topic_dir, exist_ok=True)
        
        # Copy the collection file
        shutil.copy2(
            os.path.join(topic_collections_dir, collection_file),
            os.path.join(topic_dir, collection_file)
        )
        
        # Read the collection
        with open(os.path.join(topic_dir, collection_file), 'r', encoding='utf-8') as f:
            collection = json.load(f)
        
        # Process each statement
        for statement in collection["statements"]:
            quote = statement["quote"]
            
            # Step 1: Get rough timestamps and create initial cut
            rough_timestamps = find_sentence_timestamps(quote, transcript_path)
            if rough_timestamps is None:
                print(f"Could not find rough timestamps for quote: {quote[:100]}...")
                continue
                
            rough_start, rough_end = rough_timestamps
            # add a 10 second buffer
            rough_start -= 10
            rough_end += 10
            
            # Create rough cut
            rough_clip_filename = f"statement_{statement['id']}_rough.mp4"
            rough_clip_path = os.path.join(topic_dir, rough_clip_filename)
            
            try:
                cut_video_clip(input_video_path, rough_clip_path, rough_start, rough_end)
            except Exception as e:
                print(f"Error creating rough clip for statement {statement['id']}: {e}")
                continue
            
            # Step 2: Get precise timestamps and create final cut
            precise_timestamps = get_word_level_timestamps(
                rough_clip_path,
                os.getenv("ASSEMBLYAI_API_KEY"),
                quote
            )
            
            if precise_timestamps is None:
                print(f"Could not find precise timestamps for quote: {quote[:100]}...")
                # Use rough cut as final cut
                statement["clip_path"] = rough_clip_path
                statement["timestamps"] = {
                    "rough": {"start": rough_start, "end": rough_end},
                    "precise": None
                }
                continue
            
            precise_start, precise_end = precise_timestamps
            
            # Create final precise cut
            final_clip_filename = f"statement_{statement['id']}_final.mp4"
            final_clip_path = os.path.join(topic_dir, final_clip_filename)
            
            try:
                cut_video_clip(rough_clip_path, final_clip_path, precise_start, precise_end)
                # Add clip paths and timestamps to statement
                statement["clip_path"] = final_clip_path
                statement["timestamps"] = {
                    "rough": {"start": rough_start, "end": rough_end},
                    "precise": {"start": precise_start, "end": precise_end}
                }
                # Clean up rough cut
                os.remove(rough_clip_path)
            except Exception as e:
                print(f"Error creating precise clip for statement {statement['id']}: {e}")
                # Use rough cut as final cut
                statement["clip_path"] = rough_clip_path
                statement["timestamps"] = {
                    "rough": {"start": rough_start, "end": rough_end},
                    "precise": None
                }
        
        # Save updated collection with clip paths and timestamps
        with open(os.path.join(topic_dir, collection_file), 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)


def main(input_path: str):
    mp3_path = convert_to_mp3(input_path)
    transcript_path = transcribe_audio(mp3_path, os.getenv("OPENAI_API_KEY"))
    transcript_path = "intermediate/transcript/full_transcript_verbose.json"
    raw_transcript = get_transcript_text(transcript_path)
    
    #extract_topics(raw_transcript)
    #extract_speeches(raw_transcript)

    #extract_statements()
    #score_statements()
    #create_topic_collections()
    create_shorts_from_collections(input_path, transcript_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a file path input.")
    parser.add_argument(
        "filepath",
        type=str,
        help="Path to the input file"
    )
    args = parser.parse_args()
    print(f"Received file path: {args.filepath}")
    dotenv.load_dotenv()
    main(args.filepath)
