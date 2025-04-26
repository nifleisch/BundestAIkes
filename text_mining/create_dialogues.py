import json
from pathlib import Path


def load_statements():
    """Load statements from JSONL file."""
    statements_file = Path("intermediate") / "statements.jsonl"
    if not statements_file.exists():
        print(f"Error: Statements file not found at {statements_file}")
        return []
    
    statements = []
    with open(statements_file, 'r', encoding='utf-8') as f:
        for line in f:
            statements.append(json.loads(line))
    return statements

def load_responses():
    """Load responses from JSONL file."""
    responses_file = Path("intermediate") / "responses.jsonl"
    if not responses_file.exists():
        print(f"Error: Responses file not found at {responses_file}")
        return []
    
    responses = []
    with open(responses_file, 'r', encoding='utf-8') as f:
        for line in f:
            responses.append(json.loads(line))
    return responses

def find_responses_for_statement(statement, all_responses):
    """Find all valid responses for a given statement."""
    valid_responses = []
    
    for response in all_responses:
        # Check if response is valid for this statement
        if (response['topic'] == statement['topic'] and  # Same topic
            response['id'] > statement['id'] and  # Response comes after statement
            response.get('response_to_id') == str(statement['id'])):  # Explicitly references statement
            valid_responses.append(response)
    
    return valid_responses

def create_dialogues():
    """Create dialogue collections from statements and responses."""
    # Load data
    statements = load_statements()
    responses = load_responses()
    
    if not statements or not responses:
        return
    
    # Create dialogues
    dialogues = []
    for statement in statements:
        # Find responses for this statement
        statement_responses = find_responses_for_statement(statement, responses)
        
        if statement_responses:
            # Create dialogue entry
            dialogue = {
                "statement": statement,
                "responses": statement_responses
            }
            dialogues.append(dialogue)
    
    output_file = Path("intermediate") / "dialogues.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for dialogue in dialogues:
            f.write(json.dumps(dialogue, ensure_ascii=False) + '\n')
    
    print(f"Created {len(dialogues)} dialogues")
    print(f"Saved dialogues to: {output_file}")
