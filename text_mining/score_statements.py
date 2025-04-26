from pathlib import Path
import json

from openai import OpenAI


def evaluate_statement(statement):
    """Evaluate the quality of a statement using the LLM."""
    client = OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": f"""Du bist ein*e Experte für die Analyse politischer Aussagen. 
                    Deine Aufgabe ist es, die Qualität einer Aussage nach folgenden Kriterien zu bewerten.
                    1 ist die schlechteste Bewertung, 5 ist die beste Bewertung.
                    
                    1. Selbstständigkeit (1-5):
                       - Ist die Aussage ohne weiteren Kontext verständlich?
                       - Kann sie für sich alleine stehen?
                    
                    2. Positionierung (1-5):
                       - Macht die Aussage die Position des Sprechers klar?
                       - Ist die Haltung eindeutig erkennbar?
                    
                    3. Informationsgehalt (1-5):
                       - Enthält die Aussage Fakten oder Informationen?
                       - Wird der Zuhörer informiert?
                    
                    4. Relevanz für das Thema (1-5):
                       - Ist die Aussage relevant für das Thema "{statement['topic']}"?
                       - Trägt sie zur Diskussion bei?
                    
                    5. Konsumierbarkeit (1-5):
                       - Ist die Aussage für TikTok/Instagram Reels geeignet?
                       - Ist sie kurz und prägnant?
                    
                    Gib deine Bewertung im JSON-Format mit folgender Struktur aus:
                    {{
                        "scores": {{
                            "self_sufficiency": 1-5,
                            "positioning": 1-5,
                            "information": 1-5,
                            "relevance": 1-5,
                            "consumability": 1-5
                        }},
                        "average_score": 1-5,
                        "explanation": "Kurze Begründung der Bewertung"
                    }}"""
                },
                {
                    "role": "user",
                    "content": f"Bitte bewerte diese Aussage:\n\n{statement['quote']}"
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error evaluating statement: {str(e)}")
        raise

def score_statements():
    """Process all statements and add quality scores."""
    statements_file = Path("intermediate") / "statements.jsonl"
    if not statements_file.exists():
        print(f"Error: Statements file not found at {statements_file}")
        return
    
    # Create output file for scored statements
    output_file = Path("intermediate") / "scored_statements.jsonl"
    
    # Process each statement
    with open(statements_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                statement = json.loads(line)
                print(f"Processing statement by {statement['speaker']} ({statement['party']})")

                evaluation = evaluate_statement(statement)

                statement.update({
                    "scores": evaluation["scores"],
                    "average_score": evaluation["average_score"],
                    "evaluation_explanation": evaluation["explanation"]
                })
                
                # Save to output file
                with open(output_file, 'a', encoding='utf-8') as out_f:
                    out_f.write(json.dumps(statement, ensure_ascii=False) + '\n')
                print(f"Saved scored statement with average score: {evaluation['average_score']}")
                
            except Exception as e:
                print(f"Error processing statement: {str(e)}")
                continue
    
    print(f"Analysis complete. Scored statements saved to: {output_file}")
