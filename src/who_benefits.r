########################################################
## 0.  Setup & packages                               ##
########################################################
rm(list = ls())

libs <- c("dplyr","stringr","tidyr","jsonlite",
          "ggplot2","knitr","stargazer")
invisible(lapply(libs, library, character.only = TRUE))

root <- "/Users/emilpalikot/Research/AI-Recruiter"
figs <- file.path(root,"src/figures")

########################################################
## 1.  Load & minimal clean                           ##
########################################################
treat <- read.csv(file.path(root,
           "micro1-controll-experiment-EDA/job_101(AI)_w_age_gender.csv"))
ctrl  <- read.csv(file.path(root,
           "micro1-controll-experiment-EDA/job_110(Manual)_w_age_gender.csv"))

common <- intersect(names(treat), names(ctrl))
treat  <- treat[ , common] %>% mutate(treatment = 1)
ctrl   <- ctrl  [ , common] %>% mutate(treatment = 0)

merged_data <- bind_rows(treat, ctrl) %>% distinct(email_id, .keep_all = TRUE)

## ---- add AI / human scores --------------------------
ai  <- read.csv(file.path(root,"Ai-Vetted-ranked.csv"))     %>%
       select(email_id, resume_score, ai_vetting_results)
hum <- read.csv(file.path(root,"Manual-Resume-ranked.csv")) %>%
       select(email_id, resume_score) %>%
       mutate(React = NA, JavaScript = NA, CSS = NA)

ai <- ai %>%
  mutate(
    React      = str_remove(str_extract(ai_vetting_results,
                              "React\\s*:\\s*\\w+"),      "React\\s*:\\s*"),
    JavaScript = str_remove(str_extract(ai_vetting_results,
                              "JavaScript\\s*:\\s*\\w+"), "JavaScript\\s*:\\s*"),
    CSS        = str_remove(str_extract(ai_vetting_results,
                              "HTML,\\s*CSS\\s*:\\s*\\w+"),"HTML,\\s*CSS\\s*:\\s*")
  ) %>%
  select(email_id, React, JavaScript, CSS, resume_score)
ai$resume_score <- as.numeric(ai$resume_score)
hum$resume_score <- as.numeric(hum$resume_score)

evals <- bind_rows(ai, hum)   # keep both AI & human résumé scores
merged_data <- left_join(merged_data, evals, by = "email_id")

## ---- parse education (needed for covariates) --------
parse_edu <- function(js){
  if(is.na(js) || js %in% c("[]","")) return("other")
  tolower(tryCatch(fromJSON(js)$degree[1], error = \(e) "other"))
}

merged_data$education_level <- vapply(merged_data$education, parse_edu, character(1))

########################################################
## 2.  Treated subset + feature construction           ##
########################################################
treated <- merged_data %>% filter(treatment == 1) %>%
  mutate(
    ## numeric AI skill score (0–9)
    AI_score = rowSums(across(c(React,JavaScript,CSS), ~case_when(
                  . %in% "Senior"    ~ 3,
                  . %in% "Mid-level" ~ 2,
                  . %in% "Junior"    ~ 1,
                  TRUE               ~ 0)), na.rm = TRUE),
    resume_score = as.numeric(resume_score),
    AI_score     = replace_na(AI_score,0),
    resume_score = replace_na(resume_score,0),

    ## percentiles & ranks
    AI_pct   = ecdf(AI_score)(AI_score),
    CV_pct   = ecdf(resume_score)(resume_score),
    AI_rank  = rank(AI_score),
    CV_rank  = rank(resume_score),
    rank_diff= AI_rank - CV_rank,

    ## covariates
    years_of_exp = as.numeric(years_of_exp),
    age          = as.numeric(age),
    male         = as.integer(gender == "Male"),
    high_school  = as.integer(str_detect(education_level,"high school")),
    bachelor     = as.integer(str_detect(education_level,"bachelor")),
    master       = as.integer(str_detect(education_level,"master")),
    phd          = as.integer(str_detect(education_level,"phd"))
  )

########################################################
## 3.  Who gains?  Regression on rank gap              ##
########################################################
mod_rank <- lm(rank_diff ~ years_of_exp + age + high_school +
                             bachelor + master + male + resume_score,
               data = treated)

stargazer(mod_rank, type = "text",
          title = "Who Benefits from AI Screening?  (positive rank_diff = gain)")

########################################################
## 4.  Groups: Winners / Neutral / Losers              ##
########################################################
treated <- treated %>%
  mutate(group = case_when(
    rank_diff >  quantile(rank_diff,.66,na.rm=TRUE) ~ "Benefits",
    rank_diff <  quantile(rank_diff,.33,na.rm=TRUE) ~ "Harmed",
    TRUE                                            ~ "Neutral"
  ))

## summary stats by group
summ <- treated %>% select(group, male, high_school, bachelor, master, phd, years_of_exp, age, resume_score) %>% na.omit() %>%
  group_by(group) %>%
  summarise(across(c(male,high_school,bachelor,master,phd,
                     years_of_exp,age,resume_score),
                   list(mean = mean, sd = sd), .names = "{.col}_{.fn}"),
            n = n(),
            .groups="drop")

cat(knitr::kable(summ, digits=2,
    caption = "Covariate means (sd) by benefit group"))

########################################################
## 5.  Heat-map – focus on résumé score & experience  ##
########################################################
covariates <- c("years_of_exp", "resume_score",
                "age", "male",
                "high_school","bachelor","master")

# make sure the two key covariates are numeric & non-missing
treated <- treated |>
  mutate(
    years_of_exp = as.numeric(years_of_exp),
    resume_score = as.numeric(resume_score)
  )

library(purrr)

# ---- build long summary frame -----------------------------------
hf_long <- map_dfr(covariates, function(v) {
  tmp <- treated |>
    group_by(group) |>
    summarise(
      var  = v,
      mean = mean(.data[[v]], na.rm = TRUE),
      se   = sd  (.data[[v]], na.rm = TRUE) /
             sqrt(sum(!is.na(.data[[v]]))),
      .groups = "drop"
    )
  # drop if the variable is all NA
  if (all(is.na(tmp$mean))) return(NULL) else tmp
})

# ---- z-scores per variable --------------------------------------
hf_long <- hf_long |>
  group_by(var) |>
  mutate(
    sd_var = sd(mean, na.rm = TRUE),
    z      = ifelse(is.na(sd_var) | sd_var == 0,
                    0,
                    (mean - mean(mean, na.rm = TRUE)) / sd_var)
  ) |>
  ungroup() |>
  mutate(label = sprintf("%.2f\n(%.2f)", mean, se))

# ---- nice labels & ordering -------------------------------------
var_lbl <- c(years_of_exp = "Years of Experience",
             resume_score = "Résumé Score",
             age          = "Age",xs
             male         = "Male",
             high_school  = "High School",
             bachelor     = "Bachelor’s",
             master       = "Master’s")

hf_long$var   <- factor(hf_long$var,
                        levels = covariates,
                        labels = var_lbl[covariates])

hf_long$group <- factor(hf_long$group,
                        levels = c("Benefits","Neutral","Harmed"))

# ---- draw --------------------------------------------------------
# Create a publication-quality heatmap visualization
heat <- ggplot(hf_long, aes(var, group)) +
          geom_tile(aes(fill = z), color = "white", size = 0.5) +
          geom_text(aes(label = label), size = 6, family = "serif") +
          scale_fill_gradient(low = "#E1BE6A", high = "#40B0A6", name = "z-score") +
          labs(title = "",
               caption = "Note: Cells show group means with standard errors in parentheses.") +
          theme_bw(base_size = 13, base_family = "serif") +
          theme(axis.text.x = element_text(angle = 45, hjust = 1, face = "bold", size = 14),
                axis.text.y = element_text(face = "bold", size = 24),
                axis.title = element_blank(),
                legend.position = "none",
                panel.grid = element_blank(),
                plot.title = element_text(size = 25, face = "bold", hjust = 0.5),
                plot.caption = element_text(size = 21, hjust = 0, face = "italic"))

# Save high-resolution figure for publication
ggsave(file.path(figs, "ai_benefit_heatmap.pdf"),
       heat, width = 7, height = 4, dpi = 600, device = cairo_pdf)

# Also save as PNG for presentations
ggsave(file.path(figs, "ai_benefit_heatmap.png"),
       heat, width = 17, height = 14, dpi = 300)
