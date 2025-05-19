remove(list = ls())

library(dplyr)
library(ggplot2)
library(stringr)
library(tidyr)
library(jsonlite)
library(lubridate)
library(knitr)
library(grf)
library(caret)
library(stargazer)
library(broom)
library(kableExtra)
library(gridExtra)
library(oaxaca)
library(gbm)
library(sampleSelection)

# Figures directory:
figures_dir <- "/Users/emilpalikot/Research/AI-Recruiter/src/figures"

########################################################
################ Load and prepare data #################
########################################################

# Load data files:
treatment_group <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/job_101(AI)_w_age_gender.csv")
control_group <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/job_110(Manual)_w_age_gender.csv")
final_interview <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/top_candidates_interviewed.csv")
ai_scores <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Ai-Vetted-ranked.csv")
human_scores <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Manual-Resume-ranked.csv")


# Merge treatment group with control group
columns <- colnames(treatment_group)
control_group <- control_group[, columns]

treatment_group$treatment <- 1
control_group$treatment <- 0
# Merge treatment group with control group
merged_data <- rbind(treatment_group, control_group)

# Dropping duplicates:all
merged_data <- merged_data %>% group_by(email_id) %>% mutate(n = n()) %>% ungroup()
# summarize
merged_data %>% group_by(n) %>% summarize(n = n())
merged_data <- merged_data %>% filter(n == 1) %>% select(-n)

summary(merged_data$treatment)

# Merge merged_data with final_interview by email_id
merged_data <- merged_data %>% left_join(final_interview, by = "email_id")


# Select scores from ai_scores and human_scores
ai_scores <- ai_scores[, c("email_id", "resume_score", "ai_vetting_results")]
human_scores <- human_scores[, c("email_id", "resume_score")]

# Create new columns for each technology
ai_scores <- ai_scores %>%
  mutate(
    React = str_extract(ai_vetting_results, "React\\s*:\\s*(\\w+(?:-\\w+)?)"),
    JavaScript = str_extract(ai_vetting_results, "JavaScript\\s*:\\s*(\\w+(?:-\\w+)?)"),
    CSS = str_extract(ai_vetting_results, "HTML,\\s*CSS\\s*:\\s*(\\w+(?:-\\w+)?)")
  )

# Clean up the extracted values to remove the "Technology:" part
ai_scores <- ai_scores %>%
  mutate(
    React = str_replace(React, "React\\s*:\\s*", ""),
    JavaScript = str_replace(JavaScript, "JavaScript\\s*:\\s*", ""),
    CSS = str_replace(CSS, "HTML,\\s*CSS\\s*:\\s*", "")
  )

ai_scores <- ai_scores %>% select(email_id, React, JavaScript, CSS,resume_score)

human_scores$React <- NA
human_scores$JavaScript <- NA
human_scores$CSS <- NA
human_scores <- human_scores %>% select(email_id, React, JavaScript, CSS,resume_score)
evals <- rbind(ai_scores, human_scores)

merged_data <- merged_data %>% select(email_id, country_code, years_of_exp, is_completed,vetting_creation_date, vetting_completed_date, is_passed, education,gender, age,treatment)
merged_data <- merged_data %>% left_join(evals, by = "email_id")

# Education column:
# Parse the JSON in the education column
extract_education <- function(json_str) {
  tryCatch({
    if (is.na(json_str) || json_str == "[]" || json_str == "") {
      return(data.frame())
    }
    # Parse JSON
    parsed <- fromJSON(json_str)
    return(parsed)
  }, error = function(e) {
    return(data.frame())
  })
}

# Apply the function to each row and keep track of email_id
education_data <- list()
for (i in 1:nrow(merged_data)) {
  edu_data <- extract_education(merged_data$education[i])
  if (nrow(edu_data) > 0) {
    # Directly add email_id as a column with the exact email address
    edu_data$email_id <- as.character(merged_data$email_id[i])
    education_data[[i]] <- edu_data
  }
}

# After extracting the education data, create a consistent structure

# First check what columns we have in the data
all_columns <- unique(unlist(lapply(education_data[!sapply(education_data, is.null)], colnames)))
all_columns <- all_columns[!is.na(all_columns)]

# Now standardize all dataframes to have the same columns
education_data_standardized <- lapply(education_data[!sapply(education_data, is.null)], function(df) {
  # Add missing columns
  for (col in all_columns) {
    if (!col %in% colnames(df)) {
      df[[col]] <- NA
    }
  }
  # Ensure columns are in the same order
  df <- df[, all_columns]
  return(df)
})

# Now combine the standardized dataframes
education_df <- do.call(rbind, education_data_standardized)

# Reset row names
rownames(education_df) <- NULL

# Create education level categories
education_df <- education_df %>%
  mutate(education_level = case_when(
    str_detect(tolower(degree), "bachelor|bsc|b.tech|b.sc") ~ "Bachelor's",
    str_detect(tolower(degree), "master|msc|m.tech|m.sc") ~ "Master's",
    str_detect(tolower(degree), "phd|doctorate") ~ "PhD",
    str_detect(tolower(degree), "high school|secondary|class 10|class 12|10th|12th") ~ "High School",
    TRUE ~ "Other"
  ))

# Prepare for merge:
education_df <- education_df %>% select(email_id, degree, major, education_level, start_date, end_date, is_present)


# Replace the problematic code with this:
education_df2 <- education_df %>%
  # Extract just the email portion using regex
  mutate(clean_email = str_extract(email_id, "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}")) %>%
  # Group by the clean_email
  group_by(clean_email) %>%
  # Find the most recent education record
  arrange(desc(start_date)) %>%
  slice_head(n = 1) %>%
  ungroup() %>%
  # Drop the temporary column
  select(-clean_email)

# Merge education_df with merged_data by email_id

merged_data <- merged_data %>% left_join(education_df2, by = "email_id")

# Completed and final interview:
merged_data$is_completed <- ifelse(is.na(merged_data$is_completed) & merged_data$treatment == 1, 0, merged_data$is_completed)
merged_data$final_interview <- ifelse(merged_data$email_id %in% final_interview$email_id, 1, 0)

# Prepare summary statistcs for the paper:
summary_stats_table <- merged_data %>%
  # Select relevant variables for summary statistics
  select(treatment, years_of_exp, age, gender, education_level, resume_score, React, JavaScript, CSS, is_completed, final_interview) %>%
  # Convert to appropriate types
  mutate(
    years_of_exp = as.numeric(years_of_exp),
    age = as.numeric(age),
    resume_score = as.numeric(resume_score),
    is_completed = as.numeric(is_completed),
    final_interview = as.numeric(final_interview)
  ) %>%
  # Create dummy variables for education levels
  mutate(
    high_school = ifelse(education_level == "High School", 1, 0),
    bachelor = ifelse(education_level == "Bachelor's", 1, 0),
    master = ifelse(education_level == "Master's", 1, 0),
    phd = ifelse(education_level == "PhD", 1, 0),
    male = ifelse(gender == "Male", 1, 0),
    # Calculate AI score
    AI_score = ifelse(React == "Senior", 3, ifelse(React == "Mid-level", 2, ifelse(React == "Junior", 1, 0))) + 
               ifelse(JavaScript == "Senior", 3, ifelse(JavaScript == "Mid-level", 2, ifelse(JavaScript == "Junior", 1, 0))) + 
               ifelse(CSS == "Senior", 3, ifelse(CSS == "Mid-level", 2, ifelse(CSS == "Junior", 1, 0)))
  ) %>%
  # Replace NA in AI_score with 0
  mutate(AI_score = ifelse(is.na(AI_score), 0, AI_score)) %>%
  # Group by treatment
  group_by(treatment) %>%
  # Calculate summary statistics
  summarize(
    n = n(),
    years_of_exp_mean = mean(years_of_exp, na.rm = TRUE),
    years_of_exp_sd = sd(years_of_exp, na.rm = TRUE),
    age_mean = mean(age, na.rm = TRUE),
    age_sd = sd(age, na.rm = TRUE),
    male_mean = mean(male, na.rm = TRUE),
    male_sd = sd(male, na.rm = TRUE),
    high_school_mean = mean(high_school, na.rm = TRUE),
    high_school_sd = sd(high_school, na.rm = TRUE),
    bachelor_mean = mean(bachelor, na.rm = TRUE),
    bachelor_sd = sd(bachelor, na.rm = TRUE),
    master_mean = mean(master, na.rm = TRUE),
    master_sd = sd(master, na.rm = TRUE),
    phd_mean = mean(phd, na.rm = TRUE),
    phd_sd = sd(phd, na.rm = TRUE),
    resume_score_mean = mean(resume_score, na.rm = TRUE),
    resume_score_sd = sd(resume_score, na.rm = TRUE),
    AI_score_mean = mean(AI_score, na.rm = TRUE),
    AI_score_sd = sd(AI_score, na.rm = TRUE),
    is_completed_mean = mean(is_completed, na.rm = TRUE),
    is_completed_sd = sd(is_completed, na.rm = TRUE),
    final_interview_mean = mean(final_interview, na.rm = TRUE),
    final_interview_sd = sd(final_interview, na.rm = TRUE)
  ) %>%
  ungroup()

# Create a formatted table for LaTeX output
vars <- c("Years of Experience", "Age", "Male", "High School", "Bachelor's", "Master's", "PhD", "Resume Score", "AI Score", "Completed", "Passed to Final Interview")
means_control <- c("years_of_exp_mean", "age_mean", "male_mean", "high_school_mean", "bachelor_mean", "master_mean", "phd_mean", "resume_score_mean", "AI_score_mean", "is_completed_mean", "final_interview_mean")
sds_control <- c("years_of_exp_sd", "age_sd", "male_sd", "high_school_sd", "bachelor_sd", "master_sd", "phd_sd", "resume_score_sd", "AI_score_sd", "is_completed_sd", "final_interview_sd")
means_treatment <- c("years_of_exp_mean", "age_mean", "male_mean", "high_school_mean", "bachelor_mean", "master_mean", "phd_mean", "resume_score_mean", "AI_score_mean", "is_completed_mean", "final_interview_mean")
sds_treatment <- c("years_of_exp_sd", "age_sd", "male_sd", "high_school_sd", "bachelor_sd", "master_sd", "phd_sd", "resume_score_sd", "AI_score_sd", "is_completed_sd", "final_interview_sd")

# Extract control group (treatment = 0) and treatment group (treatment = 1) statistics
control_stats <- summary_stats_table %>% filter(treatment == 0)
treatment_stats <- summary_stats_table %>% filter(treatment == 1)

# Create the formatted table
latex_table <- data.frame(
  Variable = vars,
  Control = paste0(
    sprintf("%.2f", sapply(means_control, function(x) control_stats[[x]])),
    " (", 
    sprintf("%.2f", sapply(sds_control, function(x) control_stats[[x]])),
    ")"
  ),
  Treatment = paste0(
    sprintf("%.2f", sapply(means_treatment, function(x) treatment_stats[[x]])),
    " (", 
    sprintf("%.2f", sapply(sds_treatment, function(x) treatment_stats[[x]])),
    ")"
  )
)

# Add sample size row
latex_table <- rbind(
  data.frame(
    Variable = "N",
    Control = as.character(control_stats$n),
    Treatment = as.character(treatment_stats$n)
  ),
  latex_table
)

# Generate LaTeX code - AER style (no colors, clean formatting)
latex_output <- kable(latex_table, format = "latex", booktabs = TRUE, 
                     caption = "Summary Statistics by Treatment Group",
                     align = c("l", "c", "c")) %>%
  kable_styling(latex_options = c("hold_position"))

# Print the LaTeX code to the console
cat("\\begin{table}[htbp]\n")
cat("\\centering\n")
cat(latex_output)
cat("\\caption*{\\textit{Note:} Standard deviations in parentheses. AI Score is the sum of skill levels in React, JavaScript, and CSS (Senior=3, Mid-level=2, Junior=1, None=0).}\n")
cat("\\end{table}\n")

# Save the table to a file
latex_file_path <- file.path(figures_dir, "summary_statistics_table.tex")
cat("\\begin{table}[htbp]\n", file = latex_file_path)
cat("\\centering\n", file = latex_file_path, append = TRUE)
cat(latex_output, file = latex_file_path, append = TRUE)
cat("\\caption*{\\textit{Note:} Standard deviations in parentheses. AI Score is the sum of skill levels in React, JavaScript, and CSS (Senior=3, Mid-level=2, Junior=1, None=0).}\n", file = latex_file_path, append = TRUE)
cat("\\end{table}\n", file = latex_file_path, append = TRUE)

# Add difference between means in treatment and control groups with standard error:
difference <-  as.numeric(sapply(means_treatment, function(x) treatment_stats[[x]])) -  as.numeric(sapply(means_control, function(x) control_stats[[x]]))
se <- sqrt(as.numeric(sapply(sds_treatment, function(x) treatment_stats[[x]]))^2 + as.numeric(sapply(sds_control, function(x) control_stats[[x]]))^2)

# Round to 3 decimal places:
difference <- round(difference, 3)
se <- round(se, 3)

# Add difference and standard error to the table:
difference <- append(NA, difference)
se <- append(NA, se)
latex_table <- cbind(
  latex_table,
  difference = difference,
  se = se
)


# Print the table as latex:
cat(knitr::kable(latex_table, format = "latex"))

# Save the table to a file:
cat(knitr::kable(latex_table, format = "latex"), file = file.path(figures_dir, "summary_statistics_table.tex"))

################################ Balance treatment and control groups ################################

data_balance <- merged_data %>% select(years_of_exp, education_level, gender, resume_score, treatment) %>% na.omit()
data_balance <- data_balance %>% mutate(years_of_exp = as.numeric(years_of_exp))
data_balance <- data_balance %>% mutate(treatment = as.factor(treatment))

# Get one-hot encoding variables from education levle based on the factor levels:
data_balance$high_school <- ifelse(data_balance$education_level == "High School", 1, 0)
data_balance$bachelor <- ifelse(data_balance$education_level == "Bachelor's", 1, 0)
data_balance$master <- ifelse(data_balance$education_level == "Master's", 1, 0)
data_balance$phd <- ifelse(data_balance$education_level == "PhD", 1, 0)

# Male
data_balance$male <- ifelse(data_balance$gender == "Male", 1, 0)

data_balance$resume_score <- as.numeric(data_balance$resume_score)

data_balance <- data_balance %>% select(-education_level, -gender)

# Calculate means and standard errors for each variable by treatment group
summary_stats <- data_balance %>%
  group_by(treatment) %>%
  summarize(across(
    .cols = c(years_of_exp, high_school, bachelor, master, phd, male, resume_score),
    .fns = list(
      mean = ~mean(.x, na.rm = TRUE),
      se = ~sd(.x, na.rm = TRUE) / sqrt(n())
    ),
    .names = "{.col}_{.fn}"
  )) %>%
  ungroup()

# Reshape to get treatment and control in separate rows
summary_wide <- summary_stats %>%
  pivot_wider(
    names_from = treatment,
    values_from = matches("_(mean|se)$"),
    names_glue = "{.value}_{treatment}"
  )

# Replace the problematic transmute code with:
result_table <- tibble(
  Variable = c("Years of Experience", "High School", "Bachelor's", "Master's", "PhD", "Male", "Resume Score"),
  `Treatment Mean` = c(summary_wide$years_of_exp_mean_1, summary_wide$high_school_mean_1, summary_wide$bachelor_mean_1, 
                      summary_wide$master_mean_1, summary_wide$phd_mean_1, summary_wide$male_mean_1, 
                      summary_wide$resume_score_mean_1),
  `Treatment SE` = c(summary_wide$years_of_exp_se_1, summary_wide$high_school_se_1, summary_wide$bachelor_se_1, 
                    summary_wide$master_se_1, summary_wide$phd_se_1, summary_wide$male_se_1, 
                    summary_wide$resume_score_se_1),
  `Control Mean` = c(summary_wide$years_of_exp_mean_0, summary_wide$high_school_mean_0, summary_wide$bachelor_mean_0, 
                    summary_wide$master_mean_0, summary_wide$phd_mean_0, summary_wide$male_mean_0, 
                    summary_wide$resume_score_mean_0),
  `Control SE` = c(summary_wide$years_of_exp_se_0, summary_wide$high_school_se_0, summary_wide$bachelor_se_0, 
                  summary_wide$master_se_0, summary_wide$phd_se_0, summary_wide$male_se_0, 
                  summary_wide$resume_score_se_0)
) %>%
  mutate(
    `Difference` = `Treatment Mean` - `Control Mean`,
    `Difference SE` = sqrt(`Treatment SE`^2 + `Control SE`^2)
  )

# Round the table to 3 decimal places
result_table <- result_table %>% mutate(across(where(is.numeric), round, 3))

# Print the table in markdown format
cat(knitr::kable(result_table, format = "markdown"))


################################## Average treatment effect ##################################


final_interview <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/top_candidates_interviewed.csv")
resume_scores <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Manual-Resume-ranked.csv")
final_interview %>% filter(email_id =="")
# Degree of missmatch between the files:

length(final_interview$email_id) - length(final_interview$email_id %in% merged_data$email_id)

# Without matching to the main file; as i'm dropping to many candiates
final_est <- final_interview %>% select(Interview.Type, interviewer, Result, Gender, Age..Years., Country, email_id)

# Analyze duplicates:
length(unique(final_est$email_id))
# Assign a differnet random number to the empty email_ids:
final_est$email_id <- ifelse(final_est$email_id == "", 
                            sapply(1:nrow(final_est), function(i) {
                              if(final_est$email_id[i] == "") {
                                paste0("random_", round(runif(1, 0, 1000000)))
                              } else {
                                final_est$email_id[i]
                              }
                            }), 
                            final_est$email_id)
final_est %>% group_by(email_id) %>% summarise(n = n()) %>% filter(n > 1)

## How often are the duplicates both in treatment and control?
final_est$treatment <- as.numeric(ifelse(final_est$Interview.Type == "AI + Human Interview", 1, 0))
final_est %>% group_by(email_id) %>% summarise(n = n(), groups = mean(treatment)) %>% filter(n > 1)
final_est %>% filter(email_id == "")
# Drop duplicates:
final_est <- final_est %>% group_by(email_id) %>% slice_head(n = 1) %>% ungroup()
final_est %>% summarise(n = n(), n_treatment = sum(treatment), n_control = sum(1-treatment))

# Data prep:.
final_est$outcome <- ifelse(final_est$Result == "Pass", 1, 0)
final_est$outcome_2 <- ifelse(final_est$Result == "Pass", 1, ifelse(final_est$Result == "Fail",0,NA))
final_est$male <- ifelse(final_est$Gender == "Male", 1, 0)
final_est$age <- ifelse(is.na(final_est$Age..Years.), "Not shared", final_est$Age..Years.)

ate_ols <- lm(outcome ~ treatment, data = final_est)
ate_ols_2 <- lm(outcome_2 ~ treatment, data = final_est)
stargazer(ate_ols, ate_ols_2, type = "text")

mean(final_est$outcome[final_est$treatment == 1], na.rm = TRUE)
mean(final_est$outcome[final_est$treatment == 0], na.rm = TRUE)

# Number of observations across treatment groups:
final_est %>% group_by(treatment) %>% summarise(n = n())

ate_ols_cov <- lm(outcome ~ treatment + age+ Gender, data = final_est)

stargazer(ate_ols, ate_ols_cov, type = "text")

# GRF

# change age to one-hot encodings:
# Values from unique(final_est$age): "23-27" "28-32" "33+" "18-22" ""
final_est$age_18_22 <- ifelse(final_est$age == "18-22", 1, 0)
final_est$age_23_27 <- ifelse(final_est$age == "23-27", 1, 0)
final_est$age_28_32 <- ifelse(final_est$age == "28-32", 1, 0)
final_est$age_33_plus <- ifelse(final_est$age == "33+", 1, 0)
final_est$age_not_shared <- ifelse(final_est$age == "", 1, 0)

X <- final_est %>% select(age_18_22, age_23_27, age_28_32, age_33_plus, age_not_shared, male) %>% as.matrix()
Y <- final_est %>% select(outcome) %>% as.matrix()
W <- final_est %>% select(treatment) %>% as.matrix()

tau_forest <- causal_forest(X, Y, W, num.trees = 1000)

    # Average treatment effect:
ate_grf <- average_treatment_effect(tau_forest, target.sample = "treated")

# Table for the paper: Baselien value (mean in control group) and treatment effect both wiht standard errors and the number of observations for the three methods ols, ols with covariates and grf

  # Calculate baseline value (mean in control group)
baseline_value <- mean(final_est$outcome[final_est$treatment == 0], na.rm = TRUE)

# Calculate treatment effect
treatment_effect <- mean(final_est$outcome[final_est$treatment == 1], na.rm = TRUE) - baseline_value

# Calculate standard errors
se_baseline <- sd(final_est$outcome[final_est$treatment == 0], na.rm = TRUE) / sqrt(sum(!is.na(final_est$outcome[final_est$treatment == 0])))
se_treatment <- sd(final_est$outcome[final_est$treatment == 1], na.rm = TRUE) / sqrt(sum(!is.na(final_est$outcome[final_est$treatment == 1])))
se_effect <- sqrt(se_baseline^2 + se_treatment^2) 

# Combine results into a table
ate_table <- data.frame(
  Method = c("Difference in Means", "OLS with covariates", "GRF"),
  Estimate = c(coef(ate_ols)[2], coef(ate_ols_cov)[2], ate_grf[1]),
  SE = c(summary(ate_ols)$coefficients[2, 2], summary(ate_ols_cov)$coefficients[2, 2], ate_grf[2]),
  Baseline = c(baseline_value, baseline_value, baseline_value),
  Baseline_SE = c(se_baseline, se_baseline, se_baseline),
  Observations = c(nrow(final_est), nrow(final_est), nrow(final_est))
)

# Final table for the paper:
ate_table <- t(ate_table)

# Round to 3 decimal places:
ate_table[2:nrow(ate_table),] <- round(as.numeric(ate_table[2:nrow(ate_table),]), 3)

# Print the table in markdown format
cat(knitr::kable(ate_table, format = "markdown"))


# Robustness check top 35 from manual:
final_interview <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/top_candidates_interviewed.csv")
resume_scores <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Manual-Resume-ranked.csv")

resume_match <- resume_scores %>% select(email_id,resume_score )

# Without matching to the main file; as i'm dropping to many candiates
final_est <- final_interview %>% select(Interview.Type, interviewer, Result, Gender, Age..Years., Country, email_id) %>% left_join(resume_match, by ="email_id")

# Analyze duplicates:
length(unique(final_est$email_id))
# Assign a differnet random number to the empty email_ids:
final_est$email_id <- ifelse(final_est$email_id == "", 
                            sapply(1:nrow(final_est), function(i) {
                              if(final_est$email_id[i] == "") {
                                paste0("random_", round(runif(1, 0, 1000000)))
                              } else {
                                final_est$email_id[i]
                              }
                            }), 
                            final_est$email_id)
final_est %>% group_by(email_id) %>% summarise(n = n()) %>% filter(n > 1)

## How often are the duplicates both in treatment and control?
final_est$treatment <- as.numeric(ifelse(final_est$Interview.Type == "AI + Human Interview", 1, 0))
final_est %>% group_by(email_id) %>% summarise(n = n(), groups = mean(treatment)) %>% filter(n > 1)
final_est %>% filter(email_id == "")
# Drop duplicates:
final_est <- final_est %>% group_by(email_id) %>% slice_head(n = 1) %>% ungroup()
final_est %>% summarise(n = n(), n_treatment = sum(treatment), n_control = sum(1-treatment))

# Data prep:.
final_est$outcome <- ifelse(final_est$Result == "Pass", 1, 0)
final_est$outcome_2 <- ifelse(final_est$Result == "Pass", 1, ifelse(final_est$Result == "Fail",0,NA))
final_est$male <- ifelse(final_est$Gender == "Male", 1, 0)
final_est$age <- ifelse(is.na(final_est$Age..Years.), "Not shared", final_est$Age..Years.)

# Select top 35 candidates from control group by resume_score
# Keep all candidates from treatment group
treatment_candidates <- final_est %>% filter(treatment == 1)

# Select top 35 candidates from control group by resume_score
control_candidates <- final_est %>% 
  filter(treatment == 0) %>%
  arrange(desc(resume_score)) %>%
  slice_head(n = 35)

# Combine treatment group with top 35 control candidates
final_est <- rbind(treatment_candidates, control_candidates)

# Verify the counts
cat("Treatment candidates:", nrow(treatment_candidates), "\n")
cat("Control candidates (top 35):", nrow(control_candidates), "\n")
cat("Total candidates in final dataset:", nrow(final_est), "\n")


ate_ols <- lm(outcome ~ treatment, data = final_est)
ate_ols_2 <- lm(outcome_2 ~ treatment, data = final_est)
stargazer(ate_ols, ate_ols_2, type = "text")

mean(final_est$outcome[final_est$treatment == 1], na.rm = TRUE)
mean(final_est$outcome[final_est$treatment == 0], na.rm = TRUE)

# Number of observations across treatment groups:
final_est %>% group_by(treatment) %>% summarise(n = n())

ate_ols_cov <- lm(outcome ~ treatment + age+ Gender, data = final_est)

stargazer(ate_ols, ate_ols_cov, type = "text")

# Share of candidates in treatment group that passed
mean(final_est$outcome[final_est$treatment == 1])
mean(final_est$outcome[final_est$treatment == 0])


# change age to one-hot encodings:
# Values from unique(final_est$age): "23-27" "28-32" "33+" "18-22" ""
final_est$age_18_22 <- ifelse(final_est$age == "18-22", 1, 0)
final_est$age_23_27 <- ifelse(final_est$age == "23-27", 1, 0)
final_est$age_28_32 <- ifelse(final_est$age == "28-32", 1, 0)
final_est$age_33_plus <- ifelse(final_est$age == "33+", 1, 0)
final_est$age_not_shared <- ifelse(final_est$age == "", 1, 0)

X <- final_est %>% select(age_18_22, age_23_27, age_28_32, age_33_plus, age_not_shared, male) %>% as.matrix()
Y <- final_est %>% select(outcome) %>% as.matrix()
W <- final_est %>% select(treatment) %>% as.matrix()

tau_forest <- causal_forest(X, Y, W, num.trees = 1000)

    # Average treatment effect:
ate_grf <- average_treatment_effect(tau_forest, target.sample = "treated")

# Table for the paper: Baselien value (mean in control group) and treatment effect both wiht standard errors and the number of observations for the three methods ols, ols with covariates and grf

  # Calculate baseline value (mean in control group)
baseline_value <- mean(final_est$outcome[final_est$treatment == 0], na.rm = TRUE)

# Calculate treatment effect
treatment_effect <- mean(final_est$outcome[final_est$treatment == 1], na.rm = TRUE) - baseline_value

# Calculate standard errors
se_baseline <- sd(final_est$outcome[final_est$treatment == 0], na.rm = TRUE) / sqrt(sum(!is.na(final_est$outcome[final_est$treatment == 0])))
se_treatment <- sd(final_est$outcome[final_est$treatment == 1], na.rm = TRUE) / sqrt(sum(!is.na(final_est$outcome[final_est$treatment == 1])))
se_effect <- sqrt(se_baseline^2 + se_treatment^2) 

# Combine results into a table
ate_table <- data.frame(
  Method = c("Difference in Means", "OLS with covariates", "GRF"),
  Estimate = c(coef(ate_ols)[2], coef(ate_ols_cov)[2], ate_grf[1]),
  SE = c(summary(ate_ols)$coefficients[2, 2], summary(ate_ols_cov)$coefficients[2, 2], ate_grf[2]),
  Baseline = c(baseline_value, baseline_value, baseline_value),
  Baseline_SE = c(se_baseline, se_baseline, se_baseline),
  Observations = c(nrow(final_est), nrow(final_est), nrow(final_est))
)

# Final table for the paper:
ate_table <- t(ate_table)

# Round to 3 decimal places:
ate_table[2:nrow(ate_table),] <- round(as.numeric(ate_table[2:nrow(ate_table),]), 3)

# Print the table in markdown format
cat(knitr::kable(ate_table, format = "markdown"))

# Save this as latex table for an academic paper:
library(xtable)
library(kableExtra)

# Create a properly formatted LaTeX table
latex_table <- kable(ate_table, format = "latex", booktabs = TRUE, 
                    caption = "Average Treatment Effects Across Different Estimation Methods",
                    label = "tab:ate_results") %>%
  kable_styling(full_width = FALSE) %>%
  add_header_above(c(" " = 1, "Estimation Results" = ncol(ate_table) - 1)) %>%
  footnote(general = "Note: This table presents average treatment effects estimated using three different methods. 
           Baseline values represent mean outcomes in the control group.",
           threeparttable = TRUE,
           footnote_as_chunk = TRUE)

# Save to file
cat(latex_table, file = "ate_results_table.tex")

# Also print to console
cat(latex_table)







# Select 35 candidates in the control group at random:

# Set seed for reproducibility
set.seed(123)

# Select all candidates from treatment group
treatment_candidates_random <- final_est %>% filter(treatment == 1)

# Select 35 candidates from control group at random
control_candidates_random <- final_est %>% 
  filter(treatment == 0) %>%
  sample_n(35)

# Combine treatment group with randomly selected control candidates
final_est_random <- rbind(treatment_candidates_random, control_candidates_random)

# Verify the counts
cat("Treatment candidates:", nrow(treatment_candidates_random), "\n")
cat("Control candidates (random 35):", nrow(control_candidates_random), "\n")
cat("Total candidates in random dataset:", nrow(final_est_random), "\n")

# Run the same analysis with randomly selected control group
ate_ols_random <- lm(outcome ~ treatment, data = final_est_random)
ate_ols_2_random <- lm(outcome_2 ~ treatment, data = final_est_random)
stargazer(ate_ols_random, ate_ols_2_random, type = "text")

# Compare means
cat("Treatment mean (random):", mean(final_est_random$outcome[final_est_random$treatment == 1], na.rm = TRUE), "\n")
cat("Control mean (random):", mean(final_est_random$outcome[final_est_random$treatment == 0], na.rm = TRUE), "\n")

# Number of observations across treatment groups in random sample:
final_est_random %>% group_by(treatment) %>% summarise(n = n())

# Run model with covariates
ate_ols_cov_random <- lm(outcome ~ treatment + age + Gender, data = final_est_random)

# Compare models
stargazer(ate_ols_random, ate_ols_cov_random, type = "text")


################################# Mechanisms #################################

# Create a dataframe for plotting resume scores across different groups
merged_data$resume_score <- as.numeric(merged_data$resume_score)

overall_treatment <- mean(merged_data$resume_score[merged_data$treatment == 1], na.rm = TRUE)
overall_control <- mean(merged_data$resume_score[merged_data$treatment == 0], na.rm = TRUE)

# Calculate means for reference
selected_by_ai <- mean(merged_data$resume_score[merged_data$final_interview == 1 & merged_data$treatment == 1], na.rm = TRUE)
selected_by_human <- mean(merged_data$resume_score[merged_data$final_interview == 1 & merged_data$treatment == 0], na.rm = TRUE)
not_selected <- mean(merged_data$resume_score[merged_data$final_interview == 0 & merged_data$treatment == 1], na.rm = TRUE)
completed <- mean(merged_data$resume_score[merged_data$is_completed == 1 & merged_data$treatment == 1], na.rm = TRUE)
dropped_out <- mean(merged_data$resume_score[merged_data$is_completed == 0 & merged_data$treatment == 1], na.rm = TRUE)

# Create the first plot: Selection by AI vs Human
plot1 <- ggplot() +
  geom_density(data = merged_data %>% filter(final_interview == 1 & treatment == 1),
               aes(x = resume_score, fill = "Selected by AI"), alpha = 0.6, adjust = 3) +
  geom_density(data = merged_data %>% filter(final_interview == 1 & treatment == 0),
               aes(x = resume_score, fill = "Selected by Human"), alpha = 0.6, adjust = 3) +
  geom_density(data = merged_data %>% filter(final_interview == 0 & treatment == 1),
               aes(x = resume_score, fill = "Not Selected"), alpha = 0.6, adjust = 3) +
  geom_vline(xintercept = selected_by_ai, linetype = "dashed", color = "blue") +
  geom_vline(xintercept = selected_by_human, linetype = "dashed", color = "red") +
  geom_vline(xintercept = not_selected, linetype = "dashed", color = "darkgray") +
  labs(title = "Resume Scores: AI vs Human Selection",
       x = "Resume Score",
       y = "Density") +
  scale_fill_manual(values = c("Selected by AI" = "blue", "Selected by Human" = "red", "Not Selected" = "darkgray")) +
  theme_bw() +
  theme(legend.title = element_blank(),
        legend.position = "bottom",
        text = element_text(size = 24),
        axis.title = element_text(size = 26),
        plot.title = element_text(size = 28, face = "bold"))

# Create the second plot: Completed vs Dropped Out
plot2 <- ggplot() +
  geom_density(data = merged_data %>% filter(is_completed == 1 & treatment == 1),
               aes(x = resume_score, fill = "Completed"), alpha = 0.6, adjust = 3) +
  geom_density(data = merged_data %>% filter(is_completed == 0 & treatment == 1),
               aes(x = resume_score, fill = "Dropped Out"), alpha = 0.6, adjust = 3) +
  geom_vline(xintercept = completed, linetype = "dashed", color = "green") +
  geom_vline(xintercept = dropped_out, linetype = "dashed", color = "orange") +
  labs(title = "Resume Scores: Completed vs Dropped Out",
       x = "Resume Score",
       y = "Density") +
  scale_fill_manual(values = c("Completed" = "green", "Dropped Out" = "orange")) +
  theme_bw() +
  theme(legend.title = element_blank(),
        legend.position = "bottom",
        text = element_text(size = 24),
        axis.title = element_text(size = 26),
        plot.title = element_text(size = 28, face = "bold"))

# Combine the plots into a single figure
combined_plot <- grid.arrange(plot2, plot1, ncol = 2)

# Save the combined figure
ggsave(filename = "resume_score_distributions.png", plot = combined_plot, path = figures_dir, 
       width = 25, height = 6)

############### Are people non-randomly dropping out? ###############

treated_users <- merged_data %>% filter(treatment == 1)
treated_users$dropped_out <- ifelse(treated_users$is_completed, 0, 1)
treated_users$resume_score <- as.numeric(treated_users$resume_score)
treated_users$male <- ifelse(treated_users$gender == "Male", 1, 0)
treated_users$high_school <- ifelse(treated_users$education_level == "High School", 1, 0)
treated_users$bachelor <- ifelse(treated_users$education_level == "Bachelor's", 1, 0)
treated_users$master <- ifelse(treated_users$education_level == "Master's", 1, 0)
treated_users$phd <- ifelse(treated_users$education_level == "PhD", 1, 0)
t.test(treated_users$resume_score[treated_users$dropped_out == 1], treated_users$resume_score[treated_users$dropped_out == 0])

summary(treated_users$dropped_out)

treated_users <- treated_users %>% filter(!is.na(resume_score))

ols_dropped_out <- lm(dropped_out ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = treated_users)

# Same with logit
logit_dropped_out <- glm(dropped_out ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = treated_users, family = "binomial")

stargazer(ols_dropped_out, logit_dropped_out, type = "text")

# no resume score:
ols_dropped_out_no_resume <- lm(dropped_out ~ years_of_exp + age + high_school + bachelor + master  + male, data = treated_users)

# Same with logit
logit_dropped_out_no_resume <- glm(dropped_out ~ years_of_exp + age + high_school + bachelor + master  + male, data = treated_users, family = "binomial")

stargazer(ols_dropped_out_no_resume, logit_dropped_out_no_resume, type = "latex")  

# Give output in markdown format:
cat(knitr::kable(stargazer(ols_dropped_out, logit_dropped_out, type = "text"), format = "markdown"))

# Get tidy results with confidence intervals
coef_df <- tidy(ols_dropped_out, conf.int = TRUE)

# Remove the intercept (optional)
coef_df <- coef_df %>% filter(term != "(Intercept)")

# Plot
dropped_out_forest_plot <- ggplot(coef_df, aes(x = term, y = estimate)) +
  geom_point() +
  geom_errorbar(aes(ymin = conf.low, ymax = conf.high), width = 0.2) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "red") +
  coord_flip() +  # flips axes for better readability
  labs(title = "OLS Coefficient Estimates",
       x = "Variable",
       y = "Estimate (with 95% CI)") +
  theme_bw()

# save the plot:
ggsave(filename = "dropped_out_forest_plot.png", plot = dropped_out_forest_plot, path = figures_dir)


#################### Dropping out -- rational expectations or aversion? ####################
treated_users$passed_AI <- ifelse(treated_users$is_passed == TRUE, 1, 0)
summary(treated_users$passed_AI[treated_users$is_completed == 1])
sum(treated_users$passed_AI)
participated <- treated_users %>% filter(is_completed == 1)
not_participated <- treated_users %>% filter(is_completed == 0)

ols_passed_AI <- lm(passed_AI ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = participated)
logit_passed_AI <- glm(passed_AI ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = participated, family = "binomial")

stargazer(ols_passed_AI, logit_passed_AI, type = "text")

# Give output in markdown format:
cat(knitr::kable(stargazer(ols_passed_AI, logit_passed_AI, type = "text"), format = "markdown"))


# Train GBM model
gbm_model <- gbm(
  passed_AI ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score,
  data = participated,
  distribution = "bernoulli",
  n.trees = 1000,
  interaction.depth = 3,
  shrinkage = 0.01,
  cv.folds = 5
)

# Evaluate model performance
best_iter <- gbm.perf(gbm_model, method = "cv")
print(paste("Best iteration based on CV:", best_iter))

# Calculate performance metrics
predictions <- predict(gbm_model, newdata = participated, n.trees = best_iter, type = "response")
pred_class <- ifelse(predictions > 0.5, 1, 0)
conf_matrix <- confusionMatrix(factor(pred_class), factor(participated$passed_AI))
print(conf_matrix)

# Variable importance
var_importance <- summary(gbm_model, n.trees = best_iter, plotit = FALSE)
print("Variable importance:")
print(var_importance)

summary(lm(participated$passed_AI ~ predicted_probabilities_participated))

# predict on the not participated:

predicted_probabilities <- predict(gbm_model, newdata = not_participated, n.trees = 1000, type = "response")
predicted_probabilities_participated <- predict(gbm_model, newdata = participated, n.trees = 1000, type = "response")

# add to tables
not_participated$predicted_probabilities <- predicted_probabilities
participated$predicted_probabilities <- predicted_probabilities_participated

# Create dataframes for plotting
plot_data_not_participated <- data.frame(probability = predicted_probabilities, group = "Non-Participants")
plot_data_participated <- data.frame(probability = predicted_probabilities_participated, group = "Participants")
plot_data_combined <- rbind(plot_data_not_participated, plot_data_participated)

# Create professional density plot
density_plot <- ggplot(plot_data_combined, aes(x = probability, fill = group)) +
  geom_density(alpha = 0.7, adjust = 1.5) +
  scale_fill_manual(values = c("Non-Participants" = "#3182bd", "Participants" = "#de2d26")) +
  labs(title = "Predicted Probability of Passing AI Screening",
       subtitle = "Comparison between Participants and Non-Participants",
       x = "Predicted Probability",
       y = "Density",
       fill = "") +
  theme_bw() +
  theme(text = element_text(family = "Times", size = 12),
        plot.title = element_text(size = 14, face = "bold"),
        plot.subtitle = element_text(size = 12, face = "italic"),
        axis.title = element_text(size = 12, face = "bold"),
        axis.text = element_text(size = 10),
        panel.grid.minor = element_blank(),
        panel.border = element_rect(linewidth = 1),
        legend.position = "top",
        legend.text = element_text(size = 11),
        plot.margin = unit(c(0.5, 0.5, 0.5, 0.5), "cm"))

# Add vertical lines for means
group_means <- aggregate(probability ~ group, data = plot_data_combined, FUN = mean)
density_plot <- density_plot +
  geom_vline(data = group_means, 
             aes(xintercept = probability, color = group),
             linetype = "dashed", size = 1) +
  scale_color_manual(values = c("Non-Participants" = "#3182bd", "Participants" = "#de2d26"))

# Save the plot
ggsave(filename = "predicted_probabilities_density.png", plot = density_plot, 
       path = figures_dir, width = 8, height = 6, dpi = 300)



# Create a professional plot of predicted probabilities
predicted_prob_plot <- ggplot(not_participated, aes(x = predicted_probabilities)) +
  geom_histogram(binwidth = 0.05, fill = "gray80", color = "black", alpha = 0.8) +
  geom_vline(xintercept = mean(not_participated$predicted_probabilities), 
             linetype = "dashed", color = "darkred", size = 1) +
  annotate("text", x = mean(not_participated$predicted_probabilities) + 0.1, 
           y = max(hist(not_participated$predicted_probabilities, plot = FALSE)$counts) * 0.9, 
           label = paste("Mean =", round(mean(not_participated$predicted_probabilities), 2)),
           hjust = 0, size = 3.5) +
  labs(title = "Predicted Probability of Passing AI Screening",
       subtitle = "Non-Participating Candidates",
       x = "Predicted Probability",
       y = "Frequency") +
  theme_bw() +
  theme(text = element_text(family = "Times", size = 12),
        plot.title = element_text(size = 14, face = "bold"),
        plot.subtitle = element_text(size = 12, face = "italic"),
        axis.title = element_text(size = 12, face = "bold"),
        axis.text = element_text(size = 10),
        panel.grid.minor = element_blank(),
        panel.border = element_rect(linewidth = 1),
        plot.margin = unit(c(0.5, 0.5, 0.5, 0.5), "cm"))

# Save the plot
ggsave(filename = "src/figures/predicted_probabilities_plot.png", plot = predicted_prob_plot, 
       path = figures_dir, width = 7, height = 5, dpi = 300)

# Display the plot
predicted_prob_plot

# Who are those that are in top quartile of predicted probabilities and drop out? Who are those that are in bottom quartile and drop out?
# Create a dataframe for the heatmap
df_quartile_heatmap <- data.frame(
  covariate = character(),
  avg = numeric(),
  stderr = numeric(),
  group = character(),
  scaling = numeric(),
  labels = character(),
  stringsAsFactors = FALSE
)

# Define the groups and their data
groups <- list(
  "Top Quartile - Dropped Out" = not_participated %>% filter(predicted_probabilities > quantile(predicted_probabilities, 0.75)),
  "Bottom Quartile - Dropped Out" = not_participated %>% filter(predicted_probabilities < quantile(predicted_probabilities, 0.25)),
  "Top Quartile - Participated" = {participated$predicted_probabilities <- as.numeric(participated$predicted_probabilities); 
                                  participated %>% filter(predicted_probabilities > quantile(predicted_probabilities, 0.75))},
  "Bottom Quartile - Participated" = participated %>% filter(predicted_probabilities < quantile(predicted_probabilities, 0.25))
)

# Define covariates to analyze
covariates <- c("years_of_exp", "age", "high_school", "bachelor", "master", "male", "resume_score")

# Calculate means and standard errors for each group and covariate
for (cov in covariates) {
  # Get means across all groups for this covariate
  all_means <- sapply(groups, function(df) mean(df[[cov]], na.rm = TRUE))
  
  # For each group
  for (group_name in names(groups)) {
    group_data <- groups[[group_name]]
    n <- nrow(group_data)
    
    # Calculate mean and standard error
    avg_val <- mean(group_data[[cov]], na.rm = TRUE)
    stderr_val <- sd(group_data[[cov]], na.rm = TRUE) / sqrt(sum(!is.na(group_data[[cov]])))
    
    # Calculate z-score for scaling
    z_score <- (avg_val - mean(all_means)) / sd(all_means)
    if (is.na(z_score)) z_score <- 0  # Handle case where all values are the same
    
    # Add to dataframe
    df_quartile_heatmap <- rbind(df_quartile_heatmap, data.frame(
      covariate = cov,
      avg = avg_val,
      stderr = stderr_val,
      group = group_name,
      scaling = z_score,
      labels = paste0(signif(avg_val, 3), "\n", "(", signif(stderr_val, 3), ")"),
      stringsAsFactors = FALSE
    ))
  }
}

# Make covariate names more readable
df_quartile_heatmap$covariate <- factor(df_quartile_heatmap$covariate, 
                                       levels = covariates,
                                       labels = c("Years of Experience", "Age", "High School", 
                                                 "Bachelor's", "Master's", "Male", "Resume Score"))

# Create the heatmap
quartile_heatmap <- ggplot(df_quartile_heatmap) +
  aes(covariate, group) +
  geom_tile(aes(fill = scaling)) + 
  geom_text(aes(label = labels), size = 4) +
  scale_fill_gradient(low = "#E1BE6A", high = "#40B0A6") +
  theme_minimal() + 
  ylab("") + xlab("") +
  theme(axis.text.x = element_text(size = 14, angle = 45, hjust = 1),
        axis.text.y = element_text(size = 14),
        text = element_text(size = 14),
        legend.position = "none")

# Save the heatmap
ggsave(filename = "quartile_comparison_heatmap.png", plot = quartile_heatmap, 
       path = figures_dir, width = 10, height = 8, dpi = 300)

# Display the heatmap
quartile_heatmap


# Predict probabilitie to pass to all treated users:
treated_users$predicted_probabilities <- predict(gbm_model, newdata = treated_users, n.trees = 1000, type = "response")

ols_dropped_out_predicted <- lm(dropped_out ~ predicted_probabilities + years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = treated_users)

logit_dropped_out_predicted <- glm(dropped_out ~ predicted_probabilities + years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = treated_users, family = "binomial")

stargazer(ols_dropped_out_predicted, logit_dropped_out_predicted, type = "text")

# no covariates:
ols_dropped_out_predicted_no_cov <- lm(dropped_out ~ predicted_probabilities, data = treated_users)
logit_dropped_out_predicted_no_cov <- glm(dropped_out ~ predicted_probabilities, data = treated_users, family = "binomial")

stargazer(ols_dropped_out_predicted_no_cov, logit_dropped_out_predicted_no_cov, type = "text")

treated_users$dropped_out <- ifelse(treated_users$is_completed == 0, 1, 0)
treated_users$passed_AI <- ifelse(treated_users$is_passed == TRUE, 1, 0)
treated_users$passed_AI <- ifelse(treated_users$dropped_out == 1, NA, treated_users$passed_AI)

treated_users <- treated_users %>% 
  mutate(
    # 1 = accepted / interviewed  (outcome observed)
    accepted = ifelse(is_completed == 1, 1, 0),

    # outcome: 1 = passed, 0 = failed, NA if not interviewed
    pass_AI  = case_when(
                 accepted == 0        ~ NA_real_,  # not observed
                 is_passed == TRUE     ~ 1,
                 TRUE                  ~ 0
               ),

    # make them proper two-level factors so selection() is happy
    accepted = factor(accepted,  levels = c(0, 1)),
    pass_AI  = factor(pass_AI,   levels = c(0, 1))
  )

library(pbivnorm)     # only dependency; installs in seconds

treated_users_no_na <- treated_users %>% select(accepted, pass_AI, years_of_exp, age, high_school, bachelor, master, male, resume_score)

treated_users_no_na <- treated_users_no_na %>% filter(!is.na(years_of_exp) & !is.na(age) & !is.na(high_school) & !is.na(bachelor) & !is.na(master) & !is.na(male) & !is.na(resume_score))

y1 <- treated_users_no_na$accepted              # 1 = showed up, 0 = no-show
y2 <- treated_users_no_na$pass_AI               # 1 = passed, 0 = failed, NA if no-show


X1 <- model.matrix(~ years_of_exp + age + high_school +
                     bachelor + master + male + resume_score,
                   data = treated_users_no_na)

X2 <- X1                                   # same regressors in both eqns
logLik_biprobit <- function(theta, y1, y2, X1, X2) {

  k  <- ncol(X1)
  g  <- theta[          1:k]               # γ  (selection)
  b  <- theta[  k + (1:k)]                # β  (outcome)
  at <- theta[2*k + 1]                    # atanh(ρ)  (keeps |ρ|<1)
  rho <- tanh(at)

  eta1 <- as.vector(X1 %*% g)
  eta2 <- as.vector(X2 %*% b)

  # joint probabilities
  p11 <- pbivnorm::pbivnorm( eta1,  eta2,  rho)          # A=1 , P=1
  p10 <- pbivnorm::pbivnorm( eta1, -eta2, -rho)          # A=1 , P=0
  p00 <- pnorm(-eta1)                                    # A=0       (no show)

  # assemble individual log-lik contributions
  ll  <- numeric(length(y1))
  ll[y1 == 1 & y2 == 1] <- log(p11[y1 == 1 & y2 == 1])
  ll[y1 == 1 & y2 == 0] <- log(p10[y1 == 1 & y2 == 0])
  ll[y1 == 0]           <- log(p00[y1 == 0])

  -sum(ll)                           # optim minimises
}

# separate probits for starting values
g0 <- coef(glm(y1 ~ X1 - 1, family = binomial(link = "probit")))
b0 <- coef(glm(y2[y1 == 1] ~ X2[y1 == 1, ] - 1, family = binomial(link = "probit")))
theta0 <- c(g0, b0, atanh(0.1))      # start ρ at 0.1

fit <- optim(theta0, logLik_biprobit,
             method = "BFGS",
             hessian = TRUE,
             y1 = y1, y2 = y2, X1 = X1, X2 = X2,
             control = list(maxit = 500, fnscale = 1))

conv_ok <- fit$convergence == 0
if(!conv_ok) warning("optim did not converge!")

theta_hat <- fit$par
vcov_hat  <- solve(fit$hessian)       # covariance matrix
se_hat    <- sqrt(diag(vcov_hat))

k <- ncol(X1)
out_coeff <- data.frame(
  Coef = c(theta_hat[1:k],           # γ
           theta_hat[k + (1:k)],     # β
           rho = tanh(theta_hat[2*k+1])),
  SE   = c(se_hat[1:k],
           se_hat[k + (1:k)],
           se_hat[2*k+1] * (1 - tanh(theta_hat[2*k+1])^2) )  # delta rule
)
out_coeff$z  <- out_coeff$Coef / out_coeff$SE
out_coeff$p  <- 2 * pnorm(-abs(out_coeff$z))

rownames(out_coeff) <-
  c(paste0("γ:", colnames(X1)),
    paste0("β:", colnames(X2)),
    "rho")

print(out_coeff, digits = 3)



# ------------------------------------------------------------------
# helper: one bootstrap replication --------------------------------
# ------------------------------------------------------------------
boot_two_step <- function(data, indices,
                          n.trees = 250,
                          depth   = 3,
                          shrink  = 0.01) {

  # 1. resample rows ----------------------------------------------
  d <- data[indices, ]

  # 2. re-fit GBM on *participants only* ---------------------------
  train <- subset(d, accepted == 1)           # accepted == 1 == showed up
  gbm_fit <- gbm(
    passed_AI ~ years_of_exp + age + high_school +
                bachelor + master + male + resume_score,
    data             = train,
    distribution     = "bernoulli",
    n.trees          = n.trees,
    interaction.depth= depth,
    shrinkage        = shrink,
    cv.folds         = 5,
    verbose          = FALSE
  )
  best_iter <- gbm.perf(gbm_fit, plot.it = FALSE)

  # 3. predict for *everybody* in this bootstrap world -------------
  d$pred_prob <- predict(gbm_fit, newdata = d,
                         n.trees = best_iter, type = "response")

  # 4a. second-stage OLS ------------------------------------------
  ols_fit <- lm(dropped_out ~ pred_prob + years_of_exp + age +
                              high_school + bachelor + master +
                              male + resume_score,
                data = d)

  # 4b. second-stage logit ----------------------------------------
  logit_fit <- glm(dropped_out ~ pred_prob + years_of_exp + age +
                                 high_school + bachelor + master +
                                 male + resume_score,
                   data = d, family = binomial)

  # 5. store the coefficient(s) you care about --------------------
  c(ols = coef(ols_fit)["pred_prob"],
    logit = coef(logit_fit)["pred_prob"])
}

# ------------------------------------------------------------------
# run the bootstrap ------------------------------------------------
# ------------------------------------------------------------------
set.seed(42)
B <- 250          # 500–1000 is typical; raise for final paper
library(boot)
boot_res <- boot(
  data      = treated_users,
  statistic = function(data, indices) {
    cat("Running bootstrap sample", which(duplicated(list(indices)) == FALSE), "of", B, "\n")
    boot_two_step(data, indices)
  },
  R         = B,
  parallel  = "multicore",    # "multicore" or "snow" for speed
  ncpus     = 4               # if you switch to multicore
)

# ------------------------------------------------------------------
# results ----------------------------------------------------------
# ------------------------------------------------------------------
# point estimates from the original full sample -------------------
orig_coef <- attr(boot_res$t0, "dimnames")[[1]]   # "ols" "logit"
orig_coef <- boot_res$t0

# bootstrap SEs ----------------------------------------------------
boot_se  <- apply(boot_res$t, 2, sd, na.rm = TRUE)

# percentile CIs ---------------------------------------------------
ci_ols   <- boot.ci(boot_res, type = "perc", index = 1)$percent[4:5]
ci_logit <- boot.ci(boot_res, type = "perc", index = 2)$percent[4:5]

out <- data.frame(
  model   = c("OLS", "Logit"),
  coef    = orig_coef,
  se_boot = boot_se,
  ci_lo   = c(ci_ols[1],   ci_logit[1]),
  ci_hi   = c(ci_ols[2],   ci_logit[2]),
  p_empir = 2 * pmin(
              colMeans(boot_res$t >= orig_coef, na.rm = TRUE),
              colMeans(boot_res$t <= orig_coef, na.rm = TRUE))
)

print(out, digits = 3)



#####Who benefits from the AI vetting? ####################

# Raw difference in resume scores


treated_users <- merged_data %>% filter(treatment == 1)
treated_users$AI_score <- ifelse(treated_users$React == "Senior", 3, ifelse(treated_users$React == "Mid-level", 2, ifelse(treated_users$React == "Junior", 1, 0))) + 
  ifelse(treated_users$JavaScript == "Senior", 3, ifelse(treated_users$JavaScript == "Mid-level", 2, ifelse(treated_users$JavaScript == "Junior", 1, 0))) + 
  ifelse(treated_users$CSS == "Senior", 3, ifelse(treated_users$CSS == "Mid-level", 2, ifelse(treated_users$CSS == "Junior", 1, 0)))

treated_users$AI_score <- as.numeric(treated_users$AI_score)
treated_users$AI_score <- ifelse(is.na(treated_users$AI_score), 0, treated_users$AI_score)

# Percentilles of AI and resume score:
treated_users$AI_score_percentile <- ecdf(treated_users$AI_score)(treated_users$AI_score)
treated_users$AI_rank <- rank(treated_users$AI_score)
treated_users$resume_score <- as.numeric(treated_users$resume_score)
treated_users$resume_score <- ifelse(is.na(treated_users$resume_score), 0, treated_users$resume_score)
treated_users$resume_score_percentile <- ecdf(treated_users$resume_score)(treated_users$resume_score)
treated_users$resume_rank <- rank(treated_users$resume_score)
# Regression with change in rank
treated_users$rank_diff <- treated_users$AI_rank - treated_users$resume_rank
treated_users$rank_diff <- ifelse(is.na(treated_users$rank_diff), 0, treated_users$rank_diff)

# Add education level as a factor:
treated_users$high_school <- ifelse(treated_users$education_level == "High School", 1, 0)
treated_users$bachelor <- ifelse(treated_users$education_level == "Bachelor's", 1, 0)
treated_users$master <- ifelse(treated_users$education_level == "Master's", 1, 0)
treated_users$phd <- ifelse(treated_users$education_level == "PhD", 1, 0)

#Male
treated_users$male <- ifelse(treated_users$gender == "Male", 1, 0)

# Regression with rank difference:
rank_diff_reg <- lm(rank_diff ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = treated_users)

# Add to the earlier stargazer output:
stargazer(ols_dropped_out, logit_dropped_out, rank_diff_reg, type = "text")

# Organize into three groups based on the change:

treated_users$group_1 <- ifelse(treated_users$rank_diff > quantile(treated_users$rank_diff, 0.66), 1, 0 )
treated_users$group_2 <- ifelse(treated_users$rank_diff > quantile(treated_users$rank_diff, 0.33) & treated_users$rank_diff <= quantile(treated_users$rank_diff, 0.66), 1, 0)
treated_users$group_3 <- ifelse(treated_users$rank_diff <= quantile(treated_users$rank_diff, 0.33), 1, 0)

treated_users$group <- ifelse(treated_users$group_1 == 1, "Benefits from AI", ifelse(treated_users$group_3 == 1, "Harmed by AI", "Not Impacted"))  

summary_covariates <- treated_users %>% group_by(group) %>% summarise(mean_male = mean(male, na.rm = TRUE), sd_male = sd(male, na.rm = TRUE)/sqrt(n()),
                                              mean_high_school = mean(high_school, na.rm = TRUE), sd_high_school = sd(high_school, na.rm = TRUE)/sqrt(n()),
                                              mean_bachelor = mean(bachelor, na.rm = TRUE), sd_bachelor = sd(bachelor, na.rm = TRUE)/sqrt(n()),
                                              mean_master = mean(master, na.rm = TRUE), sd_master = sd(master, na.rm = TRUE)/sqrt(n()),
                                              mean_years_of_exp = mean(years_of_exp, na.rm = TRUE), sd_years_of_exp = sd(years_of_exp, na.rm = TRUE)/sqrt(n()),
                                              mean_age = mean(age, na.rm = TRUE), sd_age = sd(age, na.rm = TRUE)/sqrt(n()),
                                              mean_resume_score = mean(resume_score, na.rm = TRUE), sd_resume_score = sd(resume_score, na.rm = TRUE)/sqrt(n()))

summary_covariates <- t(summary_covariates) %>% as.data.frame()

# Use first row as column names:
colnames(summary_covariates) <- summary_covariates[1, ]
summary_covariates <- summary_covariates[-1, ]

# Convert to numeric:
summary_covariates <- summary_covariates %>% mutate_all(as.numeric)


# Plot the heatmap:

# Create a dataframe for the heatmap from summary_covariates
df_heatmap <- data.frame(
  covariate = character(),
  avg = numeric(),
  stderr = numeric(),
  group = character(),
  scaling = numeric(),
  labels = character(),
  stringsAsFactors = FALSE
)

# Get all the covariate names (removing the mean_ and sd_ prefixes)
covariate_names <- unique(gsub("^(mean_|sd_)", "", rownames(summary_covariates)))

# For each covariate, extract the mean and standard deviation for each group
for (cov in covariate_names) {
  mean_row <- paste0("mean_", cov)
  sd_row <- paste0("sd_", cov)
  
  if (mean_row %in% rownames(summary_covariates) && sd_row %in% rownames(summary_covariates)) {
    # Get values for all groups
    means_across_groups <- as.numeric(summary_covariates[mean_row, ])
    
    # For each group
    for (group_idx in 1:ncol(summary_covariates)) {
      group_name <- colnames(summary_covariates)[group_idx]
      avg_val <- summary_covariates[mean_row, group_idx]
      stderr_val <- summary_covariates[sd_row, group_idx]
      
      # Calculate z-score for scaling (how far from mean in std dev units)
      z_score <- (avg_val - mean(means_across_groups)) / sd(means_across_groups)
      if (is.na(z_score)) z_score <- 0  # Handle case where all values are the same
      
      df_heatmap <- rbind(df_heatmap, data.frame(
        covariate = cov,
        avg = avg_val,
        stderr = stderr_val,
        group = group_name,
        scaling = z_score,
        labels = paste0(signif(avg_val, 3), "\n", "(", signif(stderr_val, 3), ")"),
        stringsAsFactors = FALSE
      ))
    }
  }
}
# Plot heatmap using the prepared data
# Reorder the factor levels to put "Benefits from AI" at the top
df_heatmap$group <- factor(df_heatmap$group, 
                          levels = c("Benefits from AI", "Not Impacted", "Harmed by AI"))

ai_heatmap <- ggplot(df_heatmap) +
  aes(covariate, group) +  # Transposed x and y
  geom_tile(aes(fill = scaling)) + 
  geom_text(aes(label = labels), size = 4) +  # Increased text size
  scale_fill_gradient(low = "#E1BE6A", high = "#40B0A6") +
  theme_minimal() + 
  ylab("") + xlab("") +
  theme(axis.text.x = element_text(size = 14),  # Increased axis text size
        axis.text.y = element_text(size = 14),  # Increased axis text size
        text = element_text(size = 14),         # Increased general text size
        legend.position = "none")  # Remove the legend

# save the plot:
ggsave(filename = "ai_heatmap.png", plot = ai_heatmap, path = figures_dir, 
       width = 15, height = 6)


# Group 1: benefits from AI vetting:
treated_users$group_1 <- ifelse(treated_users$AI_score_percentile > treated_users$resume_score_percentile  + 0.1, 1, 0)

# Group 3: harmed by AI vetting:
treated_users$group_3 <- ifelse(treated_users$AI_score_percentile < treated_users$resume_score_percentile - 0.1, 1, 0)

# How many people are in each group?
treated_users %>% group_by(group_1) %>% summarise(n = n())
treated_users %>% group_by(group_3) %>% summarise(n = n())

# Characteristics of the groups:
treated_users$male <- ifelse(treated_users$gender == "Male", 1, 0)
treated_users$high_school <- ifelse(treated_users$education_level == "High School", 1, 0)
treated_users$bachelor <- ifelse(treated_users$education_level == "Bachelor's", 1, 0)
treated_users$master <- ifelse(treated_users$education_level == "Master's", 1, 0)
treated_users$phd <- ifelse(treated_users$education_level == "PhD", 1, 0)
treated_users$years_of_exp <- as.numeric(treated_users$years_of_exp)
treated_users$age <- as.numeric(treated_users$age)
treated_users$resume_score <- as.numeric(treated_users$resume_score)
treated_users$group <- ifelse(treated_users$group_1 == 1, "Benefits from AI", ifelse(treated_users$group_3 == 1, "Harmed by AI", "Neither"))

treated_users <- treated_users %>% select(group, male, high_school, bachelor, master, phd, years_of_exp, age, resume_score) %>% na.omit()

# Means and standard deviations of characteristics by group:
summary_table <- treated_users %>% group_by(group) %>% summarise(mean_male = mean(male), sd_male = sd(male)/sqrt(n()),
                                              mean_high_school = mean(high_school), sd_high_school = sd(high_school)/sqrt(n()),
                                              mean_bachelor = mean(bachelor), sd_bachelor = sd(bachelor)/sqrt(n()),
                                              mean_master = mean(master), sd_master = sd(master)/sqrt(n()),
                                              mean_phd = mean(phd), sd_phd = sd(phd)/sqrt(n()),
                                              mean_years_of_exp = mean(years_of_exp), sd_years_of_exp = sd(years_of_exp)/sqrt(n()),
                                              mean_age = mean(age), sd_age = sd(age)/sqrt(n()),
                                              mean_resume_score = mean(resume_score), sd_resume_score = sd(resume_score)/sqrt(n()))

summary_table <- t(summary_table)

# Calculate the difference between AI and resume score percentiles
treated_users$percentile_diff <- treated_users$AI_score_percentile - treated_users$resume_score_percentile

# Create 10 buckets based on percentile difference
treated_users$diff_bucket <- cut(treated_users$percentile_diff, 
                                breaks = seq(-1, 1, by = 0.2),
                                labels = paste(seq(-0.9, 0.9, by = 0.2), "to", seq(-0.7, 1.1, by = 0.2)))

# Calculate means and standard errors by bucket for each characteristic
variables <- c("male", "high_school", "bachelor", "master", "phd", 
               "years_of_exp", "age", "resume_score")

bucket_stats <- treated_users %>%
  group_by(diff_bucket) %>%
  summarise(
    n = n(),
    across(all_of(variables), 
           list(mean = ~mean(., na.rm = TRUE),
                se = ~sd(., na.rm = TRUE)/sqrt(sum(!is.na(.)))),
           .names = "{.col}_{.fn}")
  ) %>%
  filter(!is.na(diff_bucket)) %>%
  arrange(diff_bucket)

# Function to create plot for each characteristic
create_bucket_plot <- function(var_name, title) {
  ggplot(bucket_stats, aes(x = diff_bucket, y = get(paste0(var_name, "_mean")))) +
    geom_bar(stat = "identity", fill = "skyblue", alpha = 0.7) +
    geom_errorbar(aes(ymin = get(paste0(var_name, "_mean")) - get(paste0(var_name, "_se")),
                      ymax = get(paste0(var_name, "_mean")) + get(paste0(var_name, "_se"))),
                  width = 0.3) +
    labs(title = title,
         subtitle = "By AI vs Human Score Percentile Difference",
         x = "Percentile Difference Bucket (AI - Human)",
         y = "Mean Value") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1),
          plot.title = element_text(face = "bold"),
          plot.subtitle = element_text(size = 9)) +
    geom_text(aes(label = paste0("n=", n), y = 0), vjust = -0.5, size = 3)
}

# Create all plots and arrange them in a grid
plot_titles <- c("Gender (Male)", "High School", "Bachelor's Degree", 
                "Master's Degree", "PhD", "Years of Experience", 
                "Age", "Resume Score")

plots <- mapply(create_bucket_plot, variables, plot_titles, SIMPLIFY = FALSE)

# Combine plots in a grid arrangement
library(gridExtra)
combined_plot <- grid.arrange(grobs = plots, ncol = 2)

# Save the combined plot
ggsave("ai_human_diff_characteristics.png", combined_plot, width = 14, height = 20)


# The same but three groups:
treated_users$diff_bucket_3 <- cut(treated_users$percentile_diff, 
                                breaks = seq(-1, 1, by = 0.33),
                                labels = paste(seq(-0.99, 0.99, by = 0.33), "to", seq(-0.66, 1.32, by = 0.33)))

# Calculate means and standard errors by bucket for each characteristic

bucket_stats_3 <- treated_users %>%
  group_by(diff_bucket_3) %>%
  summarise(
    n = n(),
    across(all_of(variables), 
           list(mean = ~mean(., na.rm = TRUE),
                se = ~sd(., na.rm = TRUE)/sqrt(sum(!is.na(.)))),
           .names = "{.col}_{.fn}")
  ) %>%
  filter(!is.na(diff_bucket_3)) %>%
  arrange(diff_bucket_3)

# Create all plots and arrange them in a grid
plot_titles_3 <- c("Gender (Male)", "High School", "Bachelor's Degree", 
                "Master's Degree", "PhD", "Years of Experience", 
                "Age", "Resume Score")

plots_3 <- mapply(create_bucket_plot, variables, plot_titles_3, SIMPLIFY = FALSE)


