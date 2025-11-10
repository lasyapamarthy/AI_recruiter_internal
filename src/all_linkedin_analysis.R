remove(list = ls())

library(dplyr)
library(ggplot2)
library(stringr)
library(survival)
library(riskRegression)
library(data.table)
root <- "/Users/emilpalikot/Research/AI-Recruiter"

# Merge and save the collected files:
clean_handle <- function(url) {
  url %>% 
    str_remove("^https?://[^/]+/") %>%   # drop the scheme + domain
    str_replace("^in/", "") %>%          # drop the 'in/' path segment if present
    str_remove("/$") %>%                 # drop trailing slash
    str_remove("\\?.*$") %>%                # drop any query string
    str_remove("/en")
}


#########################################################
# Load and prepare all data
#########################################################

# 1. Experimental datasets
# Load treatment and control data
treat <- read.csv(file.path(root, "experiments/resume_vetting/Ai-Vetted-ranked.csv")) %>%
  distinct(email_id, .keep_all = TRUE) %>%
  select( job_application_id,resume_score,is_passed, is_completed, ai_vetting_results) %>%
  mutate(treatment = 1)

control <- read.csv(file.path(root, "experiments/resume_vetting/Manual-Resume-ranked.csv")) %>%
  distinct(email_id, .keep_all = TRUE)  %>%
  select(job_application_id,resume_score) %>%
  mutate(is_passed = NA, is_completed = NA, ai_vetting_results = NA, treatment = 0)

# Combine treatment and control
experimental_data <- rbind(treat, control) 

# Do we have any duplicates?
print(paste("Number of duplicates:", length(experimental_data$job_application_id) - length(unique(experimental_data$job_application_id))))

# Load and prepare LinkedIn URLs
treat_linkedin <- read.csv(file.path(root, "data/treatment_linkedin_urls.csv")) %>%
  select(job_application_id, linkedin_url)
control_linkedin <- read.csv(file.path(root, "data/control_linkedin_urls.csv")) %>%
  select(job_application_id, linkedin_url)

# Combine and standardize LinkedIn URLs
matched_linkedin <- rbind(treat_linkedin, control_linkedin) %>%
  mutate(linkedin_url = sapply(linkedin_url, clean_handle))


# Do we have any duplicates?
print(paste("Number of duplicates:", length(matched_linkedin$job_application_id) - length(unique(matched_linkedin$job_application_id))))

# Merge treatment assignment with LinkedIn URLs
matched_data <- merge(experimental_data, matched_linkedin, by = "job_application_id", all.x = TRUE)
colnames(matched_data)[ncol(matched_data)] <- "handle"

# Have all observations been matched?
print(paste("Number of observations:", length(experimental_data$job_application_id)))
print(paste("Number of unique LinkedIn URLs:", length(unique(matched_data$job_application_id))))


# The number of control group observations with top resume score:
matched_data %>% filter(treatment == 0) %>% filter(resume_score == 98.75) %>% summarise(n())

# 2. LinkedIn Collected profiles

# Load the unified file
unified <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/linkedin_profiles_htmls_combined_64.csv") %>% select(linkedin_url, start_date,job_title) %>% mutate(data_collected = 1)
unified <- unified %>% distinct(linkedin_url, .keep_all = TRUE) %>% mutate(start_date = ifelse(start_date == "", NA, start_date))

collected_4 <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/linkedin_profiles_htmls_4.csv") %>% select(linkedin_url, start_date,job_title) %>% mutate(data_collected = 1)
collected_4 <- collected_4 %>% distinct(linkedin_url, .keep_all = TRUE) %>% mutate(start_date = ifelse(start_date == "", NA, start_date))

collected <- rbind(unified, collected_4)

collected_5 <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/linkedin_profiles_htmls_5.csv") %>% select(linkedin_url, start_date,job_title) %>% mutate(data_collected = 1)
collected_5 <- collected_5 %>% distinct(linkedin_url, .keep_all = TRUE) %>% mutate(start_date = ifelse(start_date == "", NA, start_date))

collected <- rbind(collected, collected_5)


collected_6 <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/linkedin_profiles_htmls_6.csv") %>% select(linkedin_url, start_date,job_title) %>% mutate(data_collected = 1)
collected_6 <- collected_6 %>% distinct(linkedin_url, .keep_all = TRUE) %>% mutate(start_date = ifelse(start_date == "", NA, start_date))

collected <- rbind(collected, collected_6)


# Do we have duplicated LinkedIn URLs?
collected %>% group_by(linkedin_url) %>% summarise(n()) %>% filter(`n()` > 1)
# If duplicated LinkedIn URLs, keep the first one:
collected <- collected %>% distinct(linkedin_url, .keep_all = TRUE)

# Remove freelancers etc.
collected$job_title <- tolower(collected$job_title)

free_lancer <- keywords <- c(
  "freelancer",
  "free-lancer",
  "freelance",
  "independent contractor",
  "contractor",
  "independent consultant",
  "consultant",
  "consultancy",
  "self-employed",
  "self employed",
  "sole proprietor",
  "sole trader",
  "gig worker",
  "gig-worker",
  "owner-operator",
  "business owner",
  "founder",
  "co-founder",
  "entrepreneur",
  "solopreneur",
  "solo-preneur",
  "independent professional",
  "independent",
  "portfolio career",
  "side hustler",
  "1099",
  "independent researcher",
  "freelance writer",
  "freelance developer",
  "freelance designer"
)

collected <- collected %>%
  mutate(start_date = ifelse(job_title %in% free_lancer, NA, start_date)) %>%
  select(-job_title)

# How many profiles have been collected?
collected %>% summarise(n())
collected$handle <- clean_handle(collected$linkedin_url)

# Save collected data:
write.csv(collected, file.path(root, "data/collected_linkedin_profiles_62.csv"), row.names = FALSE)

# 3. Merge collected and experimental data

# Share of handles that match:
length(intersect(collected$handle, matched_data$handle)) / length(collected$handle)


# Print duplicated handles:
collected %>% group_by(handle) %>% summarise(n()) %>% filter(`n()` > 1)
matched_data %>% group_by(handle) %>% summarise(n()) %>% filter(`n()` > 1)

# Keep only the first duplicate:
collected <- collected %>% distinct(handle, .keep_all = TRUE)
matched_data <- matched_data %>% distinct(handle, .keep_all = TRUE)

# Are handles unique in both files?
print(paste("Are handles unique in collected?", length(unique(collected$handle)) == length(collected$handle)))
print(paste("Are handles unique in matched_data?", length(unique(matched_data$handle)) == length(matched_data$handle)))

merged_data <- matched_data %>% left_join(collected, by = "handle") %>% filter(data_collected == 1)

print(paste("Number of collected profiles:", length(collected$handle)))

# Profiles per treatment: 
merged_data %>% filter(treatment == 1) %>% summarise(n())
merged_data %>% filter(treatment == 0) %>% summarise(n())

# 4. New Job outcome
merged_data$new_job  <- ifelse(
  merged_data$start_date %in% c(
    "2025-01","2025-02","2025-03","2025-04","2025-05",
    "Jan 2025","Feb 2025","Mar 2025","Apr 2025","May 2025",
    "Jan-2025","Feb-2025","Mar-2025","Apr-2025","May-2025"
  ),
  1, 0)

merged_data$new_job <- ifelse(merged_data$start_date == "", 0, merged_data$new_job)
merged_data$new_job <- ifelse(is.na(merged_data$new_job), 0, merged_data$new_job)

print(paste("Number of new jobs:", sum(merged_data$new_job)))
print(paste("Share of profiles with new job:", round(sum(merged_data$new_job) / length(merged_data$new_job)*100, 2), "%"))

merged_data$jan_2025 <- ifelse(merged_data$start_date %in% c("2025-01","Jan 2025"), 1, 0)
merged_data$feb_2025 <- ifelse(merged_data$start_date %in% c("2025-02","Feb 2025"), 1, 0)
merged_data$mar_2025 <- ifelse(merged_data$start_date %in% c("2025-03","Mar 2025"), 1, 0)
merged_data$apr_2025 <- ifelse(merged_data$start_date %in% c("2025-04","Apr 2025"), 1, 0)
merged_data$may_2025 <- ifelse(merged_data$start_date %in% c("2025-05","May 2025"), 1, 0)

merged_data %>% summarise( 
  m_january = mean(jan_2025),
  m_february = mean(feb_2025),
  m_march = mean(mar_2025),
  m_april = mean(apr_2025),
  m_may = mean(may_2025)
)

# 5. Create labels
## Passed and not passed AI interview:
merged_data$AI_passed <- ifelse(merged_data$is_passed == "TRUE" , 1, 0)
merged_data$AI_passed <- ifelse(is.na(merged_data$AI_passed), 0, merged_data$AI_passed)
merged_data$AI_did_not_pass <- ifelse(merged_data$is_passed == "FALSE" & merged_data$is_completed == 1, 1, 0)
merged_data$AI_did_not_pass <- ifelse(is.na(merged_data$AI_did_not_pass), 0, merged_data$AI_did_not_pass)
merged_data$AI_not_completed <- ifelse(merged_data$is_completed != 1 & merged_data$treatment == 1, 1, 0)
merged_data$AI_not_completed <- ifelse(is.na(merged_data$AI_not_completed), 0, merged_data$AI_not_completed)

## Manual choice:
n_AI_passed <- merged_data %>% filter(AI_passed == 1) %>% summarise(n()) %>% as.numeric()
merged_data$resume_score <- as.numeric(merged_data$resume_score)
### Resume score for all top candidates is the same 98.75, and that's more than the number of observatiosn in the AI group. Thus selecting all top RS with resume score 98.75; it's 4 extra observations.
quantile(merged_data$resume_score[merged_data$treatment == 0], probs = 0.6)

top_RS <- merged_data %>% filter(treatment == 0) %>% arrange(desc(resume_score)) %>% filter(resume_score == 98.75)
merged_data$manual_choice <- ifelse(merged_data$job_application_id %in% top_RS$job_application_id, 1, 0)

## Alternative RS:
alt_rs <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/data/Resume_scoring_comparison.csv")
alt_rs <- alt_rs %>% select(resume_score, job_application_id) %>% arrange(desc(resume_score)) %>% slice(1:n_AI_passed) %>% select(job_application_id) 
treat <- read.csv(file.path(root, "experiments/resume_vetting/Ai-Vetted-ranked.csv")) %>%
  distinct(email_id, .keep_all = TRUE) %>%
  select(resume_score, job_application_id)
alt_rs <- treat %>% filter(job_application_id %in% alt_rs$job_application_id)

merged_data$top_RS_alt <- ifelse(merged_data$job_application_id %in% alt_rs$job_application_id, 1, 0)

# How many profiles in each group?
merged_data %>% filter(AI_passed == 1) %>% summarise(n())
merged_data %>% filter(AI_did_not_pass == 1) %>% summarise(n())
merged_data %>% filter(AI_not_completed == 1) %>% summarise(n())
merged_data %>% filter(manual_choice == 1) %>% summarise(n())
merged_data %>% filter(top_RS_alt == 1) %>% summarise(n())
merged_data %>% filter(manual_choice == 0 & top_RS_alt == 0 & treatment == 0) %>% summarise(n())

# 6. Compute AI score

merged_data <- merged_data %>%
  mutate(
    React      = str_remove(str_extract(ai_vetting_results,
                              "React\\s*:\\s*\\w+"),      "React\\s*:\\s*"),
    JavaScript = str_remove(str_extract(ai_vetting_results,
                              "JavaScript\\s*:\\s*\\w+"), "JavaScript\\s*:\\s*"),
    CSS        = str_remove(str_extract(ai_vetting_results,
                              "HTML,\\s*CSS\\s*:\\s*\\w+"),"HTML,\\s*CSS\\s*:\\s*")
  ) 
  
merged_data <- merged_data %>%
  mutate(AI_score = rowSums(across(c(React,JavaScript,CSS), ~case_when(
                  . %in% "Senior"    ~ 3,
                  . %in% "Mid-level" ~ 2,
                  . %in% "Junior"    ~ 1,
                  TRUE               ~ 0)), na.rm = TRUE))

merged_data$AI_score <- ifelse(is.na(merged_data$AI_score), 0, merged_data$AI_score)
merged_data$AI_score <- ifelse(merged_data$is_completed == 1, merged_data$AI_score, NA)

# Data for the table with summary statistics:

mean_treatment <- merged_data %>% filter(treatment == 1) %>% summarise(mean(new_job, na.rm = TRUE))
mean_control <- merged_data %>% filter(treatment == 0) %>% summarise(mean(new_job, na.rm = TRUE))

sd_treatment <- merged_data %>% filter(treatment == 1) %>% summarise(sd(new_job, na.rm = TRUE))
sd_control <- merged_data %>% filter(treatment == 0) %>% summarise(sd(new_job, na.rm = TRUE))

n_treatment <- merged_data %>% filter(treatment == 1) %>% summarise(n())
n_control <- merged_data %>% filter(treatment == 0) %>% summarise(n())

# Print the table:
print(paste("Mean new job for treatment:", mean_treatment))
print(paste("Mean new job for control:", mean_control))
print(paste("SD new job for treatment:", sd_treatment))
print(paste("SD new job for control:", sd_control))
print(paste("N treatment:", n_treatment))
print(paste("N control:", n_control))


######################################################
# Second stage data
######################################################
data_raw <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/data/linkedin_jobs_emil.csv")

data_raw$new_job <- ifelse(
  data_raw$start_new_job %in% c(
    "2025-01","2025-02","2025-03","2025-04","2025-05",
    "Jan 2025","Feb 2025","Mar 2025","Apr 2025","May 2025",
    "Jan-2025","Feb-2025","Mar-2025","Apr-2025","May-2025",
    "25-Jan","25-Feb","25-Mar","25-Apr","25-May"
  ),
  1, 0)

data_raw$new_job <- ifelse(data_raw$start_new_job == "", 0, data_raw$new_job)
data_raw$new_job <- ifelse(is.na(data_raw$new_job), 0, data_raw$new_job)

data_raw$treated = ifelse(data_raw$Interview.Type == "AI + Human Interview", 1, 0)

data_raw$jan_2025 <- ifelse(data_raw$start_new_job %in% c("2025-01","Jan 2025","25-Jan"), 1, 0)
data_raw$feb_2025 <- ifelse(data_raw$start_new_job %in% c("2025-02","Feb 2025","25-Feb"), 1, 0)
data_raw$mar_2025 <- ifelse(data_raw$start_new_job %in% c("2025-03","Mar 2025","25-Mar"), 1, 0)
data_raw$apr_2025 <- ifelse(data_raw$start_new_job %in% c("2025-04","Apr 2025","25-Apr"), 1, 0)
data_raw$may_2025 <- ifelse(data_raw$start_new_job %in% c("2025-05","May 2025","25-May"), 1, 0)

data_for_matching <- data_raw %>% mutate(
  job_application_id = NA,
  resume_score = NA,
  is_passed = NA,
  is_completed = NA,
  ai_vetting_results = NA,
  treatment = treated,
  handle = clean_handle(Linkedin),
  linkedin_url = Linkedin,
  start_date = start_new_job,
  data_collected = 1,
  new_job = new_job,
  jan_2025 = jan_2025,
  feb_2025 = feb_2025,
  mar_2025 = mar_2025,
  apr_2025 = apr_2025,
  may_2025 = may_2025,
  AI_passed = NA,
  AI_did_not_pass = NA,
  AI_not_completed = NA,
  manual_choice = NA,
  top_RS_alt = NA,
  AI_score = NA,
  second_stage = 1
) %>% select( job_application_id, resume_score, is_passed, is_completed, ai_vetting_results, treatment, handle, linkedin_url, start_date, data_collected, new_job, jan_2025, feb_2025, mar_2025, apr_2025, may_2025, AI_passed, AI_did_not_pass, AI_not_completed, manual_choice, top_RS_alt, AI_score, second_stage)

#########################################################
# Analysis
#########################################################


merged_data$second_stage <- ifelse(merged_data$handle %in% data_for_matching$handle, 1, 0)
merged_data <- merged_data %>% select(- React, - JavaScript, - CSS)
merged_data <- merged_data %>% rbind(data_for_matching)


# 1. Mean outcomes:
mean_outcome <- c(
  mean(merged_data$new_job[merged_data$AI_passed == 1], na.rm = TRUE),
  mean(merged_data$new_job[merged_data$AI_did_not_pass == 1], na.rm = TRUE),
  mean(merged_data$new_job[merged_data$AI_not_completed == 1], na.rm = TRUE),
  mean(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE),
  mean(merged_data$new_job[merged_data$top_RS_alt == 1], na.rm = TRUE),
  mean(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 1], na.rm = TRUE),
  mean(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0], na.rm = TRUE)
)

se_outcome <- c(
  sd(merged_data$new_job[merged_data$AI_passed == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$AI_passed == 1])),
  sd(merged_data$new_job[merged_data$AI_did_not_pass == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$AI_did_not_pass == 1])),
  sd(merged_data$new_job[merged_data$AI_not_completed == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$AI_not_completed == 1])),
  sd(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$manual_choice == 1])),
  sd(merged_data$new_job[merged_data$top_RS_alt == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$top_RS_alt == 1])),
  sd(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 1])),
  sd(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0]))
)

labels <- c("AI Passed", "AI Did Not Pass", "AI Not Completed", "Manual Choice", "Alternative RS", "AI Selected", "Manual Selected")

# Put together in a table:
outcome_table <- data.frame(
  labels,
  mean_outcome,
  se_outcome
)

# Print table:
print(outcome_table)



######################################### Plot Treatment vs Control #########################################
# Create cumulative monthly indicators
merged_data$jan = merged_data$jan_2025
merged_data$feb = ifelse(merged_data$feb_2025 == 1 | merged_data$jan_2025 == 1, 1, 0)
merged_data$mar = ifelse(merged_data$mar_2025 == 1 | merged_data$feb_2025 == 1 | merged_data$jan_2025 == 1, 1, 0)
merged_data$apr = ifelse(merged_data$apr_2025 == 1 | merged_data$mar_2025 == 1 | merged_data$feb_2025 == 1 | merged_data$jan_2025 == 1, 1, 0)
merged_data$may = ifelse(merged_data$may_2025 == 1 | merged_data$apr_2025 == 1 | merged_data$mar_2025 == 1 | merged_data$feb_2025 == 1 | merged_data$jan_2025 == 1, 1, 0)



# 1. Second stage : Treatment vs Control
monthly_rates_ai_manual <- data.frame(
  Month = rep(c("Jan", "Feb", "Mar", "Apr", "May"), 2),
  Treatment = c(rep("AI Selected Second Stage", 5), rep("Manual Selected Second Stage", 5))
)

ai_stats <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(second_stage == 1 & treatment == 1)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

manual_stats <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(second_stage == 1 & treatment == 0)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

monthly_rates_ai_manual$Rate <- c(
  sapply(ai_stats, function(x) x["rate"]),
  sapply(manual_stats, function(x) x["rate"])
)

monthly_rates_ai_manual$SE <- c(
  sapply(ai_stats, function(x) x["se"]),
  sapply(manual_stats, function(x) x["se"])
)


# Add December:
monthly_rates_ai_manual <- rbind(monthly_rates_ai_manual, data.frame(
  Month = "Dec",
  Treatment = c("AI Selected Second Stage", "Manual Selected Second Stage"),
  Rate = c(0, 0),
  SE = c(0, 0)
))
monthly_rates_ai_manual$Month <- factor(monthly_rates_ai_manual$Month, 
                                      levels = c("Dec", "Jan", "Feb", "Mar", "Apr", "May"))



plot_ai_vs_manual <- ggplot(monthly_rates_ai_manual, 
                           aes(x = Month, y = Rate, color = Treatment, group = Treatment)) +
  geom_line(size = 1.2) +
  geom_point(size = 3) +
  geom_ribbon(aes(ymin = Rate - SE, 
                  ymax = Rate + SE, 
                  fill = Treatment),
              alpha = 0.2,
              color = NA) +
  labs(
    x = "Month",
    y = "Cumulative Job Acquisition Rate",
    color = "Group",
    fill = "Group"
  ) +
  theme_classic() +
  scale_y_continuous(labels = scales::percent_format()) +
  scale_color_manual(values = c("AI Selected Second Stage" = "#2166ac", "Manual Selected Second Stage" = "#762a83")) +
  scale_fill_manual(values = c("AI Selected Second Stage" = "#2166ac", "Manual Selected Second Stage" = "#762a83")) +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 24, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 22),
    axis.text = element_text(size = 21),
    legend.position = "bottom",
    legend.title = element_text(size = 22),
    legend.text = element_text(size = 21),
    panel.grid.major = element_line(color = "grey90", size = 0.5),
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 0.5)
  )

print(plot_ai_vs_manual)
ggsave(plot_ai_vs_manual, 
       file = "/Users/emilpalikot/Research/AI-Recruiter/figures/cumulative_rates_plot_1.png", 
       width = 10, height = 8)



# 2. First stage : AI Passed vs Manual Choice
# Calculate monthly cumulative rates and standard errors for AI vs Manual
monthly_rates_ai_manual <- data.frame(
  Month = rep(c("Jan", "Feb", "Mar", "Apr", "May"), 2),
  Treatment = c(rep("Passed AI Interview", 5), rep("Top Resume Score", 5))
)

# Calculate rates and standard errors for AI passed group
ai_stats <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(AI_passed == 1)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

# Calculate rates and standard errors for manual choice group
manual_stats <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(manual_choice == 1)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

monthly_rates_ai_manual$Rate <- c(
  sapply(ai_stats, function(x) x["rate"]),
  sapply(manual_stats, function(x) x["rate"])
)

monthly_rates_ai_manual$SE <- c(
  sapply(ai_stats, function(x) x["se"]),
  sapply(manual_stats, function(x) x["se"])
)

# Convert Month to factor
monthly_rates_ai_manual$Month <- factor(monthly_rates_ai_manual$Month, 
                                      levels = c("Jan", "Feb", "Mar", "Apr", "May"))

# Add December:
monthly_rates_ai_manual <- rbind(monthly_rates_ai_manual, data.frame(
  Month = "Dec",
  Treatment = c("Passed AI Interview", "Top Resume Score"),
  Rate = c(0, 0),
  SE = c(0, 0)
))
monthly_rates_ai_manual$Month <- factor(monthly_rates_ai_manual$Month, 
                                      levels = c("Dec", "Jan", "Feb", "Mar", "Apr", "May"))

# Create first plot (AI vs Manual with SE)
plot_ai_vs_manual_first_stage <- ggplot(monthly_rates_ai_manual, 
                           aes(x = Month, y = Rate, color = Treatment, group = Treatment)) +
  geom_line(size = 1.2) +
  geom_point(size = 3) +
  geom_ribbon(aes(ymin = Rate - SE, 
                  ymax = Rate + SE, 
                  fill = Treatment),
              alpha = 0.2,
              color = NA) +
  labs(
    x = "Month",
    y = "Cumulative Job Acquisition Rate",
    color = "Group",
    fill = "Group"
  ) +
  theme_classic() +
  scale_y_continuous(labels = scales::percent_format()) +
  scale_color_manual(values = c("Passed AI Interview" = "#2166ac", "Top Resume Score" = "#762a83")) +
  scale_fill_manual(values = c("Passed AI Interview" = "#2166ac", "Top Resume Score" = "#762a83")) +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 24, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 22),
    axis.text = element_text(size = 21),
    legend.position = "bottom",
    legend.title = element_text(size = 22),
    legend.text = element_text(size = 21),
    panel.grid.major = element_line(color = "grey90", size = 0.5),
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 0.5)
  )


print(plot_ai_vs_manual_first_stage)
ggsave(plot_ai_vs_manual_first_stage, 
       file = "/Users/emilpalikot/Research/AI-Recruiter/figures/cumulative_rates_plot_2.png", 
       width = 10, height = 8)

t.test(merged_data$new_job[merged_data$AI_passed == 1], merged_data$new_job[merged_data$manual_choice == 1])

# Means and standard errors for AI passed and manual choice:
mean_ai_passed <- mean(merged_data$new_job[merged_data$AI_passed == 1], na.rm = TRUE)
se_ai_passed <- sd(merged_data$new_job[merged_data$AI_passed == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$AI_passed == 1]))

mean_manual_choice <- mean(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE)
se_manual_choice <- sd(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE) / sqrt(length(merged_data$new_job[merged_data$manual_choice == 1]))

delta <- mean_ai_passed - mean_manual_choice
se_delta <- sqrt(se_ai_passed^2 + se_manual_choice^2)




# 3. Manual selections - (i) Not selected from control, (ii) seleted with micro1, (iii) selected with alternative resume score, (iv) second stage control
monthly_rates_manual_control <- data.frame(
  Month = rep(c("Jan", "Feb", "Mar", "Apr", "May"), 4),
  Treatment = c(rep("Not Selected", 5), rep("Micro1", 5), rep("Alternative RS", 5), rep("Second Stage Control", 5))
)

# Calculate rates and standard errors for manual choice group
micro1_choice <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(manual_choice == 1)
  rate <- mean(data[[m]])
  c(rate = rate)
})

alternative_rs_choice <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(top_RS_alt == 1)
  rate <- mean(data[[m]])
  c(rate = rate)
})

second_stage_control <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(second_stage == 1 & treatment == 0)
  rate <- mean(data[[m]])
  c(rate = rate)
})

not_selected <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(treatment == 0) %>% filter(manual_choice == 0 & top_RS_alt == 0)
  rate <- mean(data[[m]])
  c(rate = rate)
})

monthly_rates_manual_control$Rate <- c(
  sapply(not_selected, function(x) x["rate"]),
  sapply(micro1_choice, function(x) x["rate"]),
  sapply(alternative_rs_choice, function(x) x["rate"]),
  sapply(second_stage_control, function(x) x["rate"])
)

monthly_rates_manual_control$Month <- factor(monthly_rates_manual_control$Month, 
                                      levels = c("Jan", "Feb", "Mar", "Apr", "May"))

### Generate plot
plot_manual_control <- ggplot(monthly_rates_manual_control, 
                             aes(x = Month, y = Rate, color = Treatment, group = Treatment)) +
  geom_line(size = 1.2) +
  geom_point(size = 3) +
  labs(
    title = "Cumulative Job Acquisition Rates: Manual Selection",
    x = "Month",
    y = "Cumulative Job Acquisition Rate",
    color = "Group"
  ) +
  theme_classic() +
  scale_y_continuous(labels = scales::percent_format()) +
  scale_color_manual(values = c("Not Selected" = "#2166ac", "Micro1" = "#762a83", "Alternative RS" = "#4d9221", "Second Stage Control" = "#b2182b")) +  
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 16),
    axis.text = element_text(size = 14),
    legend.position = "bottom",
    legend.title = element_text(size = 14),
    legend.text = element_text(size = 12),
    panel.grid.major = element_line(color = "grey90", size = 0.5),
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 0.5)
  )

print(plot_manual_control)
ggsave(plot_manual_control, 
       file = "/Users/emilpalikot/Research/AI-Recruiter/figures/cumulative_rates_plot_3.png", 
       width = 10, height = 8)

# 4. AI second stage, AI passed, AI did not pass, AI did not completed
monthly_rates_ai_second_stage <- data.frame(
  Month = rep(c("Dec", "Jan", "Feb", "Mar", "Apr", "May"), 4),
  Treatment = c(rep("AI Second Stage", 6), rep("AI Passed", 6), rep("AI Did Not Pass", 6), rep("AI Did Not Complete", 6))
)

AI_second_stage <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(second_stage == 1 & treatment == 1)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

AI_passed <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(AI_passed == 1)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

AI_did_not_pass <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(AI_did_not_pass == 1)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

AI_not_completed <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(AI_not_completed == 1)
  rate <- mean(data[[m]])
  se <- sqrt(rate * (1-rate) / nrow(data))
  c(rate = rate, se = se)
})

monthly_rates_ai_second_stage$Rate <- c(
  0, sapply(AI_second_stage, function(x) x["rate"]),
  0, sapply(AI_passed, function(x) x["rate"]),
  0, sapply(AI_did_not_pass, function(x) x["rate"]),
  0, sapply(AI_not_completed, function(x) x["rate"]))

monthly_rates_ai_second_stage$SE <- c(
  0, sapply(AI_second_stage, function(x) x["se"]),
  0, sapply(AI_passed, function(x) x["se"]),
  0, sapply(AI_did_not_pass, function(x) x["se"]),
  0, sapply(AI_not_completed, function(x) x["se"]))

monthly_rates_ai_second_stage$Month <- factor(monthly_rates_ai_second_stage$Month, 
                                      levels = c("Dec", "Jan", "Feb", "Mar", "Apr", "May"))

plot_ai_second_stage <- ggplot(monthly_rates_ai_second_stage,
  aes(x = Month, y = Rate, color = Treatment, group = Treatment, fill = Treatment)) +
  geom_line(size = 1.2) +
  geom_point(size = 3) +
  geom_ribbon(aes(ymin = Rate - SE, ymax = Rate + SE), alpha = 0.2, color = NA) +
  labs(
    x = "Month",
    y = "Cumulative Job Acquisition Rate",
    color = "Group",
    fill = "Group"
  ) +
  theme_classic() +
  scale_y_continuous(labels = scales::percent_format()) +
  scale_color_manual(values = c("AI Second Stage" = "#2166ac", "AI Passed" = "#762a83", "AI Did Not Pass" = "#4d9221", "AI Did Not Complete" = "#b2182b")) +
  scale_fill_manual(values = c("AI Second Stage" = "#2166ac", "AI Passed" = "#762a83", "AI Did Not Pass" = "#4d9221", "AI Did Not Complete" = "#b2182b")) +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 16),
    axis.text = element_text(size = 14),
    legend.position = "bottom",
    legend.title = element_text(size = 14),
    legend.text = element_text(size = 12),
    panel.grid.major = element_line(color = "grey90", size = 0.5),
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 0.5)
  )

print(plot_ai_second_stage)
ggsave(plot_ai_second_stage,  
       file = "/Users/emilpalikot/Research/AI-Recruiter/figures/cumulative_rates_plot_4.png", 
       width = 10, height = 8)


# 5. High and low AI score vs Manual choice

merged_data$AI_score_high <- ifelse(merged_data$AI_score >= median(merged_data$AI_score, na.rm = TRUE), 1, 0)
merged_data$AI_score_low <- ifelse(merged_data$AI_score < median(merged_data$AI_score, na.rm = TRUE), 1, 0)

merged_data$AI_score_high <- ifelse(is.na(merged_data$AI_score_high), 0, merged_data$AI_score_high)
merged_data$AI_score_low <- ifelse(is.na(merged_data$AI_score_low), 0, merged_data$AI_score_low)

merged_data$AI_score_high <- ifelse(merged_data$is_passed == 1, merged_data$AI_score_high, NA)
merged_data$AI_score_low <- ifelse(merged_data$is_passed == 1, merged_data$AI_score_low, NA)

monthly_rates_ai_score <- data.frame(
  Month = rep(c("Jan", "Feb", "Mar", "Apr", "May"), 3),
  Treatment = c(rep("AI Score High", 5), rep("AI Score Low", 5), rep("Manual Choice", 5))
)

AI_score_high <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(AI_score_high == 1)
  rate <- mean(data[[m]])
  c(rate = rate)
})

AI_score_low <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(AI_score_low == 1)
  rate <- mean(data[[m]])
  c(rate = rate)
})

manual_choice <- lapply(c("jan", "feb", "mar", "apr", "may"), function(m) {
  data <- merged_data %>% filter(manual_choice == 1)
  rate <- mean(data[[m]])
  c(rate = rate)
})

monthly_rates_ai_score$Rate <- c(
  sapply(AI_score_high, function(x) x["rate"]),
  sapply(AI_score_low, function(x) x["rate"]),
  sapply(manual_choice, function(x) x["rate"])
)

monthly_rates_ai_score$Month <- factor(monthly_rates_ai_score$Month, 
    levels = c("Jan", "Feb", "Mar", "Apr", "May"))

plot_ai_score <- ggplot(monthly_rates_ai_score, aes(x = Month, y = Rate, color = Treatment, group = Treatment)) +
  geom_line(size = 1.2) +
  geom_point(size = 3) +
  labs(
    title = "Cumulative Job Acquisition Rates: AI Score",
    x = "Month",
    y = "Cumulative Job Acquisition Rate",
    color = "Group"
  ) +
  theme_classic() +
  scale_y_continuous(labels = scales::percent_format()) +
  scale_color_manual(values = c("AI Score High" = "#2166ac", "AI Score Low" = "#762a83", "Manual Choice" = "#4d9221")) +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 16),
    axis.text = element_text(size = 14),
    legend.position = "bottom",
    legend.title = element_text(size = 14),
    legend.text = element_text(size = 12),
    panel.grid.major = element_line(color = "grey90", size = 0.5),
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 0.5)
  )

print(plot_ai_score)
ggsave(plot_ai_score,  
       file = "/Users/emilpalikot/Research/AI-Recruiter/figures/cumulative_rates_plot_5.png", 
       width = 10, height = 8)  





#########################################################
#### Table for the paper
#########################################################

## Differnece in means
delta_mean_1 <- mean(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 1], na.rm = TRUE) - mean(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0], na.rm = TRUE)
se_1 <- sqrt(var(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 1], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 1])) + var(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0])))
baseline_1 <- mean(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0], na.rm = TRUE)
se_baseline_1 <- sqrt(var(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0])))

delta_mean_2 <- mean(merged_data$new_job[merged_data$AI_passed == 1], na.rm = TRUE) - mean(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE)
se_2 <- sqrt(var(merged_data$new_job[merged_data$AI_passed == 1], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$AI_passed == 1])) + var(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$manual_choice == 1])))
baseline_2 <- mean(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE)
se_baseline_2 <- sqrt(var(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$manual_choice == 1])))

## Survival analysis

### Second stage
survival_data_second_stage <- merged_data %>% filter(second_stage == 1) %>%
  mutate(
    treated_factor = factor(ifelse(treatment == 1, 1, 0)), # Convert to factor
    # Time to event (in months from baseline)
    time = case_when(
      jan == 1 ~ 1,
      feb == 1 ~ 2,
      mar == 1 ~ 3,
      apr == 1 ~ 4,
      may == 1 ~ 5,
      TRUE ~ 6  # Censored at end of study period
    ),
    # Event indicator (1 = got new job, 0 = censored)
    event = as.numeric(jan == 1 | feb == 1 | mar == 1 | apr == 1 | may == 1) # Ensure numeric 0/1
  ) %>% 
  select(time, event, treated_factor) %>% 
  na.omit()

cox_model_AI <- coxph(Surv(time, event) ~ treated_factor, 
                      data = survival_data_second_stage,
                      x = TRUE,
                      y = TRUE)

summary(cox_model_AI)
ate_obj_second_stage <- ate(
  cox_model_AI,
  data        = survival_data_second_stage,
  treatment   = "treated_factor",
  times       = 1:6,
  se          = TRUE,
  iid         = TRUE,
  keep.iid    = TRUE,
  avg         = "time"
)

summary(ate_obj_second_stage)
rd_summary_second_stage <- as.data.table(ate_obj_second_stage) %>%
  filter(type == "diffRisk") %>% filter(time == 6)
cox_ate_second_stage <- rd_summary_second_stage$estimate
cox_ate_se_second_stage <- rd_summary_second_stage$se


### AI passed
survival_data_AI_passed <- merged_data %>% filter(AI_passed == 1 | manual_choice == 1) %>%
  mutate(
    treated_factor = factor(ifelse(treatment == 1, 1, 0)), # Convert to factor
    # Time to event (in months from baseline)
    time = case_when(
      jan == 1 ~ 1,
      feb == 1 ~ 2,
      mar == 1 ~ 3,
      apr == 1 ~ 4,
      may == 1 ~ 5,
      TRUE ~ 6  # Censored at end of study period
    ),
    # Event indicator (1 = got new job, 0 = censored)
    event = as.numeric(jan == 1 | feb == 1 | mar == 1 | apr == 1 | may == 1) # Ensure numeric 0/1
  ) %>% 
  select(time, event, treated_factor) %>% 
  na.omit()

cox_model_AI <- coxph(Surv(time, event) ~ treated_factor, 
                      data = survival_data_AI_passed,
                      x = TRUE,
                      y = TRUE)

summary(cox_model_AI)
ate_obj_AI_passed <- ate(
  cox_model_AI,
  data        = survival_data_AI_passed,
  treatment   = "treated_factor",
  times       = 1:6,
  se          = TRUE,
  iid         = TRUE,
  keep.iid    = TRUE,
  avg         = "time"
)

summary(ate_obj_AI_passed)
rd_summary_AI_passed <- as.data.table(ate_obj_AI_passed) %>%
  filter(type == "diffRisk") %>% filter(time == 6)
cox_ate_AI_passed <- rd_summary_AI_passed$estimate
cox_ate_se_AI_passed <- rd_summary_AI_passed$se

baseline_AI_passed <- mean(merged_data$new_job[merged_data$AI_passed == 1],na.rm = TRUE)
baseline_manual_choice <- mean(merged_data$new_job[merged_data$manual_choice == 1],na.rm = TRUE)
se_baseline_AI_passed <- sqrt(var(merged_data$new_job[merged_data$AI_passed == 1], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$AI_passed == 1])))
se_baseline_manual_choice <- sqrt(var(merged_data$new_job[merged_data$manual_choice == 1], na.rm = TRUE) / sum(!is.na(merged_data$new_job[merged_data$manual_choice == 1])))

## Table for the paper

estimates <- c(delta_mean_1, delta_mean_2, cox_ate_second_stage, cox_ate_AI_passed)
se <- c(se_1, se_2, cox_ate_se_second_stage, cox_ate_se_AI_passed)
baselines <- c(baseline_1, baseline_2, baseline_AI_passed, baseline_manual_choice)
se_baselines <- c(se_baseline_1, se_baseline_2, se_baseline_AI_passed, se_baseline_manual_choice)
table_data <- data.frame(estimates, se, baselines, se_baselines)
table_data <- t(table_data)
colnames(table_data) <- c("Difference-in-means", "Difference-in-means", "Cox PH", "Cox PH")
rownames(table_data) <- c("ATE", "SE", "Baseline", "SE")
table_data <- round(table_data, 3)

print(table_data)









#########################################################
#### Key t.tests
#########################################################

# 1. Second stage: AI vs Manual
t.test(merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 1], merged_data$new_job[merged_data$second_stage == 1 & merged_data$treatment == 0])

# 2. AI passed vs manual choice
t.test(merged_data$new_job[merged_data$AI_passed == 1], merged_data$new_job[merged_data$manual_choice == 1])


# 3. OLS for the treatment group

data_reg <- merged_data %>% filter(treatment == 1) %>% mutate(AI_passed = ifelse(is.na(AI_passed), 0, AI_passed))

# Run regression and extract coefficients and standard errors
reg_results <- lm(new_job ~ second_stage + AI_passed + AI_did_not_pass, data = data_reg)
coef_data <- data.frame(
  term = names(coef(reg_results)),
  estimate = coef(reg_results),
  std.error = sqrt(diag(vcov(reg_results)))
) %>%
  filter(term != "(Intercept)")

# Create coefficient plot
ggplot(coef_data, aes(x = term, y = estimate)) +
  geom_point(size = 4.5, color = "#2166ac") +
  geom_errorbar(aes(ymin = estimate - std.error, 
                    ymax = estimate + std.error),
                width = 0.25, color = "#2166ac", size = 1.2) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray50", size = 1) +
  coord_flip() +
  labs(
    title = "Treatment Effects on Job Acquisition",
    x = "Treatment Group",
    y = "Effect Size (Percentage Points)"
  ) +
  theme_classic() +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 24, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 20, face = "bold"),
    axis.text = element_text(size = 18),
    panel.grid.major = element_line(color = "grey90", size = 0.8),
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 1.2),
    plot.margin = margin(30, 30, 30, 30)
  )

print(coef_plot)
ggsave(coef_plot, 
       file = "/Users/emilpalikot/Research/AI-Recruiter/figures/ols_plot.png", 
       width = 12, height = 8, dpi = 300)

# 4. OLS for the control group

data_reg <- merged_data %>% filter(treatment == 0) %>% mutate(manual_choice = ifelse(is.na(manual_choice), 0, manual_choice))

reg_results <- lm(new_job ~ second_stage + manual_choice, data = data_reg)
coef_data <- data.frame(
  term = names(coef(reg_results)),
  estimate = coef(reg_results),
  std.error = sqrt(diag(vcov(reg_results)))
) %>%
  filter(term != "(Intercept)")

# Create coefficient plot
ggplot(coef_data, aes(x = term, y = estimate)) +
  geom_point(size = 4.5, color = "#2166ac") +
  geom_errorbar(aes(ymin = estimate - std.error, 
                    ymax = estimate + std.error),
                width = 0.25, color = "#2166ac", size = 1.2) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray50", size = 1) +
  coord_flip() +
  labs(
    title = "Control Effects on Job Acquisition",
    x = "Control Group",
    y = "Effect Size (Percentage Points)"
  ) +
  theme_classic() +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 24, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 20, face = "bold"),
    axis.text = element_text(size = 18),
    panel.grid.major = element_line(color = "grey90", size = 0.8),
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 1.2),
    plot.margin = margin(30, 30, 30, 30)
  )
  
print(coef_plot)
ggsave(coef_plot, 
       file = "/Users/emilpalikot/Research/AI-Recruiter/figures/ols_plot_control.png", 
       width = 12, height = 8, dpi = 300)



# 5. Auxiliary comparisons

t.test(merged_data$new_job[merged_data$AI_passed == 1], merged_data$new_job[merged_data$AI_did_not_pass == 1])

## benefit of AI + human over just AI
0.2916667 - 0.2916667

0.1851852 - 0.1823362






#########################################################
#### Survival analysis
#########################################################
library(riskRegression)
library(data.table)

survival_data <- merged_data %>% filter(treatment == 1) %>%
 mutate(
  treated_factor = as.factor(AI_passed),
  time = case_when(
    jan == 1 ~ 1,
    feb == 1 ~ 2,
    mar == 1 ~ 3,
    apr == 1 ~ 4,
    may == 1 ~ 5,
    TRUE ~ 6  # Censored at end of study period
  )
 )

survival_data_AI <- merged_data %>% filter(treatment == 1) %>%
  mutate(
    treated_factor = factor(ifelse(AI_passed == 1, 1, 0)), # Convert to factor
    # Time to event (in months from baseline)
    time = case_when(
      jan == 1 ~ 1,
      feb == 1 ~ 2,
      mar == 1 ~ 3,
      apr == 1 ~ 4,
      may == 1 ~ 5,
      TRUE ~ 6  # Censored at end of study period
    ),
    # Event indicator (1 = got new job, 0 = censored)
    event = as.numeric(jan == 1 | feb == 1 | mar == 1 | apr == 1 | may == 1) # Ensure numeric 0/1
  ) %>% 
  select(time, event, treated_factor) %>% 
  na.omit()

# First fit Cox model
cox_model_AI <- coxph(Surv(time, event) ~ treated_factor, 
                      data = survival_data_AI,
                      x = TRUE,
                      y = TRUE)

summary(cox_model_AI)


ate_obj_AI <- ate(
  cox_model_AI,
  data        = survival_data_AI,
  treatment   = "treated_factor",
  times       = 1:6,
  se          = TRUE,
  iid         = TRUE,
  keep.iid    = TRUE,
  avg         = "time"
)

summary(ate_obj_AI)
rd_summary_AI <- as.data.table(ate_obj_AI) %>%
  filter(type == "diffRisk") %>% filter(time == 6)
cox_ate_AI <- rd_summary_AI$estimate
cox_ate_se_AI <- rd_summary_AI$se



survival_data_manual <- merged_data %>% filter(treatment == 0) %>%
  mutate(
    treated_factor = factor(ifelse(manual_choice == 1, 1, 0)), # Convert to factor
    # Time to event (in months from baseline)
    time = case_when(
      jan == 1 ~ 1,
      feb == 1 ~ 2,
      mar == 1 ~ 3,
      apr == 1 ~ 4,
      may == 1 ~ 5,
      TRUE ~ 6  # Censored at end of study period
    ),
    # Event indicator (1 = got new job, 0 = censored)
    event = as.numeric(jan == 1 | feb == 1 | mar == 1 | apr == 1 | may == 1) # Ensure numeric 0/1
  ) %>% 
  select(time, event, treated_factor) %>% 
  na.omit()

# First fit Cox model
cox_model_manual <- coxph(Surv(time, event) ~ treated_factor, 
                      data = survival_data_manual,
                      x = TRUE,
                      y = TRUE)

summary(cox_model_manual)


ate_obj_manual <- ate(
  cox_model_manual,
  data        = survival_data_manual,
  treatment   = "treated_factor",
  times       = 1:6,
  se          = TRUE,
  iid         = TRUE,
  keep.iid    = TRUE,
  avg         = "time"
)

summary(ate_obj_manual)
rd_summary_manual <- as.data.table(ate_obj_manual) %>%
  filter(type == "diffRisk") %>% filter(time == 6)
cox_ate_manual <- rd_summary_manual$estimate
cox_ate_se_manual <- rd_summary_manual$se

summary(merged_data$new_job)
summary(merged_data$new_job[merged_data$treatment == 0])
summary(merged_data$new_job[merged_data$treatment == 0 & merged_data$manual_choice == 1])



survival_data_mixed <- merged_data %>% filter(AI_passed == 1 | manual_choice == 1) %>%
  mutate(
    treated_factor = factor(ifelse(AI_passed == 1, 1, 0)), # Convert to factor
    # Time to event (in months from baseline)
    time = case_when(
      jan == 1 ~ 1,
      feb == 1 ~ 2,
      mar == 1 ~ 3,
      apr == 1 ~ 4,
      may == 1 ~ 5,
      TRUE ~ 6  # Censored at end of study period
    ),
    # Event indicator (1 = got new job, 0 = censored)
    event = as.numeric(jan == 1 | feb == 1 | mar == 1 | apr == 1 | may == 1) # Ensure numeric 0/1
  ) %>% 
  select(time, event, treated_factor) %>% 
  na.omit()

# First fit Cox model
cox_model_mixed <- coxph(Surv(time, event) ~ treated_factor, 
                      data = survival_data_mixed,
                      x = TRUE,
                      y = TRUE)

summary(cox_model_mixed)


ate_obj_mixed <- ate(
  cox_model_mixed,
  data        = survival_data_mixed,
  treatment   = "treated_factor",
  times       = 1:6,
  se          = TRUE,
  iid         = TRUE,
  keep.iid    = TRUE,
  avg         = "time"
)

summary(ate_obj_mixed)
rd_summary_mixed <- as.data.table(ate_obj_mixed) %>%
  filter(type == "diffRisk") %>% filter(time == 6)
cox_ate_mixed <- rd_summary_mixed$estimate
cox_ate_se_mixed <- rd_summary_mixed$se