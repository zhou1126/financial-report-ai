from sec_edgar_downloader import Downloader
import os
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime
from openai import OpenAI
import streamlit as st

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
        print(f"Downloading {report_type} filings for {ticker} between {after_date} and {before_date}...")
        print(f"Successfully downloaded {report_type} filings for {ticker} between {after_date} and {before_date}")
    except Exception as e:
            print(f"Error downloading {report_type} filings for {ticker}: {e}")
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
    for dir_pick in directory:
        for root, dirs, files in os.walk(dir_pick):
            for file_name in files:
                # Check if the file has a .txt extension
                if file_name.endswith('.txt'):
                    # Add the full path of the .txt file to the list
                    txt_files.append(os.path.join(root, file_name))
    
    return txt_files

def prep_txt(txt_data, report_type):

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
    # print(doc_types)
    # print(report_type)
    document = {}

    # Create a loop to go through each section type and save only the 10-K section in the dictionary
    for doc_type, doc_start, doc_end in zip(doc_types, doc_start_is, doc_end_is):
        print(doc_type, doc_start, doc_end)
        if doc_type == report_type:
            document[doc_type] = text_content[doc_start:doc_end]
            break  
    return document[report_type]

def item_extraction_10K(txt_data): 

    document = {}
    document['10-K'] = prep_txt(txt_data, '10-K')
    # Write the regex
    regex = re.compile(r'(>Item(\s|&#160;|&nbsp;)(1A|1B|1C|7A|7|8|9A)\.{0,1})|(ITEM\s(1A|1B|1C|7A|7|8|9A))')

    # Use finditer to math the regex
    matches = regex.finditer(document['10-K'])

    # print(matches)

    # Create the dataframe
    test_df = pd.DataFrame([(x.group(), x.start(), x.end()) for x in matches])

    test_df.columns = ['item', 'start', 'end']
    test_df['item'] = test_df.item.str.lower()

    # Get rid of unnesesary charcters from the dataframe
    test_df.replace('&#160;',' ',regex=True,inplace=True)
    test_df.replace('&nbsp;',' ',regex=True,inplace=True)
    test_df.replace(' ','',regex=True,inplace=True)
    test_df.replace('\.','',regex=True,inplace=True)
    test_df.replace('>','',regex=True,inplace=True)

    print('debug')
    print(test_df)

    # Initialize lists to store the cleaned data
    cleaned_items = []
    cleaned_starts = []
    cleaned_ends = []

    # Define the correct order of items
    correct_order = ['item1a', 'item1b', 'item1c', 'item7', 'item7a', 'item8', 'item9']

    # Initialize variables to keep track of the last valid position and item
    last_end = 0
    last_item = None

    # Iterate through the correct order

    for item in correct_order:
        # Find all rows for the current item
        item_rows = test_df[test_df['item'].str.startswith(item)]
        print(item_rows)
        if not item_rows.empty:
            for _, row in item_rows.iterrows():
                print(row['start'], last_end)
                # Check if the current start is greater than the last end
                if row['start'] > last_end:
                    # For item2, check if it starts at least 100000 after item1
                    if item == 'item1b' and last_item == 'item1a' and row['start'] < last_end + 100000:
                        continue

                    if item == 'item9a' and last_item == 'item8' and row['start'] < last_end + 10000:
                        continue
                    
                    # Add the item to the cleaned data
                    cleaned_items.append(row['item'])
                    cleaned_starts.append(row['start'])
                    cleaned_ends.append(row['end'])
                    
                    # Update the last end position and item
                    last_end = row['end']
                    last_item = item
                    
                    # Break the loop as we only want one instance of each item
                    break
                # If the item is not found and it's item3, use the end of item2
        if item not in cleaned_items:
            cleaned_items.append(item)
            cleaned_starts.append(last_end)
            cleaned_ends.append(last_end)
            last_item = item


    # for item in correct_order:
    #     # Find all rows for the current item
    #     item_rows = test_df[test_df['item'].str.startswith(item)]
        
    #     for _, row in item_rows.iterrows():
    #         # Check if the current start is greater than the last end
    #         if row['start'] > last_end:
    #             # For item1b, check if it starts at least 100000 after item1a
    #             if item == 'item1b' and last_item == 'item1a' and row['start'] < last_end + 100000:
    #                 continue
                
    #             # Add the item to the cleaned data
    #             cleaned_items.append(row['item'])
    #             cleaned_starts.append(row['start'])
    #             cleaned_ends.append(row['end'])
                
    #             # Update the last end position and item
    #             last_end = row['end']
    #             last_item = item
                
    #             # Break the loop as we only want one instance of each item
    #             break

    # Create a new DataFrame with the cleaned data
    cleaned_data = pd.DataFrame({
        'item': cleaned_items,
        'start': cleaned_starts,
        'end': cleaned_ends
    })
    print(cleaned_data)

    # WORKING FOR TSLA, COULD BE IDXMIN
    #######################################################################################################
    # test_df.to_csv('test_2.csv', index = False)
    # test_df = test_df.sort_values(by = ['item', 'start'], ascending= True)
    # print(test_df)
    # # test_df = test_df.loc[test_df.groupby('item')['start'].idxmax()].reset_index(drop=True)
    # test_df = test_df.loc[test_df.groupby('item')['start'].idxmax()].reset_index(drop=True)
    # print(test_df)
    # pos_dat = test_df.sort_values('start', ascending=True).drop_duplicates(subset=['item'], keep='last')
    #######################################################################################################
    # Drop duplicates
    pos_dat = cleaned_data.sort_values('start', ascending=True).drop_duplicates(subset=['item'], keep='last')

    # Set item as the dataframe index
    pos_dat.set_index('item', inplace=True)

    # print(pos_dat)
    # Get start 
    item_start_raw = document['10-K'][0:pos_dat['start'].loc['item1a']]

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

    return item_start_raw, item_1a_raw, item_7_raw, item_7a_raw, item_8_raw

def item_extraction_10Q(txt_data): 

    document = {}
    document['10-Q'] = prep_txt(txt_data, '10-Q')

    # Write the regex
    regex = re.compile(r'(>Item(\s|&#160;|&nbsp;)(1|2|3|4)\.{0,1})|(ITEM\s(1|2|3|4))|(Item\s(1|2|3|4))')

    # Use finditer to math the regex
    matches = regex.finditer(document['10-Q'])

    # print(matches)

    # Create the dataframe
    test_df = pd.DataFrame([(x.group(), x.start(), x.end()) for x in matches])
    # print(test_df)

    test_df.columns = ['item', 'start', 'end']
    test_df['item'] = test_df.item.str.lower()
    # test_df = test_df.loc[test_df.groupby('item')['start'].idxmin()].reset_index(drop=True)
    # print(test_df)

    # Get rid of unnesesary charcters from the dataframe
    test_df.replace('&#160;',' ',regex=True,inplace=True)
    test_df.replace('&nbsp;',' ',regex=True,inplace=True)
    test_df.replace(' ','',regex=True,inplace=True)
    test_df.replace('\.','',regex=True,inplace=True)
    test_df.replace('>','',regex=True,inplace=True)
    print(test_df)
    # Work for TSLA
    ############################################################################################################
    # test_df = test_df.sort_values(by = ['item', 'start'], ascending= True)
    # print(test_df)
    # # test_df = test_df.loc[test_df.groupby('item')['start'].idxmax()].reset_index(drop=True)
    # test_df = test_df.loc[test_df.groupby('item')['start'].idxmin()].reset_index(drop=True)
    # print(test_df)
    # pos_dat = test_df.sort_values('start', ascending=True).drop_duplicates(subset=['item'], keep='first')
    ############################################################################################################

    # Initialize lists to store the cleaned data
    cleaned_items = []
    cleaned_starts = []
    cleaned_ends = []

    # Define the correct order of items
    correct_order = ['item1', 'item2', 'item3', 'item4']

    # Initialize variables to keep track of the last valid position and item
    last_end = 0
    last_item = None

    # Iterate through the correct order
    for item in correct_order:
        # Find all rows for the current item
        item_rows = test_df[test_df['item'].str.startswith(item)]
        print(item_rows)
        if not item_rows.empty:
            for _, row in item_rows.iterrows():
                print(row['start'], last_end)
                # Check if the current start is greater than the last end
                if row['start'] > last_end:
                    # For item2, check if it starts at least 100000 after item1
                    if item == 'item2' and last_item == 'item1' and row['start'] < last_end + 100000:
                        continue
                    
                    # Add the item to the cleaned data
                    cleaned_items.append(row['item'])
                    cleaned_starts.append(row['start'])
                    cleaned_ends.append(row['end'])
                    
                    # Update the last end position and item
                    last_end = row['end']
                    last_item = item
                    
                    # Break the loop as we only want one instance of each item
                    break
                # If the item is not found and it's item3, use the end of item2
        if item not in cleaned_items:
            cleaned_items.append(item)
            cleaned_starts.append(last_end)
            cleaned_ends.append(last_end)
            last_item = item

    # Create a new DataFrame with the cleaned data
    cleaned_data = pd.DataFrame({
        'item': cleaned_items,
        'start': cleaned_starts,
        'end': cleaned_ends
    })
    print(cleaned_data)

    # Drop duplicates
    pos_dat = cleaned_data.sort_values('start', ascending=True).drop_duplicates(subset=['item'], keep='first')

    # Set item as the dataframe index
    pos_dat.set_index('item', inplace=True)
    # print(pos_dat)

    # Get start 
    item_start_raw = document['10-Q'][0:pos_dat['start'].loc['item1']]

    # Get Item 1 FINANCIAL STATEMENTS
    item_1_raw = document['10-Q'][pos_dat['start'].loc['item1']:pos_dat['start'].loc['item2']]
    # print(item_1a_raw)

    # # Get Item 2 Management’s Discussion and Analysis of Financial Condition and Results of Operations
    item_2_raw = document['10-Q'][pos_dat['start'].loc['item2']:pos_dat['start'].loc['item3']]
    # print(item_1a_raw)

    # # Get Item 3 Quantitative and Qualitative Disclosures About Market Risk
    item_3_raw = document['10-Q'][pos_dat['start'].loc['item3']:pos_dat['start'].loc['item4']]
    # print(item_3_raw)

    return item_start_raw, item_1_raw, item_2_raw, item_3_raw

def html_removal(raw_source):
    source = BeautifulSoup(raw_source, 'html.parser')
    source = source.get_text("\n\n")
    return source 

def starter_prompt(content, report_type):
    if report_type == '10-K':
        start_prompt = '\n'.join([
                    f'You are a financial analyst and you are going to read selected chapters of a {report_type} report from a company. The following is the introduction of the company and the publish date of the {report_type}.',
                    content,
                    'Summarize the following from the content you received with a title of "Basic information about the form and company": ',
                    'Company Name: ',
                    'Company Address: ',
                    'Trading Symbol(s): ',
                    'Name of each exchange on which registered: ',
                    'Commission File Number: ',
                    'For the Quarterly Period Ended: ',
                ])
    elif report_type == '10-Q':
        start_prompt = '\n'.join([
                    f'You are a financial analyst and you are going to read selected chapters of a {report_type} report from a company. The following is the introduction of the company and the publish date of the {report_type}.',
                    content,
                    'Summarize the following from the content you received: ',
                    'Company Name: ',
                    'Company Address: ',
                    'Trading Symbol(s): ',
                    'Name of each exchange on which registered: ',
                    'Commission File Number: ',
                    'For the Quarterly Period Ended: '
                ])
    else:
        start_prompt = 'Please show we did not receive any information'
    return start_prompt

def management_prompt_gen(content1, content2, content3, report_type):
    if report_type == '10-K':
        return_prompt = '\n'.join([f"As a seasoned financial analyst, you've been tasked with reviewing key sections of a company's latest {report_type} report. You've carefully examined Item 1a (Risk Factors), Item 7 (Management's Discussion and Analysis), and Item 7a (Quantitative and Qualitative Disclosures About Market Risk). Based on your analysis, please provide insights on the following areas:",
                                content1,
                                "Management's Discussion and Analysis:",
                                content2,
                                "Quantitative and Qualitative Disclosures About Market Risk:",
                                content3,
                                "In your professional opinion, please highlight:",
                                "1. The company's core strategic initiatives for the upcoming year",
                                "2. Critical risks facing the company or its market",
                                "3. Recent or potential M&A activity that could impact the company's trajectory",
                                "4. Promising organic growth opportunities the company is pursuing",
                                "5. Relevant macroeconomic factors that could affect the company's performance",
                                "Please note any areas where information is limited or unavailable in your analysis. Your insights will be crucial for our investment decision-making process."
                                ])
    elif report_type == '10-Q':
        content3 = ''
        return_prompt = '\n'.join([
                    f'You are a financial analyst and you are going to read selected chapters of a {report_type} report from a company. The following is the Item 2, Management’s Discussion and Analysis of Financial Condition and Results of Operations.',
                    content1,
                    'Item 3 Quantitative and Qualitative Disclosures About Market Risk',
                    content2,
                    'Summarize the following from the content you received: ',
                    'Main Strategies that the company is going to use',
                    'Main Market or Company Risks',
                    'Main Merger and Acquisition activities that have finalized or are being considered',
                    'New Organic Growth initiatives',
                    'Macroeconomics opportunities and concerns',
                    'If you do not find the corresponding data and say you do not find the data.'
                ])
    else:
        return_prompt = 'Please show we did not receive any information'
    return return_prompt

def financial_prompt_gen(content, report_type):
    common_prompts = [
        f"You are a financial analyst reviewing the {report_type} report of a company. Analyze the following financial data, focusing on key metrics and their trends:",
        content,
        "1. Growth Metrics:",
        "   a) Origination Dollar: Provide YoY and QoQ growth rates.",
        "   b) Total Receivables: Provide YoY and QoQ growth rates.",
        "2. Profitability Metrics:",
        "   a) Revenue: State the amount and calculate YoY and QoQ growth rates.",
        "   b) Net Interest Margin: Provide total dollar amount and per dollar receivable. Calculate YoY and QoQ changes.",
        "   c) EBITDA: State the amount and calculate YoY and QoQ growth rates.",
        "3. Efficiency Metrics:",
        "   a) Charge-off as a percentage of receivables: State the percentage and note any YoY or QoQ changes.",
        "   b) Operating expenses: Provide total dollar amount and per dollar receivable. Calculate YoY and QoQ changes.",
        "   c) Cost of Funds: State the percentage and note any YoY or QoQ changes.",
        "4. Strategic Initiatives:",
        "   a) Summarize any completed or potential Merger and Acquisition activities.",
        "   b) Outline new Organic Growth initiatives.",
        "5. Market Analysis:",
        "   a) Identify macroeconomic opportunities that could benefit the company.",
        "   b) Highlight macroeconomic concerns that could pose risks to the company.",
        "6. Financial Health Assessment:",
        "   Provide an overall assessment of the company's financial health based on the above metrics.",
        "7. Forward-Looking Statement:",
        "   Based on the data and trends, provide a brief outlook for the company's next quarter or year.",
        "If any of the requested data is not available, clearly state which information is missing."
    ]

    if report_type in ['10-K', '10-Q']:
        return '\n'.join(common_prompts)
    else:
        return "Error: Unsupported report type. Please provide either a 10-K or 10-Q report."

def financial_analysis_report(prompt1, prompt2, prompt3):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    
    system_message = {"role": "system", "content": "You are an expert financial analyst providing detailed and accurate financial insights."}
    
    def generate_analysis(prompt):
        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a more capable model for financial analysis
            messages=[
                system_message,
                {"role": "user", "content": prompt}
            ],
            stream=True,
            temperature=0,  # Lower temperature for more focused and consistent output
            # max_tokens=10000  # Adjust based on the desired length of each analysis section
        )
        return st.write_stream(completion)

    st.subheader("Initial Financial Analysis")
    start_results = generate_analysis(prompt1)

    st.subheader("Management Performance Evaluation")
    management_results = generate_analysis(prompt2)

    st.subheader("Financial Report Summary")
    report_results = generate_analysis(prompt3)

    return start_results, management_results, report_results

def process_report(report_type, right_txt):
    def extract_and_polish(extraction_func, txt):
        raw_items = extraction_func(txt)
        return [html_removal(item) for item in raw_items]

    def generate_prompts(polished_items, report_type):
        start_prompt = starter_prompt(polished_items[0], report_type)
        management_prompt = management_prompt_gen(*polished_items[1:-1], report_type)
        financial_prompt = financial_prompt_gen(polished_items[-1], report_type)
        return start_prompt, management_prompt, financial_prompt

    if report_type == '10-K':
        extraction_func = item_extraction_10K
        items = extract_and_polish(extraction_func, right_txt[0])
        prompts = generate_prompts(items, '10-K')
    elif report_type == '10-Q':
        extraction_func = item_extraction_10Q
        items = extract_and_polish(extraction_func, right_txt[0])
        prompts = generate_prompts(items, '10-Q')
    else:
        raise ValueError(f"Unsupported report type: {report_type}")

    return financial_analysis_report(*prompts)
