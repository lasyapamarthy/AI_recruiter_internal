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

final_interview <- final_interview %>% select(email_id, Result)
final_interview$outcome <- ifelse(final_interview$Result == "Pass", 1, ifelse(final_interview$Result == "Fail", 0, NA))

final_interview <- final_interview %>% select(email_id, outcome) %>% na.omit()

# Do we have any duplicates?
final_interview %>% group_by(email_id) %>% summarise(n = n()) %>% filter(n > 1)

# Filter out duplicates:
final_interview <- final_interview %>% group_by(email_id) %>% slice_head(n = 1) %>% ungroup()
final_interview <- final_interview %>% left_join(merged_data, by = "email_id")

final_interview$resume_score <- as.numeric(final_interview$resume_score)


ate_ols <- lm(outcome ~ treatment, data = final_interview)
ate_ols_cov <- lm(outcome ~ treatment + years_of_exp + age+ education_level + gender + resume_score, data = final_interview)

stargazer(ate_ols, ate_ols_cov, type = "text")

# Prepare dataset for grf:
final_interview_grf <- final_interview %>% select(outcome, treatment, years_of_exp, age, education_level, gender, resume_score)

# Change covariate to numeric:
final_interview_grf$years_of_exp <- as.numeric(final_interview_grf$years_of_exp)
final_interview_grf$age <- as.numeric(final_interview_grf$age)
final_interview_grf$resume_score <- as.numeric(final_interview_grf$resume_score)
final_interview_grf$high_school <- ifelse(final_interview_grf$education_level == "High School", 1, 0)
final_interview_grf$bachelor <- ifelse(final_interview_grf$education_level == "Bachelor's", 1, 0)
final_interview_grf$master <- ifelse(final_interview_grf$education_level == "Master's", 1, 0)
final_interview_grf$phd <- ifelse(final_interview_grf$education_level == "PhD", 1, 0)

# Drop education_level column
final_interview_grf <- final_interview_grf %>% select(-education_level)

final_interview_grf$male <- ifelse(final_interview_grf$gender == "Male", 1, 0)

final_interview_grf <- final_interview_grf %>% na.omit()

X <- final_interview_grf %>% select(years_of_exp, age, high_school, bachelor, master, phd, male, resume_score) %>% as.matrix()
Y <- final_interview_grf %>% select(outcome) %>% as.matrix()
W <- final_interview_grf %>% select(treatment) %>% as.matrix()

# Tau forest
tau_forest <- causal_forest(X, Y, W, num.trees = 1000)

# Average treatment effect:
ate_grf <- average_treatment_effect(tau_forest, target.sample = "treated")

# Combine ATE estimates from all different methods:
ate_estimates <- data.frame(
  Method = c("Difference in Means", "OLS with covariates", "GRF"),
  Estimate = c(coef(ate_ols)[2], coef(ate_ols_cov)[2], ate_grf[1]),
  SE = c(summary(ate_ols)$coefficients[2, 2], summary(ate_ols_cov)$coefficients[2, 2], ate_grf[2])
)

# Print the table in markdown format
cat(knitr::kable(ate_estimates, format = "markdown"))

############### Are people non-randomly dropping out? ###############

treated_users <- merged_data %>% filter(treatment == 1)
treated_users$dropped_out <- ifelse(is.na(treated_users$is_completed), 1, 0)
treated_users$resume_score <- as.numeric(treated_users$resume_score)
treated_users$male <- ifelse(treated_users$gender == "Male", 1, 0)
treated_users$high_school <- ifelse(treated_users$education_level == "High School", 1, 0)
treated_users$bachelor <- ifelse(treated_users$education_level == "Bachelor's", 1, 0)
treated_users$master <- ifelse(treated_users$education_level == "Master's", 1, 0)
treated_users$phd <- ifelse(treated_users$education_level == "PhD", 1, 0)

summary(treated_users$dropped_out)
ols_dropped_out <- lm(dropped_out ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = treated_users)

# Same with logit
logit_dropped_out <- glm(dropped_out ~ years_of_exp + age + high_school + bachelor + master  + male + resume_score, data = treated_users, family = "binomial")

stargazer(ols_dropped_out, logit_dropped_out, type = "text")

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



#################### Who benefits from the AI vetting? ####################

treated_users <- merged_data %>% filter(treatment == 1)
treated_users$AI_score <- ifelse(treated_users$React == "Senior", 3, ifelse(treated_users$React == "Mid-level", 2, ifelse(treated_users$React == "Junior", 1, 0))) + 
  ifelse(treated_users$JavaScript == "Senior", 3, ifelse(treated_users$JavaScript == "Mid-level", 2, ifelse(treated_users$JavaScript == "Junior", 1, 0))) + 
  ifelse(treated_users$CSS == "Senior", 3, ifelse(treated_users$CSS == "Mid-level", 2, ifelse(treated_users$CSS == "Junior", 1, 0)))

treated_users$AI_score <- as.numeric(treated_users$AI_score)
treated_users$AI_score <- ifelse(is.na(treated_users$AI_score), 0, treated_users$AI_score)

# Percentilles of AI and resume score:
treated_users$AI_score_percentile <- ecdf(treated_users$AI_score)(treated_users$AI_score)
treated_users$resume_score <- as.numeric(treated_users$resume_score)
treated_users$resume_score <- ifelse(is.na(treated_users$resume_score), 0, treated_users$resume_score)
treated_users$resume_score_percentile <- ecdf(treated_users$resume_score)(treated_users$resume_score)

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
