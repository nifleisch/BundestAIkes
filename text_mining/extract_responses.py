from pathlib import Path
from openai import OpenAI
import json
import re


def load_topics():
    """Load available topics from topics.json."""
    topics_file = Path("intermediate") / "topics.json"
    if not topics_file.exists():
        print(f"Error: Topics file not found at {topics_file}")
        return []
    
    with open(topics_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("themen", [])

def create_speech_summary(speeches):
    """Create a summary of all speeches for context."""
    summary = "Übersicht aller Redebeiträge:\n"
    for speech in speeches:
        summary += f"ID: {speech['id']}, Redner: {speech['speaker']} ({speech['party']}), Themen: {', '.join(speech['topics'])}\n"
    return summary

def extract_quotes(speech, all_speeches, available_topics):
    """Extract meaningful quotes from a speech."""
    client = OpenAI()
    try:
        # Create speech summary for context
        speech_summary = create_speech_summary(all_speeches)
        
        # Call the API with structured output
        response = client.chat.completions.create(
            model="o4-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""Du bist Expert*in für die Analyse politischer Redebeiträge und Debatten.  
Deine Aufgabe ist es, **ausschließlich** Zitate zu extrahieren, die **als Reaktion** auf einen vorherigen Redebeitrag formuliert wurden.

Kontext aller Redebeiträge:
{speech_summary}

Verfügbare Themen (bitte nur diese verwenden):
{', '.join(available_topics)}

Wähle **nur** Zitate aus, die:
- eine Reaktion auf einen anderen Redebeitrag sind  
- in sich, ohne weiteren Kontext verständlich sind  
- maximal 4 Sätze lang sind  
- eine klare Kernaussage oder ein Argument enthalten  
- sich für Social Media (YouTube Shorts, TikTok) eignen  

Für jedes Zitat liefere im JSON-Format:
1. `first_sentence`: Genauer erster Satz des Zitats  
2. `last_sentence`: Genauer letzter Satz des Zitats  
3. `topic`: Hauptthema (eines der oben genannten)
6. `response_to_id`: ID des Redebeitrags, auf den geantwortet wird  

Output-Struktur:
```json
{{
  "quotes": [
    {{
      "first_sentence": "...",
      "last_sentence": "...",
      "topic": "...",
      "response_to_id": "ID-des-vorherigen-Beitrags"
    }}
    // ggf. weitere
  ]
}}
```"""
                },
                {
                    "role": "user",
                    "content": f"Bitte analysiere diesen Redebeitrag und extrahiere die wichtigsten Reaktions-Zitate:\n\n{speech['transcript']}"
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error extracting quotes: {str(e)}")
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

def extract_responses():
    """Process all speeches and extract quotes."""
    # Load available topics
    available_topics = load_topics()
    if not available_topics:
        return
    
    # Read the speeches file
    speeches_file = Path("intermediate") / "speeches.jsonl"
    if not speeches_file.exists():
        print(f"Error: Speeches file not found at {speeches_file}")
        return
    
    # Read all speeches first
    all_speeches = []
    with open(speeches_file, 'r', encoding='utf-8') as f:
        for line in f:
            all_speeches.append(json.loads(line))
    
    # Create output file for all quotes
    output_file = Path("intermediate") / "responses.jsonl"
    
    # Process each speech
    for speech in all_speeches:
        try:
            print(f"Processing speech {speech['id']} by {speech['speaker']} ({speech['party']})")
            
            # Extract quotes
            quotes_data = extract_quotes(speech, all_speeches, available_topics)
            
            # Save quotes to the combined JSONL file
            with open(output_file, 'a', encoding='utf-8') as out_f:
                for quote in quotes_data["quotes"]:
                    # Extract the full quote text
                    quote_text = extract_text_between_sentences(
                        speech["transcript"],
                        quote["first_sentence"],
                        quote["last_sentence"]
                    )
                    
                    if quote_text:
                        # Create the complete quote object
                        quote_object = {
                            "id": speech["id"],
                            "quote": quote_text,
                            "topic": quote["topic"],
                            "response_to_id": quote.get("response_to_id"),
                            "speaker": speech["speaker"],
                            "party": speech["party"]
                        }
                        
                        # Write to JSONL file
                        out_f.write(json.dumps(quote_object, ensure_ascii=False) + '\n')
                        print(f"Saved quote about {quote['topic']}")
            
        except Exception as e:
            print(f"Error processing speech {speech['id']}: {str(e)}")
            continue
    
    print(f"Analysis complete. All quotes saved to: {output_file}")
