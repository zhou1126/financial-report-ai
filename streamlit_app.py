import streamlit as st
from sec_edgar_downloader import Downloader
import os
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime

from utility import get_dates_for_year, report_download, find_subdirectories, find_txt_files, item_extraction_10K, html_removal

from openai import OpenAI

st.title("Financial Report AI analyst")
# st.write(
#     "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
# )

# no api key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
st.session_state.ticker = st.text_input("**Enter the ticker**", value = "")
print(st.session_state.ticker)

st.session_state.report_type = st.selectbox(
                                                "Which report do you want AI to analyze?",
                                                ("10-K", "10-Q"),
                                            )
# st.write("You selected:", st.session_state.report_type)

st.session_state.year = st.number_input("**Year of Report**", value = 2024)
# st.session_state.year = int(st.session_state.year)
print(st.session_state.year)

account_email = 'zhou60302@gmail.com'
# test
st.write(f'You are asking to analyze {st.session_state.year} {st.session_state.report_type} report of {st.session_state.ticker}')

after_date, before_date = get_dates_for_year(st.session_state.year)
print(after_date, before_date)
tgt_dir = report_download(st.session_state.ticker, st.session_state.report_type, account_email, after_date, before_date)

# # print(tgt_dir)

if tgt_dir:
    subdirectories = find_subdirectories(tgt_dir)
    right_subdir = ''
    right_txt = ''
    # Print all subdirectories
    for subdir in subdirectories:
        # print(subdir)
        data_year = int(subdir.split("/")[-1].split("-")[1]) + 2000
        # print(data_year)
        if data_year == st.session_state.year:
            right_subdir = subdir
    
    print(right_subdir)

    txt_files = find_txt_files(right_subdir)

    if len(txt_files) == 1:
        right_txt = txt_files[0]
    else: 
        # Print all .txt files found
        for txt_file in txt_files:
            txt_file_name = txt_file.split("/")[-1].split(".")[0]
            if txt_file_name == 'full-submission':
                right_txt = txt_file

    print(right_txt)

    raw_1a, raw_7, raw_7a, raw_8 = item_extraction_10K(right_txt)

    polished_1a = html_removal(raw_1a)
    polished_7 = html_removal(raw_7)
    polished_7a = html_removal(raw_7a)
    polished_8 = html_removal(raw_8)

    management_prompt = '\n'.join([
        'You are a financial analyst and you are going to read selected chapters of a 10-K report from a company. The following is the Item 1a, the Risk Factors.',
        polished_1a,
        'Item 7 Management Discussion and Analysis',
        polished_7,
        'Item 7a Quantitative and Qualitative Disclosures About Market Risk',
        polished_7a,
        'Summarize the following from the content you received: ',
        'Main Strategies that the company is going to use',
        'Main Market or Company Risks',
        'Main Merger and Acquisition activities that have finalized or are being considered',
        'New Organic Growth initiatives',
        'Macroeconomics opportunities and concerns',
        'If you do not find the corresponding data and say you do not find the data.'
    ])

    financial_report_prompt = '\n'.join([
        'You are a financial analyst and you are going to read Financial Statements and Supplementary Data of a 10-K report from a company. The data is as follows and contains the current year and previous year or years data.',
        polished_8,
        'Find the corresponding metric, Origination Dollar, Total Receivables, and analyze the Year-Over-Year and Quarter-Over-Quarter growth trend',
        'Find the corresponding metric, Revenue, Net Interest Margin total in dollar terms and per dollar receivable term, Charge-off in percentage of receivables, Operation expense in dollar terms and per dollar receivable, EBITDA, Cost of Fund,and analyze the Year-Over-Year and Quarter-Over-Quarter growth trend',
        'Main Merger and Acquisition activities that have finalized or are being considered',
        'New Organic Growth initiatives',
        'Macroeconomics opportunities and concerns',
        'If you do not find the corresponding data and say you do not find the data.'
    ])

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            # {"role": "system", "content": "You are a financial analyst"},
            {
                "role": "user",
                "content": management_prompt
            }
        ],
        stream=True
    )
    management_results = st.write_stream(completion)
    # print(completion.choices[0].message.content)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            # {"role": "system", "content": "You are a financial analyst"},
            {
                "role": "user",
                "content": financial_report_prompt
            }
        ],
        stream=True
    )

    report_results = st.write_stream(completion)

    # print(compldfetion.choices[0].message.content)