# ---------------------------------------------------------------------------
# 0.  libraries --------------------------------------------------------------
library(dplyr)
library(dbscan)        # HDBSCAN
library(uwot)          # UMAP
library(cluster)       # silhouette()
library(factoextra)    # elbow, silhouette plots
library(ggplot2)
library(tidyr)         # unnest_wider (if you need it elsewhere)
library(stargazer)
library(wordcloud2)
library(tidytext)
library(tidyverse)
library(openai) 
# ---------------------------------------------------------------------------
# 1.  read the wide CSV -------------------------------------------------------
embeds_dataframe <- read.csv("data/embeds_dataframe.csv",
                             stringsAsFactors = FALSE)

emb_cols <- grep("^embeds_relevant\\.embedding_", names(embeds_dataframe),
                 value = TRUE)

embed_mat <- embeds_dataframe[emb_cols] |>
  mutate(across(everything(), as.numeric)) |>
  as.matrix()

id_vec  <- embeds_dataframe$job_application_id
is_good <- rowSums(is.na(embed_mat)) == 0
good_mat <- embed_mat[is_good, , drop = FALSE]

cat(sum(!is_good), "rows had NA in at least one dimension and keep NA labels\n")

# ---------------------------------------------------------------------------
# 2.  PCA – keep ≥ 90 % cumulative variance ----------------------------------
# 2a.  run a *full-rank* PCA once
pca_full <- prcomp(good_mat, center = TRUE, scale. = TRUE)

# 2b.  find the first PC index whose cumulative variance ≥ 0.95
eigvals       <- pca_full$sdev^2
cum_explained <- cumsum(eigvals / sum(eigvals))
rank_pca      <- which(cum_explained >= 0.95)[1]          # guarantees ≥ 90 %

cat(sprintf("Retaining %d PCs (%.2f %% variance)\n",
            rank_pca, cum_explained[rank_pca] * 100))

# 2c.  project data onto those PCs
mat_pca <- pca_full$x[, 1:rank_pca, drop = FALSE]

df_var <- data.frame(
  PC  = seq_along(eigvals),
  Prop = eigvals / sum(eigvals),
  Cum  = cum_explained
)

ggplot(df_var, aes(PC, Prop)) +
  geom_col(fill = "grey70") +
  geom_line(aes(y = Cum), colour = "steelblue", size = 1) +
  geom_point(aes(y = Cum), colour = "steelblue") +
  geom_vline(xintercept = rank_pca, linetype = "dashed", colour = "red") +
  annotate("text", x = rank_pca, y = 0,
           label = paste0(rank_pca, " PCs\n(", round(cum_explained[rank_pca]*100,1)," %)"),
           vjust = -0.5, hjust = -0.1, colour = "red") +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
  labs(title = "Scree & cumulative variance (red line = 90 %)",
       y = "Variance explained", x = "Principal component") +
  theme_minimal()


# Start wiht the clusters
set.seed(42)
mat_umap <- umap(mat_pca, n_neighbors = 30, min_dist = 0.1,
                 metric = "cosine")

# ---------------------------------------------------------------------------
# 3.  k-means  ---------------------------------------------------------------
fviz_nbclust(mat_pca, kmeans, method = "wss")          # elbow plot
fviz_nbclust(mat_pca, kmeans, method = "silhouette")   # silhouette plot

k_opt <- 8        # <-- pick from the plots
km    <- kmeans(mat_pca, centers = k_opt, nstart = 30)

sil_km <- silhouette(km$cluster, dist(mat_pca))
cat(sprintf("k-means (k = %d) mean silhouette: %.3f\n",
            k_opt, mean(sil_km[, 'sil_width'])))

# ---------------------------------------------------------------------------
# 4.  hierarchical (Ward) clustering  ----------------------------------------
# cosine distance on PCA scores
cosine_dist <- function(x) {
  x <- x / sqrt(rowSums(x * x))
  as.dist(1 - tcrossprod(x))
}
dmat <- cosine_dist(mat_pca)

fviz_nbclust(mat_pca, FUN = hcut, method = "silhouette")  # helper

k_hc <- 10          # <-- choose (8-15 typical)
hc   <- hclust(dmat, method = "ward.D2")
hc_labels <- cutree(hc, k = k_hc)

sil_hc <- silhouette(hc_labels, dmat)
cat(sprintf("Hierarchical (k = %d) mean silhouette: %.3f\n",
            k_hc, mean(sil_hc[, 'sil_width'])))

# ---------------------------------------------------------------------------
# 5.  (optional) HDBSCAN for comparison  -------------------------------------
minPts_hdb <- 7
hdb <- hdbscan(mat_umap, minPts = minPts_hdb)
cat("HDBSCAN produced",
    length(unique(hdb$cluster[hdb$cluster > 0])),
    "clusters (minPts =", minPts_hdb, ")\n")

# ---------------------------------------------------------------------------
# 6.  attach labels back to **all** rows -------------------------------------
km_all  <- rep(NA_integer_, length(id_vec))
hc_all  <- rep(NA_integer_, length(id_vec))
hdb_all <- rep(NA_integer_, length(id_vec))

km_all [is_good] <- km$cluster
hc_all [is_good] <- hc_labels
hdb_all[is_good] <- hdb$cluster

cluster_table <- tibble(
  job_application_id = id_vec,
  has_embedding      = is_good,
  km_cluster         = km_all,
  hc_cluster         = hc_all,
  hdb_cluster        = hdb_all
)

write.csv(cluster_table,
          "embedding_clusters_with_ids.csv",
          row.names = FALSE)

# ---------------------------------------------------------------------------
# 7.  quick visual (optional)  ----------------------------------------------
plot_df <- as.data.frame(mat_umap) |>
  mutate(km  = factor(km$cluster),
         hc  = factor(hc_labels),
         hdb = factor(hdb$cluster))

ggplot(plot_df, aes(V1, V2, colour = km)) +
  geom_point(size = 1, alpha = 0.8) +
  scale_colour_viridis_d(option = "plasma") +
  labs(title = sprintf("k-means (k = %d) – UMAP view", k_opt),
       colour = "cluster") +
  theme_minimal()

ggplot(plot_df, aes(V1, V2, colour = hc)) +
  geom_point(size = 1, alpha = 0.8) +
  scale_colour_viridis_d(option = "turbo") +
  labs(title = sprintf("Hierarchical (k = %d) – UMAP view", k_hc),
       colour = "cluster") +
  theme_minimal()

####################### Match to the experiment data ------------------------

treatment_group <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Ai-Vetted-ranked.csv")

# Create new columns for each technology
treatment_group <- treatment_group %>%
  mutate(
    React = str_extract(ai_vetting_results, "React\\s*:\\s*(\\w+(?:-\\w+)?)"),
    JavaScript = str_extract(ai_vetting_results, "JavaScript\\s*:\\s*(\\w+(?:-\\w+)?)"),
    CSS = str_extract(ai_vetting_results, "HTML,\\s*CSS\\s*:\\s*(\\w+(?:-\\w+)?)")
  )

# Clean up the extracted values to remove the "Technology:" part
treatment_group <- treatment_group %>%
  mutate(
    React = str_replace(React, "React\\s*:\\s*", ""),
    JavaScript = str_replace(JavaScript, "JavaScript\\s*:\\s*", ""),
    CSS = str_replace(CSS, "HTML,\\s*CSS\\s*:\\s*", "")
  )


treatment_group$AI_score <- ifelse(treatment_group$React == "Senior", 3, ifelse(treatment_group$React == "Mid-level", 2, ifelse(treatment_group$React == "Junior", 1, 0))) + 
  ifelse(treatment_group$JavaScript == "Senior", 3, ifelse(treatment_group$JavaScript == "Mid-level", 2, ifelse(treatment_group$JavaScript == "Junior", 1, 0))) + 
  ifelse(treatment_group$CSS == "Senior", 3, ifelse(treatment_group$CSS == "Mid-level", 2, ifelse(treatment_group$CSS == "Junior", 1, 0)))



analysis_data <- treatment_group %>% select(job_application_id, email_id, is_completed, is_passed, resume_score, AI_score) %>% filter(is_completed == 1) %>% mutate(resume_score = as.numeric(resume_score)) 

analysis_data <- analysis_data %>% left_join(cluster_table, by = "job_application_id")%>% filter(!is.na(km_cluster))

analysis_data$passed <- ifelse(analysis_data$is_passed == TRUE, 1, 0)
# Make cluster 1 the reference level for both clustering methods
analysis_data$hc_cluster <- relevel(as.factor(analysis_data$hc_cluster), ref = "1")
analysis_data$km_cluster <- relevel(as.factor(analysis_data$km_cluster), ref = "1")


summary(type_1 <- glm(passed ~ hc_cluster + resume_score, data = analysis_data, family = "binomial"))

summary(type_2 <- glm(passed ~ km_cluster + resume_score, data = analysis_data, family = "binomial"))

stargazer(type_1, type_2, type = "text",
          title = "Logistic Regression Results",
          covariate.labels = c("Intercept", "Hierarchical Cluster 2",
                              "Hierarchical Cluster 3", "Hierarchical Cluster 4",
                              "Hierarchical Cluster 5", "Hierarchical Cluster 6",
                              "Hierarchical Cluster 7", "Hierarchical Cluster 8",
                              "Resume Score"),
          out = "logistic_regression_results.txt")


# Make cluster 1 the reference level for both clustering methods
analysis_data$hc_cluster <- relevel(as.factor(analysis_data$hc_cluster), ref = "1")
analysis_data$km_cluster <- relevel(as.factor(analysis_data$km_cluster), ref = "1")

summary(type_3 <- lm(AI_score ~  km_cluster + resume_score, data = analysis_data))

stargazer(type_2,type_3, type = "text")


# Bar plot with AI score by cluster
# Calculate mean and standard error by cluster
cluster_summary <- analysis_data %>%
  group_by(km_cluster) %>%
  summarise(
    mean_score = mean(AI_score, na.rm = TRUE),
    se = sd(AI_score, na.rm = TRUE) / sqrt(n())
  )

# Create bar plot with error bars
ggplot(cluster_summary, aes(x = km_cluster, y = mean_score)) +
  geom_bar(stat = "identity", fill = "steelblue", width = 0.7, alpha = 0.8) +
  geom_errorbar(aes(ymin = mean_score - se, ymax = mean_score + se), 
                width = 0.2, color = "black", linewidth = 0.5) +
  theme_minimal(base_size = 14) +
  theme(
    axis.title = element_text(face = "bold", size = 16),
    axis.text = element_text(size = 14),
    plot.title = element_text(face = "bold", size = 18, hjust = 0.5),
    panel.grid.major.y = element_line(color = "gray90"),
    panel.grid.minor = element_blank(),
    panel.border = element_rect(fill = NA, color = "gray80", linewidth = 0.5)
  ) +
  labs(title = "Mean AI Score by Cluster",
       x = "Cluster",
       y = "AI Score",
       caption = "Note: Error bars represent standard errors") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1)))

# Save the bar plot to the figures directory
ggsave(
  filename = file.path(figures_dir, "ai_score_by_cluster.png"),
  width = 10,
  height = 7,
  dpi = 300
)





###### Wordclouds
# Get the transcriptsq
data <- read.csv("/Users/emilpalikot/Downloads/transcripts_6400_records.csv")
experiment_data <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/job_101(AI)_w_age_gender.csv")

relevant_job_applicantion_ids <- experiment_data$job_application_id[!is.na(experiment_data$is_completed)]
transcripts_relevant <- data$interview_transcript[data$job_application_id %in% relevant_job_applicantion_ids]

analysis_df <- tibble(
  job_application_id    = cluster_table$job_application_id,
  km_cluster            = cluster_table$km_cluster,
  hc_cluster            = cluster_table$hc_cluster,
  text                  = transcripts_relevant               # <- cleaned text
) %>% 
  filter(!is.na(km_cluster))

  # remotes::install_github("ropensci/openai")
Sys.setenv(OPENAI_API_KEY = "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")      # or store it in .Renviron

model_name <- "gpt-4o"      # or "gpt-4-turbo-preview"
# ── helper to clean + truncate one transcript --------------------------------


# ────────────────────────────────────────────────────────────────────────────
#  CLEAN-AND-TRUNCATE HELPERS
#  – strip bad bytes  → always valid UTF-8
#  – truncate to keep prompts short
# ────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────
#  SANITISE + TRUNCATE HELPERS
# ────────────────────────────────────────────────────────────────────────────
safe_utf8  <- function(x) iconv(x, from = "", to = "UTF-8", sub = "")
safe_trunc <- function(txt, max_chars = 1200) substr(safe_utf8(txt), 1, max_chars)
token_est  <- function(x) nchar(safe_utf8(x), type = "bytes") / 4   # ≈ tokens

# ────────────────────────────────────────────────────────────────────────────
#  PAIR-WISE COMPARISON  (baseline vs target)  ───────────────────────────────
# ────────────────────────────────────────────────────────────────────────────
compare_pair <- function(baseline_id,
                         target_id,
                         max_examples      = 30,          # upper bound per cluster
                         clus_var          = "km_cluster",
                         model_name        = "gpt-4o-mini",
                         max_chars_per_doc = 1200,
                         max_prompt_tokens = 35000) {
  
  # helper: sample + clean one cluster --------------------------------------
  sample_cluster <- function(cid, n) {
    df <- analysis_df %>% dplyr::filter(!!sym(clus_var) == cid)
    if (nrow(df) == 0) return(NULL)
    df <- dplyr::slice_sample(df, n = min(n, nrow(df)))
    df$text <- vapply(df$text, safe_trunc, character(1),
                      max_chars = max_chars_per_doc)
    df$cluster_id <- cid
    df
  }
  
  # start with max_examples each, reduce later if needed --------------------
  n_base   <- max_examples
  n_target <- max_examples
  
  build_prompt <- function(base_df, targ_df) {
    paste(
      "You are an interviewing-skills analyst.",
      "Below are interview excerpts from two clusters of candidates. First, remove questions asked by the interviewer. Then, write EXACTLY four bullets *per cluster* beginning with",
      "'Compared to the other cluster, candidates in Cluster X …'",
      "Cover technical and non-technical differences (positive & negative). Make sure to have at least one point that covers the non-technical aspects such as hesitation, structure of thoughts, and communication skills. This is a very important task, so please be very careful and precise. Candidates are applying for the same jobs as a junior software engineer.",
      "",
      "### CLUSTER ", baseline_id, " ###\n",
      paste0(purrr::imap_chr(base_df$text,
               ~ paste0('-- Example ', .y, ' --\n', .x)), collapse = "\n\n"),
      "\n\n### CLUSTER ", target_id, " ###\n",
      paste0(purrr::imap_chr(targ_df$text,
               ~ paste0('-- Example ', .y, ' --\n', .x)), collapse = "\n\n")
    )
  }
  
  repeat {
    df_base <- sample_cluster(baseline_id, n_base)
    df_targ <- sample_cluster(target_id,  n_target)
    if (is.null(df_base) || is.null(df_targ))
      return(NA_character_)                                # one cluster empty
    
    prompt  <- safe_utf8(build_prompt(df_base, df_targ))
    
    if (token_est(prompt) <= max_prompt_tokens || (n_base == 1 && n_target == 1))
      break                                                # fits budget
    
    # trim evenly: drop one example from the larger sample first ------------
    if (n_base >= n_target && n_base > 1) n_base <- n_base - 1
    else if (n_target > 1)                n_target <- n_target - 1
  }
  
  # call model --------------------------------------------------------------
  res <- tryCatch(
    openai::create_chat_completion(
      model    = model_name,
      messages = list(
        list(role = "system", content = "You are a helpful data analyst."),
        list(role = "user",   content = prompt)
      ),
      temperature = 0.2
    ),
    error = function(e) e$message
  )
  
  if (!is.list(res)) {
    warning(sprintf("OpenAI error (%s vs %s): %s", baseline_id, target_id, res))
    return(NA_character_)
  }
  if (is.data.frame(res$choices)) res$choices$message.content[1]
  else                            res$choices[[1]]$message$content
}

# ────────────────────────────────────────────────────────────────────────────
#  RUN: baseline vs every other cluster  -------------------------------------
baseline <- 1            # change to any cluster you like

summary_tbl <- purrr::map_dfr(
  setdiff(unique(analysis_df$km_cluster), baseline),
  ~ tibble::tibble(
      comparison = paste(baseline, .x, sep = "_vs_"),
      summary    = compare_pair(
                     baseline_id   = baseline,
                     target_id     = .x,
                     max_examples  = 30,        # stays the same
                     clus_var      = "km_cluster",
                     model_name    = model_name # ← here
                   )
    )
)
write.csv(summary_tbl, "data/cluster_pairwise_differences.csv", row.names = FALSE)



# Get the final interview data
final_interview <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/top_candidates_interviewed.csv")

final_analysis <- treatment_group %>% select(job_application_id, email_id, is_completed, is_passed, resume_score) %>% filter(is_completed == 1) %>% mutate(resume_score = as.numeric(resume_score))

final_analysis <- final_analysis %>% left_join(cluster_table, by = "job_application_id") 

final_interview <- final_interview %>% left_join(final_analysis, by = "email_id") 

final_interview$passed <- ifelse(final_interview$Result == "Pass", 1, 0)

final_interview$hc_cluster <- relevel(as.factor(final_interview$hc_cluster), ref = "1")
final_interview$km_cluster <- relevel(as.factor(final_interview$km_cluster), ref = "1")

final_interview <- final_interview %>% filter(!is.na(hc_cluster))

summary(type_1 <- glm(passed ~ hc_cluster + resume_score, data = final_interview, family = "binomial"))

summary(type_2 <- glm(passed ~ km_cluster + resume_score, data = final_interview, family = "binomial"))

stargazer(type_1, type_2, type = "text",
          title = "Logistic Regression Results",
          covariate.labels = c("Intercept", "Hierarchical Cluster 2",
                              "Hierarchical Cluster 3", "Hierarchical Cluster 4",
                              "Hierarchical Cluster 5", "Hierarchical Cluster 6",
                              "Hierarchical Cluster 7", "Hierarchical Cluster 8",   
                              "Resume Score"),
          out = "logistic_regression_results.txt")





