## Optimal Policy Analysis with DoubleML-style Influence-Function SEs (clustered by subject)
## Author: Emil Palikot (modified to use Chernozhukov IF SEs)
## Date: 2025

# Clear environment and load libraries
remove(list = ls())

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(survival)
  library(nnet)       # multinom
  library(ggplot2)
  library(lpSolve)
  library(splines)
  library(stargazer)
})

set.seed(123)

########################################################################
## TASK 1: COMBINE DATASETS INTO ALL_DATA
########################################################################

data_path <- "/Users/emilpalikot/Research/DareIT_aux_cleanup/Replication_package_data"

mentoring_data  <- read.csv(file.path(data_path, "mentoring.csv"))
challenges_data <- read.csv(file.path(data_path, "challenges_second.csv"))
applicants_data <- read.csv(file.path(data_path, "mentoring_applicants.csv"))

# Harmonize misc fields
challenges_data$social_science <- "2"
applicants_data$UX            <- "2"

applicants_clean <- applicants_data %>%
  select(-education, -residence, -age, -social_science) %>%
  mutate(group = "applicant",
         selected = 0,
         experiment_group = "applicant")

mentoring_clean <- mentoring_data %>%
  mutate(group = ifelse(treated == 1, "mentoring", "control"),
         selected = 1,
         experiment_group = ifelse(treated == 1, "mentoring", "mentoring_control")) %>%
  select(tech_job, prof_experience, STEM, Warsaw, small_town, masters,
         over_30, new_job_date, UX, group, selected, experiment_group)

challenges_clean <- challenges_data %>%
  mutate(group = ifelse(treated == 1, "challenges", "control"),
         selected = 0,
         experiment_group = ifelse(treated == 1, "challenges", "challenges_control")) %>%
  select(tech_job, prof_experience, STEM, Warsaw, small_town, masters,
         over_30, new_job_date, UX, group, selected, experiment_group)

all_data <- bind_rows(applicants_clean, mentoring_clean, challenges_clean) %>%
  mutate(
    not_UX = ifelse(UX == "0", 1, 0),
    group = ifelse(group == "control" | is.na(group), "applicant", group),
    prof_experience = ifelse(is.na(prof_experience),
                             mean(prof_experience, na.rm = TRUE),
                             prof_experience),
    subject_id = 1:n()
  ) %>%
  select(-UX)

cat("=== TASK 1 SUMMARY ===\n")
cat("Total observations:", nrow(all_data), "\n")
print(table(all_data$group))
cat("\nAverage outcomes by group:\n")
print(all_data %>% group_by(group) %>% summarise(mean_tech_job = mean(tech_job, na.rm = TRUE)))

########################################################################
## TASK 2: CREATE TRAIN AND TEST DATASETS (subject-level split within group)
########################################################################

train_subjects <- all_data %>%
  group_by(group) %>%
  summarise(subjects = list(sample(unique(subject_id), 0.5*n_distinct(subject_id)))) %>%
  pull(subjects) %>% unlist()

train_data <- all_data %>% filter(subject_id %in% train_subjects)
test_data  <- all_data %>% filter(!(subject_id %in% train_subjects))

cat("\n=== TASK 2 SUMMARY ===\n")
cat("Train set size:", nrow(train_data), "\n")
cat("Test set size:", nrow(test_data), "\n")
cat("Train set distribution:\n"); print(table(train_data$group))
cat("Test set distribution:\n");  print(table(test_data$group))

########################################################################
## TASK 3: CREATE LONG FORMAT WITH MONTHLY OBSERVATIONS (1-15)
########################################################################

create_monthly_data <- function(data) {
  data %>%
    group_by(subject_id, tech_job, prof_experience, STEM, Warsaw, small_town,
             masters, over_30, not_UX, group, selected, new_job_date, experiment_group) %>%
    tidyr::expand(month = 1:15) %>%
    mutate(tech_job_monthly = ifelse(is.na(new_job_date), 0,
                                     ifelse(month >= new_job_date, 1, 0))) %>%
    ungroup()
}

train_data_monthly <- create_monthly_data(train_data)
test_data_monthly  <- create_monthly_data(test_data)

convert_types <- function(data) {
  data %>%
    mutate(
      subject_id        = as.factor(subject_id),
      tech_job_monthly  = as.numeric(tech_job_monthly),
      experiment_group  = as.factor(experiment_group),
      selected          = as.numeric(selected),
      STEM              = as.numeric(STEM),
      Warsaw            = as.numeric(Warsaw),
      small_town        = as.numeric(small_town),
      masters           = as.numeric(masters),
      over_30           = as.numeric(over_30),
      not_UX            = as.numeric(not_UX),
      prof_experience   = as.numeric(prof_experience),
      group             = factor(group, levels = c("applicant","mentoring","challenges")),
      month             = as.numeric(month)
    )
}

train_data_monthly <- convert_types(train_data_monthly)
test_data_monthly  <- convert_types(test_data_monthly)
train_data$subject_id <- as.factor(train_data$subject_id)
test_data$subject_id  <- as.factor(test_data$subject_id)

cat("\n=== TASK 3 SUMMARY ===\n")
cat("Train monthly observations:", nrow(train_data_monthly), "\n")
cat("Test  monthly observations:", nrow(test_data_monthly), "\n")

########################################################################
## TASK 4: SIMPLE SUMMARY TABLES (optional)
########################################################################

create_summary_table <- function(data, data_monthly, label) {
  overall <- data %>%
    group_by(group) %>%
    summarise(
      n = n(),
      mean_tech_job = mean(tech_job, na.rm = TRUE),
      se_tech_job   = sd(tech_job, na.rm = TRUE) / sqrt(n()),
      .groups = 'drop'
    )
  monthly <- data_monthly %>%
    group_by(group) %>%
    summarise(
      mean_tech_job_monthly = mean(tech_job_monthly, na.rm = TRUE),
      .groups = 'drop'
    )
  overall %>% left_join(monthly, by = "group") %>% mutate(dataset = label)
}

train_summary   <- create_summary_table(train_data, train_data_monthly, "Train")
test_summary    <- create_summary_table(test_data,  test_data_monthly,  "Test")
combined_summary <- bind_rows(train_summary, test_summary)
cat("\n=== TASK 4 SUMMARY ===\n"); print(combined_summary)

########################################################################
## TASK 5: COX MODEL (TRAIN) FOR POLICY CATEs + PREDICTIONS ON TEST
########################################################################

cox_model <- coxph(
  Surv(month, tech_job_monthly) ~ selected + group + STEM + Warsaw +
    small_town + masters + over_30 + not_UX + prof_experience +
    group * (STEM + small_town + masters + over_30 + not_UX + prof_experience),
  data = train_data_monthly
)

mk_new_group <- function(data, g) data %>% mutate(group = factor(g, levels = c("applicant","mentoring","challenges")))
test_as_mentoring  <- mk_new_group(test_data_monthly, "mentoring")
test_as_challenges <- mk_new_group(test_data_monthly, "challenges")
test_as_applicants <- mk_new_group(test_data_monthly, "applicant")

pred_m <- predict(cox_model, newdata = test_as_mentoring,  type = "expected")
pred_c <- predict(cox_model, newdata = test_as_challenges, type = "expected")
pred_a <- predict(cox_model, newdata = test_as_applicants, type = "expected")

prediction_matrix <- data.frame(
  subject_id      = test_data_monthly$subject_id,
  month           = test_data_monthly$month,
  pred_mentoring  = pred_m,
  pred_challenges = pred_c,
  pred_applicants = pred_a,
  cate_mentoring  = pred_m - pred_a,
  cate_challenges = pred_c - pred_a
)

policy_assignment <- prediction_matrix %>%
  group_by(subject_id) %>%
  summarise(
    cate_mentoring  = mean(cate_mentoring),
    cate_challenges = mean(cate_challenges),
    .groups = 'drop'
  )

predicted_outcomes <- prediction_matrix %>%
  group_by(subject_id) %>%
  summarise(
    pred_mentoring  = mean(pred_mentoring),
    pred_challenges = mean(pred_challenges),
    pred_applicants = mean(pred_applicants),
    .groups = 'drop'
  )

## Quick delta-method SEs for Cox-based ATEs on log-hazard difference (optional)
V    <- vcov(cox_model)
beta <- coef(cox_model)

Xa <- model.matrix(cox_model, test_as_applicants)
Xm <- model.matrix(cox_model, test_as_mentoring)
Xc <- model.matrix(cox_model, test_as_challenges)

lp_a <- as.numeric(Xa %*% beta)
lp_m <- as.numeric(Xm %*% beta)
lp_c <- as.numeric(Xc %*% beta)
Ea   <- predict(cox_model, newdata = test_as_applicants, type = "expected")
H0   <- Ea / exp(lp_a)

Tj <- table(test_data_monthly$subject_id)
row_w <- 1 / as.numeric(Tj)[match(test_data_monthly$subject_id, names(Tj))]
row_w <- row_w / dplyr::n_distinct(test_data_monthly$subject_id)
wexp <- H0 * row_w

grad_m <- colSums(Xm * (wexp * exp(lp_m))) - colSums(Xa * (wexp * exp(lp_a)))
grad_c <- colSums(Xc * (wexp * exp(lp_c))) - colSums(Xa * (wexp * exp(lp_a)))

mentoring_se_loghaz  <- sqrt(as.numeric(t(grad_m) %*% V %*% grad_m))
challenges_se_loghaz <- sqrt(as.numeric(t(grad_c) %*% V %*% grad_c))

########################################################################
## TASK 6: AIPW WITH CROSS-FITTING + IF-BASED (DoubleML) SEs
########################################################################

# Helper: subject-level folds (stratified on group & a couple of covariates)
make_subject_folds <- function(test_data, n_folds = 10, stratify = TRUE) {
  if (stratify) {
    subj_df <- test_data %>% distinct(subject_id, group, STEM, over_30)
    fold_info <- subj_df %>%
      group_by(group, STEM, over_30) %>%
      mutate(fold = sample(rep(1:n_folds, length.out = n()))) %>%
      ungroup() %>% select(subject_id, fold)
  } else {
    fold_info <- test_data %>% distinct(subject_id) %>%
      mutate(fold = sample(1:n_folds, n(), replace = TRUE))
  }
  fold_info
}

# Core estimator: 1 repetition, K-fold cross-fitting (DML2 style)
estimate_aipw_crossfit_dml <- function(test_data, test_data_monthly, n_folds = 10, stratify_folds = TRUE) {
  fold_info <- make_subject_folds(test_data, n_folds, stratify_folds)
  test_monthly <- test_data_monthly %>% left_join(fold_info, by = "subject_id")
  test_subjects <- test_data %>% left_join(fold_info, by = "subject_id")

  all_outcomes <- list()
  all_props    <- list()

  for (k in 1:n_folds) {
    fold_test_m <- test_monthly %>% filter(fold == k)
    fold_train_m<- test_monthly %>% filter(fold != k)
    fold_train  <- test_subjects %>% filter(fold != k)
    fold_test_s <- test_subjects %>% filter(fold == k)

    if (nrow(fold_test_m) == 0 || nrow(fold_test_s) == 0) next

    # Outcome model (Cox on monthly, as in your pipeline)
    levels_group <- c("applicant","mentoring","challenges")
    fold_train_m$group <- factor(fold_train_m$group, levels = levels_group)

    cox_fold <- coxph(
      Surv(month, tech_job_monthly) ~ group + selected + STEM + Warsaw +
        small_town + masters + over_30 + not_UX + prof_experience +
        group * (STEM + small_town + masters + over_30 + prof_experience),
      data = fold_train_m
    )

    pred_m <- predict(cox_fold, newdata = fold_test_m %>% mutate(group = factor("mentoring",  levels = levels_group)), type = "expected")
    pred_c <- predict(cox_fold, newdata = fold_test_m %>% mutate(group = factor("challenges", levels = levels_group)), type = "expected")
    pred_a <- predict(cox_fold, newdata = fold_test_m %>% mutate(group = factor("applicant",  levels = levels_group)), type = "expected")

    fold_outcomes <- data.frame(
      subject_id      = fold_test_m$subject_id,
      month           = fold_test_m$month,
      pred_mentoring  = pred_m,
      pred_challenges = pred_c,
      pred_applicants = pred_a,
      actual_outcome  = fold_test_m$tech_job_monthly,
      group           = fold_test_m$group
    )

    all_outcomes[[k]] <- fold_outcomes

    # Propensity (multinomial on subject-level covariates)
    fold_train$group <- factor(fold_train$group, levels = levels_group)
    prop_model <- multinom(
      group ~ STEM + small_town + masters + over_30 + prof_experience,
      data = fold_train, trace = FALSE
    )
    fold_test_s$group <- factor(fold_test_s$group, levels = levels_group)
    prop_pred <- as.matrix(predict(prop_model, newdata = fold_test_s, type = "probs"))
    coln <- colnames(prop_pred)

    p_m <- if ("mentoring"  %in% coln) prop_pred[, "mentoring"]  else rep(NA_real_, nrow(fold_test_s))
    p_c <- if ("challenges" %in% coln) prop_pred[, "challenges"] else rep(NA_real_, nrow(fold_test_s))
    p_a <- if ("applicant"  %in% coln) prop_pred[, "applicant"]  else rep(NA_real_, nrow(fold_test_s))

    # Fill missing via 1 - sum(other)
    to0 <- function(x) { x[is.na(x)] <- 0; x }
    if (all(is.na(p_a))) p_a <- 1 - to0(p_m) - to0(p_c)
    if (all(is.na(p_m))) p_m <- 1 - to0(p_a) - to0(p_c)
    if (all(is.na(p_c))) p_c <- 1 - to0(p_a) - to0(p_m)

    eps <- 1e-6
    p_a <- pmin(pmax(p_a, eps), 1 - eps)
    p_m <- pmin(pmax(p_m, eps), 1 - eps)
    p_c <- pmin(pmax(p_c, eps), 1 - eps)

    all_props[[k]] <- data.frame(
      subject_id = fold_test_s$subject_id,
      prop_applicant  = as.numeric(p_a),
      prop_mentoring  = as.numeric(p_m),
      prop_challenges = as.numeric(p_c)
    )
  }

  # Aggregate to subject-level
  outcomes_df <- bind_rows(all_outcomes) %>%
    group_by(subject_id) %>%
    summarise(
      pred_mentoring  = mean(pred_mentoring),
      pred_challenges = mean(pred_challenges),
      pred_applicants = mean(pred_applicants),
      actual_outcome  = mean(actual_outcome),
      group           = first(as.character(group)),
      .groups = 'drop'
    )

  props_df <- bind_rows(all_props) %>% group_by(subject_id) %>% summarise(
    prop_applicant  = mean(prop_applicant),
    prop_mentoring  = mean(prop_mentoring),
    prop_challenges = mean(prop_challenges),
    .groups = 'drop'
  )

  df <- outcomes_df %>%
    left_join(props_df, by = "subject_id") %>%
    mutate(
      group = factor(group, levels = c("applicant","mentoring","challenges")),
      # AIPW per arm at subject level (winsorized to [0,1])
      aipw_mentoring  = pred_mentoring  + (actual_outcome - pred_mentoring)  * (group == "mentoring")  / prop_mentoring,
      aipw_challenges = pred_challenges + (actual_outcome - pred_challenges) * (group == "challenges") / prop_challenges,
      aipw_applicants = pred_applicants + (actual_outcome - pred_applicants) * (group == "applicant")  / prop_applicant
    )

  # Winsorize to [0,1] to stabilize tails (optional)
  clamp01 <- function(x) pmax(0, pmin(1, x))
  df <- df %>%
    mutate(
      aipw_mentoring  = clamp01(aipw_mentoring),
      aipw_challenges = clamp01(aipw_challenges),
      aipw_applicants = clamp01(aipw_applicants)
    )

  # Influence contributions for DoubleML-style SEs (cluster = subject)
  n <- nrow(df)
  mu_M <- mean(df$aipw_mentoring)
  mu_C <- mean(df$aipw_challenges)
  mu_A <- mean(df$aipw_applicants)

  df <- df %>%
    mutate(
      psi_M = aipw_mentoring  - mu_M,
      psi_C = aipw_challenges - mu_C,
      psi_A = aipw_applicants - mu_A
    )

  list(subject_level = df,
       means = c(Mentoring = mu_M, Challenges = mu_C, Applicants = mu_A))
}

aipw_fit <- estimate_aipw_crossfit_dml(test_data, test_data_monthly, n_folds = 10, stratify_folds = TRUE)
aipw_scores <- aipw_fit$subject_level
n_subj <- nrow(aipw_scores)

# IF-based SEs for the three arm means
se_mu <- function(x) sd(x)/sqrt(length(x))
point_estimates <- c(
  Mentoring  = mean(aipw_scores$aipw_mentoring),
  Challenges = mean(aipw_scores$aipw_challenges),
  Applicants = mean(aipw_scores$aipw_applicants)
)
standard_errors <- c(
  Mentoring  = se_mu(aipw_scores$aipw_mentoring),
  Challenges = se_mu(aipw_scores$aipw_challenges),
  Applicants = se_mu(aipw_scores$aipw_applicants)
)

aipw_summary <- data.frame(
  Treatment = names(point_estimates),
  Point_Estimate = as.numeric(point_estimates),
  Standard_Error = as.numeric(standard_errors)
) %>%
  mutate(CI_Lower = Point_Estimate - 1.96*Standard_Error,
         CI_Upper = Point_Estimate + 1.96*Standard_Error)

cat("\n=== TASK 6 (AIPW + IF-SE) SUMMARY ===\n")
print(aipw_summary)

########################################################################
## TASK 6b: Compare treatment effects (RCT, Cox, AIPW with IF-SE)
########################################################################

# Experiment estimates (loaded externally)
load("src/replication_package/tables/ate_table.RData")
ate_mentoring_rct     <- ate_table[1,3]
ate_challenges_rct    <- ate_table[1,6]
se_ate_mentoring_rct  <- ate_table[2,3]
se_ate_challenges_rct <- ate_table[2,6]

# Cox-policy ATEs (on "expected event" scale difference) with delta SE on log-hazard diff
ate_mentoring_cox  <- mean((pred_m - pred_a)[1:length(pred_m)])
ate_challenges_cox <- mean((pred_c - pred_a)[1:length(pred_c)])

# AIPW ATEs and IF-SEs (differences use covariance via sd of differences)
diff_MA <- aipw_scores$aipw_mentoring - aipw_scores$aipw_applicants
diff_CA <- aipw_scores$aipw_challenges - aipw_scores$aipw_applicants

ate_aipw_mentoring <- mean(diff_MA)
ate_aipw_challenges<- mean(diff_CA)
se_ate_aipw_mentoring <- sd(diff_MA)/sqrt(n_subj)
se_ate_aipw_challenges<- sd(diff_CA)/sqrt(n_subj)

methods <- c("Experiment(Mentoring)", "Experiment(Challenges)",
             "Policy Assignment(Mentoring)", "Policy Assignment(Challenges)",
             "Policy Evaluation(Mentoring)", "Policy Evaluation(Challenges)")

ate_table_out <- data.frame(
  Method = methods,
  ATE = c(ate_mentoring_rct, ate_challenges_rct,
          ate_mentoring_cox, ate_challenges_cox,
          ate_aipw_mentoring, ate_aipw_challenges),
  SE  = c(se_ate_mentoring_rct, se_ate_challenges_rct,
          mentoring_se_loghaz, challenges_se_loghaz,
          se_ate_aipw_mentoring, se_ate_aipw_challenges),
  stringsAsFactors = FALSE
)

print(ate_table_out)

########################################################################
## TASK 7: OPTIMAL POLICY SOLVER + EVALUATION with IF-SEs
########################################################################

optimal_policy_solver <- function(mentoring_cate, challenges_cate,
                                  capacity_mentoring, capacity_challenges,
                                  capacity_nothing, IDs) {
  if (abs(capacity_mentoring + capacity_challenges + capacity_nothing - 1) > 1e-6) {
    stop("Capacities must sum to 1")
  }
  df <- data.frame(Mentoring = mentoring_cate, Challenges = challenges_cate, Nothing = 0)
  n <- nrow(df); p <- ncol(df)
  obj <- as.vector(t(as.matrix(df)))

  C <- matrix(0, n + p, n*p)
  for (i in 1:n) C[i, (p*i-2):(p*i)] <- 1      # row: each person picks one program
  for (j in 1:p) C[n+j, seq(j, n*p, by=p)] <- 1 # column: program totals

  ment_cap <- floor(capacity_mentoring  * n + 1e-9)
  chal_cap <- floor(capacity_challenges * n + 1e-9)
  noth_cap <- n - ment_cap - chal_cap

  rhs <- c(rep(1, n), ment_cap, chal_cap, noth_cap)
  dir <- c(rep("=", n), "<=", "<=", "<=")

  sol <- lpSolve::lp("max", obj, C, dir, rhs, all.bin = TRUE)
  if (sol$status != 0) stop("LP failed with status ", sol$status)

  A <- matrix(sol$solution, n, p, byrow = TRUE)
  P <- apply(A, 1, function(r) which(r == 1L))
  program_code <- LETTERS[P]
  program_name <- c("Mentoring","Challenges","Nothing")[P]

  data.frame(ID = IDs, Assignment = program_code, Program_assignment = program_name, stringsAsFactors = FALSE)
}

# Merge CATEs with AIPW (evaluation domain)
policy_data <- policy_assignment %>%
  left_join(aipw_scores, by = "subject_id") %>%
  filter(!is.na(aipw_mentoring))

# Define policies
optimal_policies <- list(
  list(name = "Random Assignment", shares = c(0.15, 0.15, 0.70), random = TRUE),
  list(name = "Optimal - Current Capacity", shares = c(0.15, 0.15, 0.70), random = FALSE),
  list(name = "Optimal - 1/2-1/2", shares = c(0.50, 0.50, 0.00), random = FALSE),
  list(name = "Optimal - 1/3 - 1/3", shares = c(0.34, 0.33, 0.33), random = FALSE)
)

# IF-based SE helpers ---------------------------------------------------

# For treated-only policy value under a fixed allocation:
# value = mean over treated of (μ_arm - μ_A). IF is sd of that per-subject delta over treated / sqrt(n_treated)
policy_value_and_se <- function(allocation, aipw_df) {
  ids_A <- allocation$ID[allocation$Assignment == "A"] # Mentoring group
  ids_B <- allocation$ID[allocation$Assignment == "B"] # Challenges group
  ids_C <- allocation$ID[allocation$Assignment == "C"]

  map <- aipw_df %>% mutate(subject_id = as.character(subject_id))
  idxA <- match(as.character(ids_A), map$subject_id); idxA <- idxA[!is.na(idxA)]
  idxB <- match(as.character(ids_B), map$subject_id); idxB <- idxB[!is.na(idxB)]
  idxC <- match(as.character(ids_C), map$subject_id); idxC <- idxC[!is.na(idxC)]

  # deltas among treated
  dA <- (map$aipw_mentoring[idxA]  - map$aipw_applicants[idxA])
  dB <- (map$aipw_challenges[idxB] - map$aipw_applicants[idxB])

  nA <- length(dA); nB <- length(dB); nT <- nA + nB
  value <- if (nT > 0) (sum(dA) + sum(dB))/nT else 0

  se_val <- if (nT > 0) {
    sd(c(dA, dB))/sqrt(nT)
  } else 0

  # predicted outcome level across all subjects under the allocation
  Z <- numeric(nrow(map))
  if (nA > 0) Z[idxA] <- map$aipw_mentoring[idxA]
  if (nB > 0) Z[idxB] <- map$aipw_challenges[idxB]
  if (length(idxC) > 0) Z[idxC] <- map$aipw_applicants[idxC]

  pred_level <- mean(Z)
  se_level   <- sd(Z) / sqrt(length(Z))

  list(value = value, se_value = se_val, predicted_level = pred_level, se_level = se_level,
       n_mentoring = nA, n_challenges = nB, n_nothing = length(idxC))
}

# For "random assignment" with shares s = (s_M, s_C, s_A), the per-subject mixture works for SE.
policy_random_value_and_se <- function(shares, aipw_df) {
  sM <- shares[1]; sC <- shares[2]; sA <- shares[3]
  df <- aipw_df
  # Treated-only value mixture per subject
  V_i <- (sM*(df$aipw_mentoring - df$aipw_applicants) +
          sC*(df$aipw_challenges - df$aipw_applicants)) / (sM + sC)
  value <- mean(V_i)
  se_value <- sd(V_i)/sqrt(nrow(df))
  # Predicted outcome level (mixture)
  Z_i <- sM*df$aipw_mentoring + sC*df$aipw_challenges + sA*df$aipw_applicants
  pred_level <- mean(Z_i)
  se_level   <- sd(Z_i)/sqrt(nrow(df))
  list(value = value, se_value = se_value, predicted_level = pred_level, se_level = se_level)
}

# Evaluate policies
policy_results <- list()

for (policy in optimal_policies) {
  if (policy$random) {
    rp <- policy_random_value_and_se(policy$shares, aipw_scores)
    policy_results[[policy$name]] <- list(
      policy_name = policy$name,
      policy_value = rp$value, se_value = rp$se_value,
      predicted_outcome_level = rp$pred_level, se_level = rp$se_level
    )
  } else {
    allocation <- optimal_policy_solver(
      policy_data$cate_mentoring, policy_data$cate_challenges,
      policy$shares[1], policy$shares[2], policy$shares[3],
      policy_data$subject_id
    )
    ev <- policy_value_and_se(allocation, aipw_scores)
    policy_results[[policy$name]] <- c(list(policy_name = policy$name), ev)
  }
}

# Observed policy (as implemented in the test set)
observed_groups <- test_data %>%
  group_by(subject_id) %>%
  summarise(group = first(as.character(group)), .groups = 'drop') %>%
  filter(subject_id %in% policy_data$subject_id)

obs_assign <- ifelse(observed_groups$group == "mentoring",  "A",
               ifelse(observed_groups$group == "challenges","B","C"))
obs_names  <- ifelse(observed_groups$group == "mentoring",  "Mentoring",
               ifelse(observed_groups$group == "challenges","Challenges","Nothing"))

observed_allocation <- data.frame(
  ID = observed_groups$subject_id,
  Assignment = obs_assign,
  Program_assignment = obs_names,
  stringsAsFactors = FALSE
)

obs <- policy_value_and_se(observed_allocation, aipw_scores)
policy_results[["Observed Policy"]] <- c(list(policy_name = "Observed Policy"), obs)

# Summarize
policy_names <- sapply(policy_results, function(x) x$policy_name)
policy_values <- sapply(policy_results, function(x) x$policy_value)
predicted_lvls <- sapply(policy_results, function(x) x$predicted_level)
se_values <- sapply(policy_results, function(x) x$se_value)
se_levels <- sapply(policy_results, function(x) x$se_level)

policy_summary <- data.frame(
  Policy = policy_names,
  Policy_Value = as.numeric(policy_values),
  Predicted_Outcome_Level = as.numeric(predicted_lvls),
  Standard_Error = as.numeric(se_values),
  Level_SE = as.numeric(se_levels),
  stringsAsFactors = FALSE
) %>%
  mutate(
    CI_Lower = Policy_Value - 1.96*Standard_Error,
    CI_Upper = Policy_Value + 1.96*Standard_Error
  )

cat("\n=== POLICY EVALUATION (IF-SE) SUMMARY ===\n")
print(policy_summary)

# Visualization (effects, ±1 SE)
policy_plot <- ggplot(
  policy_summary %>% filter(!Policy %in% c("Observed Policy")),
  aes(x = reorder(Policy, Policy_Value), y = Policy_Value)
) +
  geom_point(size = 6, shape = 21, fill = "white", stroke = 1.2) +
  geom_errorbar(aes(ymin = Policy_Value - Standard_Error,
                    ymax = Policy_Value + Standard_Error),
                width = 0.2, size = 1) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
  theme_minimal() +
  labs(x = NULL, y = "Average Treatment Effect (treated-only value)") +
  theme(
    text = element_text(family = "serif", size = 14),
    axis.text.x = element_text(size = 13, angle = 45, hjust = 1),
    axis.text.y = element_text(size = 13),
    axis.title  = element_text(size = 14),
    panel.grid.major.x = element_blank(),
    panel.grid.minor   = element_blank(),
    panel.border       = element_rect(color = "black", fill = NA),
    plot.margin        = margin(1,1,1,1,"cm")
  )

dir.create("src/replication_package/figures", recursive = TRUE, showWarnings = FALSE)
ggsave("src/replication_package/figures/policy_effects.png", policy_plot, width = 8, height = 6)
print(policy_plot)

########################## Best allocation gain per group (IF-SEs) ##########################

mentoring_capacity  <- 0.15
challenges_capacity <- 0.15
nothing_capacity    <- 1 - mentoring_capacity - challenges_capacity
shares <- c(mentoring_capacity, challenges_capacity, nothing_capacity)

allocation <- optimal_policy_solver(
  policy_data$cate_mentoring, policy_data$cate_challenges,
  mentoring_capacity, challenges_capacity, nothing_capacity,
  policy_data$subject_id
)

# Map for quick lookup
aipw_map <- aipw_scores %>%
  mutate(subject_id = as.character(subject_id)) %>%
  select(subject_id, aipw_mentoring, aipw_challenges, aipw_applicants)

summarize_allocation_effects <- function(allocation, aipw_map) {
  group_labels <- c(A = "Mentoring group", B = "Challenges group", C = "Nothing group")
  eval_levels  <- c("Mentoring","Challenges","Applicants")

  out <- lapply(c("A","B","C"), function(g) {
    ids <- allocation$ID[allocation$Assignment == g]
    idx <- match(as.character(ids), aipw_map$subject_id); idx <- idx[!is.na(idx)]
    if (length(idx) == 0) {
      data.frame(Group = group_labels[[g]],
                 Evaluated_Assignment = eval_levels,
                 Predicted = NA_real_,
                 ATE_vs_Applicants = NA_real_,
                 n = 0L, stringsAsFactors = FALSE)
    } else {
      pred_M <- mean(aipw_map$aipw_mentoring[idx])
      pred_C <- mean(aipw_map$aipw_challenges[idx])
      pred_A <- mean(aipw_map$aipw_applicants[idx])
      ate_MA <- mean(aipw_map$aipw_mentoring[idx]  - aipw_map$aipw_applicants[idx])
      ate_CA <- mean(aipw_map$aipw_challenges[idx] - aipw_map$aipw_applicants[idx])
      data.frame(
        Group = group_labels[[g]],
        Evaluated_Assignment = eval_levels,
        Predicted = c(pred_M, pred_C, pred_A),
        ATE_vs_Applicants = c(ate_MA, ate_CA, 0),
        n = length(idx),
        stringsAsFactors = FALSE
      )
    }
  })
  df <- bind_rows(out)
  df$Group <- factor(df$Group, levels = c("Mentoring group","Challenges group","Nothing group"))
  df$Evaluated_Assignment <- factor(df$Evaluated_Assignment, levels = c("Mentoring","Challenges","Applicants"))
  arrange(df, Group, Evaluated_Assignment)
}

point_summary <- summarize_allocation_effects(allocation, aipw_map)

# IF-style SEs for subset means: sd / sqrt(m) within each (Group, Assignment)
subset_se <- function(vals, m) if (m > 1) sd(vals)/sqrt(m) else NA_real_

compute_se_tables <- function(allocation, aipw_map) {
  out <- list()
  for (g in c("A","B","C")) {
    ids <- allocation$ID[allocation$Assignment == g]
    idx <- match(as.character(ids), aipw_map$subject_id); idx <- idx[!is.na(idx)]
    m <- length(idx)
    if (m == 0) next
    vals_pred <- list(
      Mentoring  = aipw_map$aipw_mentoring[idx],
      Challenges = aipw_map$aipw_challenges[idx],
      Applicants = aipw_map$aipw_applicants[idx]
    )
    vals_ate <- list(
      Mentoring  = aipw_map$aipw_mentoring[idx]  - aipw_map$aipw_applicants[idx],
      Challenges = aipw_map$aipw_challenges[idx] - aipw_map$aipw_applicants[idx],
      Applicants = aipw_map$aipw_applicants[idx] - aipw_map$aipw_applicants[idx]
    )
    out[[g]] <- data.frame(
      Group = c("Mentoring group","Challenges group","Nothing group")[match(g, c("A","B","C"))],
      Evaluated_Assignment = c("Mentoring","Challenges","Applicants"),
      Predicted_SE = sapply(vals_pred, subset_se, m = m),
      ATE_SE       = sapply(vals_ate,  subset_se, m = m),
      stringsAsFactors = FALSE
    )
  }
  bind_rows(out)
}

se_tables <- compute_se_tables(allocation, aipw_map)
alloc_summary <- point_summary %>%
  left_join(se_tables, by = c("Group","Evaluated_Assignment")) %>%
  mutate(
    Predicted_CI_L = Predicted - 1.96*Predicted_SE,
    Predicted_CI_U = Predicted + 1.96*Predicted_SE,
    ATE_CI_L       = ATE_vs_Applicants - 1.96*ATE_SE,
    ATE_CI_U       = ATE_vs_Applicants + 1.96*ATE_SE
  )

cat("\n=== ALLOCATION-GROUP METRICS (IF-SEs) ===\n")
print(alloc_summary, row.names = FALSE)

# Save LaTeX table
dir.create("src/replication_package/tables", recursive = TRUE, showWarnings = FALSE)

nothing_group_label <- "Out of Dare IT group"
fmt_num  <- function(x, d=3) formatC(x, format="f", digits=d)
fmt_cell <- function(x, se, dv=3, ds=3) if (is.na(x) || is.na(se)) "--" else paste0(fmt_num(x,dv), " (", fmt_num(se,ds), ")")

share_A <- mean(allocation$Assignment == "A")
share_B <- mean(allocation$Assignment == "B")
share_C <- mean(allocation$Assignment == "C")

n_A <- sum(allocation$Assignment == "A")
n_B <- sum(allocation$Assignment == "B")
n_C <- sum(allocation$Assignment == "C")

pull_cell <- function(group, arm, what = c("ATE","Pred")) {
  what <- match.arg(what)
  row <- subset(alloc_summary, Group == group & Evaluated_Assignment == arm)
  if (!nrow(row)) return(c(val=NA_real_, se=NA_real_))
  if (what == "ATE") c(val=row$ATE_vs_Applicants[1], se=row$ATE_SE[1])
  else               c(val=row$Predicted[1],       se=row$Predicted_SE[1])
}
gA <- "Mentoring group"; gB <- "Challenges group"; gC <- "Nothing group"
aM <- "Mentoring";       aC <- "Challenges";       aA <- "Applicants"

c_M_A <- pull_cell(gA,aM,"ATE"); c_C_A <- pull_cell(gA,aC,"ATE")
c_M_B <- pull_cell(gB,aM,"ATE"); c_C_B <- pull_cell(gB,aC,"ATE")
c_M_C <- pull_cell(gC,aM,"ATE"); c_C_C <- pull_cell(gC,aC,"ATE")

se_diff <- function(se1, se2) sqrt(se1^2 + se2^2)
diff_A_val <- c_M_A["val"] - c_C_A["val"]; diff_A_se <- se_diff(c_M_A["se"], c_C_A["se"])
diff_B_val <- c_M_B["val"] - c_C_B["val"]; diff_B_se <- se_diff(c_M_B["se"], c_C_B["se"])
diff_C_val <- c_M_C["val"] - c_C_C["val"]; diff_C_se <- se_diff(c_M_C["se"], c_C_C["se"])

hdr <- paste0("\\textbf{} & \\textbf{Mentoring group} & \\textbf{Challenges group} & \\textbf{", nothing_group_label, "} \\\\")
row_share <- paste0("Share & ", fmt_num(share_A,2), " & ", fmt_num(share_B,2), " & ", fmt_num(share_C,2), " \\\\")
row_optimal <- paste0("Optimal 2 & ", fmt_cell(c_M_A["val"], c_M_A["se"]), " & ",
                                   fmt_cell(c_C_B["val"], c_C_B["se"]), " & -- \\\\")
row_M <- paste0("Mentoring & ",
                fmt_cell(c_M_A["val"], c_M_A["se"]), " & ",
                fmt_cell(c_M_B["val"], c_M_B["se"]), " & ",
                fmt_cell(c_M_C["val"], c_M_C["se"]), " \\\\")
row_C <- paste0("Challenges & ",
                fmt_cell(c_C_A["val"], c_C_A["se"]), " & ",
                fmt_cell(c_C_B["val"], c_C_B["se"]), " & ",
                fmt_cell(c_C_C["val"], c_C_C["se"]), " \\\\")
row_diff <- paste0("Mentoring - Challenges & ",
                   fmt_cell(diff_A_val, diff_A_se), " & ",
                   fmt_cell(diff_B_val, diff_B_se), " & ",
                   fmt_cell(diff_C_val, diff_C_se), " \\\\")

caption_txt <- "Gains From Assignment Policy Optimal 2 per Assignment Group"
label_txt   <- "targetting"
note_txt <- paste0(
  "\\footnotesize{\\textit{Note:} Policy value is the average treatment effect relative to Applicants ",
  "for each group's assignment. Groups are fixed by the optimal policy; IF-based SEs (subject-level).}"
)

tex <- paste0(
"\\begin{table}[]\n",
"  \\caption{", caption_txt, "}\n",
"  \\label{", label_txt, "}\n",
"  \\centering\n",
"  \\resizebox{0.65\\textwidth}{!}{%\n",
"    \\begin{tabular}{lccc}\n",
"    \\toprule\\toprule\n",
"    ", hdr, "\n",
"    \\midrule\n",
"    ", row_share, "\n",
"    \\midrule\n",
"    \\multicolumn{4}{@{}l}{\\textit{ATE under assignment to: }}\\\\\n",
"    ", row_optimal, "\n",
"    ", row_M, "\n",
"    ", row_C, "\n",
"    \\midrule\n",
"    \\multicolumn{4}{@{}l}{\\textit{Difference in ATE between assignments:}}\\\\\n",
"    ", row_diff, "\n",
"    \\bottomrule\\bottomrule\n",
"    \\end{tabular}\n",
"  }\n",
"  \\caption*{", note_txt, "}\n",
"\\end{table}\n"
)
out_file <- "src/replication_package/tables/alloc_summary_table.tex"
writeLines(tex, out_file)
cat("Wrote:", normalizePath(out_file, winslash = "/"), "\n")

########################## Capacity curves (no SEs, deterministic curves) ##########################

capacity_levels <- c(0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)
combined_capacity_results <- lapply(capacity_levels, function(capacity) {
  optimal_policy_solver(
    policy_data$cate_mentoring, policy_data$cate_challenges,
    capacity, capacity, 1 - 2*capacity,
    policy_data$subject_id
  )
})
names(combined_capacity_results) <- as.character(capacity_levels)

combined_ate <- numeric(length(capacity_levels))
average_outcome_levels_combined <- numeric(length(capacity_levels))
for (i in seq_along(capacity_levels)) {
  tmp_alloc <- combined_capacity_results[[i]]
  ev <- policy_value_and_se(tmp_alloc, aipw_scores)
  combined_ate[i] <- (mean((aipw_scores$aipw_mentoring - aipw_scores$aipw_applicants)[match(tmp_alloc$ID[tmp_alloc$Assignment=="A"], as.character(aipw_scores$subject_id))], na.rm=TRUE) +
                      mean((aipw_scores$aipw_challenges - aipw_scores$aipw_applicants)[match(tmp_alloc$ID[tmp_alloc$Assignment=="B"], as.character(aipw_scores$subject_id))], na.rm=TRUE))/2
  average_outcome_levels_combined[i] <- ev$predicted_level
}

# Random policy expected outcomes at each capacity
average_outcome_levels_random <- sapply(capacity_levels, function(cap) {
  sM <- cap; sC <- cap; sA <- 1 - 2*cap
  sM*mean(aipw_scores$aipw_mentoring) +
    sC*mean(aipw_scores$aipw_challenges) +
    sA*mean(aipw_scores$aipw_applicants)
})

capacity_levels_with_zero <- c(0, capacity_levels)
applicant_outcome <- mean(aipw_scores$aipw_applicants)
average_outcome_levels_combined_with_zero <- c(applicant_outcome, average_outcome_levels_combined)
average_outcome_levels_random_with_zero   <- c(applicant_outcome, average_outcome_levels_random)

plot_data <- data.frame(
  capacity = rep(capacity_levels_with_zero, 2),
  outcome  = c(average_outcome_levels_combined_with_zero, average_outcome_levels_random_with_zero),
  policy   = rep(c("Optimal", "Random"), each = length(capacity_levels_with_zero))
)

p1 <- ggplot(plot_data, aes(x = capacity, y = outcome, linetype = policy)) +
  geom_line(size = 1.2) +
  scale_linetype_manual(values = c("solid","dashed")) +
  theme_bw() +
  theme(panel.grid.minor = element_blank(),
        panel.grid.major = element_line(color="gray90"),
        panel.border = element_rect(color = "black", fill = NA, size = 1.2),
        axis.ticks = element_line(size = 1.2),
        axis.text  = element_text(size = 12),
        axis.title = element_text(size = 14),
        legend.position = "bottom",
        legend.title = element_blank(),
        legend.text  = element_text(size = 12)) +
  labs(x = "Program Capacity", y = "Average Outcome") +
  scale_x_continuous(breaks = seq(0, 0.5, by = 0.05), labels = scales::number_format(accuracy = 0.01)) +
  scale_y_continuous(labels = scales::number_format(accuracy = 0.01))
ggsave("src/replication_package/figures/optimal_vs_random_capacity.png", p1, width = 6, height = 4)

plot_data_ate <- data.frame(
  capacity = rep(capacity_levels, 2),
  ate      = c(combined_ate,
               rep(mean(c(mean(aipw_scores$aipw_mentoring - aipw_scores$aipw_applicants),
                          mean(aipw_scores$aipw_challenges - aipw_scores$aipw_applicants))), length(capacity_levels))),
  policy = rep(c("Optimal","Random"), each = length(capacity_levels))
)

p2 <- ggplot(plot_data_ate, aes(x=capacity, y=ate, linetype = policy)) +
  geom_line(size = 1.2) +
  scale_linetype_manual(values = c("solid","dashed")) +
  theme_bw() +
  theme(panel.grid.minor = element_blank(),
        panel.grid.major = element_line(color="gray90"),
        panel.border = element_rect(color = "black", fill = NA, size = 1.2),
        axis.ticks = element_line(size = 1.2),
        axis.text  = element_text(size = 12),
        axis.title = element_text(size = 14),
        legend.position = "bottom",
        legend.title = element_blank(),
        legend.text  = element_text(size = 12)) +
  labs(x = "Program Capacity", y = "Average Treatment Effect") +
  scale_x_continuous(breaks = seq(0.05, 0.5, by = 0.05), labels = scales::number_format(accuracy = 0.01)) +
  scale_y_continuous(labels = scales::number_format(accuracy = 0.01))
ggsave("src/replication_package/figures/ate_optimal_vs_random_capacity.png", p2, width = 6, height = 4)

########################################################################
## Mentoring Assignment Policies (IF-SEs; no bootstrap)
########################################################################

mentor_policy_assignment <- policy_assignment %>%
  select(subject_id, cate_mentoring) %>%
  left_join(predicted_outcomes, by = "subject_id")

# Convenience: pull per-id outcomes
get_vals <- function(ids) {
  idx <- match(as.character(ids), as.character(aipw_scores$subject_id))
  idx <- idx[!is.na(idx)]
  list(
    ATE     = aipw_scores$aipw_mentoring[idx] - aipw_scores$aipw_applicants[idx],
    Outcome = aipw_scores$aipw_mentoring[idx]
  )
}
se_mean <- function(x) if (length(x)>1) sd(x)/sqrt(length(x)) else NA_real_

n_take <- ceiling(0.25 * nrow(mentor_policy_assignment))

# Highest CATE
ids_highest_cate <- mentor_policy_assignment %>% arrange(desc(cate_mentoring)) %>%
  slice(1:n_take) %>% pull(subject_id)
v_high <- get_vals(ids_highest_cate)

# Most Promising (top by pred_applicants)
ids_most_prom <- mentor_policy_assignment %>% mutate(rank = rank(-pred_applicants)) %>%
  filter(rank <= n_take) %>% pull(subject_id)
v_most <- get_vals(ids_most_prom)

# Least Promising (bottom by pred_applicants)
ids_least_prom <- mentor_policy_assignment %>% mutate(rank = rank(pred_applicants)) %>%
  filter(rank <= n_take) %>% pull(subject_id)
v_least <- get_vals(ids_least_prom)

# Highest chances if treated (pred_mentoring + cate_mentoring)
ids_highest_ch <- mentor_policy_assignment %>%
  mutate(outcome_if_treated = pred_mentoring + cate_mentoring) %>%
  arrange(desc(outcome_if_treated)) %>% slice(1:n_take) %>% pull(subject_id)
v_ch <- get_vals(ids_highest_ch)

# Random (everyone)
ids_random <- mentor_policy_assignment %>% pull(subject_id)
v_rand <- get_vals(ids_random)

mentor_policy_summary <- data.frame(
  Policy       = c("Highest CATE","Most Promising","Least Promising","Highest Chances if Treated","Random"),
  Mean_ATE     = c(mean(v_high$ATE), mean(v_most$ATE), mean(v_least$ATE), mean(v_ch$ATE), mean(v_rand$ATE)),
  SE_ATE       = c(se_mean(v_high$ATE), se_mean(v_most$ATE), se_mean(v_least$ATE), se_mean(v_ch$ATE), se_mean(v_rand$ATE)),
  Mean_Outcome = c(mean(v_high$Outcome), mean(v_most$Outcome), mean(v_least$Outcome), mean(v_ch$Outcome), mean(v_rand$Outcome)),
  SE_Outcome   = c(se_mean(v_high$Outcome), se_mean(v_most$Outcome), se_mean(v_least$Outcome), se_mean(v_ch$Outcome), se_mean(v_rand$Outcome)),
  stringsAsFactors = FALSE
)

save(mentor_policy_summary, file = "src/replication_package/tables/policy_summary_with_se.RData")
write.csv(mentor_policy_summary, file = "src/replication_package/tables/policy_summary_with_se.csv", row.names = FALSE)

cat("\n=== Mentoring Assignment Policies (IF-SEs) ===\n")
print(mentor_policy_summary)
