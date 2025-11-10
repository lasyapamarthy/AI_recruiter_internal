remove(list = ls())

library(dplyr)
library(stringr)

root <- "/Users/emilpalikot/Research/AI-Recruiter"
# Files we wanted to collect:
passed <- read.table(file.path(root, "data/linkedin_urls.txt"), header = FALSE, stringsAsFactors = FALSE)
not_passed <- read.table(file.path(root, "data/other_groups_linkedin_urls.txt"), header = FALSE, stringsAsFactors = FALSE)
all_files <- rbind(passed, not_passed)

# Add alternative resumescore
alt_rs <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/data/Resume_scoring_comparison.csv")

alt_rs <- alt_rs %>% select(resume_score, job_application_id) %>% arrange(desc(resume_score)) %>% slice(1:300)

trt_linkedin <- read.csv(file.path(root, "data/treatment_linkedin_urls.csv")) %>%
  select(job_application_id, linkedin_url)
alt_rs <- alt_rs %>% left_join(trt_linkedin, by = "job_application_id")

alt_rs <- alt_rs %>% select(linkedin_url) %>% rename(V1 = linkedin_url)

all_files <- rbind(all_files, alt_rs)
all_files <- all_files %>% distinct(V1, .keep_all = TRUE)



# Files we collected:
combined_safari_htmls_experiences <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/latest_experience_528.csv")%>% mutate(start_date = ifelse(start_date == "", NA, start_date))

# Drop emtpy profiles
combined_safari_htmls_experiences <- combined_safari_htmls_experiences %>% filter(start_date != "")
cleaned_linkedin_profiles <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/cleaned_linkedin_profiles.csv") %>% mutate(start_date = ifelse(start_date == "", NA, start_date))

combined_safari_htmls_experiences <- rbind(combined_safari_htmls_experiences, cleaned_linkedin_profiles)

# Gentle scraper files:
gentle_scraper_files <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/data/linkedin/parsed_profiles_final.csv")  %>% mutate(start_date = ifelse(start_date == "", NA, start_date))

combined_safari_htmls_experiences <- rbind(combined_safari_htmls_experiences, gentle_scraper_files)

# Gentle 2:.

gentle_scraper_files_2 <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/linkedin_profiles_htmls_2.csv") %>% mutate(start_date = ifelse(start_date == "", NA, start_date))

combined_safari_htmls_experiences <- rbind(combined_safari_htmls_experiences, gentle_scraper_files_2)


# Merge and save the collected files:
clean_handle <- function(url) {
  url %>% 
    str_remove("^https?://[^/]+/") %>%   # drop the scheme + domain
    str_replace("^in/", "") %>%          # drop the 'in/' path segment if present
    str_remove("/$") %>%                 # drop trailing slash
    str_remove("\\?.*$")                 # drop any query string
}

all_files  <- all_files  %>% mutate(handle = clean_handle(V1))
combined_safari_htmls_experiences <- combined_safari_htmls_experiences %>% 
  mutate(handle = clean_handle(linkedin_url)) %>% mutate(data_collected = 1)

# Drop duplicates:

all_files <- all_files %>% distinct(handle, .keep_all = TRUE)
combined_safari_htmls_experiences <- combined_safari_htmls_experiences %>% distinct(handle, .keep_all = TRUE)

# ----- do the match ---------------------------------------------------------
matches <- all_files %>%
  left_join(combined_safari_htmls_experiences, by = "handle")

matches$data_collected <- ifelse(is.na(matches$data_collected), 0, matches$data_collected)


# Save data to collect as a txt file with LinkedIn URLs:

# Get is_passed profiles that are not yet collected:
missing_is_passed <- matches$V1[matches$is_passed == 1 & matches$data_collected == 0]
# Get profiles not yet collected
to_collect <- matches$V1[matches$data_collected == 0]

# Randomize order of the URLs:
to_collect <- sample(to_collect) 


write.table(to_collect, file.path(root, "data/linkedin/linkedin_urls_to_collect.txt"), row.names = FALSE, col.names = FALSE, quote = FALSE)

# Save the matches:
write.csv(matches, file.path(root, "data/linkedin/collected_files.csv"), row.names = FALSE)
