import streamlit as st
from sec_edgar_downloader import Downloader
import os
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime

from utility import get_dates_for_year, report_download, find_subdirectories, find_txt_files, item_extraction_10K, html_removal, item_extraction_10Q
from utility import starter_prompt, management_prompt_gen, financial_prompt_gen, financial_analysis_report
from openai import OpenAI

st.title("Financial Report AI analyst")

# no api key
# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
st.session_state.ticker = st.text_input("**Enter the ticker**", value = "")
print(st.session_state.ticker)

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

    after_date, before_date = get_dates_for_year(st.session_state.year)
    print(after_date, before_date)
    tgt_dir = report_download(st.session_state.ticker, st.session_state.report_type, account_email, after_date, before_date)

    # # print(tgt_dir)

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
            for r_txt in right_txt[0:1]:
                start_10k_raw, item1a_10k_raw, item7_10k_raw, item7a_10k_raw, item8_10k_raw = item_extraction_10K(r_txt)

                polished_start_10k = html_removal(start_10k_raw)
                polished_1a = html_removal(item1a_10k_raw)
                polished_7 = html_removal(item7_10k_raw)
                polished_7a = html_removal(item7a_10k_raw)
                polished_8 = html_removal(item8_10k_raw)

                # Load start prompt
                start_prompt_10K = starter_prompt(polished_start_10k, '10-K')

                # Load management analysis prompt for strategy analysis
                management_prompt_10K = management_prompt_gen(polished_1a, polished_7, polished_7a, '10-K')        

                # Load financial metrics
                financial_report_prompt_10K = financial_prompt_gen(polished_8, '10-K')

                # Show results
                start_results_10K, management_results_10K, report_results_10K = financial_analysis_report(start_prompt_10K, management_prompt_10K, financial_report_prompt_10K)

        elif st.session_state.report_type == '10-Q':
            for r_txt in right_txt[0:]:
                start_10q_raw, item1_10q_raw, item2_10q_raw, item3_10q_raw = item_extraction_10Q(r_txt)

                polished_start_10q = html_removal(start_10q_raw)
                polished_item1_10q = html_removal(item1_10q_raw)
                polished_item2_10q = html_removal(item2_10q_raw)
                polished_item3_10q = html_removal(item3_10q_raw)

                # Load start prompt
                start_prompt_10Q = starter_prompt(polished_start_10q, '10-Q')

                # Load management prompt
                management_prompt_10Q = management_prompt_gen(polished_item2_10q, polished_item3_10q, '', '10-Q')
                
                # Load financial metrics
                financial_report_prompt_10Q = financial_prompt_gen(polished_item1_10q, '10-Q')

                # results_showing_in_UI
                start_results_10Q, management_results_10Q, report_results_10Q = financial_analysis_report(start_prompt_10Q, management_prompt_10Q, financial_report_prompt_10Q)
                
