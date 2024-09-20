# from openai import OpenAI
# import streamlit as st

# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

from utility import report_download, get_dates_for_year, find_subdirectories, find_txt_files
account_email = 'zhou60302@gmail.com'
year = 2024
after_date, before_date = get_dates_for_year(year)
print(after_date, before_date)
tgt_dir = report_download('TSLA', '10-Q', account_email, after_date, before_date)
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

