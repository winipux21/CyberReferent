import pandas as pd
import re

def load_vak_list(path='data/VAK_journals.csv'):
    return pd.read_csv(path)

def find_journal_name(reference):
    match = re.search(r'//\s*(.*?)\.\s*\d{4}', reference)
    if match:
        return match.group(1).strip().lower()
    return ""

def validate_references(references, vak_df):
    valid, invalid = [], []
    vak_journals_lower = vak_df['journal'].str.lower().tolist()

    for ref in references:
        journal_name = find_journal_name(ref)
        if journal_name:
            found = [j for j in vak_journals_lower if journal_name in j or j in journal_name]
            if found:
                matched_journal = vak_df[vak_df['journal'].str.lower() == found[0]].iloc[0]
                valid.append((ref, matched_journal['journal'], matched_journal['ISSN']))
            else:
                invalid.append(ref)
        else:
            invalid.append(ref)
    return valid, invalid
