import streamlit as st
from sec_edgar_downloader import Downloader
import os
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime

from utility import get_dates_for_year, report_download, find_subdirectories, find_txt_files, process_report
from openai import OpenAI

st.title("Financial Report AI analyst")

# no api key
# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
st.session_state.ticker = st.text_input("**Enter the ticker**", value = "")
print(st.session_state.ticker)

st.session_state.reference_ticker = st.text_input("**Enter the reference company ticker**", value = "")
print(st.session_state.reference_ticker)

st.session_state.report_type = st.selectbox(
                                                "Which report do you want AI to analyze?",
                                                ("10-K", "10-Q"),
                                            )
# st.write("You selected:", st.session_state.report_type)

st.session_state.year = st.number_input("**Year of Report**", value = 2024)
st.run_button = st.button('Run the analysis')

# st.session_state.year = int(st.session_state.year)
print(st.session_state.year)

account_email = 'zhou60302@gmail.com'

if st.run_button: 
    # test
    st.write(f'We are analyzing {st.session_state.year} {st.session_state.report_type} report of {st.session_state.ticker}')
    st.write(f'Data Source: U.S. Securities and Exchange Commission (SEC), Electronic Data Gathering, Analysis, and Retrieval system (EDGAR)')

    # Get the reporting year
    after_date, before_date = get_dates_for_year(st.session_state.year)
    print(after_date, before_date)

    # Download targeting company report
    tgt_dir = report_download(st.session_state.ticker, st.session_state.report_type, account_email, after_date, before_date)

    if st.session_state.reference_ticker:
        ref_tgt_dir = report_download(st.session_state.reference_ticker, st.session_state.report_type, account_email, after_date, before_date)
        print(ref_tgt_dir)

    if tgt_dir:
        subdirectories = find_subdirectories(tgt_dir)
        right_subdir = []
        right_txt = []
        # Print all subdirectories
        for subdir in subdirectories:
            # print(subdir)
            data_year = int(subdir.split("/")[-1].split("-")[1]) + 2000
            # print(data_year)
            if data_year == st.session_state.year:
                right_subdir.append(subdir)

        # print(right_subdir)

        txt_files = find_txt_files(right_subdir)
        # print(txt_files)

        for txt_file in txt_files:
            txt_file_name = txt_file.split("/")[-1].split(".")[0]
            if txt_file_name == 'full-submission':
                right_txt.append(txt_file)

        # print(right_txt)
        if st.session_state.report_type == '10-K':
            start_results_10K, management_results_10K, report_results_10K = process_report('10-K', right_txt[0:1])
        elif st.session_state.report_type == '10-Q':
            start_results_10Q, management_results_10Q, report_results_10Q = process_report('10-Q', right_txt[0:])