library(ggplot2)
library(readr)
library(tidyverse)

cbbPalette <- c("#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7")

papers_by_year_and_sampling_data <- read_csv("papers-by-year-and-sampling-data.csv")

full_df <- papers_by_year_and_sampling_data %>% gather("key", "value", totals:difference, factor_key=TRUE)

ggplot(papers_by_year_and_sampling_data, aes(x=X1)) + 
  geom_line(aes(y=totals), color="black") + 
  geom_line(aes(y=sampled), color="#0072B2") +
  geom_line(aes(y=final), color="#56B4E9") +
  labs(title = "Papers per year in our dataset",
       subtitle = "Showing the effect of downsampling") +
  xlab("Year") +
  ylab("Count")

df <- full_df %>% filter(key != "dropped") %>% filter(key != "difference") %>% filter(key != "all_published")

ggplot(df, aes(x=X1, y=value, color=key)) + 
  geom_line() + 
  # labs(title = "Papers per year in our dataset",
  #      subtitle = "Showing the effect of downsampling") +
  theme(legend.position = c(0.25, 0.75)) +
  theme(legend.title = element_text(size = 0), 
        legend.text = element_text(size = 8)) +
  # guides(shape = guide_legend(override.aes = list(size = 0.5))) +
  guides(color = guide_legend(override.aes = list(size = 0.5))) +
  scale_color_manual(labels = c("All Papers", "Stratified Sample", "Annotated"), values=cbbPalette) +
  xlab("Year") +
  ylab("Count")

ggsave("papers-by-year.png", width = 8, height = 6, units = "cm")


df <- df %>% filter(key !="sampled")

ggplot(df, aes(x=X1, y=value, color=key)) + 
  geom_line() + 
  # labs(title = "Papers per year in our dataset",
  #      subtitle = "Showing the effect of downsampling") +
  theme(legend.position = c(0.2, 0.7)) +
  theme(legend.title = element_text(size = 0), 
        legend.text = element_text(size = 8)) +
  # guides(shape = guide_legend(override.aes = list(size = 0.5))) +
  guides(color = guide_legend(override.aes = list(size = 0.5))) +
  scale_color_manual(labels = c("All Papers", "Sample"), values=cbbPalette) +
  xlab("Year") +
  ylab("Count")

ggsave("papers-by-year_80-paper-samlple-only.png", width = 8, height = 6, units = "cm")

df <- df %>% filter(key !="final")

ggplot(df, aes(x=X1, y=value, color=key)) + 
  geom_line() + 
  # labs(title = "Papers per year in our dataset",
  #      subtitle = "Showing the effect of downsampling") +
  theme(legend.position = c(0.25, 0.75)) +
  theme(legend.title = element_text(size = 0), 
        legend.text = element_text(size = 8)) +
  # guides(shape = guide_legend(override.aes = list(size = 0.5))) +
  guides(color = guide_legend(override.aes = list(size = 0.5))) +
  scale_color_manual(labels = c("All Papers", "Stratified Sample", "Annotated"), values=cbbPalette) +
  xlab("Year") +
  ylab("Count")

ggsave("papers-by-year-total.png", width = 8, height = 6, units = "cm")


df <- full_df %>% filter(key != "dropped") %>% filter(key != "final") %>% filter(key != "sampled") %>% filter(key != "all_published")

ggplot(df, aes(x=X1, y=value, fill=key)) + 
  geom_col(position = position_stack(reverse=TRUE)) + 
  # labs(title = "Papers per year in our dataset",
  #      subtitle = "Showing the effect of downsampling") +
  theme(legend.position = c(0.25, 0.75)) +
  theme(legend.title = element_text(size = 0), 
        legend.text = element_text(size = 8)) +
  # guides(shape = guide_legend(override.aes = list(size = 0.5))) +
  guides(color = guide_legend(override.aes = list(size = 0.5))) +
  scale_fill_manual(labels = c("w/Human Eval", "All Papers"), values=cbbPalette) +
  xlab("Year") +
  ylab("Count")

ggsave("papers-by-year-proportion.png", width = 8, height = 6, units = "cm")