import streamlit as st
from sec_edgar_downloader import Downloader
import os
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime

from openai import OpenAI

st.title("Financial Report AI analyst")
# st.write(
#     "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
# )

client = OpenAI(api_key = "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")
# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
st.session_state.ticker = st.text_input("**Enter the ticker**", value = "")
print(st.session_state.ticker)

st.session_state.report_type = st.selectbox(
                                                "Which report do you want AI to analyze?",
                                                ("10-K"),
                                            )
# st.write("You selected:", st.session_state.report_type)

st.session_state.year = st.text_input("**Year of Report**", value = "")
print(st.session_state.year)

st.write(f'You are asking to analyze {st.session_state.year} {st.session_state.report_type} report of {st.session_state.report_type}')

def get_dates_for_year(year):
    current_year = datetime.now().year
    current_date = datetime.now()
    
    # First date of the given year
    after_date = datetime(year, 1, 1)
    
    if year == current_year:
        # If the given year is the current year, set before_date to the current date
        before_date = current_date
    else:
        # If the year is not the current year, set before_date to the last date of that year
        before_date = datetime(year, 12, 31)
    
    return after_date, before_date

def report_download(ticker, report_type, account_email, after_date, before_date):
    target_dir = ''
    try: 
        dl = Downloader(ticker, account_email)
        dl.get(report_type, ticker, after=after_date, before=before_date)
        base_dir = os.getcwd()
        target_dir = os.path.join(base_dir, "sec-edgar-filings", ticker, report_type)
        print(f"Downloading 10-K filings for {ticker} between {after_date} and {before_date}...")
        print(f"Successfully downloaded 10-K filings for {ticker} between {after_date} and {before_date}")
    except Exception as e:
            print(f"Error downloading 10-K filings for {ticker}: {e}")
    return target_dir

def find_subdirectories(tgt_dir):
    subdirs = []
    # Walk through the directory
    for root, dirs, files in os.walk(tgt_dir):
        # Append each subdirectory to the list
        for dir_name in dirs:
            subdirs.append(os.path.join(root, dir_name))
    return subdirs

def find_txt_files(directory):
    txt_files = []
    
    # Walk through the directory
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            # Check if the file has a .txt extension
            if file_name.endswith('.txt'):
                # Add the full path of the .txt file to the list
                txt_files.append(os.path.join(root, file_name))
    
    return txt_files

def item_extraction(txt_data): 

    with open(txt_data, 'r', encoding='utf-8') as f:
        text_content = f.read()

    # Regex to find <DOCUMENT> tags
    doc_start_pattern = re.compile(r'<DOCUMENT>')
    doc_end_pattern = re.compile(r'</DOCUMENT>')
    # Regex to find <TYPE> tag prceeding any characters, terminating at new line
    type_pattern = re.compile(r'<TYPE>[^\n]+')

    # Create 3 lists with the span idices for each regex

    ### There are many <Document> Tags in this text file, each as specific exhibit like 10-K, EX-10.17 etc
    ### First filter will give us document tag start <end> and document tag end's <start> 
    ### We will use this to later grab content in between these tags
    doc_start_is = [x.end() for x in doc_start_pattern.finditer(text_content)]
    doc_end_is = [x.start() for x in doc_end_pattern.finditer(text_content)]

    ### Type filter is interesting, it looks for <TYPE> with Not flag as new line, ie terminare there, with + sign
    ### to look for any char afterwards until new line \n. This will give us <TYPE> followed Section Name like '10-K'
    ### Once we have have this, it returns String Array, below line will with find content after <TYPE> ie, '10-K' 
    ### as section names
    doc_types = [x[len('<TYPE>'):] for x in type_pattern.findall(text_content)]

    document = {}

    # Create a loop to go through each section type and save only the 10-K section in the dictionary
    for doc_type, doc_start, doc_end in zip(doc_types, doc_start_is, doc_end_is):
        if doc_type == '10-K':
            document[doc_type] = text_content[doc_start:doc_end]

    # Write the regex
    regex = re.compile(r'(>Item(\s|&#160;|&nbsp;)(1A|1B|1C|7A|7|8|9A)\.{0,1})|(ITEM\s(1A|1B|1C|7A|7|8|9A))')

    # Use finditer to math the regex
    matches = regex.finditer(document['10-K'])

    print(matches)

    # Create the dataframe
    test_df = pd.DataFrame([(x.group(), x.start(), x.end()) for x in matches])

    test_df.columns = ['item', 'start', 'end']
    test_df['item'] = test_df.item.str.lower()

    test_df = test_df.loc[test_df.groupby('item')['start'].idxmax()].reset_index(drop=True)

    # Get rid of unnesesary charcters from the dataframe
    test_df.replace('&#160;',' ',regex=True,inplace=True)
    test_df.replace('&nbsp;',' ',regex=True,inplace=True)
    test_df.replace(' ','',regex=True,inplace=True)
    test_df.replace('\.','',regex=True,inplace=True)
    test_df.replace('>','',regex=True,inplace=True)

    # Drop duplicates
    pos_dat = test_df.sort_values('start', ascending=True).drop_duplicates(subset=['item'], keep='last')

    # Set item as the dataframe index
    pos_dat.set_index('item', inplace=True)

    # print(pos_dat)

    # Get Item 1a Risk Factors
    item_1a_raw = document['10-K'][pos_dat['start'].loc['item1a']:pos_dat['start'].loc['item1b']]

    # Get Item 1b Unresolved Staff Comments
    # item_1b_raw = document['10-K'][pos_dat['start'].loc['item1b']:pos_dat['start'].loc['item1c']]

    # Get Item 7 MD&A
    item_7_raw = document['10-K'][pos_dat['start'].loc['item7']:pos_dat['start'].loc['item7a']]

    # Get Item 7A Quantitative and Qualitative Disclosures About Market Risk
    item_7a_raw = document['10-K'][pos_dat['start'].loc['item7a']:pos_dat['start'].loc['item8']]

    # Get Item 8 Financial Statements and Supplementary Data
    item_8_raw = document['10-K'][pos_dat['start'].loc['item8']:pos_dat['start'].loc['item9a']]

    return item_1a_raw, item_7_raw, item_7a_raw, item_8_raw

def html_removal(raw_source):
    source = BeautifulSoup(raw_source, 'html.parser')
    source = source.get_text("\n\n")
    return source 

after_date, before_date = get_dates_for_year(year)
print(after_date, before_date)
tgt_dir = report_download(ticker, report_type, account_email, after_date, before_date)

# print(tgt_dir)

if tgt_dir:
    subdirectories = find_subdirectories(tgt_dir)
    right_subdir = ''
    right_txt = ''
    # Print all subdirectories
    for subdir in subdirectories:
        # print(subdir)
        data_year = int(subdir.split("/")[-1].split("-")[1]) + 2000
        # print(data_year)
        if data_year == year:
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

    raw_1a, raw_7, raw_7a, raw_8 = item_extraction(right_txt)

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
        ]
    )
    management_results = st.write_stream(completion.choices[0].message.content)
    # print(completion.choices[0].message.content)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            # {"role": "system", "content": "You are a financial analyst"},
            {
                "role": "user",
                "content": financial_report_prompt
            }
        ]
    )

    report_results = st.write_stream(completion.choices[0].message.content)

    # print(completion.choices[0].message.content)