# Analysis for "Twenty Years of Confusion"

This folder contains a copy of our annotations (`terminology_complete.xlsx`) and the code necessary to reproduce the figures and tables from our paper.

Run

    python full_stats.py

to generate most of the figures, tables, and intermediate data representations.

There is a Pipfile for those who use `pipenv` to manage their Python environment and a `requirements.txt` for reference.

Figure 1 was generated by running `papers-by-year.R` in R, which loads data from `papers-by-year.R`.
Note that this figure erroneously counts 11 papers as having human evaluations which were not included in the final dataset, because they did not actually include a human evaluation.

You can configure your R environment by installing:

* `ggplot2`
* `readr`
* `tidyverse`

or using the included [`renv.lock`](https://rstudio.github.io/renv/articles/renv.html) file.

## Inventory

* `Data/`  
  empty folder to serve as a destination for `full_stats.py` outputs
* `Figures/`  
  empty folder to serve as a destination for `full_stats.py` outputs
* `Tables/`  
  empty folder to serve as a destination for `full_stats.py` outputs
* `full_stats.py`  
  Python script to generate tables and figures for analysis
* `papers-by-year.R`
  script to generate figure 1 from the paper
* `papers-by-year-and-sampling-data.csv`
  data used by `papers-by-year.R`
* `Pipfile`  
  a list of Python requirements for use with [`pipenv`](https://pypi.org/project/pipenv/)
* `README.md`  
  this file
* `requirements.txt`  
  a simple list of Python requirements for use with `pip`
* `Sankeh_plots.ipynb`
  Jupyter notebook used to explore and generate Sankey plots
* `sheetreader.py`  
  a helper module for loading XLSX data for our analyses
* `terminology_complete.xlsx`  
  our annotations
  

## How it works

### Reading the Excel file

This repository contains the Excel file with our annotations, and some scripts to analyze them.
The most important file is `sheetreader.py`, which loads the Excel file and builds an index of the papers.
You can use it like this:

```python
from sheetreader import get_index    

INDEX = get_index('terminology.xlsx')
```

`INDEX` is a dictionary with the paper IDs as keys, and lists of rows as values.
Each row is represented as a dictionary. This makes it straightforward to analyze the data.

### Analyzing the data

The file `full_stats.py` shows how to analyze the data.
After loading the Excel file and generating an index, it is easy to loop over all 
the papers and generate relevant statistics.

### Inspecting the results
There are multiple folders where results are automatically generated:
* `./Data` contains JSON files for further computation.
* `./Figures` contains figures that can be embedded in the paper.
* `./Tables` contains LaTeX tables that can be pasted in the paper. (Probably a good idea to shorten them in the code with an additional parameter.)

