rm(list = ls()) 

library(dplyr)
root <- "/Users/emilpalikot/Research/AI-Recruiter"
treat <- read.csv(file.path(root, "Ai-Vetted-ranked.csv"))
control <- read.csv(file.path(root, "Manual-Resume-ranked.csv"))

treat_linkedin <- read.csv(file.path(root, "data/treatment_linkedin_urls.csv"))
control_linkedin <- read.csv(file.path(root, "data/control_linkedin_urls.csv"))

# Drop duplicates in both:
treat <- treat %>% distinct(email_id, .keep_all = TRUE)
control <- control %>% distinct(email_id, .keep_all = TRUE)


passed_treat <- treat %>% filter(is_passed == TRUE) %>% select(email_id, job_application_id) %>% mutate(treatment = 1)
#Top 287 in control by resume score
control_top <- control %>% arrange(desc(resume_score)) %>% head(287) %>% select(email_id, job_application_id) %>% mutate(treatment = 0)

# Match both groups and order randomly:
matched_data <- rbind(passed_treat, control_top) %>%
  mutate(random_order = sample(n())) %>%
  arrange(random_order) %>%
  select(-random_order)

# Select linkedin

treat_linkedin <- treat_linkedin %>% select(job_application_id, linkedin_url)
control_linkedin <- control_linkedin %>% select(job_application_id, linkedin_url)

matched_linkedin <- rbind(treat_linkedin, control_linkedin)

# Merge with matched_data
matched_data <- merge(matched_data, matched_linkedin, by = "job_application_id", all.x = TRUE)


# Save linkdin_urls as text file
write.table(matched_data$linkedin_url, file.path(root, "data/linkedin_urls.txt"), row.names = FALSE, col.names = FALSE, quote = FALSE)


######################## New groups #####################


# 1. Completed did not pass:


completed_did_not_pass <- treat %>% filter(is_passed == FALSE) %>% select(email_id, job_application_id) %>% mutate(treatment = 1)

# Randomly select 287 from completed did not pass:

completed_did_not_pass_top <- completed_did_not_pass %>% sample_n(287)

# Match with linkedin:

completed_did_not_pass_top_linkedin <- completed_did_not_pass_top %>% merge(matched_linkedin, by = "job_application_id", all.x = TRUE)




#. 2. DId not complete:

did_not_complete <- treat %>% filter(is_completed != 1) %>% select(email_id, job_application_id) %>% mutate(treatment = 1)

# Randomly select 287 from completed did not pass:

did_not_complete_top <- did_not_complete %>% sample_n(287)

# Match with linkedin:

did_not_complete_top_linkedin <- did_not_complete_top %>% merge(matched_linkedin, by = "job_application_id", all.x = TRUE)



#. 3. Low resume score:

low_resume_score <- control %>% filter(!is.na(resume_score)) %>% arrange(desc(resume_score)) %>% tail(287) %>% select(email_id, job_application_id) %>% mutate(treatment = 0)

# Match with linkedin:

low_resume_score_top_linkedin <- low_resume_score %>% merge(matched_linkedin, by = "job_application_id", all.x = TRUE)

# Match all three groups and save as text file

other_groups <- rbind(completed_did_not_pass_top_linkedin, did_not_complete_top_linkedin, low_resume_score_top_linkedin)

write.table(other_groups$linkedin_url, file.path(root, "data/other_groups_linkedin_urls.txt"), row.names = FALSE, col.names = FALSE, quote = FALSE)


# Create a mapping file from linkedin url to treatment group and other group label

mapping <- data.frame(
  linkedin_url = other_groups$linkedin_url,
  treatment_group = other_groups$treatment,
  other_group_label = c("completed_did_not_pass", "did_not_complete", "low_resume_score")
)

# Save mapping file
write.csv(mapping, file.path(root, "data/other_groups_mapping.csv"), row.names = FALSE)








