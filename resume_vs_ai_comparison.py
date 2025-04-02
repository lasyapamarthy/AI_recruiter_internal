# %%
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
import ast
llm = ChatOpenAI(model_name="gpt-4o",temperature=0)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


df = pd.read_csv("micro1-standford-data-job-resume-skill-ai-skill-hire.csv")
print(df.head())
# %%
for i,row in df.iterrows():
    skills = row['ai_vetted_skills'].lower().split('|')
    not_experienced_skills = []
    for skill in skills:
        if 'mid-level' in skill:
            not_experienced_skills.append(skill.split(':')[0].strip())
    df.at[i, 'mid-level-skills'] = str(not_experienced_skills)
df.to_csv("mid-level-skills.csv", index=False)


for i,row in df.iterrows():
    junior_skills = ast.literal_eval(row['mid-level-skills'])  # Safely converts string representation of list to actual list
    print(junior_skills)
    skills = row['resume_skills']
    print(skills)
    matched_skills_not_experienced = []
    for skill in junior_skills:
        llm_response = llm(f"You are a recruiter. You are given a skill - {skill} and you need to verify if this skill is present in the list of skills - {skills} return True if it is present and False if it is not present. Example output is True or False ALWAYS and nothing else NO additional text. Don't Consider case, spaces and punctuation focus on the meaning and name of the skill like 'python' and 'python 3' are the same skill.")
        print(skill)
        print(llm_response.content)
        if llm_response.content == "True":
            matched_skills_not_experienced.append(skill)    
    df.at[i, 'matched-skills-mid-level'] = str(matched_skills_not_experienced)
df.to_csv("matched-skills-mid-level.csv", index=False)
        


# %%
for i,row in df.iterrows():
    skills = row['ai_vetted_skills'].lower().split('|')
    total_skills_count = len(skills)
    try:
        resume_skills = row['resume_skills'].lower().split(',')
    except:
        resume_skills = []
        continue    
    matched_skills_count = 0
    for skill in skills:
        new_skill = skill.split(':')[0].strip()
        llm_response = llm(f"You are a recruiter. You are given a skill - {new_skill} and you need to verify if this skill is present in the list of skills - {resume_skills} return True if it is present and False if it is not present. Example output is True or False ALWAYS and nothing else NO additional text. Don't Consider case, spaces and punctuation focus on the meaning and name of the skill like 'python' and 'python 3' are the same skill.")
        if llm_response.content == "True":
            matched_skills_count += 1
    df.at[i, 'matched_skills_percent'] = matched_skills_count/total_skills_count*100
    #write this to a csv file
df.to_csv("matched_skills_percent.csv", index=False)


# %%
#Calculate average matched skills percent after removing the rows where matched_skills_percent is 0
average_matched_skills_percent = df['matched_skills_percent'].mean()
print(average_matched_skills_percent)


