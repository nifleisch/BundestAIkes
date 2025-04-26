import json
import re
from pathlib import Path

from openai import OpenAI


def extract_speeches(transcript):
    """Extract individual speeches from the transcript with speaker, party, and topic information."""
    client = OpenAI()
    try:
        # Call the API with structured output
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": """Du bist ein*e Expert*in für die Analyse politischer Reden und Debatten. 
                    Deine Aufgabe ist es, das Transkript in einzelne Redebeiträge zu unterteilen.
                    Für jeden Redebeitrag gib bitte Folgendes an:
                    1. Den genauen ersten Satz
                    2. Den genauen letzten Satz
                    3. Den Redner/die Rednerin (wenn bekannt, sonst "unknown")
                    4. Die Partei (wenn bekannt, sonst "unknown")
                    5. Eine Liste der behandelten Themen

                    Gib deine Analyse im JSON-Format mit folgender Struktur aus:
                    {
                        "speeches": [
                            {
                                "first_sentence": "Genauer erster Satz aus dem Transkript",
                                "last_sentence": "Genauer letzter Satz aus dem Transkript",
                                "speaker": "Name des Redners/der Rednerin oder 'unknown'",
                                "party": "Name der Partei oder 'unknown'",
                                "topics": ["Thema 1", "Thema 2", ...]
                            }
                        ]
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Bitte analysiere dieses Transkript und unterteile es in einzelne Redebeiträge:\n\n{transcript}"
                }
            ],
            response_format={"type": "json_object"}
        )

        speeches_data = json.loads(response.choices[0].message.content)
        save_speeches(transcript, speeches_data)
        
    except Exception as e:
        print(f"Error extracting speeches: {str(e)}")
        raise

def extract_text_between_sentences(text, first_sentence, last_sentence):
    """Extract text between two sentences, including the sentences themselves."""
    # Escape special characters in the sentences
    first_sentence = re.escape(first_sentence)
    last_sentence = re.escape(last_sentence)
    
    # Create pattern to match text between sentences
    pattern = f"{first_sentence}.*?{last_sentence}"
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(0)
    return None

def save_speeches(transcript, speeches_data):
    """Save each speech as a JSONL entry with full transcript."""
    output_file = Path("intermediate") / "speeches.jsonl"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, speech in enumerate(speeches_data["speeches"]):
            # Extract the full transcript for this speech
            speech_text = extract_text_between_sentences(
                transcript,
                speech["first_sentence"],
                speech["last_sentence"]
            )
            
            if speech_text:
                # Create the complete speech object
                speech_object = {
                    "id": i,
                    "transcript": speech_text,
                    "speaker": speech["speaker"],
                    "party": speech["party"],
                    "topics": speech["topics"]
                }
                
                # Write to JSONL file
                f.write(json.dumps(speech_object, ensure_ascii=False) + '\n')
                print(f"Saved speech by {speech['speaker']} ({speech['party']})")
