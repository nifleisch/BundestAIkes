import json
from pathlib import Path
from openai import OpenAI
from collections import Counter
import re


def load_statements():
    """Load scored statements from JSONL file."""
    statements_file = Path("intermediate") / "scored_statements.jsonl"
    if not statements_file.exists():
        print(f"Error: Scored statements file not found at {statements_file}")
        return []
    
    statements = []
    with open(statements_file, 'r', encoding='utf-8') as f:
        for line in f:
            statements.append(json.loads(line))
    return statements

def get_top_topics(statements, n=5):
    """Get the n most frequent topics."""
    topic_counter = Counter(statement['topic'] for statement in statements)
    return topic_counter.most_common(n)

def get_best_statements_for_topic(statements, topic, n=5):
    """Get the n best statements for a given topic."""
    topic_statements = [s for s in statements if s['topic'] == topic]
    return sorted(topic_statements, key=lambda x: x['average_score'], reverse=True)[:n]

def create_topic_collection(topic, statements):
    """Create a curated collection of statements for a topic."""
    client = OpenAI()
    try:
        # Format statements for the prompt
        statements_text = "\n\n".join([
            f"{i+1}. {s['quote']} (Speaker: {s['speaker']}, {s['party']})"
            for i, s in enumerate(statements)
        ])
        
        # Call the API to select and order statements
        response = client.chat.completions.create(
            model="o4-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""Du bist ein*e Experte für die Analyse politischer Debatten. 
                    Deine Aufgabe ist es, eine kurze, prägnante Sammlung von Aussagen zu einem Thema zu erstellen.
                    
                    Ich möchte einen Überblick über das Thema "{topic}" geben, das im Deutschen Bundestag diskutiert wurde.
                    Ich habe dir mehrere Aussagen zu diesem Thema zur Verfügung gestellt.
                    
                    Bitte wähle 2-3 Aussagen aus, die:
                    - gut zusammenpassen
                    - das gleiche Thema behandeln
                    - idealerweise verschiedene Perspektiven bieten
                    - sich gut für TikTok eignen
                    
                    Bitte ordne die Aussagen so, dass sie in einem TikTok-Video gut aufeinander aufbauen.
                    
                    Gib deine Auswahl im JSON-Format mit folgender Struktur aus:
                    {{
                        "selected_ids": [1, 2, 3],  # Die Nummern der ausgewählten Aussagen
                        "explanation": "Kurze Erklärung, warum diese Aussagen gut zusammenpassen"
                    }}"""
                },
                {
                    "role": "user",
                    "content": f"Hier sind die Aussagen zum Thema {topic}:\n\n{statements_text}"
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error creating topic collection: {str(e)}")
        raise

def save_topic_collection(topic, statements, selected_ids, explanation):
    """Save the curated collection to a JSONL file."""
    # Create topic_collections directory
    collections_dir = Path("intermediate") / "topic_collections"
    collections_dir.mkdir(exist_ok=True)
    
    # Create filename from topic (lowercase, replace spaces with underscores)
    filename = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower())
    output_file = collections_dir / f"{filename}.jsonl"
    
    # Get the selected statements in the specified order
    selected_statements = [statements[i-1] for i in selected_ids]
    
    # Add collection metadata
    collection = {
        "topic": topic,
        "explanation": explanation,
        "statements": selected_statements
    }
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(collection, ensure_ascii=False, indent=2))
    
    print(f"Saved topic collection to: {output_file}")

def create_topic_collections():
    # Load statements
    statements = load_statements()
    if not statements:
        return
    
    # Get top 5 topics
    top_topics = get_top_topics(statements, n=8)
    print("\nMost frequent topics:")
    for topic, count in top_topics:
        print(f"- {topic}: {count} statements")
    
    # Process each top topic
    for topic, _ in top_topics:
        print(f"\nProcessing topic: {topic}")
        
        # Get best statements for this topic
        best_statements = get_best_statements_for_topic(statements, topic)
        print(f"Found {len(best_statements)} best statements")
        
        # Create curated collection
        collection = create_topic_collection(topic, best_statements)
        
        # Save collection
        save_topic_collection(topic, best_statements, collection["selected_ids"], collection["explanation"])
