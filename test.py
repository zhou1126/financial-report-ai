from openai import OpenAI
import streamlit as st

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

from utility import report_download, get_dates_for_year, find_subdirectories, find_txt_files, item_extraction_10Q, item_extraction_10K, html_removal
account_email = 'zhou60302@gmail.com'
year = 2024
after_date, before_date = get_dates_for_year(year)
report_type = '10-Q'
ticker = 'DLTR'

# Yixiang cases
# 'OMF', 'DFS', 'COF'
# test cases
# 'DLTR', 'TSLA', 'BRC'
# failed
# 'NIO'

# ticker = 'TSLA'
# ticker = 'BRC'
print(after_date, before_date)
tgt_dir = report_download(ticker, report_type, account_email, after_date, before_date)
print(tgt_dir)
subdirectories = find_subdirectories(tgt_dir)
print(subdirectories)

right_subdir = []
right_txt = []
# Print all subdirectories
for subdir in subdirectories:
    # print(subdir)
    data_year = int(subdir.split("/")[-1].split("-")[1]) + 2000
    # print(data_year)
    if data_year == year:
        right_subdir.append(subdir)

print(right_subdir)

txt_files = find_txt_files(right_subdir)
print(txt_files)

for txt_file in txt_files:
    txt_file_name = txt_file.split("/")[-1].split(".")[0]
    if txt_file_name == 'full-submission':
        right_txt.append(txt_file)

print(right_txt)

for r_txt in right_txt[0:1]:
    print(r_txt)
    if report_type == '10-K':
        start_10k_raw, item1a_10k_raw, item7_10k_raw, item7a_10k_raw, item8_10k_raw = item_extraction_10K(r_txt)
        polished_start_10k = html_removal(start_10k_raw)
        polished_1a = html_removal(item1a_10k_raw)
        polished_7 = html_removal(item7_10k_raw)
        polished_7a = html_removal(item7a_10k_raw)
        polished_8 = html_removal(item8_10k_raw)
        # print(polished_7)
    elif report_type == '10-Q':
        start_10q_raw, item1_10q_raw, item2_10q_raw, item3_10q_raw = item_extraction_10Q(r_txt)
        polished_start_10q = html_removal(start_10q_raw)
        polished_item1_10q = html_removal(item1_10q_raw)
        polished_item2_10q = html_removal(item2_10q_raw)
        polished_item3_10q = html_removal(item3_10q_raw)
        # print(polished_item3_10q)
