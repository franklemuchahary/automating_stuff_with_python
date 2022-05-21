import json
import qgrid
import pandas as pd
import requests as r
from tqdm import tqdm
from fake_useragent import UserAgent

AGENTS = UserAgent()

def request_url(url):
    '''
    function for making the request and getting json data
    
    Inputs:
        url: api endpoint to make a call to
        
    Returns:
        json_dict: dictionary with all outputs
    '''
    headers = {'user-agent':AGENTS.random}
    try:
        req = r.get(url, headers=headers, timeout=10)
    except Exception as e:
        print(e)
            
    if req.status_code == 200:
        json_dump = req.text
        json_dict = json.loads(json_dump)
        return json_dict

state_list = request_url(
    'https://cdn-api.co-vin.in/api/v2/admin/location/states'
)

final_df_list = []

for state in tqdm(state_list['states']):
    district_list = request_url(
        'https://cdn-api.co-vin.in/api/v2/admin/location/districts/' + str(state['state_id'])
    )
    
    district_df = pd.DataFrame(district_list['districts'])
    district_df['state_id'] = state['state_id']
    district_df['state_name'] = state['state_name']
    
    final_df_list.append(district_df)

final_df = pd.concat(final_df_list).reset_index(drop=True)
final_df.to_csv('district_ids.csv', index=False)
print(final_df.to_string())
