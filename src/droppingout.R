########################################################
## 0.  House-keeping & packages                       ##
########################################################
rm(list = ls())

required_pkgs <- c(
  "dplyr", "ggplot2", "stringr", "tidyr", "lubridate",
  "knitr", "grf", "caret", "stargazer", "broom",
  "kableExtra", "gridExtra", "gbm", "jsonlite", "purrr"
)
invisible(lapply(required_pkgs, library, character.only = TRUE))

root_dir    <- "/Users/emilpalikot/Research/AI-Recruiter"
figures_dir <- file.path(root_dir, "src/figures")

########################################################
## 1.  Load data                                      ##
########################################################
treatment_group <- read.csv(
  file.path(root_dir,
            "micro1-controll-experiment-EDA/job_101(AI)_w_age_gender.csv")
)
ai_scores <- read.csv(file.path(root_dir, "experiments/resume_vetting/Ai-Vetted-ranked.csv"))

########################################################
## 2.  Drop duplicate candidates                      ##
########################################################
data_analysis <- treatment_group %>% distinct(email_id, .keep_all = TRUE)

########################################################
## 3.  AI-score cleanup                               ##
########################################################
ai_scores <- ai_scores %>%
  select(email_id, resume_score, ai_vetting_results) %>%
  mutate(
    React      = str_remove(str_extract(ai_vetting_results,
                             "React\\s*:\\s*\\w+"), "React\\s*:\\s*"),
    JavaScript = str_remove(str_extract(ai_vetting_results,
                             "JavaScript\\s*:\\s*\\w+"), "JavaScript\\s*:\\s*"),
    CSS        = str_remove(str_extract(ai_vetting_results,
                             "HTML,\\s*CSS\\s*:\\s*\\w+"), "HTML,\\s*CSS\\s*:\\s*")
  ) %>%
  select(email_id, React, JavaScript, CSS, resume_score)

########################################################
## 4.  Merge main data + AI scores                    ##
########################################################
data_analysis <- data_analysis %>%
  select(email_id, country_code, years_of_exp, is_completed,
         vetting_creation_date, vetting_completed_date,
         is_passed, education, gender, age) %>%
  left_join(ai_scores, by = "email_id")

########################################################
## 5.  Parse education JSON                           ##
########################################################
parse_education <- function(json_str) {
  if (is.na(json_str) || json_str %in% c("[]", "")) return(NULL)
  tryCatch(fromJSON(json_str), error = function(e) NULL)
}

education_df <- map_dfr(seq_len(nrow(data_analysis)), function(i) {
  ed <- parse_education(data_analysis$education[i])
  if (is.null(ed) || nrow(ed) == 0) return(NULL)
  ed$email_id <- data_analysis$email_id[i]
  ed
})

if (nrow(education_df)) {
  education_df <- education_df %>%
    mutate(
      education_level = case_when(
        str_detect(degree, regex("bachelor|bsc|b\\.tech|b\\.sc", TRUE)) ~ "Bachelor's",
        str_detect(degree, regex("master|msc|m\\.tech|m\\.sc",   TRUE)) ~ "Master's",
        str_detect(degree, regex("phd|doctorate",                TRUE)) ~ "PhD",
        str_detect(degree, regex("high school|secondary|class (10|12)|10th|12th",
                                 TRUE))                                    ~ "High School",
        TRUE ~ "Other"
      )
    ) %>%
    select(email_id, degree, major, education_level, start_date, end_date, is_present) %>%
    group_by(email_id) %>% arrange(desc(start_date)) %>% slice(1) %>% ungroup()

  data_analysis <- left_join(data_analysis, education_df, by = "email_id")
}

########################################################
## 6.  Feature engineering                            ##
########################################################
data_analysis <- data_analysis %>%
  mutate(
    is_completed = replace_na(is_completed, 0),
    dropped_out  = if_else(is_completed == 1, 0, 1),
    resume_score = as.numeric(resume_score),
    male         = (gender == "Male") * 1,
    high_school  = (education_level == "High School") * 1,
    bachelor     = (education_level == "Bachelor's")  * 1,
    master       = (education_level == "Master's")    * 1,
    phd          = (education_level == "PhD")         * 1
  ) %>%
  filter(!is.na(resume_score))

########################################################
## 7.  Baseline regressions                           ##
########################################################
form_cov      <- dropped_out ~ years_of_exp + age + high_school +
                 bachelor + master + male + resume_score
form_no_score <- update(form_cov, . ~ . - resume_score)

ols_dropped_out            <- lm(form_cov,      data_analysis)
logit_dropped_out          <- glm(form_cov,      data_analysis, family = binomial)
ols_dropped_out_no_resume  <- lm(form_no_score, data_analysis)
logit_dropped_out_no_resume<- glm(form_no_score, data_analysis, family = binomial)

baseline_models <- list(ols_dropped_out, logit_dropped_out,
                        ols_dropped_out_no_resume, logit_dropped_out_no_resume)
stargazer(baseline_models, type = "text", title = "Baseline regressions")

########################################################
## 8.  Predict pass probabilities (GBM)               ##
########################################################
participated <- data_analysis %>%
  filter(is_completed == 1) %>%
  mutate(passed_AI = (is_passed == "TRUE") * 1)

gbm_model <- gbm(
  passed_AI ~ years_of_exp + age + high_school + bachelor +
              master + male + resume_score,
  data              = participated,
  distribution      = "bernoulli",
  n.trees           = 1000,
  interaction.depth = 3,
  shrinkage         = 0.01,
  cv.folds          = 5,
  verbose           = FALSE
)

data_analysis$predicted_probabilities <- predict(
  gbm_model, newdata = data_analysis, n.trees = 1000, type = "response"
)

hist(data_analysis$predicted_probabilities)

########################################################
## 9.  Regressions w/ predicted probability           ##
########################################################
ols_pred_only   <- lm(dropped_out ~ predicted_probabilities, data_analysis)
logit_pred_only <- glm(dropped_out ~ predicted_probabilities,
                       data_analysis, family = binomial)

ols_pred_cov   <- lm(update(form_cov, . ~ predicted_probabilities + .),
                     data_analysis)
logit_pred_cov <- glm(update(form_cov, . ~ predicted_probabilities + .),
                      data_analysis, family = binomial)

########################################################
## 10. Final summary table                            ##
########################################################
# Create a list of all regression models
all_models <- list(
  "OLS without resume score" = ols_dropped_out_no_resume,
  "OLS with covariates" = ols_dropped_out,
  "OLS with predicted prob + covariates" = ols_pred_cov,
  "OLS with predicted prob only" = ols_pred_only
)

# Pass the list to stargazer
stargazer(all_models,
          type = "latex",
          title = "Regression Results",
          align = TRUE,
          single.row = TRUE,
          column.labels = names(all_models),
          model.numbers = FALSE)
