remove(list = ls())

library(openai)
library(dplyr)
library(purrr)
library(tibble)
library(tidyr)
data <- read.csv("/Users/emilpalikot/Downloads/transcripts_6400_records.csv")
experiment_data <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/job_101(AI)_w_age_gender.csv")

relevant_job_applicantion_ids <- experiment_data$job_application_id[!is.na(experiment_data$is_completed)]
transcripts_relevant <- data$interview_transcript[data$job_application_id %in% relevant_job_applicantion_ids]

Sys.setenv(OPENAI_API_KEY = "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")      # or store it in .Renviron

# ------- parameters ----------------------------------------------------------
max_tokens_per_req <- 7500
model_id           <- "text-embedding-3-small"

# ---------------------------------------------------------------------------
# 1 . sanitise text so OpenAI receives valid UTF-8
sanitize <- function(x) iconv(x, from = "", to = "UTF-8", sub = "")
transcripts_clean <- vapply(transcripts_relevant, sanitize, character(1))
# ---------------------------------------------------------------------------
# 2 . batch: pack until ~7 500-token limit
token_est <- sapply(transcripts_clean, function(x) length(charToRaw(x)) / 4)
batch_id  <- floor(cumsum(token_est) / max_tokens_per_req)
batches   <- split(transcripts_clean, batch_id)
# ---------------------------------------------------------------------------
# 3 . helpers ---------------------------------------------------------------
embed_safe   <- safely(function(txt) {
  create_embedding(model = model_id, input = txt)$data$embedding[[1]]
})

embed_batch  <- function(vec) {
  res <- try(
    create_embedding(model = model_id, input = vec),
    silent = TRUE
  )
  if (!inherits(res, "try-error")) {
    return(res$data$embedding)          # happy path: full list
  }
  # batch failed → fall back to item-by-item
  message("Batch failed; retrying items individually …")
  out <- map(vec, ~ embed_safe(.x)$result)
  # any NULLs (still failing) turn into NA placeholders
  map(out, ~ if (is.null(.x)) NA else .x)
}
# ---------------------------------------------------------------------------
# 4 . run through all batches -----------------------------------------------
embeds_relevant <- vector("list", length(transcripts_clean))
start_idx <- 1

# Print once, up front
cat("Total number of batches:", length(batches), "\n")

for (i in seq_along(batches)) {
  b <- batches[[i]]

  cat(sprintf("Processing batch %d of %d\n", i, length(batches)))

  vecs <- embed_batch(b)

  end_idx <- start_idx + length(b) - 1
  embeds_relevant[start_idx:end_idx] <- vecs
  start_idx <- end_idx + 1           # <-- still tracks row position, not batch #
}


saveRDS(embeds_relevant, "data/embeds_relevant.rds")

# Match emebds_relevant to job_application_id
# Load embeds_relevant
embeds_relevant <- readRDS("data/embeds_relevant.rds")


dim_emb <- length(embeds_relevant[[ which(map_lgl(embeds_relevant, is.numeric))[1] ]])


embeds_filled <- map(
  embeds_relevant,
  ~ if (is.numeric(.x)) .x            # good embedding → keep as is
    else rep(NA_real_, dim_emb)       # failed → pad with NA vector
)
embeds_df <- tibble(
  doc_id   = paste0("doc_", seq_along(embeds_filled)),
  embedding = embeds_filled            # list-column (one vector per row)
)
print(embeds_df, n = 3)

embeds_wide <- embeds_df |>
  unnest_wider(embedding, names_sep = "_")    # needs tidyr ≥ 1.3

# Match emebds_relevant to job_application_id
application_ids <- data$job_application_id[data$job_application_id %in% relevant_job_applicantion_ids]

embeds_dataframe <- data.frame(
  job_application_id = application_ids,
  embeds_relevant = embeds_wide
)

write.csv(embeds_dataframe, "data/embeds_dataframe.csv", row.names = FALSE)
