import json
from pathlib import Path

from openai import OpenAI

def extract_topics(transcript):
    """Extract the most relevant topics from the transcript."""
    client = OpenAI()
    try:
        # Call the API with structured output
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": """Du bist ein*e Experte für die Analyse politischer Reden und Debatten. 
                    Deine Aufgabe ist es, die 15 wichtigsten Themen aus dem Transkript zu identifizieren.
                    
                    Wichtige Regeln:
                    - Jedes Thema soll maximal 3 Wörter lang sein (auf deutsch)
                    - Die Themen sollen prägnant und aussagekräftig sein
                    - Die Themen sollen die Hauptdiskussionspunkte der Debatte abdecken
                    - Die Themen sollen in der Reihenfolge ihrer Wichtigkeit sortiert sein
                    
                    Gib deine Analyse im JSON-Format mit folgender Struktur aus:
                    {
                        "themen": ["Thema 1", "Thema 2", ...]
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Bitte analysiere dieses Transkript und identifiziere die wichtigsten Themen:\n\n{transcript}"
                }
            ],
            response_format={"type": "json_object"}
        )
        topics_data = json.loads(response.choices[0].message.content)
        output_file = Path("intermediate") / "topics.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(topics_data, f, indent=2, ensure_ascii=False)
        print(f"Topics extracted. Saved to: {output_file}")
        
    except Exception as e:
        print(f"Error extracting topics: {str(e)}")
        raise
