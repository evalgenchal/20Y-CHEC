import pandas as pd
from collections import defaultdict, Counter

def get_index(filename):
		"""
		Load the Excel file and generate an index, based on the key of the paper.
		If there is no key, skip the row.
		"""
		df = pd.read_excel(filename, sheet_name=0,header=1)
		# Replace all NaN in empty fields with the empty string.
		df.replace(float('nan'), '', regex=True,inplace=True)
		df.columns = ["key", "annotator", "date_annotated", "annotation_comments", 
									"exclude", "time_taken", "pub_venue", "pub_authors", "pub_year", 
									"pub_url", "system_language", "system_input", "system_output", 
									"system_task", "op_response_values", "op_instrument_size", 
									"op_instrument_type", "op_data_type", "op_form", 
									"op_question_prompt_verbatim", "op_question_prompt_paraphrase", 
									"op_statistics", "criterion_verbatim", "criterion_definition_verbatim", 
									"criterion_paraphrase", "criterion_definition_paraphrase"]
		df["criterion_verbatim"] = df["criterion_verbatim"].astype(str)
		records = df.to_dict('records')
		index = defaultdict(list)
		for record in records:
				key = record['key']
				if record["exclude"] == 'TRUE':
						continue
				elif record["annotator"] == "DG":
						continue
				elif key == 'END_OF_DOC':
						break
				index[key].append(record)
		return index
