from typing import Collection, Dict, List, Optional, Tuple

from nltk.metrics.agreement import AnnotationTask
from nltk.metrics import jaccard_distance, masi_distance

import gspread
import os
import pandas as pd


def extract_iaa_df_by_column_name(annotation_df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Extract a three-column dataframe with `column_name` items grouped by `source_spreadsheet` and `key`."""
    return annotation_df[['source_spreadsheet', 'key', column_name]] \
        .groupby(['source_spreadsheet', 'key'])[column_name] \
        .apply(frozenset).reset_index()


def extract_records_for_nltk(iaa_df: pd.DataFrame) -> List[Tuple]:
    """The first column in the `to_records()` representation is an index, which we don't need for `nltk`."""
    return [(b, c, d) for _, b, c, d in iaa_df.to_records()]


def pretty_print_iaa_by_column(iaa_by_column_dict, values=("alpha_jaccard", "alpha_masi")):
    print(f"column\t{'  '.join(values)}")
    for column in iaa_by_column_dict:
        values_string = '    '.join([f"{iaa_by_column_dict[column][value]:.2f}" for value in values])
        print(f"{column}\t{values_string}")


class IAASpreadsheetScheme(object):
    CLOSED_CLASS_COLUMNS = None
    OPEN_CLASS_COLUMNS = None
    ALL_DATA_COLUMNS = None
    METADATA_COLUMNS = None
    ALL_COLUMNS = None

    HIERARCHY_DICT = None

    # Generate pop-up to log in through Google.
    # If the pop-up has previously been generated,
    # this will instead use the existing authorization.
    google_session = gspread.oauth()

    _GOOGLE_SESSION = gspread.oauth()

    @classmethod
    def load_locally_fallback_to_web(cls, filepath: str, urls: Collection[str]) -> pd.DataFrame:
        if os.path.exists(filepath):
            annotation_df = pd.read_csv(filepath)
        else:
            annotation_df = cls.prepare_df_from_google_sheets(urls)
            annotation_df.to_csv(filepath)
        return annotation_df

    @classmethod
    def prepare_df_from_google_sheets(cls, url_collection: Collection[str]) -> pd.DataFrame:
        spreadsheets = map(cls._GOOGLE_SESSION.open_by_url, url_collection)

        # Just the first sheet contains the annotations
        # There is a second sheet in each spreadsheet which contains the 'backing data',
        # i.e. the valid labels for closed-class categories in the annotation sheet
        annotation_sheets = [spreadsheet.worksheet("Annotation Sheet") for spreadsheet in spreadsheets]
        data = [sheet.get_all_values() for sheet in annotation_sheets]

        # The first two rows contain header information, so we drop this from the data we have loaded from each spreadsheet.
        for sheet in data:
            sections = sheet.pop(0)
            headers = sheet.pop(0)

        dataframes = [pd.DataFrame(sheet) for sheet in data]

        # The full dataset is the concatenation of all of the loaded spreadsheets
        # where we have added a column representing which spreadsheet the data came from originally.
        annotation_df = pd.concat(dataframes, keys=range(1, len(dataframes) + 1))

        # Initially the columns have integer indices
        # We assign names to the columns
        annotation_df.columns = cls.ALL_COLUMNS

        # Drop rows marked for exclusion by their annotators
        annotation_df = annotation_df[annotation_df.exclude != "TRUE"]

        # Convert multilevel indices to simple indices via to_records()
        annotation_df = pd.DataFrame(annotation_df.to_records())

        # Drop the unnecessary within-spreadsheet index from the full dataset
        annotation_df = annotation_df.drop("level_1", 1)

        # Give the which-spreadsheet-did-it-come-from column a sensible name
        annotation_df.rename(columns={"level_0": "source_spreadsheet"},
                             errors="ignore",
                             inplace=True)

        return annotation_df

    @classmethod
    def run_closed_class_jaccard_and_masi(cls, df: pd.DataFrame) -> Dict:
        iaa_by_column = {column: {"df": extract_iaa_df_by_column_name(df, column)} for column in cls.CLOSED_CLASS_COLUMNS}

        for column in iaa_by_column:
            task = AnnotationTask(distance=jaccard_distance)
            task.load_array(extract_records_for_nltk(iaa_by_column[column]['df']))
            iaa_by_column[column]['alpha_jaccard'] = task.alpha()

            task = AnnotationTask(distance=masi_distance)
            task.load_array(extract_records_for_nltk(iaa_by_column[column]['df']))
            iaa_by_column[column]['alpha_masi'] = task.alpha()
        return iaa_by_column

    @classmethod
    def print_absolute_agreement(cls, dataframe: pd.DataFrame, iaa_by_column_dict: Optional[Dict] = None) -> None:
        if iaa_by_column_dict is None:
            iaa_by_column_dict = cls.run_closed_class_jaccard_and_masi(dataframe)
        for column in cls.CLOSED_CLASS_COLUMNS:
            df = iaa_by_column_dict[column]['df']
            print(f"Interannotator agreement for {column}")
            annotator_list = dataframe.source_spreadsheet.unique()
            print(" \t" + "\t".join([str(annotator) for annotator in annotator_list]))
            for a1 in annotator_list:
                a1_vals = list(df[df.source_spreadsheet == a1][column])
                print(f"{a1}", end="\t")
                pairwise_agreements = []
                for a2 in annotator_list:
                    a2_vals = list(df[df.source_spreadsheet == a2][column])
                    agreement_sum = 0
                    for a1_val, a2_val in zip(a1_vals, a2_vals):
                        agreement_sum += 1 - jaccard_distance(a1_val, a2_val)
                    pairwise_agreements.append(agreement_sum / min(len(a1_vals), len(a2_vals)))
                    print(f"{pairwise_agreements[-1]:.2f}", end="\t")
                print(f"\t{(sum(pairwise_agreements) - 1) / (len(pairwise_agreements) - 1):.2f}")
            print()
            print()


class IAAv1SpreadsheetScheme(IAASpreadsheetScheme):
    CLOSED_CLASS_COLUMNS = ["system_input", "system_output", "system_task", "criterion_paraphrase", "op_form",
                            "op_data_type", "op_instrument_type"]
    OPEN_CLASS_COLUMNS = ["system_application_domain",
                          "criterion_verbatim", "criterion_definition_verbatim", "criterion_definition_paraphrase",
                          "op_question_prompt_verbatim", "op_question_prompt_paraphrase", "op_instrument_size",
                          "op_response_values", "op_statistics"]
    ALL_DATA_COLUMNS = ["system_language", "system_input", "system_output", "system_task", "system_application_domain",
                        "criterion_verbatim", "criterion_definition_verbatim", "criterion_paraphrase",
                        "criterion_definition_paraphrase",
                        "op_form", "op_question_prompt_verbatim", "op_question_prompt_paraphrase", "op_data_type",
                        "op_instrument_type", "op_instrument_size", "op_response_values", "op_statistics"]
    METADATA_COLUMNS = ["key",
                        "annotator", "date_annotated", "double_checked_by", "date_double_checked", "annotation_comments", "exclude", "time_taken",
                        "pub_venue", "pub_authors", "pub_year", "pub_url"]
    ALL_COLUMNS = METADATA_COLUMNS + ALL_DATA_COLUMNS

    HIERARCHY_DICT = {"Quantitative Criteria":
                          ["Quantitative Criteria",
                           "Input Surface Form Retention", "Input Content Retention"],
                      "Quality of Surface Form":
                          ["Quality of Surface Form",
                           "Correctness of Surface Form", "Grammaticality", "Spelling Accuracy",
                           "Quality of Expression ('well-written')", "Speech Quality",
                           "Aesthetic Quality of Surface Form", "Appropriateness of form given context"],
                      "Quality of Content":
                          ["Quality of Content",
                           "Correctness of Content", "Correctness relative to input",
                           "Correctness relative to external reference",
                           "Answerability from input",
                           "Adequacy/Appropriateness", "Adequacy", "Adequacy Precision", "Adequacy Recall",
                           "Appropriateness given context",
                           "Quality of Content", "Informativeness", "Information - too much/not enough"],
                      "Quality of text as a whole":
                          ["Quality of text as a whole",
                           "Coherence", "Cohesion", "Wellorderedness", "Referent Resolvability",
                           "Complexity", "Complexity/Simplicity of Form", "Complexity/Simplicity of Content",
                           "Technicality/requires subject expertise",
                           "Naturalness",
                           "Naturalness (likelihood in context/situation)", "Naturalness (form)",
                           "Naturalness (content)",
                           "Conversationality", "Ease of Communication",
                           "Readability", "Fluency", "Clarity", "Understandability",
                           "Nonredundancy", "Nonredundancy (form)", "Nonredundancy (content)",
                           "Vagueness/Specificity", "Vagueness/Specificity (form)", "Vagueness/Specificity (content)",
                           "Variedness", "Variedness (form)", "Variedness (content)",
                           "Originality", "Originality (form)", "Originality (content)",
                           "Intended Property", "Detectability of Text Property"],
                      "Extralinguistic Quality":
                          ["Extralinguistic Quality",
                           "Criteria related to Listener/Reader", "Effect on listener",
                           "Inferrability of Speaker Stance", "Inferrability of Speaker Trait", "Learnability",
                           "Visualisability",
                           "Humanlikeness", "Humanlikeness (form)", "Humanlikeness (content)",
                           "Usefulness (nonspecific)", "Usefulness for task / information need",
                           "Criteria related to system", "User Satisfaction", "Usability"]}


class IAAv2SpreadsheetScheme(IAASpreadsheetScheme):
    CLOSED_CLASS_COLUMNS = ["system_input", "system_output", "system_task", "criterion_paraphrase", "op_form",
                            "op_data_type", "op_instrument_type"]
    OPEN_CLASS_COLUMNS = ["criterion_verbatim", "criterion_definition_verbatim", "criterion_definition_paraphrase",
                          "op_question_prompt_verbatim", "op_question_prompt_paraphrase", "op_instrument_size",
                          "op_response_values", "op_statistics"]
    ALL_DATA_COLUMNS = ["system_language", "system_input", "system_output", "system_task",
                        "op_response_values", "op_instrument_size", "op_instrument_type", "op_data_type", "op_form",
                        "op_question_prompt_verbatim", "op_question_prompt_paraphrase", "op_statistics",
                        "criterion_verbatim", "criterion_definition_verbatim", "criterion_paraphrase",
                        "criterion_definition_paraphrase"]
    METADATA_COLUMNS = ["key",
                        "annotator", "date_annotated", "annotation_comments", "exclude", "time_taken",
                        "pub_venue", "pub_authors", "pub_year", "pub_url",]
    ALL_COLUMNS = METADATA_COLUMNS + ALL_DATA_COLUMNS

    HIERARCHY_DICT = {"Correctness of outputs":
                          ["Correctness of outputs",
                           "Correctness of outputs in their own right",
                           "Correctness of outputs in their own right (form)",
                           "Grammaticality",
                           "Spelling accuracy",
                           "Correctness of outputs in their own right (content)",
                           "Correctness of outputs in their own right (both form and content)",
                           "Correctness of outputs relative to input",
                           "Correctness of outputs relative to input (form)",
                           "Correctness of outputs relative to input (content)",
                           "Correctness of outputs relative to input (both form and content)",
                           "Correctness of outputs relative to external frame of reference",
                           "Correctness of outputs relative to external frame of reference (form)",
                           "Correctness of outputs relative to external frame of reference (content)",
                           "Factual truth",
                           "Correctness of outputs relative to external frame of reference (both form and content)"
                           ],
                      "Goodness of outputs (excluding correctness)":
                          ["Goodness of outputs (excluding correctness)",
                           "Goodness of outputs in their own right",
                           "Goodness of outputs in their own right (form)",
                           "Speech quality",
                           "Nonredundancy (form)",
                           "Goodness of outputs in their own right (content)",
                           "Nonredundancy (content)",
                           "Information content of outputs",
                           "Coherence",
                           "Wellorderedness",
                           "Cohesion",
                           "Goodness of outputs in their own right (both form and content)",
                           "Readability",
                           "Fluency",
                           "Understandability",
                           "Clarity",
                           "Nonredundancy (both form and content)",
                           "Goodness of outputs relative to input",
                           "Goodness of outputs relative to input (form)",
                           "Goodness of outputs relative to input (content)",
                           "Answerability",
                           "Goodness of outputs relative to input (both form and content)",
                           "Goodness of outputs relative to external frame of reference",
                           "Goodness of outputs relative to linguistic context in which they are read/heard",
                           "Naturalness",
                           "Naturalness (form)",
                           "Naturalness (content)",
                           "Naturalness (both form and content)",
                           "Appropriateness",
                           "Appropriateness (form)",
                           "Appropriateness (content)",
                           "Appropriateness (both form and content)",
                           "Goodness of outputs relative to how humans use language",
                           "Humanlikeness",
                           "Humanlikeness (form)",
                           "Humanlikeness (content)",
                           "Humanlikeness (both form and content)",
                           "Goodness of outputs relative to system use",
                           "Goodness as system explanation",
                           "Usability",
                           "User satisfaction",
                           "Ease of communication",
                           "Usefulness (nonspecific)",
                           "Usefulness for task/information need",
                           "Goodness of outputs relative to grounding",
                           "Referent resolvability"
                           ],
                      "Feature-type criteria":
                          ["Feature-type criteria",
                           "Feature-type criteria assessed looking at outputs in their own right",
                           "Text Property [PROPERTY]",
                           "Text Property [Complexity/simplicity]",
                           "Text Property [Complexity/simplicity (form)]",
                           "Text Property [Complexity/simplicity (content)]",
                           "Text Property [Complexity/simplicity (both form and content)]"
                           "Feature-type criteria assessed looking at outputs and inputs",
                           "Detectability of controlled feature [PROPERTY]",
                           "Feature-type criteria assessed looking at outputs and external frame of reference",
                           "Effect on reader/listener [EFFECT]",
                           "Inferrability of speaker/author stance [OBJECT]",
                           "Inferrability of speaker/author trait [TRAIT]"
                           ]
                      }


class IAAv2ecSpreadsheetScheme(IAAv2SpreadsheetScheme):
    CLOSED_CLASS_COLUMNS = ["system_input", "system_output", "system_task", "criterion_paraphrase", "op_form",
                            "op_data_type", "op_instrument_type"]
    OPEN_CLASS_COLUMNS = ["criterion_verbatim", "criterion_definition_verbatim", "criterion_definition_paraphrase",
                          "op_question_prompt_verbatim", "op_question_prompt_paraphrase", "op_instrument_size",
                          "op_response_values", "op_statistics"]
    ALL_DATA_COLUMNS = ["system_language", "system_input", "system_output", "system_task",
                        "op_response_values", "op_instrument_size", "op_instrument_type", "op_data_type", "op_form",
                        "op_question_prompt_verbatim", "op_question_prompt_paraphrase", "op_statistics",
                        "criterion_verbatim", "criterion_definition_verbatim", "criterion_paraphrase",
                        "criterion_definition_paraphrase"]
    ALL_DATA_COLUMNS = [element for pair in zip(ALL_DATA_COLUMNS, [f"{x}_evidence_found" for x in ALL_DATA_COLUMNS]) for element in pair]
    ALL_DATA_COLUMNS = ALL_DATA_COLUMNS[:-4] + [ALL_DATA_COLUMNS[-4]] + [ALL_DATA_COLUMNS[-2]]

    METADATA_COLUMNS = ["key",
                        "annotator", "date_annotated",
                        "evidence_collector", "date_evidenced", "time_taken_evidence", "evidence_collector_comments",
                        "annotation_comments", "exclude", "time_taken",
                        "pub_venue", "pub_authors", "pub_year", "pub_url"]

    ALL_COLUMNS = METADATA_COLUMNS + ALL_DATA_COLUMNS

    @classmethod
    def prepare_df_from_google_sheets(cls, url_collection: Collection[str]) -> pd.DataFrame:
        spreadsheets = map(cls._GOOGLE_SESSION.open_by_url, url_collection)

        # Just the first sheet contains the annotations
        # There is a second sheet in each spreadsheet which contains the 'backing data',
        # i.e. the valid labels for closed-class categories in the annotation sheet
        annotation_sheets = [spreadsheet.worksheet("Annotation Sheet") for spreadsheet in spreadsheets]
        data = [sheet.get_all_values() for sheet in annotation_sheets]

        # The first two rows contain header information, so we drop this from the data we have loaded from each spreadsheet.
        end_of_doc_index = []
        for sheet in data:
            sections = sheet.pop(0)
            headers = sheet.pop(0)
            # Only read data in until the first column has a value "END_OF_DOC"
            keys = [row[0] for row in sheet]
            end_of_doc_index.append(keys.index('END_OF_DOC'))
        data = [sheet[:end_of_doc_index[i]] for i, sheet in enumerate(data)]

        dataframes = [pd.DataFrame(sheet) for sheet in data]

        # The full dataset is the concatenation of all of the loaded spreadsheets
        # where we have added a column representing which spreadsheet the data came from originally.
        annotation_df = pd.concat(dataframes, keys=range(1, len(dataframes) + 1))

        print(annotation_df.head())
        print(cls.ALL_COLUMNS)

        # Initially the columns have integer indices
        # We assign names to the columns
        annotation_df.columns = cls.ALL_COLUMNS

        # Drop rows marked for exclusion by their annotators
        annotation_df = annotation_df[annotation_df.exclude != "TRUE"]

        # Convert multilevel indices to simple indices via to_records()
        annotation_df = pd.DataFrame(annotation_df.to_records())

        # Drop the unnecessary within-spreadsheet index from the full dataset
        annotation_df = annotation_df.drop("level_1", 1)

        # Give the which-spreadsheet-did-it-come-from column a sensible name
        annotation_df.rename(columns={"level_0": "source_spreadsheet"},
                             errors="ignore",
                             inplace=True)

        return annotation_df


class IAAv2eaSpreadsheetScheme(IAAv2ecSpreadsheetScheme):
    ALL_DATA_COLUMNS = IAAv2ecSpreadsheetScheme.ALL_DATA_COLUMNS
    ALL_DATA_COLUMNS = ALL_DATA_COLUMNS[:8] + ["system_evidence_found"] + ALL_DATA_COLUMNS[8:16] + ["operationalisation_evidence_found"] + ALL_DATA_COLUMNS[16:] + ["criterion_evidence_found"]

    ALL_COLUMNS = IAAv2ecSpreadsheetScheme.METADATA_COLUMNS + ALL_DATA_COLUMNS
