from dotenv import load_dotenv
import os
load_dotenv()
import json
import re
from anthropic import Anthropic

from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=ANTHROPIC_API_KEY)

def score_interview(transcript_file):
    with open(transcript_file, 'r') as file:
        transcript_data = json.loads(file.read())
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Analyze this technical interview transcript carefully: {transcript_data}

            Evaluate the interview across multiple dimensions, give score only based on interviewer's responses not candidates. For each criterion, provide a score from 1-10 with one decimal place precision.

            Return only a JSON object with the following structure, no other text:
            {{
                "conversational_quality": {{
                    "dialogue_flow": <score>,
                    "response_building": <score>,
                    "acknowledgement": <score>,
                    "overall_score": <score> (Low score if interviewer is only asking questions and not engaging with the candidate)
                }},
                "technical_quality": {{
                    "skill_alignment": <score>,
                    "logical_progression": <score>,
                    "question_clarity": <score>,
                    "overall_score": <score> (This should be high for well thought out questions and vice versa)
                }}
            }}

            Scoring criteria:

            Conversational Quality:
            - dialogue_flow: How natural and engaging is the dialogue flow by the interviewer
            - response_building: How well interviewer builds upon candidate responses and his professional etiquettes
            - acknowledgement: How well interviewer acknowledges candidate responses
            
            Technical Quality:
            - skill_alignment: Alignment of questions with stated skill requirements
            - logical_progression: How well questions build to assess breadth and depth
            - question_clarity: Clarity and unambiguity of questions
            Note: Overall score should not be the average of the individual scores rather it should be independent of the individual scores. Be very consistent with your scoring and be as objective as possible.
            """
        }]
    )
    return response

def save_score(response, file_path, file_index):
    response_str = response.content[0].text
    print(response_str)
    try:
        # Use regex to find JSON pattern between curly braces
        json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            # Convert cleaned JSON string to dictionary
            response_json = json.loads(json_str)
        else:
            raise ValueError("No JSON pattern found in response")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing response JSON: {e}")
        return None
    
    # Get interview ID from filename by removing .json extension
    interview_id = os.path.basename(file_path).replace('.json','')
    
    # Create/append to CSV file based on file_index
    csv_path = f"/Users/pavankumarsv/projects/micro1/support/fine_tuning/NPS/transcript_evals_2025_04_08/transcripts-scores/transcripts-{file_index}.csv"
    
    # Create file with headers if it doesn't exist
    if not os.path.exists(csv_path):
        with open(csv_path, 'w') as f:
            f.write("interview_id,conversational_quality_overall_score,technical_quality_overall_score,conversational_quality_dialogue_flow,conversational_quality_response_building,conversational_quality_acknowledgement,technical_quality_skill_alignment,technical_quality_logical_progression,technical_quality_question_clarity\n")
            
    # Parse the response JSON directly without regex
    try:
        scores = response_json
        # Append scores
        with open(csv_path, 'a') as f:
            f.write(f"{interview_id},{scores['conversational_quality']['overall_score']},{scores['technical_quality']['overall_score']},{scores['conversational_quality']['dialogue_flow']},{scores['conversational_quality']['response_building']},{scores['conversational_quality']['acknowledgement']},{scores['technical_quality']['skill_alignment']},{scores['technical_quality']['logical_progression']},{scores['technical_quality']['question_clarity']}\n")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for {interview_id}: {e}")
        
    return

if __name__ == "__main__":
    interview_dir = "/Users/pavankumarsv/projects/micro1/support/fine_tuning/NPS/transcript_evals_2025_04_08/transcript_jsons/"

    for i, interview_file in enumerate(os.listdir(interview_dir)):
        if interview_file.endswith('.json'):
            file_path = os.path.join(interview_dir, interview_file)
            print(f"Processing {file_path} for file index {i}")
            response = score_interview(file_path)
            save_score(response, file_path, i)
            
