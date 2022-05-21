import json
import os
import asyncio
import email, smtplib, ssl
import pandas as pd
import requests as r
from datetime import datetime as dt
from datetime import timedelta as td
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv(verbose=True)

SENDER_EMAIL = os.environ['EMAIL_SENDER']
SENDER_PASSWORD = os.environ['EMAIL_SENDER_PASS']
RECEIVER_EMAIL = os.environ['RECEIVER_EMAIL']

DISTRICT_IDS_LIST = [149]

AGENTS = UserAgent()

proxy_url = 'https://free-proxy-list.net/'
res_proxy = r.get(proxy_url, headers={'user-agent':AGENTS.random})

soup = BeautifulSoup(res_proxy.text, 'lxml')
table = soup.find("table", attrs={"class":"table"})

df_proxy = pd.concat(pd.read_html(str(table))).reset_index(drop=True)
df_proxy.dropna(inplace=True)
df_proxy['proxy'] = df_proxy['IP Address'] + ":" + df_proxy['Port'].astype(int).astype(str)
df_proxy = df_proxy[df_proxy['Country'] == "India"].reset_index(drop=True).head(10)
PROXY_LIST = list(df_proxy['proxy'].values)

print(PROXY_LIST)

def async_request(url):
    '''
    function for making the request and getting json data
    
    Inputs:
        url: api endpoint to make a call to
        
    Returns:
        json_dict: dictionary with all outputs
    '''
    headers = {'user-agent':AGENTS.random}
    for idx, proxy in enumerate(PROXY_LIST):
        try:
            req = r.get(url, headers=headers, proxies={'http':proxy}, timeout=10)
            break
        except Exception as e:
            print(e)
            if idx == len(PROXY_LIST)-1:
                req = r.get(url, headers=headers)
            else: 
                pass
            
    if req.status_code == 200:
        json_dump = req.text
        json_dict = json.loads(json_dump)
        return json_dict

def fetch(district_ids = [149]):
    '''
    Function to make loop through the urls, clean the response body and convert them to dataframes
    
    Inputs:
        district_ids: list
            IDs of districts for which you want to fetch the vaccine availability info
            
    Returns:
        body_plain: text body for email to be sent 
        eligible_df_html_body: html table body for email to be sent
    '''
    
    ### specify date
    base = dt.today()
    date_list = [base + td(days=x) for x in range(10)]
    date_str = [x.strftime("%d-%m-%Y") for x in date_list]
    
    list_of_dicts = []

    for date in date_str:
        url_list = [
            "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id=" + \
            str(dist) + "&date=" + date for dist in district_ids
        ]
        
        print(url_list)
        
        ### asyncio calls - fetch data for multiple dates parallely for faster processing
        event_loop = asyncio.get_event_loop()
        Executor = ThreadPoolExecutor(max_workers=len(url_list))
        tasks = [event_loop.run_in_executor(Executor, async_request, url) for url in url_list]
        
        json_results = event_loop.run_until_complete(asyncio.gather(*tasks))
        
        list_of_dicts.extend([i for i in json_results if i != None])
            
    list_of_base_df = []
    
    ### cleanup and convert to dataframes
    for i in list_of_dicts:
        try:
            list_of_base_df.append(pd.DataFrame(i['centers']))
        except Exception as e:
            print(str(e))
            
    df_1 = pd.concat(list_of_base_df).reset_index(drop=True)
    
    
    df_list = []

    for index, row in df_1.iterrows():
        address = row['address']
        block = row['block_name']
        center = row['center_id']
        district = row['district_name']

        df = pd.DataFrame(row['sessions'])
        df['address'] = address
        df['block'] = block
        df['center_id'] = center
        df['district'] = district

        df_list.append(df)
        
    final_df = pd.concat(df_list).reset_index(drop=True).drop('slots', axis=1).drop_duplicates()
    
    print(final_df.head(10))
    
    ### save entire data as csv
    final_df.to_csv('latest_fetched_info.csv', index=False)
    
    ### subset only eligible centres
    eligible_df = final_df[(final_df['available_capacity'] > 0) & (final_df['min_age_limit'] < 45)]
    print(eligible_df)
    
    ### convert to html for adding to email body
    eligible_df_html_body = eligible_df.to_html()

    if eligible_df.shape[0] > 0:
        body_plain = '''
        VACCINES AVAILABLE FOR 18-45 IN THE FOLLOWING CENTERS   
        '''
    else:
        body_plain = '''
        VACCINES NOT AVAILABLE YET FOR 18-45
        '''
    
    return body_plain, eligible_df_html_body

def email_send(body_plain, eligible_df_html_body, subject = "COWIN VACCINE AUTOMATED UPDATES"):
    '''
    function to send email with the vaccine availability table, text body and csv attachment
    
    Inputs:
        body_plain: text body for email
        eligible_df_html_body: html table body for email
        subject: text subject for email    
    '''
    
    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL
    message["Subject"] = subject
    message["Bcc"] = "" # Recommended for mass emails

    # Add body to email
    message.attach(MIMEText(body_plain, "plain"))
    message.attach(MIMEText(eligible_df_html_body, "html"))

    # In same directory as script
    filename = "latest_fetched_info.csv"  

    # Open file in binary mode
    with open(filename, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email    
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        "attachment; filename="+filename
    )

    # Add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()

    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)

    print("Sent")

try:
    ### fetch data
    body_plain, eligible_df_html_body = fetch(DISTRICT_IDS_LIST)
    
    ### send email based on availability
    if 'NOT AVAILABLE' not in body_plain:
        email_send(
            "Vaccine Available for 18-45. Email with details will be sent shortly.", 
            eligible_df_html_body, 
            "VACCINE AVAILABLE FOR 18-45"
        )
    else:
        email_send(
            body_plain,
            eligible_df_html_body
        )
except Exception as e:
    ### send error email
    print(str(e))
    body_plain, eligible_df_html_body = "Error in Automation. Failed with error: " +  str(e), "<h4> Error in Automation </h4>"
    email_send(
        body_plain, 
        eligible_df_html_body
    )
