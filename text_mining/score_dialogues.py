from pathlib import Path
from openai import OpenAI
import json


def evaluate_dialogue(dialogue):
    client = OpenAI()
    """Evaluate the quality of a dialogue using the LLM."""
    try:
        # Format dialogue for the prompt
        dialogue_text = f"""Original Statement:
Speaker: {dialogue['statement']['speaker']} ({dialogue['statement']['party']})
Quote: {dialogue['statement']['quote']}

Responses:"""
        
        for response in dialogue['responses']:
            dialogue_text += f"""
Speaker: {response['speaker']} ({response['party']})
Quote: {response['quote']}"""
        
        # Call the API with structured output
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": f"""Du bist ein*e Experte für die Analyse politischer Debatten. 
                    Deine Aufgabe ist es, die Qualität eines Dialogs nach folgenden Kriterien zu bewerten.
                    1 ist die schlechteste Bewertung, 5 ist die beste Bewertung.
                    
                    1. Klare Positionierung (1-5):
                       - Transportiert die Aussage eine klare Botschaft?
                       - Wird die Position des Sprechers deutlich?
                    
                    2. Unterschiedliche Perspektiven (1-5):
                       - Kommen die Sprecher aus verschiedenen Parteien?
                       - Werden unterschiedliche Standpunkte vertreten?
                    
                    3. Relevante Reaktionen (1-5, doppelte Gewichtung):
                       - Reagieren die Antworten direkt auf die ursprüngliche Aussage?
                       - Wird auf konkrete Punkte eingegangen?
                       - Wird argumentativ auf die Aussage eingegangen?
                    
                    4. Social Media Eignung (1-5):
                       - Ist der Dialog für TikTok/Instagram Reels geeignet?
                       - Ist er kurz und prägnant?
                       - Ist er auch ohne Kontext verständlich?
                    
                    Gib deine Bewertung im JSON-Format mit folgender Struktur aus:
                    {{
                        "scores": {{
                            "positioning": 1-5,
                            "different_views": 1-5,
                            "relevant_responses": 1-5,
                            "social_media": 1-5
                        }},
                        "weighted_average": 1-5,  # Berechne den Durchschnitt mit doppelter Gewichtung für relevant_responses
                        "explanation": "Kurze Begründung der Bewertung"
                    }}"""
                },
                {
                    "role": "user",
                    "content": f"Bitte bewerte diesen Dialog:\n\n{dialogue_text}"
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error evaluating dialogue: {str(e)}")
        raise

def score_dialogues():
    """Process all dialogues and add quality scores."""
    # Read the dialogues file
    dialogues_file = Path("intermediate") / "dialogues.jsonl"
    if not dialogues_file.exists():
        print(f"Error: Dialogues file not found at {dialogues_file}")
        return
    
    # Load all dialogues
    dialogues = []
    with open(dialogues_file, 'r', encoding='utf-8') as f:
        for line in f:
            dialogues.append(json.loads(line))
    
    # Process each dialogue
    scored_dialogues = []
    for dialogue in dialogues:
        try:
            print(f"Processing dialogue with statement by {dialogue['statement']['speaker']}")
            
            # Evaluate dialogue
            evaluation = evaluate_dialogue(dialogue)
            
            # Add scores to the dialogue
            dialogue.update({
                "scores": evaluation["scores"],
                "weighted_average": evaluation["weighted_average"],
                "evaluation_explanation": evaluation["explanation"]
            })
            
            scored_dialogues.append(dialogue)
            print(f"Scored dialogue with weighted average: {evaluation['weighted_average']}")
            
        except Exception as e:
            print(f"Error processing dialogue: {str(e)}")
            continue
    
    # Sort dialogues by weighted average score
    scored_dialogues.sort(key=lambda x: x['weighted_average'], reverse=True)
    
    # Save to output file
    output_file = Path("intermediate") / "scored_dialogues.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for dialogue in scored_dialogues:
            f.write(json.dumps(dialogue, ensure_ascii=False) + '\n')
    
    print(f"Analysis complete. Scored dialogues saved to: {output_file}")
