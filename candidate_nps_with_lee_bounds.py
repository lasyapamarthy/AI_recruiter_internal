# %%
from datetime import datetime, timedelta
import pandas as pd
import os

# %%
import pandas as pd

# Path to the folder containing CSV files

df1_sample = pd.read_csv("df1_sample.csv")
df2_sample = pd.read_csv("df2_sample.csv")
df3_sample = pd.read_csv("df3_sample.csv")

# %%
import os
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI


OPEN_API_KEY = os.getenv("OPEN_API_KEY")
os.environ["OPENAI_API_KEY"] = OPEN_API_KEY
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# %%


# %%
from langchain import LLMChain, PromptTemplate
import time

def create_sentiment_chain(llm):
    """Create the LLMChain for sentiment analysis"""
    sentiment_prompt = PromptTemplate(
        input_variables=["feedbacks"],
        template=(
            "You are tasked with analyzing feedback about an AI interview experience. "
            "For each feedback message, provide exactly one numerical rating on a scale from 1 to 5, where:\n"
            "1 = Extremely negative\n"
            "2 = Negative\n"
            "3 = Neutral\n"
            "4 = Positive\n"
            "5 = Extremely positive\n\n"
            "IMPORTANT: Be considerate and empathetic when analyzing feedback. Favor a lenient and neutral perspective. "
            "When in doubt about the tone of the feedback, prioritize giving a slightly higher score to reflect fairness and avoid strict criticism. "
            "Ratings should lean towards representing an optimistic or constructive view when reasonable.\n\n"
            "If a feedback message is null, empty, or contains only whitespace, or <NULL>, respond with '-1'.\n"
            "If the feedback content is ambiguous or neutral, give a score of '4' instead of '3'.\n\n"
            "IMPORTANT: Your response MUST ONLY contain one number for each feedback message, separated by '|||'. "
            "Do not include any other text, formatting, or multiple ratings.\n\n"
            "Feedbacks (separated by '|||'):\n{feedbacks}\n\nRatings (separated by '|||'):"
        )
    )
    return LLMChain(llm=llm, prompt=sentiment_prompt)

def process_sentiment_batches(feedbacks, batch_size=10, llm=None):
    """Process feedbacks in batches and return sentiment ratings"""
    if not llm:
        raise ValueError("LLM must be provided")
    
    total_feedbacks = len(feedbacks)
    results = []
    llm_chain = create_sentiment_chain(llm)
    
    print(f"Starting sentiment analysis for {total_feedbacks} feedbacks")
    
    for i in range(0, total_feedbacks, batch_size):
        batch = feedbacks[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"\nProcessing batch {batch_num}: Input size = {len(batch)}", flush=True)

        retries = 3
        success = False
        
        while retries > 0 and not success:
            try:
                # Add delay for retries
                if retries < 3:
                    print(f"Retry attempt {4-retries} for batch {batch_num}", flush=True)
                    time.sleep(2)
                
                # On last retry, process individually
                if retries == 1:
                    print(f"Attempting individual processing for batch {batch_num}", flush=True)
                    batch_results = []
                    for feedback in batch:
                        try:
                            # Clean and validate individual feedback
                            cleaned_feedback = str(feedback).strip() if feedback else "<NULL>"
                            response = llm_chain.run(feedbacks=cleaned_feedback)
                            rating = response.strip()
                            # Validate rating
                            if rating in ['1', '2', '3', '4', '5', '-1']:
                                batch_results.append(rating)
                            else:
                                batch_results.append('-1')
                        except Exception as e:
                            print(f"Individual feedback failed: {str(e)}", flush=True)
                            batch_results.append("-1")
                    ratings = batch_results
                else:
                    # Process as batch
                    cleaned_batch = [str(f).strip() if f else "<NULL>" for f in batch]
                    response = llm_chain.run(feedbacks="|||".join(cleaned_batch))
                    ratings = [r.strip() for r in response.strip().split("|||")]
                
                # Validate ratings
                if len(ratings) == len(batch):
                    # Ensure all ratings are valid
                    validated_ratings = []
                    for rating in ratings:
                        if rating in ['1', '2', '3', '4', '5', '-1']:
                            validated_ratings.append(rating)
                        else:
                            validated_ratings.append('-1')
                    
                    results.extend(validated_ratings)
                    print(f"Batch {batch_num} processed successfully.", flush=True)
                    success = True
                    break
                else:
                    print(f"Mismatch in batch {batch_num}: Expected {len(batch)} ratings, got {len(ratings)}.", flush=True)
                    retries -= 1
                    
            except Exception as e:
                print(f"Error in batch {batch_num}: {str(e)}", flush=True)
                retries -= 1

        # Fallback for failed batches
        if not success:
            print(f"Batch {batch_num} failed after all retries. Assigning default ratings (-1).", flush=True)
            results.extend(["-1"] * len(batch))
        
        print(f"Completed {min(i + batch_size, total_feedbacks)}/{total_feedbacks} feedbacks.", flush=True)
    
    return results


# %%
df3_sample["feedback_cleaned"] = df3_sample["feedback_message"].apply(
    lambda feedback: feedback.replace("\n", " ") if feedback and isinstance(feedback, str) and 
        feedback.strip() else "<NULL>"
)


# %%
feedback_list = df3_sample["feedback_cleaned"].tolist()
results = process_sentiment_batches(feedback_list, 25, llm=llm)

# %%


# %%
df3_sample["rating_from_llm"] = results
df3_sample["ratings_from_llm_as_int"] = pd.to_numeric(df3_sample["rating_from_llm"], \
                                                errors='coerce').\
                                        fillna(-1).astype(int)

# %%


# %%
# import pandas as pd
# df3_sample = pd.read_csv("df3_sample.csv")
# %%
df3_sample["rate_star"].describe()
# %%
df3_sample["ratings_from_llm_as_int"].describe()

df3_sample.loc[df3_sample["ratings_from_llm_as_int"] == -1, "ratings_from_llm_as_int"] = None


# # %%
# df3_sample["ratings_from_llm_as_int"].describe()
# # %%
df3_sample.rename(columns={"rate_star": "rate_star_old"}, inplace=True)


# # %%
df3_sample.rename(columns={"ratings_from_llm_as_int": "rate_star"}, inplace=True)
df3_sample.to_csv("df3_sample.csv", index=False)

# %%
print(df1_sample["rate_star"].describe())
print(df2_sample["rate_star"].describe())    
print(df3_sample["rate_star"].describe())
# %%


# %%
import pandas as pd

# Function to calculate missing records percentage
def calculate_missing_percentage(df):
    total_records = len(df)
    missing_records = df[(df["rate_star"].isna()) & (df["feedback_message"].isna())].shape[0]
    missing_percentage = (missing_records / total_records) * 100
    return missing_percentage

# Calculate missing records percentage for each dataframe
missing_df1 = calculate_missing_percentage(df1_sample)
missing_df2 = calculate_missing_percentage(df2_sample)
missing_df3 = calculate_missing_percentage(df3_sample)

# Create a summary DataFrame
missing_summary = pd.DataFrame({
    "DataFrame": ["df1_sample", "df2_sample", "df3_sample"],
    "Missing Records (%)": [missing_df1, missing_df2, missing_df3]
})

# Display the missing records percentage summary
print(missing_summary)


# %%

# Function to calculate mean, Lee upper, and lower bounds
def calculate_lee_bounds(df, max_rating=5, min_rating=1):
    observed_count = df["rate_star"].count()  # Total non-null ratings
    missing_count = df["rate_star"].isna().sum()  # Total missing ratings
    sum_observed_ratings = df["rate_star"].sum()  # Sum of existing ratings

    # Compute Lee bounds
    NPS_observed = sum_observed_ratings / observed_count if observed_count > 0 else 0
    NPS_upper = (sum_observed_ratings + (missing_count * max_rating)) / (observed_count + missing_count)
    NPS_lower = (sum_observed_ratings + (missing_count * min_rating)) / (observed_count + missing_count)

    return NPS_observed, NPS_upper, NPS_lower

# Calculate Lee bounds for each dataframe
df1_NPS_observed, df1_NPS_upper, df1_NPS_lower = calculate_lee_bounds(df1_sample)
df2_NPS_observed, df2_NPS_upper, df2_NPS_lower = calculate_lee_bounds(df2_sample)
df3_NPS_observed, df3_NPS_upper, df3_NPS_lower = calculate_lee_bounds(df3_sample)

# Create a summary DataFrame
lee_bounds_summary = pd.DataFrame({
    "DataFrame": ["df1_sample", "df2_sample", "df3_sample"],
    "NPS_Observed": [df1_NPS_observed, df2_NPS_observed, df3_NPS_observed],
    "NPS_Upper_Bound": [df1_NPS_upper, df2_NPS_upper, df3_NPS_upper],
    "NPS_Lower_Bound": [df1_NPS_lower, df2_NPS_lower, df3_NPS_lower]
})

# Display the Lee bounds summary
print(lee_bounds_summary)

lee_bounds_summary.to_csv("lee_bounds_summary.csv", index=False)

# %%
print(df1_sample["rate_star"].mean())
print(df2_sample["rate_star"].mean())    
print(df3_sample["rate_star"].mean())
# %%


# %%



