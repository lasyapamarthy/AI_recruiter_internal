library(dplyr)
library(ggplot2)
library(oaxaca)

# Load second stage dataset:
final_interview <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/top_candidates_interviewed.csv")

# Load and match resume scores:
resume_scores_manual <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Manual-Resume-ranked.csv")
resume_scores_ai <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/AI-Vetted-ranked.csv")

resume_scores_manual <- resume_scores_manual %>% select(email_id, resume_score)
resume_scores_ai <- resume_scores_ai %>% select(email_id, resume_score)

resume_scores <- rbind(resume_scores_manual, resume_scores_ai)
resume_scores <- resume_scores %>% group_by(email_id) %>% slice_head(n = 1) %>% ungroup()


# Without matching to the main file; as i'm dropping to many candiates

final_est <- final_interview %>% select(Interview.Type, interviewer, Result, Gender, Age..Years., Country, email_id)
final_est <- final_est %>% left_join(resume_scores, by = "email_id")


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

# Oaxaca-Blinder decomposition:
# finalists or all applicants, depending on Option A / B

# linear probability model (binary outcome coded 0/1)
# The oaxaca formula requires a specific format with the group indicator after |
# Convert age to numeric factors before decomposition
# The error occurs because 'age' is a character variable that can't be used in matrix multiplication
final_est$age_factor <- as.factor(final_est$age)

# Run Oaxaca-Blinder decomposition with properly formatted variables
# Convert age_factor to dummy variables to avoid non-conformable arguments error
# Create dummy variables for each age category
final_est$age_18_22 <- ifelse(final_est$age == "18-22", 1, 0)
final_est$age_23_27 <- ifelse(final_est$age == "23-27", 1, 0)
final_est$age_28_32 <- ifelse(final_est$age == "28-32", 1, 0)
final_est$age_33_plus <- ifelse(final_est$age == "33+", 1, 0)
final_est$age_not_shared <- ifelse(final_est$age == "Not shared" | final_est$age == "", 1, 0)

# Run Oaxaca-Blinder decomposition with dummy variables instead of factors
# Handle missing values in resume_score before decomposition
final_est$resume_score <- as.numeric(final_est$resume_score)
final_est <- final_est %>% filter(!is.na(resume_score))

# Ensure all variables are properly formatted
final_est$age_18_22 <- as.numeric(final_est$age_18_22)
final_est$age_23_27 <- as.numeric(final_est$age_23_27)
final_est$age_28_32 <- as.numeric(final_est$age_28_32)
final_est$age_33_plus <- as.numeric(final_est$age_33_plus)
final_est$age_not_shared <- as.numeric(final_est$age_not_shared)
final_est$male <- as.numeric(final_est$male)
final_est$treatment <- as.numeric(final_est$treatment)

# Run Oaxaca-Blinder decomposition with proper data formatting
decomp <- oaxaca(outcome ~ age_23_27 + age_28_32  + 
                   male + resume_score | treatment,
                 data = final_est,
                 R = 100)               # reduced bootstrap iterations for stability

summary(decomp)

plot(decomp)  


x_sum <- summary(decomp)

# helper: pick the variables list whose first column is the desired weight
pick_weight <- function(twofold, w = 1) {
  which_weight <- which(
    vapply(twofold$variables,
           function(x) unique(x[ , "group.weight"]), numeric(1)) == w
  )
  twofold$variables[[which_weight]]
}

# choose group.weight = 1 (Oaxaca–Ransom)
tbl_raw <- pick_weight(x_sum$twofold, w = 1)

# reshape and clean
tbl_tidy <- tbl_raw %>%
  as.data.frame() %>%
  rownames_to_column("variable") %>%
  select(variable,
         explained      = `coef(explained)`,
         se_exp         = `se(explained)`,
         unexplained    = `coef(unexplained)`,
         se_unexp       = `se(unexplained)`) %>%
  mutate(across(where(is.numeric), round, 3))

# ------------------------------------------------------------
# 3.  Display
# ------------------------------------------------------------
tbl_tidy %>%
  kable(caption = "Blinder–Oaxaca decomposition (two-fold, weight = 1)",
        align = "lrrrr") %>%
  kable_styling(full_width = FALSE, position = "center")
# Save the plot

