library(dplyr)

# Load raw data
raw_data <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/data/math_phd_v1.csv")
raw_data <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/data/math_phd2.csv")


# Select data for the randomization:
data_random <- raw_data %>% select( Email.ID, Job.Application.Date,Resume.URL, About.Candidate,Linkedin.URL,Current.Application.Stage,Resume.Score,AI.Match.Score,Soft.Skills.Result,Human.Data.Exercise.Result, Coding.Round.Result, Proctoring.Score,Candidate.Profile.URL,Certified.Talent.Profile.Link, Skill..introduction, Skill..Calculus...Differentiation, Skill..Probability...Statistics,Skill..Applied.Problem.Solving)

# How many candidates are in the data and how many are AI vetted?
summary(as.factor(data_random$Current.Application.Stage))
## We have 143 AI Vetted Candidates and 435 non-AI vetted candidates.

# Select only those that passed the AI vetting:
data_random_passed <- data_random %>% filter(Current.Application.Stage == "AI Vetted")

# Define Stratification:
cols <- c(
  "Skill..introduction",
  "Skill..Calculus...Differentiation",
  "Skill..Probability...Statistics",
  "Skill..Applied.Problem.Solving"
)

# TRUE where value is Senior or Mid-level
mat <- sapply(cols, function(nm) data_random_passed[[nm]] %in% c("Senior", "Mid-level"))

# count how many are TRUE per row (ignore NAs)
data_random_passed$no_experienced_sum <- rowSums(mat, na.rm = TRUE)

# label stratum
data_random_passed$stratum <- ifelse(
  data_random_passed$no_experienced_sum > 0, "Experienced", "No Experienced"
)


data_random_passed$stratum <- ifelse(data_random_passed$no_experienced_sum == 0,1, ifelse(data_random_passed$no_experienced_sum == 1, 2, 3))

# Assign treatment within each stratum:
data_random_passed <- data_random_passed %>% group_by(stratum) %>% mutate(treatment = ifelse(row_number() <= n()/2, 1, 0)) %>% ungroup()

# Sanity checks:
summary(data_random_passed$treatment)
data_random_passed %>% group_by(stratum) %>% summarise(mean(treatment))

# Control group:
control_group <- data_random_passed %>% filter(treatment == 0) %>% select(Email.ID, Resume.URL, About.Candidate,Linkedin.URL,Resume.Score)
dim(control_group)
# Treatment group:
treatment_group <- data_random_passed %>% filter(treatment == 1) %>% select(-stratum, -treatment, -no_experienced_sum, -Job.Application.Date)
dim(treatment_group)
# Save the data:
write.csv(data_random_passed, "/Users/emilpalikot/Research/AI-Recruiter/data/math_phd_v2_randomized.csv", row.names = FALSE)
write.csv(control_group, "/Users/emilpalikot/Research/AI-Recruiter/data/math_phd_v2_control_group.csv", row.names = FALSE)
write.csv(treatment_group, "/Users/emilpalikot/Research/AI-Recruiter/data/math_phd_v2_treatment_group.csv", row.names = FALSE)
