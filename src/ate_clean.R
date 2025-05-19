########################################################
## 0.  Setup                                          ##
########################################################
rm(list = ls())

libs <- c("dplyr", "stringr", "tidyr", "jsonlite",
          "stargazer", "grf", "broom", "knitr", "kableExtra")
invisible(lapply(libs, library, character.only = TRUE))

root_dir <- "/Users/emilpalikot/Research/AI-Recruiter"
fig_dir  <- file.path(root_dir, "src/figures")

########################################################
## 1.  Load & core clean                              ##
########################################################
treat <- read.csv(file.path(root_dir,
           "micro1-controll-experiment-EDA/job_101(AI)_w_age_gender.csv"))
ctrl  <- read.csv(file.path(root_dir,
           "micro1-controll-experiment-EDA/job_110(Manual)_w_age_gender.csv"))

common <- intersect(names(treat), names(ctrl))
treat  <- treat[ , common] %>% mutate(treatment = 1)
ctrl   <- ctrl [ , common] %>% mutate(treatment = 0)

dat <- bind_rows(treat, ctrl) %>% distinct(email_id, .keep_all = TRUE)

## résumé scores (for balance + robustness samples)
resume <- read.csv(file.path(root_dir, "Manual-Resume-ranked.csv")) %>%
          select(email_id, resume_score)
dat <- left_join(dat, resume, by = "email_id")

## parse education JSON ➜ education_level
parse_edu <- function(js) {
  if (is.na(js) || js %in% c("[]", "")) return(NA_character_)
  tryCatch(tolower(fromJSON(js)$degree[1]), error = \(e) NA_character_)
}
dat$education_level <- vapply(dat$education, parse_edu, character(1))

dat <- dat %>%
  mutate(
    years_of_exp = as.numeric(years_of_exp),
    age          = as.numeric(age),
    male         = as.integer(gender == "Male"),
    resume_score = as.numeric(resume_score)
  )

########################################################
## 2.  Summary-statistics table                       ##
########################################################
sum_vars <- c("years_of_exp","age","male","resume_score")
edu_lvls <- c("high school","bachelor","master","phd")
for (v in edu_lvls){
  dat[[gsub(" ", "_", v)]] <- as.integer(str_detect(dat$education_level, v))
}

sum_vars <- c(sum_vars, gsub(" ", "_", edu_lvls))

summary_tbl <- dat %>%
  select(treatment, all_of(sum_vars)) %>%
  group_by(treatment) %>%
  summarise(across(everything(),
                   list(mean = \(x) mean(x, na.rm = TRUE),
                        sd   = \(x)   sd(x, na.rm = TRUE)),
                   .names = "{.col}_{.fn}"),
            n = n(),
            .groups = "drop")

fmt <- function(v) sprintf("%.2f (%.2f)", v[1], v[2])

build_row <- function(var) {
  c(var,
    fmt(unlist(summary_tbl[summary_tbl$treatment==0,
                           paste0(var, c("_mean","_sd"))])),
    fmt(unlist(summary_tbl[summary_tbl$treatment==1,
                           paste0(var, c("_mean","_sd"))])))
}

summ_rows <- t(vapply(sum_vars, build_row, character(3)))
colnames(summ_rows) <- c("Variable","Control","Treatment")
summ_rows <- rbind(c("N",
                     summary_tbl$n[summary_tbl$treatment==0],
                     summary_tbl$n[summary_tbl$treatment==1]),
                   summ_rows)

cat(kable(as.data.frame(summ_rows), format = "latex", booktabs = TRUE,
          caption = "Summary statistics by treatment group"))

########################################################
## 2b. Balance table with t-tests                     ##
########################################################
# Calculate summary statistics by treatment group
summary_stats <- dat %>%
  group_by(treatment) %>%
  summarize(across(all_of(sum_vars), 
                   list(mean = ~mean(., na.rm = TRUE),
                        se = ~sd(., na.rm = TRUE)/sqrt(sum(!is.na(.)))),
                   .names = "{.col}_{.fn}"),
            .groups = "drop")

# Reshape to wide format for easier access
summary_wide <- summary_stats %>%
  pivot_wider(names_from = treatment, 
              values_from = -treatment,
              names_glue = "{.value}_{treatment}")

# Create the balance table
result_table <- tibble(
  Variable = c("Years of Experience", "Age", "Male", "High School", "Bachelor's", "Master's", "PhD", "Resume Score"),
  `Treatment Mean` = c(summary_wide$years_of_exp_mean_1, summary_wide$age_mean_1, summary_wide$male_mean_1, 
                      summary_wide$high_school_mean_1, summary_wide$bachelor_mean_1, summary_wide$master_mean_1, 
                      summary_wide$phd_mean_1, summary_wide$resume_score_mean_1),
  `Treatment SE` = c(summary_wide$years_of_exp_se_1, summary_wide$age_se_1, summary_wide$male_se_1, 
                    summary_wide$high_school_se_1, summary_wide$bachelor_se_1, summary_wide$master_se_1, 
                    summary_wide$phd_se_1, summary_wide$resume_score_se_1),
  `Control Mean` = c(summary_wide$years_of_exp_mean_0, summary_wide$age_mean_0, summary_wide$male_mean_0, 
                    summary_wide$high_school_mean_0, summary_wide$bachelor_mean_0, summary_wide$master_mean_0, 
                    summary_wide$phd_mean_0, summary_wide$resume_score_mean_0),
  `Control SE` = c(summary_wide$years_of_exp_se_0, summary_wide$age_se_0, summary_wide$male_se_0, 
                  summary_wide$high_school_se_0, summary_wide$bachelor_se_0, summary_wide$master_se_0, 
                  summary_wide$phd_se_0, summary_wide$resume_score_se_0)
) %>%
  mutate(
    `Difference` = `Treatment Mean` - `Control Mean`,
    `Difference SE` = sqrt(`Treatment SE`^2 + `Control SE`^2)
  )

# Round the table to 3 decimal places
result_table <- result_table %>% mutate(across(where(is.numeric), round, 3))

# Print the table in markdown format
cat(knitr::kable(result_table, format = "markdown", 
                 caption = "Balance table with treatment-control differences"))


########################################################
## 3.  ATE datasets                                   ##
########################################################
ate0 <- read.csv(file.path(root_dir,
           "micro1-controll-experiment-EDA/top_candidates_interviewed.csv")) %>%
  transmute(email_id,
            treatment = as.integer(Interview.Type == "AI + Human Interview"),
            outcome   = as.integer(Result == "Pass"),
            male      = as.integer(Gender == "Male"),
            age       = ifelse(`Age..Years.` == "18-22" | `Age..Years.` == "23-27", 0, 1)) %>%
  distinct(email_id, .keep_all = TRUE) %>%
  left_join(resume, by = "email_id") %>%          # resume_score already loaded
  drop_na(outcome)

## robustness samples ---------------------------------
ctrl_top35 <- ate0 %>% filter(treatment == 0) %>%
              arrange(desc(resume_score)) %>% slice_head(n = 35)
sample_top <- bind_rows(filter(ate0, treatment == 1), ctrl_top35)

set.seed(123)
ctrl_rand35 <- ate0 %>% filter(treatment == 0) %>% sample_n(35)
sample_rand <- bind_rows(filter(ate0, treatment == 1), ctrl_rand35)

########################################################
## 4.  Regressions                                    ##
########################################################
# full sample
m1_full <- lm(outcome ~ treatment,                 data = ate0)
m2_full <- lm(outcome ~ treatment + male + age,    data = ate0)

# top-35 résumé controls
m1_top  <- lm(outcome ~ treatment,                 data = sample_top)
m2_top  <- lm(outcome ~ treatment + male + age,    data = sample_top)

## Mean in treatment and control
mean(sample_top$outcome[sample_top$treatment == 1])
mean(sample_top$outcome[sample_top$treatment == 0])

# random-35 controls
m1_rand <- lm(outcome ~ treatment,                 data = sample_rand)
m2_rand <- lm(outcome ~ treatment + male + age,    data = sample_rand)

########################################################
## 5.  Report with stargazer                          ##
########################################################

# Top 35 résumé controls
stargazer(m1_top, m2_top,
          type = "text",
          title = "Top 35 résumé controls",
          column.labels = c("Unadjusted", "Adjusted"),
          dep.var.labels = "Pass to Interview",
          omit.stat = c("f", "ser"))

# Random 35 controls
stargazer(m1_rand, m2_rand,
          type = "text",
          title = "Random 35 controls",
          column.labels = c("Unadjusted", "Adjusted"),
          dep.var.labels = "Pass to Interview",
          omit.stat = c("f", "ser"))

# Full sample
stargazer(m1_full, m2_full,
          type = "text",
          title = "Full sample",
          column.labels = c("Unadjusted", "Adjusted"),
          dep.var.labels = "Pass to Interview",
          omit.stat = c("f", "ser"))
