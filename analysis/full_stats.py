# Local
from sheetreader import get_index

# Internal
from collections import Counter, defaultdict
import json
import operator
import os
import re
from itertools import combinations, cycle

# External
from tabulate import tabulate
from matplotlib import pyplot as plt
import seaborn as sns
import pandas as pd


################################################################################
# Output

def write_json(object, filename):
    "Write object to a JSON file."
    with open(f'./Data/{filename}', 'w') as f:
        json.dump(object, f, indent=2)


def write_table(rows, headers, filename):
    "Write LaTeX table to a file."
    table = tabulate(rows, headers=headers, tablefmt='latex_booktabs')
    with open(f'./Tables/{filename}', 'w') as f:
        f.write(table)


def write_frequency_table(counter, headers, filename):
    "Write a frequency table to a file, in LaTeX format."
    write_table(rows=counter.most_common(),
                headers=headers,
                filename=filename)


################################################################################
# Statistics

# TODO:
# * Compute percentages to put in the text. This could be done using the counters
#   that are already provided in the main function.
# * Compute min, max, most frequent scale size (key: op_instrument_size)
#
# DONE:
# * Confusion tables, showing which criteria get confused the most
# * Plot of how often authors specify criteria/definitions 
# * Frequency tables:
#   - Languages
#   - Tasks
#   - Output formats
#   - Author-specified criteria
#   - Criteria paraphrase
#   - Languages
#   - Statistics used

def unique_count_contents(index, key):
    # Counts unique number of instances a per paper level:
    unique_counter = Counter()
    for paper, rows in index.items():
        for row in rows:
            value_counter = count_contents({paper: [row]}, key)
            for value_key in value_counter.keys():
                if value_key in unique_counter:
                    unique_counter[value_key] = unique_counter[value_key] + 1
                else:
                    unique_counter[value_key] = 1
    return unique_counter


def count_all_contents(index, key):
    # Counts all instances for a given column key:
    all_counter = Counter()
    for paper, rows in index.items():
        for row in rows:
            value_counter = count_contents({paper: [row]}, key, True)
            for value_key, count in value_counter.items():
                if value_key in all_counter:
                    all_counter[value_key] = all_counter[value_key] + count
                else:
                    all_counter[value_key] = count
    return all_counter


def count_contents(index, key, count_blank=False):
    # Counts the number of times that values occur in a particular column:
    value_counter = Counter()
    for paper, rows in index.items():
        value = rows[0][key]
        value = value.lower()
        if 'Multiple' in value or 'multiple' in value:
            if key != "system_output":
                value = " ".join(value.split(":")[1:])
                items = value.strip().split(', ')
                value_counter.update([item.strip() for item in items])
            elif key == "system_output":
                value = value.replace("multiple (list all):", "").strip()
                items = value.strip().split(', ')
                value_counter.update([item.strip() for item in items])

        elif value not in {"", "none given", "not given", "blank"}:
            value = value.strip()
            value_counter[value] += 1
        elif value in {"", "none given", "not given", "blank"} and count_blank:
            value = "None Given/Blank"
            value_counter[value] += 1
    return value_counter


def count_contents_paraphase(index, key):
    # Counts the number of times that values occur in a particular column:
    value_counter = Counter()
    for paper, rows in index.items():
        value = rows[0][key]
        value = value.strip()
        if 'Multiple' in value or 'multiple' in value:
            value = " ".join(value.split(":")[1:])
            value = value.replace("-", "").strip()
            value = re.sub(r'(\d*\/*\d*\w\.) ', ' ', value)
            items = value.strip().split(', ')
            value_counter.update([item.strip() for item in items])
        elif value != "":
            value = value.replace("-", "").strip()
            value = re.sub(r'(\d*\/*\d*\w\.) ', ' ', value)
            value = value.strip()
            value_counter[value] += 1
    return value_counter


def count_statistic(index, key):
    # Counts the number of times that values occur in a particular column""
    value_counter = Counter()
    for paper, rows in index.items():
        value = rows[0][key]
        value = value.lower()
        if value != "" and value != "none given":
            split_crit = ""
            if "," in value:
                split_crit = ","
            else:
                split_crit = ";"
            items = value.split(split_crit)
            for item in items:
                value_counter[item.strip()] += 1
    return value_counter


stats_normalisation_dict = {"SD": "standard deviation",
                            "standard dev": "standard deviation",
                            "Mean": "mean",
                            "means": "mean",
                            "raw counts": "raw numbers"}


def normalise_statistics_terms(term: str):
    if term in stats_normalisation_dict:
        return [stats_normalisation_dict[term]]
    if "ANOVA" in term:
        return ["ANOVA"]
    if "Kruskal-Wallis" in term:
        return ["Kruskall-Wallis"]
    if re.match("[Aa]nalysis [Oo]f [Vv]ariance", term):
        return ["ANOVA"]
    if re.match("Mann-Whitney.*U", term):
        return ["Mann-Whitney U-test"]
    if re.match("[Cc]hi[\- ]sq", term):
        return ["Chi-squared"]
    if re.match("[Rr]atio", term):
        return ['ratio']
    if "percentage" in term:
        return ["proportion"]
    if "specif" in term:
        return ['underspecified']
    if term.startswith("t-test"):
        return ['t-test']
    return [term]


def count_statistic_modified(index, key):
    # Counts the number of times that values occur in a particular column:
    value_counter = Counter()
    for paper, rows in index.items():
        value = rows[0][key]
        if value != "" and value != "none given":
            split_crit = ""
            if "," in value:
                split_crit = ","
            else:
                split_crit = ";"
            value = re.sub("(2|two|Two)-tail(ed)*", "two-tailed", value)
            items = value.split(split_crit)
            for item in items:
                normalised = normalise_statistics_terms(item.strip())
                for x in normalised:
                    value_counter[x] += 1
    return value_counter


def convert_percent(counter_values):
    # Converts the values of the counter into percentages:
    counts = list(counter_values.values())
    sum_counts = sum(counts)
    percent_counter = Counter()
    for k, v in counter_values.items():
        if k not in percent_counter:
            percent_counter[k] = round((v / sum_counts) * 100, 2)
    return percent_counter


def count_empty(index, key):
    """
    Count for any key how many papers leave the value unspecified.
    Note that this function only checks the first of the rows corresponding to a paper.
    """
    count = 0
    for paper, rows in index.items():
        value = rows[0][key]
        if value in {"", "none given", "not given", "blank", "unclear"}:
            count += 1
    return count


def year_wise_counts(index, key, filename):
    """
    Calculates year wise counts (before and after 2010) and writes it a latex file
    Inputs - 
        Index - excel file
        Key - column which needs to be calculated
        filename - filename of the tex file
    Outputs:
        A latex file of the counts containing the criterion, before 2010, after 2010, total values 
    """
    b4_value_counter = Counter()
    after_value_counter = Counter()
    for paper, rows in index.items():
        value = rows[0][key]
        value = value.lower()
        year = rows[0]["pub_year"]
        if 'Multiple' in value or 'multiple' in value and key != "system_output":
            value = " ".join(value.split(":")[1:])
            items = value.strip().split(', ')
            if year < 2010:
                b4_value_counter.update([item.strip() for item in items])
            else:
                after_value_counter.update([item.strip() for item in items])
        elif value != "":
            if year < 2010:
                b4_value_counter[value] += 1
            else:
                after_value_counter[value] += 1
    rows = []
    languages = list(set(list(b4_value_counter.keys()) + list(after_value_counter.keys())))
    for lang in languages:
        if lang in b4_value_counter.keys():
            b4_value = b4_value_counter[lang]
        else:
            b4_value = 0
        if lang in after_value_counter.keys():
            after_value = after_value_counter[lang]
        else:
            after_value = 0
        rows.append([lang, b4_value, after_value, b4_value + after_value])
    rows.sort(key=lambda k: k[3], reverse=True)
    headers = ['Criterion', 'Before 2010', 'After 2010', "Total"]
    write_table(rows, headers, filename)


def year_wise_verbatim_def_counts(index, filename):
    """
    Calculates year wise counts (before and after 2010) of the verbatim criterion and writes it a latex file
    Inputs - 
        Index - excel file
        filename - filename of the tex file
    Outputs:
        A latex file of the counts containing the criterion, before 2010, after 2010, total values 
    """
    b4_value_counter = Counter()
    after_value_counter = Counter()
    for paper, rows in index.items():
        for row in rows:
            verbatim = row["criterion_verbatim"].lower().strip()
            definition = row["criterion_definition_verbatim"].lower().strip()
            year = row["pub_year"]
            if verbatim != "" and verbatim != "none given" and verbatim != "not given":
                if definition != "" and definition != "none given" and definition != "not given":
                    if year < 2010:
                        if verbatim in b4_value_counter.keys():
                            b4_value_counter[verbatim] = b4_value_counter[verbatim] + 1
                        else:
                            b4_value_counter[verbatim] = 1
                    else:
                        if verbatim in after_value_counter.keys():
                            after_value_counter[verbatim] = after_value_counter[verbatim] + 1
                        else:
                            after_value_counter[verbatim] = 1
    rows = []
    all_criterion = list(set(list(after_value_counter.keys()) + list(b4_value_counter.keys())))
    for crit in all_criterion:
        if crit in b4_value_counter.keys():
            b4_value = b4_value_counter[crit]
        else:
            b4_value = 0
        if crit in after_value_counter.keys():
            after_value = after_value_counter[crit]
        else:
            after_value = 0
        rows.append([crit, b4_value, after_value, b4_value + after_value])
    rows.sort(key=lambda k: k[3], reverse=True)
    headers = ['Criterion', 'Before 2010', 'After 2010', "Total"]
    write_table(rows, headers, filename)


def count_verbatim_criterion(index, filename):
    """
    Calculates counts of the criterion definition and if an associated defition was provided or not
    Inputs - 
        Index - excel file
        filename - filename of the tex file
    Outputs:
        A latex file of the counts containing the criterion, Definitions given, Definitions not given
    """
    criterion_given = dict()
    criterion_no_given = dict()
    for paper, rows in index.items():
        for row in rows:
            verbatim = row["criterion_verbatim"]
            definition = row["criterion_definition_verbatim"]
            if verbatim not in {"", "none given", "not given"}:
                if definition not in {"", "none given", "not given"}:
                    if verbatim in criterion_given.keys():
                        criterion_given[verbatim] = criterion_given[verbatim] + 1
                    else:
                        criterion_given[verbatim] = 1
                else:
                    if verbatim in criterion_no_given.keys():
                        criterion_no_given[verbatim] = criterion_no_given[verbatim] + 1
                    else:
                        criterion_no_given[verbatim] = 1

    all_criterion = list(set(list(criterion_given.keys()) + list(criterion_no_given.keys())))
    rows = []
    for crit in all_criterion:
        if crit in criterion_given.keys():
            given = criterion_given[crit]
        else:
            given = 0
        if crit in criterion_no_given.keys():
            not_given = criterion_no_given[crit]
        else:
            not_given = 0
        rows.append([crit, given, not_given])

    headers = ['Criterion', 'Definitions \n Given', 'Definitions \n Not Given']
    write_table(rows, headers, filename)


def count_verbatim_definiton(index):
    """
    Calculates counts of the criterion definition and if an associated defition was provided or not and is grouped by before 2010 or after 2010.
    Inputs - 
        Index - excel file
        filename - filename of the tex file
    Outputs:
        A latex file of the counts containing the criterion, Definitions given, Definitions not given and is grouped by year (before 2010) and (after 2010).
    """
    given_b4_2010 = 0
    given_after_2010 = 0
    not_given_b4_2010 = 0
    not_given_after_2010 = 0
    for paper, rows in index.items():
        for row in rows:
            year = row["pub_year"]
            definition = row["criterion_definition_verbatim"]
            if definition != "" and definition != "not given" and definition != "blank" and definition != "unclear" and definition != "none given":
                if year < 2010:
                    given_b4_2010 += 1
                else:
                    given_after_2010 += 1
            else:
                if year < 2010:
                    not_given_b4_2010 += 1
                else:
                    not_given_after_2010 += 1

    print("Num of times Verbatim Definition for a criteria is given (pre 2010): {}".format(given_b4_2010))
    print("Num of times Verbatim Definition for a criteria is given (post 2010): {}".format(given_after_2010))
    print(
        "Num of times Verbatim Definition for a criteria is given (Total): {}".format(given_after_2010 + given_b4_2010))
    print("------------------------------ \n")
    print("Num of times Verbatim Definition for a criteria is not given (pre 2010): {}".format(not_given_b4_2010))
    print("Num of times Verbatim Definition for a criteria is not given (post 2010): {}".format(not_given_after_2010))
    print("Num of times Verbatim Definition for a criteria is not given (Total): {}".format(
        not_given_b4_2010 + not_given_after_2010))


################################################################################

# task to criterion

def task_2_criterion(index, task_counter, filename):
    """
    Calculates counts of task and its associated criterion
    Inputs - 
        Index - excel file
        task_counter - A counter of task counts
        filename - filename of the tex file
    Outputs:
        A latex file of the counts containing task, verbatim criterion and count.
    """
    task2criterion = dict()
    for paper, rows in index.items():
        for row in rows:
            task = row["system_task"]
            verbatim = row["criterion_verbatim"]
            task = task.replace("multiple (list all): ", "").strip()
            if verbatim != "" and verbatim != "none given" and verbatim != "not given":
                verbatim = verbatim.lower().strip()
                if task in task2criterion:
                    criterion_values = task2criterion[task]
                    if verbatim in criterion_values:
                        criterion_values[verbatim] = criterion_values[verbatim] + 1
                    else:
                        criterion_values[verbatim] = 1
                    task2criterion[task] = criterion_values
                else:
                    criterion_values = {}
                    criterion_values[verbatim] = 1
                    task2criterion[task] = criterion_values
    rows = []
    for key, value in task_counter.most_common():
        if key in task2criterion.keys():
            v = task2criterion[key]
            sorted_values = dict(sorted(v.items(), key=operator.itemgetter(1), reverse=True))
            for crit, count in sorted_values.items():
                rows.append([key, crit, count])
        headers = ['Task', 'Verbatim Criterion', 'Count']

    write_table(rows, headers, filename)
    df = pd.DataFrame(rows, columns=['Task', 'Verbatim Criterion', 'Count'])
    df.to_excel("./Data/task2criterion.xlsx", index=False)


def task_2_criterion_standardized(index, task_counter, filename):
    """
    Calculates counts of task and its associated criterion (standardized)
    Inputs - 
        Index - excel file
        task_counter - A counter of task counts
        filename - filename of the tex file
    Outputs:
        A latex file of the counts containing task, verbatim criterion (Standardized) and count.
    """

    task2criterion = dict()
    for paper, rows in index.items():
        for row in rows:
            task = row["system_task"]
            verbatim = row["criterion_paraphrase"]
            task = task.replace("multiple (list all): ", "").strip()
            verbatim = verbatim.replace("-", "").strip()
            verbatim = re.sub(r'(\d*\/*\d*\w\.) ', ' ', verbatim)
            verbatim = verbatim.replace(".", "").strip()
            verbatim = verbatim.replace("Multiple (list all):", "").strip()
            if "," in verbatim:
                split_verbatim = verbatim.split(",")
            else:
                split_verbatim = [verbatim]
            for verb in split_verbatim:
                if verb != "" and verb != "none given" and verb != "not given":
                    verb = verb.lower().strip()
                    if task in task2criterion:
                        criterion_values = task2criterion[task]
                        if verb in criterion_values:
                            criterion_values[verb] = criterion_values[verb] + 1
                        else:
                            criterion_values[verb] = 1
                        task2criterion[task] = criterion_values
                    else:
                        criterion_values = {}
                        criterion_values[verb] = 1
                        task2criterion[task] = criterion_values
    rows = []
    for key, value in task_counter.most_common():
        if key in task2criterion.keys():
            v = task2criterion[key]
            sorted_values = dict(sorted(v.items(), key=operator.itemgetter(1), reverse=True))
            for crit, count in sorted_values.items():
                rows.append([key, crit, count])
        headers = ['Task', 'Verbatim Criterion', 'Count']

    write_table(rows, headers, filename)
    df = pd.DataFrame(rows, columns=['Task', 'Verbatim Criterion', 'Count'])
    df.to_excel("./Data/task2criterion_standardized.xlsx", index=False)


def criterion_2_paraphrased(index, filename):
    """
    Calculates counts of criterion and its paraphrased criterion
    Inputs - 
        Index - excel file
        filename - filename of the tex file
    Outputs:
        A latex file of the counts containing task, verbatim criterion (Standardized) and count.
        A excel mapping varbatim to the standarized counts [Needed for the Sankey Diagram]
    """
    verbatim2paraphrase = dict()
    for paper, rows in index.items():
        for row in rows:
            verbatim = row["criterion_verbatim"].lower()
            if verbatim != "" and verbatim != "not given" and verbatim != "blank" and verbatim != "unclear" and verbatim != "none given":
                verbatim = verbatim.strip()
                paraphrase = row["criterion_paraphrase"]
                paraphrase = paraphrase.lower()
                paraphrase = paraphrase.replace("multiple (list all)", "").strip()
                paraphrase = paraphrase.replace("-", "").strip()
                paraphrase = re.sub(r'(\d*\/*\d*\w\.)', ' ', paraphrase)
                paraphrase = paraphrase.replace(".", "").strip()
                paraphrase = paraphrase.replace(":", "").strip()
                if "," in paraphrase:
                    split_para = paraphrase.split(",")
                else:
                    split_para = [paraphrase]
                for verb in split_para:
                    if verb != "" and verb != "none given" and verb != "not given":
                        verb = verb.lower().strip() + " "
                        if verbatim in verbatim2paraphrase:
                            criterion_values = verbatim2paraphrase[verbatim]
                            if verb in criterion_values:
                                criterion_values[verb] = criterion_values[verb] + 1
                            else:
                                criterion_values[verb] = 1
                            verbatim2paraphrase[verbatim] = criterion_values
                        else:
                            criterion_values = {}
                            criterion_values[verb] = 1
                            verbatim2paraphrase[verbatim] = criterion_values
    rows = []
    for key, value in verbatim2paraphrase.items():
        # for k,v in task2criterion.items():
        # if key in task2criterion.keys():
        # v = task2criterion[key]
        sorted_values = dict(sorted(value.items(), key=operator.itemgetter(1), reverse=True))
        for crit, count in sorted_values.items():
            rows.append([key, crit, count])
        headers = ['Verbatim', 'Standardised', 'Count']

    write_table(rows, headers, filename)
    df = pd.DataFrame(rows, columns=['Verbatim', 'Standardised', 'Count'])
    df.to_excel("./Data/verbatim_to_standardized.xlsx", index=False)


################################################################################
# Create confusion tables

def get_confusion_indices(index):
    "Build confusion indices."
    author_criteria_index = defaultdict(set)
    paraphrase_criteria_index = defaultdict(set)
    for paper, rows in index.items():
        for row in rows:
            verbatim = row["criterion_verbatim"]
            paraphrase = row["criterion_paraphrase"]
            # If verbatim is specified
            if verbatim not in {'not given', 'none given'}:
                # Add paraphrase to the set of criteria that are denoted by the verbatim criterion.
                author_criteria_index[verbatim].add(paraphrase)
                # Add verbatim to the set of criteria that are used to refer to the paraphrased criterion.
                paraphrase_criteria_index[paraphrase].add(verbatim)
    return author_criteria_index, paraphrase_criteria_index


def get_confusion_indices_modified(index):
    "Build confusion indices."
    author_criteria_index = defaultdict(set)
    paraphrase_criteria_index = defaultdict(set)
    for paper, rows in index.items():
        for row in rows:
            verbatim = row["criterion_verbatim"]
            paraphrase = row["criterion_paraphrase"]
            # If verbatim is specified
            if verbatim not in {'not given', 'none given'}:
                # Add paraphrase to the set of criteria that are denoted by the verbatim criterion.
                paraphrase = paraphrase.replace("-", "").strip()
                paraphrase = re.sub(r'(\d*\/*\d*\w\.)', ' ', paraphrase)
                paraphrase = paraphrase.replace(".", "").strip()
                paraphrase = paraphrase.replace(",", "COMMA")
                author_criteria_index[verbatim.lower()].add(paraphrase)
                # Add verbatim to the set of criteria that are used to refer to the paraphrased criterion.
                paraphrase_criteria_index[paraphrase].add(verbatim)
    return author_criteria_index, paraphrase_criteria_index


def get_confusion_indices_modified_for_table_9(index):
    "Build confusion indices."
    author_criteria_index = defaultdict(set)
    paraphrase_criteria_index = defaultdict(set)
    for paper, rows in index.items():
        for row in rows:
            verbatim = row["criterion_verbatim"]
            paraphrase = row["criterion_paraphrase"]
            # If verbatim is specified
            if verbatim not in {'not given', 'none given'}:
                # Add paraphrase to the set of criteria that are denoted by the verbatim criterion.
                paraphrase = paraphrase.replace("-", "").strip()
                paraphrase = re.sub(r'(\d*\/*\d*\w\.)', ' ', paraphrase)
                paraphrase = paraphrase.replace(".", "").strip()
                paraphrase = paraphrase.replace(",", "COMMA")
                author_criteria_index[verbatim.lower()].add(paraphrase)
                # Add verbatim to the set of criteria that are used to refer to the paraphrased criterion.
                paraphrase_criteria_index[paraphrase].add(verbatim)
    return author_criteria_index, paraphrase_criteria_index


def value_length(pair):
    "Key function, that measures the length of the second value of a pair."
    return len(pair[1])


def get_confusion_table(confusion_index, n=10):
    """
    Construct a table with the top-n terms that have the most confusion.
    (Where confusion means the extent to which multiple terms are associated with the same criterion.)
    """
    frequency_list = sorted(confusion_index.items(),
                            key=value_length,
                            reverse=True)
    rows = [[criterion, ', '.join(corresponding_set), len(corresponding_set)]
            for criterion, corresponding_set in frequency_list[:n]]
    header = ['Criterion', 'Corresponding criteria', 'Amount']
    return rows, header


def write_confusion_tables(index, n=10):
    """
    Write confusion tables to a file.
    
    This main function uses the following two functions:
    - get_confusion_indices()
    - get_confusion_table()
    """
    author_criteria_index, paraphrase_criteria_index = get_confusion_indices(index)
    author_criteria_index_mod_for_table_9, paraphrase_criteria_index_mod_for_table_9 = get_confusion_indices_modified_for_table_9(
        index)

    rows, headers = get_confusion_table(author_criteria_index, n)
    write_table(rows, headers, "confusion_author_criteria.tex")

    rows, headers = get_confusion_table(paraphrase_criteria_index, n)
    write_table(rows, headers, "confusion_paraphrased_criteria.tex")

    rows, headers = get_confusion_table(author_criteria_index_mod_for_table_9, n)
    write_table(rows, headers, "confusion_author_criteria_mod.tex")

    rows, headers = get_confusion_table(paraphrase_criteria_index_mod_for_table_9, n)
    write_table(rows, headers, "confusion_paraphrased_criteria_mod.tex")


################################################################################
# Code to compute how often authors specify criteria/definitions.

# Helper function
def check_presence(row, key):
    "Check if value is present in the row."
    value = row[key]
    if value in ['', 'none given', 'not given']:
        return None
    else:
        return value.lower()


# Helper function
def determine_frequency(some_list):
    "Function to provide rough frequency indication."
    if all(some_list):
        return 'all'
    elif any(some_list):
        return 'some'
    else:
        return 'no'


# Main function. If you want to generate a table, then you could transform specifications
# into a DataFrame, and compute the percentages using Pandas.
def author_criteria_definitions(index):
    "Get data on whether authors specify criteria or definitions."
    specifications = []
    for paper, rows in index.items():
        # Add criteria data
        criteria = [check_presence(row, "criterion_verbatim") for row in rows]
        entry = dict(paper=paper, kind='criteria', frequency=determine_frequency(criteria))
        specifications.append(entry)
        # Add definition data
        definitions = [check_presence(row, "criterion_definition_verbatim") for row in rows]
        entry = dict(paper=paper, kind='definitions', frequency=determine_frequency(definitions))
        specifications.append(entry)
    return specifications


def plot_acd(index, filename='are_definitions_criteria_given.pdf'):
    "Plot whether authors specify criteria or definitions."
    data = author_criteria_definitions(index)
    df = pd.DataFrame(data)
    ax = sns.countplot(x="kind",
                       hue="frequency",
                       hue_order=("all", "some", "no"),
                       data=df,
                       palette=sns.color_palette("ch:start=.2,rot=-.3", n_colors=3))
    ax.set(xlabel='Quality Criterion Element',
           ylabel='Frequency')
    ax.set_xticklabels(["Names", "Definitions"])
    hatches = cycle(['/', '+', 'o', 'x', '\\', '*', 'o', 'O', '.'])
    for i, bar in enumerate(ax.patches):
        if i % 2 == 0:
            hatch = next(hatches)
        bar.set_hatch(hatch)
    leg = plt.legend(title=None, labels=['all given', 'some given', 'none given'], labelspacing=1, handlelength=4)
    for patch in leg.get_patches():
        patch.set_height(14)
        patch.set_y(-4.5)
    plt.savefig(f"./Figures/{filename}")


################################################################################
# Main code

def main():
    # Build index
    index = get_index("./terminology_complete.xlsx")

    # Compute frequency tables (First Row only):
    task_counter = count_contents(index, 'system_task')
    output_counter = count_contents(index, 'system_output')
    language_counter = count_contents(index, 'system_language')
    criterion_verbatim_counter = count_contents(index, 'criterion_verbatim')
    criterion_paraphrase_counter = count_contents_paraphase(index, 'criterion_paraphrase')
    stat_counter = count_statistic(index, 'op_statistics')
    stat_counter_mod = count_statistic_modified(index, 'op_statistics')
    response_elicitation_counter = count_contents(index, 'op_form')

    # Unique Complete Counts:
    task_unique_counter = unique_count_contents(index, 'system_task')
    output_unique_counter = unique_count_contents(index, 'system_output')
    input_unique_counter = unique_count_contents(index, 'system_input')
    language_unique_counter = unique_count_contents(index, 'system_language')

    # Complete Counts including blanks:
    op_response_values_inc_blank = count_all_contents(index, "op_response_values")
    op_instrument_size_inc_blank = count_all_contents(index, "op_instrument_size")
    op_instrument_type_inc_blank = count_all_contents(index, "op_instrument_type")
    op_data_type_inc_blank = count_all_contents(index, "op_data_type")
    op_form_inc_blank = count_all_contents(index, "op_form")
    op_question_prompt_verbatim_inc_blank = count_all_contents(index, "op_question_prompt_verbatim")
    op_question_prompt_paraphrase_inc_blank = count_all_contents(index, "op_question_prompt_paraphrase")
    op_statistics_inc_blank = count_all_contents(index, "op_statistics")

    criterion_verbatim_inc_blank = count_all_contents(index, "criterion_verbatim")
    criterion_definition_verbatim_inc_blank = count_all_contents(index, "criterion_definition_verbatim")
    criterion_paraphrase_inc_blank = count_all_contents(index, "criterion_paraphrase")
    criterion_definition_paraphrase_inc_blank = count_all_contents(index, "criterion_definition_paraphrase")

    ##COunt empty
    print("Number of empty Response elictiation: {}".format(count_empty(index, "op_form")))
    ## Year wise counts

    year_wise_counts(index, 'system_language', "language_by_year.tex")
    year_wise_counts(index, 'system_task', "task_by_year.tex")
    task_2_criterion(index, task_counter, "task2criterion.tex")
    task_2_criterion_standardized(index, task_counter, "task2criterion_standardized.tex")
    criterion_2_paraphrased(index, "verbatim2standardised.tex")
    year_wise_verbatim_def_counts(index, "defintion_give_by_year.tex")

    # Verbatim crierion given or not
    count_verbatim_criterion(index, "verbatim_given_or_not.tex")

    # Verbatim crierion given or not irrespective if the criteria was mention or not
    count_verbatim_definiton(index)
    # Convert frequencies to percent
    percent_task_counter = convert_percent(task_counter)
    percent_output_counter = convert_percent(output_counter)
    percent_language_counter = convert_percent(language_counter)
    percent_criterion_verbatim_counter = convert_percent(criterion_verbatim_counter)
    percent_criterion_paraphrase_counter = convert_percent(criterion_paraphrase_counter)
    percent_stat_counter = convert_percent(stat_counter)
    percent_response_elicitation_counter = convert_percent(response_elicitation_counter)

    # Write to files: JSON (for further processing)
    write_json(task_counter, 'system_task.json')
    write_json(output_counter, 'system_output.json')
    write_json(language_counter, 'system_language.json')
    write_json(criterion_verbatim_counter, 'criterion_verbatim.json')
    write_json(criterion_paraphrase_counter, 'criterion_paraphrase.json')
    write_json(stat_counter, 'op_statistics.json')
    write_json(stat_counter_mod, 'op_statistics_mod.json')
    write_json(response_elicitation_counter, 'response_elicitation.json')

    # Write to files: LaTeX
    write_frequency_table(task_counter, ['Task', 'Count'], 'system_task.tex')
    write_frequency_table(output_counter, ['Output', 'Count'], 'system_output.tex')
    write_frequency_table(language_counter, ['Language', 'Count'], 'system_language.tex')
    write_frequency_table(criterion_verbatim_counter, ['Criterion (author-defined)', 'Count'], 'criterion_verbatim.tex')
    write_frequency_table(criterion_paraphrase_counter, ['Criterion (standardised)', 'Count'],
                          'criterion_paraphrase.tex')
    write_frequency_table(stat_counter, ['Statistical method', 'Count'], 'op_statistics.tex')
    write_frequency_table(stat_counter_mod, ['Statistical method', 'Count'], 'op_statistics_mod.tex')
    write_frequency_table(response_elicitation_counter, ['Response Elicitation', 'Count'], 'response_elicitation.tex')

    # Write percentage frequencies to LaTex
    write_frequency_table(percent_task_counter, ['Task', 'Count (%)'], 'system_task_percent.tex')
    write_frequency_table(percent_output_counter, ['Output', 'Count (%)'], 'system_output_percent.tex')
    write_frequency_table(percent_language_counter, ['Language', 'Count (%)'], 'system_language_percent.tex')
    write_frequency_table(percent_criterion_verbatim_counter, ['Criterion (author-defined)', 'Count (%)'],
                          'criterion_verbatim_percent.tex')
    write_frequency_table(percent_criterion_paraphrase_counter, ['Criterion (standardised)', 'Count (%)'],
                          'criterion_paraphrase_percent.tex')
    write_frequency_table(percent_stat_counter, ['Statistical method', 'Count (%)'], 'op_statistics_percent.tex')
    write_frequency_table(percent_response_elicitation_counter, ['Response Elicitation', 'Count (%)'],
                          'response_elicitation_percent.tex')

    # Unique Complete Tables:
    write_frequency_table(task_unique_counter, ['Task', 'Count'], 'system_unique_task.tex')
    write_frequency_table(output_unique_counter, ['Output', 'Count'], 'system_unique_output.tex')
    write_frequency_table(input_unique_counter, ['Input', 'Count'], 'system_unique_input.tex')
    write_frequency_table(language_unique_counter, ['Language', 'Count'], 'system_unique_language.tex')

    # Complete All including Blanks Tables:
    write_frequency_table(op_response_values_inc_blank, ['Response Values', 'Count'], 'op_response_values_complete.tex')
    write_frequency_table(op_instrument_size_inc_blank, ['Instrument Size', 'Count'], 'op_instrument_size_complete.tex')
    write_frequency_table(op_instrument_type_inc_blank, ['Instrument Type', 'Count'], 'op_instrument_type_complete.tex')
    write_frequency_table(op_data_type_inc_blank, ['Data Type', 'Count'], 'op_data_type_complete.tex')
    write_frequency_table(op_form_inc_blank, ['Form', 'Count'], 'op_form_complete.tex')
    write_frequency_table(op_question_prompt_verbatim_inc_blank, ['Verbatim Question Prompt', 'Count'],
                          'op_question_prompt_verbatim_complete.tex')
    write_frequency_table(op_question_prompt_paraphrase_inc_blank, ['Paraphrase Question Prompt', 'Count'],
                          'op_question_prompt_paraphrase_complete.tex')
    write_frequency_table(op_statistics_inc_blank, ['Statistics Name', 'Count'], 'op_statistics_complete.tex')

    write_frequency_table(criterion_verbatim_inc_blank, ['Criterion Verbatim', 'Count'],
                          'criterion_verbatim_complete.tex')
    write_frequency_table(criterion_definition_verbatim_inc_blank, ['Criterion Definition Verbatim', 'Count'],
                          'criterion_definition_verbatim_complete.tex')
    write_frequency_table(criterion_paraphrase_inc_blank, ['Criterion Paraphrase', 'Count'],
                          'criterion_paraphrase_complete.tex')
    write_frequency_table(criterion_definition_paraphrase_inc_blank, ['Criterion Paraphrase', 'Count'],
                          'criterion_definition_paraphrase_complete.tex')

    # Plot how often authors specify criteria or definitions.
    plot_acd(index)

    # Generate tables showing which criteria correspond to the most different 
    # author-provided terms, and vice versa.
    write_confusion_tables(index, 10)


if __name__ == "__main__":
    os.makedirs("Data", exist_ok=True)
    os.makedirs("Figures", exist_ok=True)
    os.makedirs("Tables", exist_ok=True)
    main()
