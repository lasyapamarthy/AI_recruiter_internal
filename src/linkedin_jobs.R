rm(list = ls())

library(dplyr);      library(tidyr);     library(broom);      library(msm)
library(survival);   library(rms);       library(data.table); library(readr)
library(stringr);    library(riskRegression);  library(kableExtra); library(ggplot2)
library(pec)

# Load linkedin data:

data_raw <- read_csv("data/linkedin_jobs_emil.csv")


data_raw$new_job_date = ifelse(data_raw$start_new_job == "Feb-25", 1, ifelse(data_raw$start_new_job == "Mar-25", 2, ifelse(data_raw$start_new_job == "Apr-25", 3, ifelse(data_raw$start_new_job == "May-25", 4, 5))))
data_raw$new_job_date = ifelse(is.na(data_raw$new_job_date), 5, data_raw$new_job_date)
summary(data_raw$new_job_date)
data_raw$got_job = ifelse(data_raw$new_job_date %in% c(1,2,3,4), 1, 0)
data_raw$treated = ifelse(data_raw$`Interview Type` == "AI + Human Interview", 1, 0)
data_raw$treated_factor = factor(data_raw$treated)

data_est <- data_raw %>%
  select(new_job_date, got_job, treated, treated_factor) 


# Some raw comparisons:
t.test(data_raw$got_job ~ data_raw$treated)


# Plot
# Load ggplot2 library
# Create a dataframe for plotting
# Calculate control group probabilities
control_count <- nrow(data_est[data_est$treated == 0,])
control_probs <- c(
  0, # January (month 0) - everyone starts with 0
  sum(data_est$new_job_date <= 1 & data_est$treated == 0)/control_count,
  sum(data_est$new_job_date <= 2 & data_est$treated == 0)/control_count,
  sum(data_est$new_job_date <= 3 & data_est$treated == 0)/control_count,
  sum(data_est$new_job_date <= 4 & data_est$treated == 0)/control_count
)

# Calculate treatment group probabilities
treatment_count <- nrow(data_est[data_est$treated == 1,])
treatment_probs <- c(
  0, # January (month 0) - everyone starts with 0
  sum(data_est$new_job_date <= 1 & data_est$treated == 1)/treatment_count,
  sum(data_est$new_job_date <= 2 & data_est$treated == 1)/treatment_count,
  sum(data_est$new_job_date <= 3 & data_est$treated == 1)/treatment_count,
  sum(data_est$new_job_date <= 4 & data_est$treated == 1)/treatment_count
)

# Create the plot data frame
plot_data <- data.frame(
  month = rep(0:4, 2),
  group = factor(rep(c("Control", "Treatment"), each = 5)),
  probability = c(control_probs, treatment_probs)
)

# Create the plot
job_probability_plot <- ggplot(plot_data, aes(x = month, y = probability, color = group, group = group)) +
  geom_line(size = 1.2) +
  geom_point(size = 4) +
  scale_x_continuous(breaks = 0:4, labels = c("Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25")) +
  scale_y_continuous(labels = scales::percent) +
  labs(
    title = "Probability of Having a Job Over Time",
    x = "Month",
    y = "Probability of Having a Job",
    color = "Interview Type"
  ) +
  theme_classic(base_size = 14) +
  theme(
    legend.position = "bottom",
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.margin = margin(20, 20, 20, 20),
    axis.title = element_text(size = 14, face = "bold"),
    axis.text = element_text(size = 12),
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 12),
    panel.grid.major.y = element_line(color = "gray90"),
    panel.border = element_rect(color = "black", fill = NA, size = 0.5)
  ) +
  scale_color_manual(values = c("Control" = "#0072B2", "Treatment" = "#D55E00"),
                     labels = c("Control" = "Human-only Interview", "Treatment" = "AI+Human Interview"))

# Display the plot
print(job_probability_plot)

# Save in figures directory


# Save the plot to the figures directory
ggsave(
  filename = "job_probability_over_time.png",
  plot = job_probability_plot,
  path = "src/figures/",
  width = 10,
  height = 7,
  dpi = 300
)




# Survival analysis:
fit <- cph(formula = Surv(new_job_date, got_job)~ treated_factor ,data=data_est,y=TRUE,x=TRUE)
ateFit1a <- ate(fit, data = data_est, treatment = "treated_factor", times = 1:5)
summary(ateFit1a)
summary(ateFit1a, short = TRUE, type = "meanRisk")
summary(ateFit1a, short = TRUE, type = "diffRisk")
summary(ateFit1a, short = TRUE, type = "ratioRisk")


# Plot with model estimates -- for now hardcoded by an LLM

## 1. Hard-code the table --------------------------------------------------
risk_df <- tribble(
  ~time, ~treated_factor, ~risk,  ~lower, ~upper,
     1,      0,            0.0258, 0.00, 0.06,
     2,      0,            0.0781, 0.01, 0.15,
     3,      0,            0.1413, 0.05, 0.24,
     4,      0,            0.1413, 0.05, 0.24,
     5,      0,            0.1413, 0.05, 0.24,
     1,      1,            0.0482, 0.00, 0.10,
     2,      1,            0.1426, 0.06, 0.23,
     3,      1,            0.2503, 0.12, 0.38,
     4,      1,            0.2503, 0.12, 0.38,
     5,      1,            0.2503, 0.12, 0.38
) %>% 
  mutate(treated_factor = factor(treated_factor,
                                 levels = c(0, 1),
                                 labels = c("Control", "Treatment")))

## 2. Plot ---------------------------------------------------------------
ggplot(risk_df,
       aes(x = time, y = risk,
           colour = treated_factor, fill = treated_factor,
           group  = treated_factor)) +
  geom_ribbon(aes(ymin = lower, ymax = upper),
              alpha = 0.15, colour = NA) +
  geom_line(size = 1.2) +
  geom_point(size = 2.5) +
  scale_color_brewer(palette = "Set1") +
  scale_fill_brewer(palette = "Set1") +
  labs(x = "Time (months)",
       y = "Standardised Cumulative Risk",
       colour = "", fill = "") +
  theme_bw() +
  theme(legend.position = "top",
        text = element_text(family = "Times", size = 12),
        axis.title = element_text(size = 12, face = "bold"),
        axis.text = element_text(size = 10),
        panel.grid.minor = element_blank(),
        panel.border = element_rect(linewidth = 1),
        legend.text = element_text(size = 11),
        plot.margin = unit(c(0.5, 0.5, 0.5, 0.5), "cm")) +
  scale_x_continuous(breaks = 1:5)

# Match covariates:

cov_data <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/top_candidates_interviewed.csv")
# Load and match resume scores:
resume_scores_manual <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Manual-Resume-ranked.csv")
resume_scores_ai <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/AI-Vetted-ranked.csv")

resume_scores_manual <- resume_scores_manual %>% select(email_id, resume_score)
resume_scores_ai <- resume_scores_ai %>% select(email_id, resume_score)

resume_scores <- rbind(resume_scores_manual, resume_scores_ai)
resume_scores <- resume_scores %>% group_by(email_id) %>% slice_head(n = 1) %>% ungroup()
resume_match <- resume_scores %>% select(email_id,resume_score )
# Without matching to the main file; as i'm dropping to many candiates
cov_data <- cov_data %>% select(Profile.link.Interview.Link, Gender, Age..Years., email_id) %>% left_join(resume_match, by ="email_id")

cov_data$male <- ifelse(cov_data$Gender == "Male", 1, 0)
cov_data$age <- ifelse(is.na(cov_data$Age..Years.), "Not shared", cov_data$Age..Years.)
colnames(data_raw)[5] <- "Profile.link.Interview.Link"
data_matched <- data_raw %>% left_join(cov_data, by = "Profile.link.Interview.Link") %>% mutate(young = ifelse(age == " 18-22" | age == "23-27",1,0)) %>% select(new_job_date, got_job, treated, treated_factor, male, young, resume_score) %>% mutate(resume_score = as.numeric(resume_score)) %>% na.omit()



# Fit a model:
fit <- cph(formula = Surv(new_job_date, got_job)~ treated_factor + male + young + resume_score,data=data_matched,y=TRUE,x=TRUE)
ateFit1a <- ate(fit, data = data_matched, treatment = "treated_factor", times = 1:5)
summary(ateFit1a)
summary(ateFit1a, short = TRUE, type = "meanRisk")
summary(ateFit1a, short = TRUE, type = "diffRisk")
summary(ateFit1a, short = TRUE, type = "ratioRisk")

