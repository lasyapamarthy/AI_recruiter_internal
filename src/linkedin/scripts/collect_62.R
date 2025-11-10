root <- "/Users/emilpalikot/Research/AI-Recruiter"
clean_handle <- function(url) {
  url %>% 
    str_remove("^https?://[^/]+/") %>%   # drop the scheme + domain
    str_replace("^in/", "") %>%          # drop the 'in/' path segment if present
    str_remove("/$") %>%                 # drop trailing slash
    str_remove("\\?.*$") %>%                # drop any query string
    str_remove("/en")
}

# 1 Load experiment data:

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
  mutate(handle = sapply(linkedin_url, clean_handle))


merged_data <- left_join(experimental_data, matched_linkedin, by = "job_application_id")

# 2. Load data already collected:

collected <- read.csv(file.path(root, "data/collected_linkedin_profiles_62.csv"))

# 3. Remove data already collected:

merged_data_continue <- merged_data %>% filter(!handle %in% collected$handle) 

# 4. Select data for collection:


## i. 500 top resume score:
top_rs <- merged_data_continue %>% arrange(desc(resume_score)) %>% filter(resume_score == 98.75) %>% select(linkedin_url)# %>% sample_n(500)

# 5. Save data for collection:
# Merge passed_ai, not_passed_ai, and top_rs:

to_collect <- top_rs

# Save to txt
write.table(to_collect, file.path(root, "data/linkedin/linkedin_urls_to_collect_62.txt"), row.names = FALSE, col.names = FALSE, quote = FALSE)


