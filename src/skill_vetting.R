# there are two ways of looking at this: (1) first we have people whose resumes we vetted and checked that they claim to have these skills; (2) someone, applying that requires a specific skill, but then they during the AI interview it turns out they don't have that skill.

# (1)

rm(list = ls())

library(dplyr)
library(stringr)
library(knitr)
library(kableExtra)
library(scales) 
library(sandwich)
library(lmtest)
library(stargazer)
# Load the data
data <- read.csv("data/skill_vetting.csv")

## Share of candidates with 3 vetted skills 

data <- data %>% 
  mutate(
    three_vetted_skills = ifelse(total_vetted_skills == 3, 1, 0)
  )

mean(data$three_vetted_skills,na.rm = TRUE)
mean(data$total_resume_skills,na.rm = TRUE)


# Count the number of not experienced skills:list

data <- data %>% 
  mutate(
    n_not_experienced = str_count(non_experienced_skills, "not experienced"),
    n_not_experienced = ifelse(is.na(n_not_experienced), 0, n_not_experienced),
    n_not_experienced = ifelse(n_not_experienced > 3, 3, n_not_experienced)
  )

summary(data$n_not_experienced)
summary(data$total_vetted_skills)

# Share not experienced skills

data <- data %>% 
  mutate(
    one_or_more_not_experienced = ifelse(n_not_experienced > 0, 1, 0),
    two_or_more_not_experienced = ifelse(n_not_experienced > 1, 1, 0),
    three_or_more_not_experienced = ifelse(n_not_experienced > 2, 1, 0)
  )

n_applicants <- dim(data)[1]


mean_1_or_more_not_experienced <- mean(data$one_or_more_not_experienced)
mean_2_or_more_not_experienced <- mean(data$two_or_more_not_experienced)
mean_3_or_more_not_experienced <- mean(data$three_or_more_not_experienced)

se_1_or_more_not_experienced <- sqrt(mean_1_or_more_not_experienced * (1 - mean_1_or_more_not_experienced) / n_applicants)
se_2_or_more_not_experienced <- sqrt(mean_2_or_more_not_experienced * (1 - mean_2_or_more_not_experienced) / n_applicants)
se_3_or_more_not_experienced <- sqrt(mean_3_or_more_not_experienced * (1 - mean_3_or_more_not_experienced) / n_applicants)


#(2)

# Load the data
treatment_group <- read.csv("/Users/emilpalikot/Research/AI-Recruiter/Ai-Vetted-ranked.csv")

treatment_group$completed <- ifelse(treatment_group$is_completed == 1, 1, 0)
treatment_group$completed <- ifelse(is.na(treatment_group$is_completed), 0, treatment_group$completed)


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


analysis_data <- treatment_group %>% filter(completed == 1) %>% mutate(
  one_or_more_not_experienced = ifelse(React == "Not" | JavaScript == "Not" | CSS == "Not", 1, 0),
  two_or_more_not_experienced = ifelse(React == "Not" & JavaScript == "Not" | React == "Not" & CSS == "Not" | JavaScript == "Not" & CSS == "Not", 1, 0),
  three_or_more_not_experienced = ifelse(React == "Not" & JavaScript == "Not" & CSS == "Not", 1, 0)
)

n_applicants <- dim(analysis_data)[1]
summary(analysis_data$one_or_more_not_experienced)

mean_1_or_more_not_experienced_2 <- mean(analysis_data$one_or_more_not_experienced,na.rm = TRUE)
mean_2_or_more_not_experienced_2 <- mean(analysis_data$two_or_more_not_experienced,na.rm = TRUE)
mean_3_or_more_not_experienced_2 <- mean(analysis_data$three_or_more_not_experienced,na.rm = TRUE)

se_1_or_more_not_experienced_2 <- sqrt(mean_1_or_more_not_experienced_2 * (1 - mean_1_or_more_not_experienced_2) / n_applicants)
se_2_or_more_not_experienced_2 <- sqrt(mean_2_or_more_not_experienced_2 * (1 - mean_2_or_more_not_experienced_2 ) / n_applicants)
se_3_or_more_not_experienced_2 <- sqrt(mean_3_or_more_not_experienced_2 * (1 - mean_3_or_more_not_experienced_2) / n_applicants)

########################################################
## Create a professional table for academic paper     ##
########################################################



# Create a data frame for the first analysis
analysis_1 <- data.frame(
  Metric = c("One or more skills not experienced", 
             "Two or more skills not experienced", 
             "Three skills not experienced"),
  Proportion = c(mean_1_or_more_not_experienced, 
                 mean_2_or_more_not_experienced, 
                 mean_3_or_more_not_experienced),
  SE = c(se_1_or_more_not_experienced, 
         se_2_or_more_not_experienced, 
         se_3_or_more_not_experienced)
)

# Create a data frame for the second analysis
     <- data.frame(
  Metric = c("One or more skills not experienced", 
             "Two or more skills not experienced", 
             "Three skills not experienced"),
  Proportion = c(mean_1_or_more_not_experienced_2, 
                 mean_2_or_more_not_experienced_2, 
                 mean_3_or_more_not_experienced_2),
  SE = c(se_1_or_more_not_experienced_2, 
         se_2_or_more_not_experienced_2, 
         se_3_or_more_not_experienced_2)
)

# Combine the analyses into a single table
combined_table <- data.frame(
  Metric = analysis_1$Metric,
  Prop_Analysis1 = analysis_1$Proportion,
  SE_Analysis1 = analysis_1$SE,
  Prop_Analysis2 = analysis_2$Proportion,
  SE_Analysis2 = analysis_2$SE
)

# Format the table with proper column names
formatted_table <- combined_table %>%
  mutate(
    Prop_Analysis1 = sprintf("%.3f", Prop_Analysis1),
    SE_Analysis1 = sprintf("(%.3f)", SE_Analysis1),
    Prop_Analysis2 = sprintf("%.3f", Prop_Analysis2),
    SE_Analysis2 = sprintf("(%.3f)", SE_Analysis2)
  )



# For LaTeX output (if needed for academic papers)
latex_table <- kable(formatted_table, 
      format = "latex",
      col.names = c("Skill Deficiency Metric", 
                    "Proportion", "SE", 
                    "Proportion", "SE"),
      align = c("l", "c", "c", "c", "c"),
      caption = "Proportion of Candidates with Skill Deficiencies",
      booktabs = TRUE) %>%
  kable_styling(latex_options = c("hold_position"),
                full_width = FALSE) %>%
  add_header_above(c(" " = 1, 
                     "First Analysis" = 2, 
                     "Second Analysis" = 2)) %>%
  footnote(general = "Note: Standard errors in parentheses.",
           threeparttable = TRUE)

# Write LaTeX table to file
cat(latex_table, file = "src/figures/skill_vetting_table.tex")

######################################################## Heterogeneity analysis ########################################################

data_hte <- analysis_data %>%               
  mutate(
    resume_score       = as.numeric(resume_score),
    high_resume_rating = if_else(
      resume_score > mean(resume_score, na.rm = TRUE), "Above Mean", "Below Mean")
  ) %>% filter(is.na(resume_score) == FALSE)




# Join gender & age (trim whitespace in gender)
gender_data <- read.csv(
  "/Users/emilpalikot/Research/AI-Recruiter/micro1-controll-experiment-EDA/job_101(AI)_w_age_gender.csv"
) %>% 
  select(job_application_id, gender, age) %>% 
  mutate(gender = str_trim(gender))

data_hte <- data_hte %>% 
  left_join(gender_data, by = "job_application_id") %>% 
  mutate(
    age_plus        = if_else(age  > mean(age,  na.rm = TRUE), "Older",  "Younger"),
    years_of_exp    = as.numeric(years_of_exp),
    experience_plus = if_else(years_of_exp > mean(years_of_exp, na.rm = TRUE),
                              "Above Mean", "Below Mean")
  ) %>% filter(is.na(experience_plus) == FALSE)

data_hte <- data_hte %>% filter(is.na(age_plus) == FALSE) %>% filter(is.na(one_or_more_not_experienced) == FALSE) %>% filter(is.na(two_or_more_not_experienced) == FALSE) %>% filter(is.na(three_or_more_not_experienced) == FALSE)

# --------------------------------------------------------------
# 2. Helper: summarise one subgroup and pivot long
# --------------------------------------------------------------
summarise_misreport <- function(df, group_var, subgroup_name) {
  df %>% 
    group_by({{ group_var }}) %>% 
    summarise(across(
      c(one_or_more_not_experienced,
        two_or_more_not_experienced,
        three_or_more_not_experienced),
      ~ mean(.x, na.rm = TRUE),
      .names = "{.col}"
    ), .groups = "drop") %>% 
    pivot_longer(
      cols      = starts_with(c("one", "two", "three")),
      names_to  = "deficiency_metric",
      values_to = "share"
    ) %>% 
    mutate(
      subgroup = subgroup_name,
      level    = as.character({{ group_var }})
    )
}

# --------------------------------------------------------------
# 3. Build one tidy table for all subgroups
# --------------------------------------------------------------
# Modify the summarise_misreport function to include standard errors
summarise_misreport <- function(df, group_var, subgroup_name) {
  df %>% 
    group_by({{ group_var }}) %>% 
    summarise(across(
      c(one_or_more_not_experienced,
        two_or_more_not_experienced,
        three_or_more_not_experienced),
      list(
        mean = ~ mean(.x, na.rm = TRUE),
        se = ~ sqrt(mean(.x, na.rm = TRUE) * (1 - mean(.x, na.rm = TRUE)) / n())
      ),
      .names = "{.col}_{.fn}"
    ), .groups = "drop") %>% 
    pivot_longer(
      cols      = starts_with(c("one", "two", "three")),
      names_to  = c("deficiency_metric", ".value"),
      names_pattern = "(.+)_(.+)"
    ) %>% 
    mutate(
      subgroup = subgroup_name,
      level    = as.character({{ group_var }})
    )
}

# --------------------------------------------------------------
# 3. Build one tidy table for all subgroups
# --------------------------------------------------------------
summary_long <- bind_rows(
  summarise_misreport(data_hte, high_resume_rating, "Resume rating"),
  summarise_misreport(data_hte, gender,            "Gender"),
  summarise_misreport(data_hte, age_plus,          "Age"),
  summarise_misreport(data_hte, experience_plus,   "Experience")
) %>% 
  mutate(                                             # cleaner labels & order
    deficiency_metric = recode(deficiency_metric,
      one_or_more_not_experienced   = "≥1 skill",
      two_or_more_not_experienced   = "≥2 skills",
      three_or_more_not_experienced = "3 skills"
    ),
    deficiency_metric = factor(deficiency_metric,
      levels = c("≥1 skill", "≥2 skills", "3 skills"))
  )

# named vector: label = column that defines the subgroup
subgroups <- c(
  "Resume rating" = "high_resume_rating",
  "Gender"        = "gender",
  "Age"           = "age_plus",
  "Experience"    = "experience_plus"
)

p_values <- imap_dfr(subgroups, function(var, label) {

  tmp <- data_hte %>% filter(!is.na(.data[[var]]))

  g <- factor(tmp[[var]])               # ensure factor
  stopifnot(nlevels(g) == 2)            # fail fast if not binary

  tibble(
    subgroup          = label,
    deficiency_metric = c("≥1 skill","≥2 skills","3 skills"),
    p_value = c(
      t.test(one_or_more_not_experienced   ~ g, data = tmp)$p.value,
      t.test(two_or_more_not_experienced   ~ g, data = tmp)$p.value,
      t.test(three_or_more_not_experienced ~ g, data = tmp)$p.value
    )
  )
})


# Convert p-values to significance stars
p_values$p_value <- case_when(
  p_values$p_value < 0.001 ~ "***",
  p_values$p_value < 0.01  ~ "**",
  p_values$p_value < 0.05  ~ "*",
  p_values$p_value < 0.1   ~ "†",
  TRUE                     ~ "ns"
)
# Join p-values with summary data
plot_data <- summary_long %>%
  group_by(subgroup, deficiency_metric) %>%
  mutate(
    y_max = max(mean + 1.96*se),
    y_pos = y_max + 0.01  # Reduced space between bars and significance stars
  ) %>%
  left_join(p_values, by = c("subgroup", "deficiency_metric"))

# Create the plot with p-values
ggplot(plot_data,
       aes(x = deficiency_metric, y = mean, fill = level)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_errorbar(
    aes(ymin = mean - 1.96*se, ymax = mean + 1.96*se),
    position = position_dodge(width = 0.7),
    width = 0.2
  ) +
  # Add p-value text closer to the bars
  geom_text(
    aes(y = y_pos, label = p_value),
    position = position_dodge(width = 0),
    size = 3.5,
    vjust = 0  # Adjust vertical position to be closer to bars
  ) +
  facet_wrap(~ subgroup, nrow = 2) +
  scale_y_continuous(
    labels = scales::percent_format(accuracy = 1),
    expand = expansion(mult = c(0, 0.1))  # Reduced top expansion to bring stars closer
  ) +
  scale_fill_brewer(
    palette = "Set2",
    name = NULL
  ) +
  labs(
    x = "The number of misreported skills",
    y = "Share of candidates"
  ) +
  theme_bw(base_size = 18) +
  theme(
    panel.grid.major.x = element_blank(),
    panel.grid.minor   = element_blank(),
    legend.position    = "bottom",
    strip.background   = element_rect(fill = "white", color = "gray80"),
    strip.text         = element_text(face = "bold", size = 14),
    axis.title         = element_text(size = 18, face = "bold"),
    axis.text          = element_text(size = 18),
    legend.text        = element_text(size = 18),
    plot.title         = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.caption       = element_text(size = 14, hjust = 0),
    plot.margin        = unit(c(1, 1, 1, 1), "cm")
  )

ggsave("src/figures/skill_vetting_hte.png", width = 14, height = 8, dpi = 300)


######################################################## Income analysis ########################################################

data_country <- data_hte %>% select(country_code) %>% distinct() 

write.csv(data_country, file = "data/data_country.csv", row.names = FALSE)
# Define rich and poor countries
rich_countries <- c(
  "US","CA","GB","DE","AE","ES","PL","RO","IL","AU","FR","IT","SA","SE",
  "IE","PT","CL","NL","SG","FI","BG","GR","UY","HU","HR","NZ","QA","BE",
  "CH","LT","NO","EE","RU","AT","DK","SK","KR","OM","TW"
)

poor_countries <- c(
  "IN","PK","NG","EG","BD","BR","TR","PH","AR","KE","ZA","CO","LK","ID",
  "MA","MX","LB","ET","TN","UA","NP","GH","AL","VE","XK","IR","CR","EC",
  "PE","MY","DO","DZ","GE","AM","MK","RW","CM","AZ","UG","VN","TH","BA",
  "PS","IQ","ZW","NI","SN","UZ","BO","CI","SY","MG","SV","BJ","MM","TZ",
  "BY","JO","RS"
)

# Create a new variable for country income group
data_hte <- data_hte %>% mutate(
  income_group = ifelse(country_code %in% rich_countries, "Rich", "Poor")
)

data_hte <- data_hte %>% filter(is.na(income_group) == FALSE)

# Calculate means by income group and create a summary dataframe
income_summary <- data_hte %>% 
  group_by(income_group) %>% 
  summarize(
    mean_one_or_more_not_experienced = mean(one_or_more_not_experienced, na.rm = TRUE),
    mean_two_or_more_not_experienced = mean(two_or_more_not_experienced, na.rm = TRUE),
    mean_three_or_more_not_experienced = mean(three_or_more_not_experienced, na.rm = TRUE)
  ) %>% 
  ungroup()

# Convert to long format for plotting
income_summary_long <- income_summary %>%
  pivot_longer(
    cols = starts_with("mean_"),
    names_to = "metric",
    values_to = "value"
  ) %>%
  mutate(
    metric = case_when(
      metric == "mean_one_or_more_not_experienced" ~ "≥1 skill",
      metric == "mean_two_or_more_not_experienced" ~ "≥2 skills",
      metric == "mean_three_or_more_not_experienced" ~ "3 skills",
      TRUE ~ metric
    ),
    metric = factor(metric, levels = c("≥1 skill", "≥2 skills", "3 skills"))
  )

# Create bar plot
ggplot(income_summary_long, aes(x = income_group, y = value, fill = metric)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.9), width = 0.8) +
  geom_text(aes(label = scales::percent(value, accuracy = 0.1)), 
            position = position_dodge(width = 0.9), 
            vjust = -0.5, 
            size = 4) +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
  scale_fill_brewer(palette = "Set1", name = "Misreported skills") +
  labs(
    title = "Skill Misreporting by Country Income Group",
    x = "Country Income Group",
    y = "Share of candidates misreporting skills"
  ) +
  theme_bw(base_size = 14) +
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_blank()
  )

gdp_data <- read.csv("data/country_code_gdp_per_capita.csv")

data_hte_gdp <- data_hte %>% left_join(gdp_data, by = "country_code")
data_hte_gdp <- data_hte_gdp %>% filter(is.na(gdp_per_capita) == FALSE)


# Create a list to store models and results
models <- list()
dependent_vars <- c("one_or_more_not_experienced", "two_or_more_not_experienced", "three_or_more_not_experienced")
model_names <- c("≥1 skill", "≥2 skills", "3 skills")



data_hte_gdp$gdp_per_capita <- data_hte_gdp$gdp_per_capita/1000

# Run regressions with clustered standard errors at the country level
# Run the regressions with clustered standard errors
ols_one_skill <- lm(one_or_more_not_experienced ~ gdp_per_capita, data = data_hte_gdp)
ols_one_skill_vcov <- vcovCL(ols_one_skill, cluster = data_hte_gdp$country_code)
ols_one_skill_coef <- coeftest(ols_one_skill, vcov = ols_one_skill_vcov)

ols_two_skill <- lm(two_or_more_not_experienced ~ gdp_per_capita, data = data_hte_gdp)
ols_two_skill_vcov <- vcovCL(ols_two_skill, cluster = data_hte_gdp$country_code)
ols_two_skill_coef <- coeftest(ols_two_skill, vcov = ols_two_skill_vcov)

ols_three_skill <- lm(three_or_more_not_experienced ~ gdp_per_capita, data = data_hte_gdp)
ols_three_skill_vcov <- vcovCL(ols_three_skill, cluster = data_hte_gdp$country_code)
ols_three_skill_coef <- coeftest(ols_three_skill, vcov = ols_three_skill_vcov)

# Create a stargazer table with the regression results
stargazer(ols_one_skill, ols_two_skill, ols_three_skill, 
          type = "latex",
          se = list(sqrt(diag(ols_one_skill_vcov)), 
                   sqrt(diag(ols_two_skill_vcov)), 
                   sqrt(diag(ols_three_skill_vcov))),
          title = "GDP per Capita and Skill Misreporting",
          column.labels = c("≥1 skill", "≥2 skills", "3 skills"),
          dep.var.labels = "Skill Misreporting",
          covariate.labels = c("Intercept", "GDP per Capita (thousands)"),
          add.lines = list(c("Country Clustered SEs", "Yes", "Yes", "Yes")),
          out = "src/figures/gdp_skill_misreporting_table.tex")

# For use in subsequent calculations
ols_one_skill <- ols_one_skill_coef
ols_two_skill <- ols_two_skill_coef
ols_three_skill <- ols_three_skill_coef

magnitudes <- c(
  "≥1 skill" = coef(ols_one_skill)[2] * sd(data_hte_gdp$gdp_per_capita, na.rm = TRUE) * 100 / mean(data_hte_gdp$one_or_more_not_experienced, na.rm = TRUE),
  "≥2 skills" = coef(ols_two_skill)[2] * sd(data_hte_gdp$gdp_per_capita, na.rm = TRUE) * 100 / mean(data_hte_gdp$two_or_more_not_experienced, na.rm = TRUE),
  "3 skills" = coef(ols_three_skill)[2] * sd(data_hte_gdp$gdp_per_capita, na.rm = TRUE) * 100 / mean(data_hte_gdp$three_or_more_not_experienced, na.rm = TRUE)
)
clustered_standard_errors <- c(
  "≥1 skill" = sqrt(diag(vcovCL(ols_one_skill, cluster = data_hte_gdp$country_code)))[2],
  "≥2 skills" = sqrt(diag(vcovCL(ols_two_skill, cluster = data_hte_gdp$country_code)))[2],
  "3 skills" = sqrt(diag(vcovCL(ols_three_skill, cluster = data_hte_gdp$country_code)))[2]
)













data_gdp <- data_hte %>% group_by(country_code) %>% mutate(
  mean_one_or_more_not_experienced = mean(one_or_more_not_experienced, na.rm = TRUE),
  mean_two_or_more_not_experienced = mean(two_or_more_not_experienced, na.rm = TRUE),
  mean_three_or_more_not_experienced = mean(three_or_more_not_experienced, na.rm = TRUE)
) %>% slice(1) %>% ungroup() %>% select(country_code, mean_one_or_more_not_experienced, mean_two_or_more_not_experienced, mean_three_or_more_not_experienced, gdp_ppp_per_capita) %>% data.frame()

# Create a long format dataset for plotting
data_gdp_long <- data_gdp %>%
  pivot_longer(
    cols = starts_with("mean_"),
    names_to = "metric",
    values_to = "value"
  ) %>%
  mutate(
    metric = case_when(
      metric == "mean_one_or_more_not_experienced" ~ "≥1 skill",
      metric == "mean_two_or_more_not_experienced" ~ "≥2 skills",
      metric == "mean_three_or_more_not_experienced" ~ "3 skills",
      TRUE ~ metric
    ),
    metric = factor(metric, levels = c("≥1 skill", "≥2 skills", "3 skills"))
  )

# Create the scatter plot with GDP per capita and misreporting rates
ggplot(data_gdp_long, aes(x = gdp_ppp_per_capita, y = value, color = metric)) +
  geom_point(alpha = 0.7, size = 3) +
  geom_smooth(method = "lm", se = TRUE, alpha = 0.2) +
  scale_x_log10(labels = scales::dollar_format()) +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
  scale_color_brewer(palette = "Set1", name = "Misreported skills") +
  labs(
    title = "Relationship Between GDP Per Capita and Skill Misreporting",
    x = "GDP Per Capita (PPP, log scale)",
    y = "Share of candidates misreporting skills",
    caption = "Each point represents a country. Lines show linear regression with 95% confidence intervals."
  ) +
  theme_bw(base_size = 14) +
  theme(
    panel.grid.minor = element_blank(),
    legend.position = "bottom",
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 14, face = "bold"),
    axis.text = element_text(size = 12),
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 12),
    plot.caption = element_text(size = 10, hjust = 0),
    plot.margin = unit(c(1, 1, 1, 1), "cm")
  ) + ylim(0, 0.7) 

# Save the plot
ggsave("src/figures/skill_vetting_gdp_relationship.png", width = 10, height = 8, dpi = 300)
# Create GDP per capita groups (above and below median)
data_gdp <- data_gdp %>%
  mutate(gdp_group = case_when(
    gdp_ppp_per_capita <= median(gdp_ppp_per_capita, na.rm = TRUE) ~ "Below Median GDP",
    TRUE ~ "Above Median GDP"
  )) %>%
  mutate(gdp_group = factor(gdp_group, levels = c("Below Median GDP", "Above Median GDP")))

# Calculate mean values by GDP group
data_gdp_grouped <- data_gdp %>%
  group_by(gdp_group) %>%
  summarize(
    mean_one_or_more = mean(mean_one_or_more_not_experienced, na.rm = TRUE),
    mean_two_or_more = mean(mean_two_or_more_not_experienced, na.rm = TRUE),
    mean_three_or_more = mean(mean_three_or_more_not_experienced, na.rm = TRUE),
    n_countries = n()
  ) %>%
  pivot_longer(
    cols = starts_with("mean_"),
    names_to = "metric",
    values_to = "value"
  ) %>%
  mutate(
    metric = case_when(
      metric == "mean_one_or_more" ~ "≥1 skill",
      metric == "mean_two_or_more" ~ "≥2 skills",
      metric == "mean_three_or_more" ~ "3 skills",
      TRUE ~ metric
    ),
    metric = factor(metric, levels = c("≥1 skill", "≥2 skills", "3 skills"))
  )

# Create the grouped bar plot
ggplot(data_gdp_grouped, aes(x = gdp_group, y = value, fill = metric)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.9), width = 0.8) +
  geom_text(aes(label = scales::percent(value, accuracy = 0.1)), 
            position = position_dodge(width = 0.9), 
            vjust = -0.5, 
            size = 3.5) +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1), limits = c(0, 0.7)) +
  scale_fill_brewer(palette = "Set1", name = "Misreported skills") +
  labs(
    title = "Skill Misreporting by GDP Per Capita Group",
    x = "GDP Per Capita Group",
    y = "Share of candidates misreporting skills",
    caption = paste("Countries per group: Below Median GDP =", 
                   data_gdp_grouped$n_countries[data_gdp_grouped$gdp_group == "Below Median GDP" & data_gdp_grouped$metric == "≥1 skill"],
                   ", Above Median GDP =", 
                   data_gdp_grouped$n_countries[data_gdp_grouped$gdp_group == "Above Median GDP" & data_gdp_grouped$metric == "≥1 skill"])
  ) +
  theme_bw(base_size = 14) +
  theme(
    panel.grid.minor = element_blank(),
    legend.position = "bottom",
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 14, face = "bold"),
    axis.text = element_text(size = 12),
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 12),
    plot.caption = element_text(size = 10, hjust = 0),
    plot.margin = unit(c(1, 1, 1, 1), "cm")
  )

# Save the plot
ggsave("src/figures/skill_vetting_gdp_groups.png", width = 10, height = 8, dpi = 300)
