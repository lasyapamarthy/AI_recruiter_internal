import pandas as pd
import ast
from langchain_openai import ChatOpenAI
import os
import json

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def extract_skills_by_level(skill_text, level_type='junior'):
    """Extract skills from a skill text string based on level type."""
    try:
        if pd.isna(skill_text):
            return str([])
        
        skill_text = str(skill_text)
        skills = skill_text.lower().split('|')
        processed_skills = []
        
        for skill_entry in skills:
            skill_entry = skill_entry.strip()
            # For non-experienced skills, we look for entries WITHOUT 'junior'
            if level_type == 'junior' and 'junior' not in skill_entry:
                continue
            if level_type == 'non_experienced' and 'junior' in skill_entry:
                continue
                
            # Split the skill part and level part
            if ':' in skill_entry:
                skill_part, level = skill_entry.split(':')
            else:
                skill_part, level = skill_entry, ''
            
            # If the skill part contains comma, split it into multiple skills
            if ',' in skill_part:
                individual_skills = [s.strip() for s in skill_part.split(',')]
                for skill in individual_skills:
                    processed_skills.append(f"{skill}: {level.strip()}" if level else skill)
            else:
                processed_skills.append(skill_entry)
        
        return str(processed_skills)
    except Exception as e:
        print(f"Error processing skill text: {str(e)}")
        return str([])

def create_skill_matcher(model_name="gpt-4o", temperature=0):
    """Create a LLM-based skill matcher."""
    llm = ChatOpenAI(model_name=model_name, temperature=temperature)

    def match_skill(skill, skill_list):
        try:
            prompt = (
                f"You are a recruiter. You are given a skill '{skill}' and need to "
                f"verify if this skill is present in the list of skills: {skill_list}. "
                "Return True if it is present and False if it is not present. "
                "Output must be True or False ONLY, with no additional text. "
                "Ignore case, spaces, and punctuation. Focus on the meaning and "
                "consider variations of the same skill (e.g., 'python' and 'python 3' are the same skill)."
            )
            response = llm(prompt)
            return response.content.strip().lower() == "true"
        except Exception as e:
            print(f"Error matching skill {skill}: {str(e)}")
            return False

    return match_skill

def extract_non_experienced_skills(skill_text):
    """Extract skills that are specifically marked as 'Not experienced'."""
    try:
        if pd.isna(skill_text):
            return str([])
        
        skill_text = str(skill_text)
        skills = skill_text.lower().split('|')
        processed_skills = []
        
        for skill_entry in skills:
            skill_entry = skill_entry.strip()
            
            # Check specifically for 'not experienced'
            if 'not experienced' in skill_entry:
                # Split the skill part and level part
                if ':' in skill_entry:
                    skill_part, level = skill_entry.split(':')
                else:
                    skill_part, level = skill_entry, ''
                
                # If the skill part contains comma, split it into multiple skills
                if ',' in skill_part:
                    individual_skills = [s.strip() for s in skill_part.split(',')]
                    for skill in individual_skills:
                        processed_skills.append(f"{skill}: not experienced")
                else:
                    processed_skills.append(skill_entry)
        
        return str(processed_skills)
    except Exception as e:
        print(f"Error processing skill text: {str(e)}")
        return str([])

def process_skills_matching(df, skill_matcher):
    """Process skills matching for each row in the dataframe."""
    for i, row in df.iterrows():
        print(f"\n--- Processing Record {i+1} ---")
        try:
            # Process junior skills
            junior_skills = ast.literal_eval(row['junior_skills'])
            resume_skills = row['resume_skills']
            
            print(f"Junior Skills Found: {junior_skills}")
            
            # Match junior skills
            matched_junior_skills = [
                skill for skill in junior_skills
                if skill_matcher(skill.split(':')[0].strip(), resume_skills)
            ]
            df.at[i, 'matched_skills_junior'] = str(matched_junior_skills)
            print(f"Matched Junior Skills: {matched_junior_skills}")
            
            # Process non-experienced skills
            non_exp_skills = ast.literal_eval(row['non_experienced_skills'])
            print(f"Non-Experienced Skills Found: {non_exp_skills}")
            
            # Match non-experienced skills - using same matcher as junior skills
            matched_non_exp_skills = [
                skill for skill in non_exp_skills
                if skill_matcher(skill.split(':')[0].strip() if ':' in skill else skill, resume_skills)
            ]
            df.at[i, 'matched_skills_non_experienced'] = str(matched_non_exp_skills)
            print(f"Matched Non-Experienced Skills: {matched_non_exp_skills}")
            
        except Exception as e:
            print(f"Error processing row {i}: {str(e)}")
            if 'matched_skills_junior' not in df.columns:
                df.at[i, 'matched_skills_junior'] = str([])
            df.at[i, 'matched_skills_non_experienced'] = str([])

    return df

def calculate_skill_match_percentage(df, skill_matcher):
    """Calculate the percentage of matched skills for each row in the dataframe."""
    for i, row in df.iterrows():
        print(f"\n--- Calculating Match Percentage for Record {i+1} ---")
        try:
            if pd.isna(row['ai_vetted_skills']):
                print("No AI vetted skills found - skipping")
                df.at[i, 'matched_skills_percent_junior'] = 0
                df.at[i, 'matched_skills_percent_non_experienced'] = 0
                continue
                
            # Process junior skills percentage
            junior_skills = ast.literal_eval(row['junior_skills'])
            total_junior_skills = len(junior_skills)
            
            # Process non-experienced skills percentage
            non_exp_skills = ast.literal_eval(row['non_experienced_skills'])
            total_non_exp_skills = len(non_exp_skills)
            
            try:
                if pd.isna(row['resume_skills']):
                    print("No resume skills found")
                    resume_skills = []
                else:
                    resume_skills = str(row['resume_skills']).lower().split(',')
                    print(f"Resume skills found: {resume_skills}")
            except (AttributeError, TypeError):
                print(f"Warning: Invalid resume skills format in row {i}")
                resume_skills = []

            if not resume_skills:
                print("No valid resume skills - setting match percentages to 0")
                df.at[i, 'matched_skills_percent_junior'] = 0
                df.at[i, 'matched_skills_percent_non_experienced'] = 0
                continue

            # Calculate junior skills match percentage
            matched_junior_count = len(ast.literal_eval(row['matched_skills_junior']))
            junior_percentage = (
                matched_junior_count / total_junior_skills * 100
            ) if total_junior_skills > 0 else 0
            
            # Calculate non-experienced skills match percentage
            matched_non_exp_count = len(ast.literal_eval(row['matched_skills_non_experienced']))
            non_exp_percentage = (
                matched_non_exp_count / total_non_exp_skills * 100
            ) if total_non_exp_skills > 0 else 0
            
            df.at[i, 'matched_skills_percent_junior'] = junior_percentage
            df.at[i, 'matched_skills_percent_non_experienced'] = non_exp_percentage
            
            print(f"Junior Skills - Matched: {matched_junior_count}/{total_junior_skills} ({junior_percentage:.2f}%)")
            print(f"Non-Experienced Skills - Matched: {matched_non_exp_count}/{total_non_exp_skills} ({non_exp_percentage:.2f}%)")
            
        except Exception as e:
            print(f"Error processing row {i}: {str(e)}")
            df.at[i, 'matched_skills_percent_junior'] = 0
            df.at[i, 'matched_skills_percent_non_experienced'] = 0

    return df

def main():
    print("Starting skill matching process...")
    
    # Read input data
    print("\nReading input data...")
    df = pd.read_csv("/Users/pavankumarsv/projects/micro1/stanford-research-docs/Resume vs. AI Vetted Skills/random_720.csv")
    print(f"Total records to process: {len(df)}")

    # Extract both junior and non-experienced skills
    print("\nExtracting skills by level...")
    df['junior_skills'] = df['ai_vetted_skills'].apply(lambda x: extract_skills_by_level(x, 'junior'))
    df['non_experienced_skills'] = df['ai_vetted_skills'].apply(extract_non_experienced_skills)
    df.to_csv("skills_by_level.csv", index=False)
    print("Skills extracted and saved to skills_by_level.csv")

    # Match skills
    print("\nMatching skills with resume skills...")
    skill_matcher = create_skill_matcher()
    df = process_skills_matching(df, skill_matcher)

    # Calculate match percentages
    print("\nCalculating skill match percentages...")
    df = calculate_skill_match_percentage(df, skill_matcher)
    
    # Calculate averages
    avg_junior_percent = df['matched_skills_percent_junior'].mean()
    avg_non_exp_percent = df['matched_skills_percent_non_experienced'].mean()
    
    print(f"\nFinal Results:")
    print(f"Average junior skill match percentage: {avg_junior_percent:.2f}%")
    print(f"Average non-experienced skill match percentage: {avg_non_exp_percent:.2f}%")

    df.to_csv("/Users/pavankumarsv/projects/micro1/stanford-research-docs/Resume vs. AI Vetted Skills/random_720_skills_by_level.csv", index=False)
    print("\nResults saved to matched_skills_analysis.csv")

if __name__ == "__main__":
    main()
