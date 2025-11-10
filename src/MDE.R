library(dplyr)

# Final stage data
final_interview <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/top_candidates_interviewed.csv")
final_interview$treatment <- ifelse(final_interview$Interview.Type == "AI + Human Interview", 1, 0)


# Add resume score to the data:
treat <- read.csv(file.path(root, "experiments/resume_vetting/Ai-Vetted-ranked.csv")) %>%
  distinct(email_id, .keep_all = TRUE) %>%
  select( email_id,resume_score,is_passed, is_completed, ai_vetting_results) %>%
  mutate(treatment = 1)

control <- read.csv(file.path(root, "experiments/resume_vetting/Manual-Resume-ranked.csv")) %>%
  distinct(email_id, .keep_all = TRUE)  %>%
  select(email_id,resume_score) %>%
  mutate(is_passed = NA, is_completed = NA, ai_vetting_results = NA, treatment = 0)

# Combine treatment and control
rs_data <- rbind(treat, control) 
rs_data <- rs_data %>% distinct(email_id, .keep_all = TRUE) %>% select(email_id, resume_score)

final_interview <- left_join(final_interview, rs_data, by = "email_id")

# Set seed for reproducibility
set.seed(123)

# Select all candidates from treatment group
treatment_candidates <- final_interview %>% filter(treatment == 1)

# Select top 35 candidates from control group by resume_score
control_candidates <- final_interview %>% 
  filter(treatment == 0) %>%
  arrange(desc(resume_score)) %>%
  slice_head(n = 35)
# Combine treatment group with randomly selected control candidates
final_interview <- rbind(treatment_candidates, control_candidates)

# Verify the counts
cat("Treatment candidates:", nrow(treatment_candidates), "\n")
cat("Control candidates (random 35):", nrow(control_candidates), "\n")
cat("Total candidates in random dataset:", nrow(final_interview), "\n")

# Number of candidates interviewed in treatment and control groups:
n_treatment <- final_interview %>% filter(treatment == 1) %>% nrow()
n_control <- final_interview %>% filter(treatment == 0) %>% nrow()

# Outcome in control group:
final_interview$Pass <- ifelse(final_interview$Result == "Pass", 1, 0)
baseline <- mean(final_interview$Pass[final_interview$treatment == 0])
sd_control <- sd(final_interview$Pass[final_interview$treatment == 0])

# Minimum detectable effect:
# Calculate MDE using standard formula with alpha = 0.05 and power = 0.8
alpha <- 0.05  # significance level
power <- 0.8   # statistical power
z_alpha <- qnorm(1 - alpha/2)  # z-score for significance level
z_power <- qnorm(power)        # z-score for power

# Calculate MDE
mde <- (z_alpha + z_power) * sqrt((sd_control^2 / n_control) + (sd_control^2 / n_treatment))

t.test(final_interview$Pass[final_interview$treatment == 1], final_interview$Pass[final_interview$treatment == 0])



######################## Rubin & Imbens permutation test ########################




perm_test <- function(treat, outcome, B = 50000, seed = 123) {
  stopifnot(length(treat) == length(outcome),
            setequal(unique(treat), c(0, 1)))

  set.seed(seed)

  ## observed difference
  obs_diff <- mean(outcome[treat == 1]) - mean(outcome[treat == 0])

  ## container for permutation statistics
  perm_stats <- numeric(B)

  ## permute treatment labels B times
  for (b in seq_len(B)) {
    shuffled <- sample(treat)                 # complete randomisation
    perm_stats[b] <- mean(outcome[shuffled == 1]) -
                     mean(outcome[shuffled == 0])
  }

  ## p-values
  p_one <- mean(perm_stats >= obs_diff)       # one-sided (superiority)
  p_two <- mean(abs(perm_stats) >= abs(obs_diff))   # two-sided

  list(obs_diff   = obs_diff,
       p_one_side = p_one,
       p_two_side = p_two,
       perm_stats = perm_stats)
}


result <- perm_test(final_interview$treatment, final_interview$Pass, B = 10000)

cat("Observed difference (T - C) =", round(result$obs_diff, 3), "\n")
cat("One-sided p-value =", round(result$p_one_side, 4), "\n")
cat("Two-sided p-value =", round(result$p_two_side, 4), "\n")




png(filename = "figures/permutation_distribution.png", width = 10, height = 6, units = "in", res = 300)

# Recreate the plot for saving
par(mar = c(5, 5, 4, 2) + 0.1, 
    cex.lab = 1.2, 
    cex.axis = 1.1, 
    cex.main = 1.3,
    family = "serif")

hist(result$perm_stats, 
     breaks = 30, 
     main = "Permutation Distribution of Treatment Effect",
     xlab = "Difference in Pass Rate (Treatment − Control)",
     ylab = "Frequency",
     col = "lightgray",
     border = "white",
     probability = TRUE)

lines(density(result$perm_stats), 
      col = "darkblue", 
      lwd = 2)

abline(v = result$obs_diff, 
       col = "darkred", 
       lwd = 2, 
       lty = 2)

text(result$obs_diff, 
     max(hist(result$perm_stats, breaks = 30, plot = FALSE)$density) * 0.8, 
     paste("Observed\ndifference =", round(result$obs_diff, 3)),
     pos = 4,
     col = "darkred",
     cex = 0.9)

legend("topright", 
       legend = paste("Two-sided p-value =", round(result$p_two_side, 4)),
       bty = "n",
       cex = 1.1)

# Close the device to save the file
dev.off()



