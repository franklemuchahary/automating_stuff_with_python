#!/usr/bin/env python
# coding: utf-8

# In[1]:


import asyncio
import json
import dotenv
import os
import requests as rq
import pandas as pd
import numpy as np
from tqdm import notebook, tqdm
from sqlalchemy import create_engine
from concurrent.futures import ThreadPoolExecutor

pd.set_option('max.columns', 500)


# ### Load env and Create DB Connection
# 
# - Create and environment file with PASSWORD, USERNAME and TEAM_ID
# - Initialize the SQLite DB Connection

# In[2]:


dotenv.load_dotenv()

db_conn = create_engine('sqlite:///fpl_data_sqlite.db')


# ### Declare Constants

# In[43]:


START_GW = 1

CURRENT_SEASON = '2021/22'

GW_LOOKAHEAD_NUM = 3

NEW_SEASON = False


# ### Fetch Base Info
# This is the base api which has the following information:
# - info about all the teams (teams)
# - player information and stats till the current gameweek (elements)
# - info about all gameweeks in current season (events)

# In[4]:


base_url = 'https://fantasy.premierleague.com/api/bootstrap-static/'

base_url_response = rq.request('GET', base_url)
base_url_response_dict = json.loads(base_url_response.text)


# In[5]:


teams_info_df = pd.DataFrame(base_url_response_dict['teams'])


# In[6]:


teams_info_df.to_sql('teams_info', db_conn, if_exists='replace', index=False)


# ### Calculate Next Gameweek No

# In[7]:


next_gameweek = min([i['id'] for i in base_url_response_dict['events'] if i['finished'] == False])
next_gameweek


# ### Fetch Fixtures Info
# This api provides information at a fixure and gameweek level for all gameweeks (Both Past and Future Gameweeks)

# In[8]:


fixt_url = 'https://fantasy.premierleague.com/api/fixtures/'

fixt_response = rq.request('GET', fixt_url)
fixt_response_dict = json.loads(fixt_response.text)


# In[9]:


fixtures_df = pd.DataFrame(fixt_response_dict)


# In[10]:


fixtures_df['season'] = CURRENT_SEASON
fixtures_df.drop('stats', axis=1, inplace=True, errors='ignore')
fixtures_df['kickoff_time'] = pd.to_datetime(fixtures_df['kickoff_time'])


# In[11]:


fixtures_df.head()


# In[12]:


fixtures_df.to_sql('fixtures_history_' + CURRENT_SEASON, db_conn, if_exists='replace', index=False)


# ### Get Next 3 Fixtures and Create a Pivot Table
# Perform some data transformation to get info for the next 3 gameweeks based on the current gameweek  
# This transformed data will be useful for using as variables while trying to train ML Models or building Optimization Models

# In[13]:


next_fixt = fixtures_df[fixtures_df.event.isin(range(next_gameweek, next_gameweek + GW_LOOKAHEAD_NUM))]


# In[14]:


next_fixt.head()


# In[15]:


next_fixt_away = next_fixt[['event', 'team_a', 'team_a_difficulty', 'team_h', 'team_h_difficulty']].copy()
next_fixt_away.rename(
    columns = {
        'event':'gw', 'team_a':'team_id', 
        'team_a_difficulty':'match_difficulty',
        'team_h':'opponent_team_id',
        'team_h_difficulty':'match_difficulty_for_opponent'
    },
    inplace=True
)
next_fixt_away['game_type'] = 'away'


next_fixt_home = next_fixt[['event', 'team_a', 'team_a_difficulty', 'team_h', 'team_h_difficulty']].copy()
next_fixt_home.rename(
    columns = {
        'event':'gw', 'team_h':'team_id', 
        'team_h_difficulty':'match_difficulty',
        'team_a':'opponent_team_id',
        'team_a_difficulty':'match_difficulty_for_opponent'
    },
    inplace=True
)
next_fixt_home['game_type'] = 'home'


# In[16]:


next_fixt_base = pd.concat([next_fixt_away, next_fixt_home]).reset_index(drop=True)
next_fixt_base = next_fixt_base.pivot(
    index = ['team_id'],
    columns = ['gw'],
    values = ['match_difficulty', 'opponent_team_id', 'match_difficulty_for_opponent', 'game_type']
)
temp = next_fixt_base.columns
next_fixt_base.columns = ['next_' + str( int(i[1]) - (next_gameweek - 1) ) + '_gw_' + i[0] for i in temp]
next_fixt_base = next_fixt_base.reset_index()
next_fixt_base['calculated_at_gw'] = next_gameweek - 1
next_fixt_base['season'] = CURRENT_SEASON


# In[17]:


next_fixt_base.head()


# In[18]:


next_fixt_base.to_sql('next_three_fixtures_info', db_conn, if_exists='append', index=False)


# ### Get Past GW Player Stats
# This api provides player level stats for all game weeks (stats). It returns information at player id level.   
# Need to make individual api calls for each game week

# In[19]:


past_gw_stats_base = []

for gw in tqdm(range(START_GW, next_gameweek)):
    player_gw_stats = []
    
    url = 'https://fantasy.premierleague.com/api/event/' + str(gw) + '/live/'

    past_gw_response = rq.request('GET', url)
    past_gw_response = json.loads(past_gw_response.text)

    for item in past_gw_response['elements']:
        item['stats']['player_id'] = item['id'] 
        player_gw_stats.append(item['stats'])
        
    player_gw_stats = pd.DataFrame(player_gw_stats)
    player_gw_stats['gw'] = gw
    player_gw_stats['season'] = CURRENT_SEASON
    
    past_gw_stats_base.append(player_gw_stats)


# In[20]:


past_gw_player_stats = pd.concat(past_gw_stats_base).reset_index(drop=True)
past_gw_player_stats.head()


# In[21]:


past_gw_player_stats.to_sql('player_stats_all_gameweeks_season_'+CURRENT_SEASON, db_conn, if_exists='replace', index=False)


# Perform Data Transformation to Get Past 3 Gameweek Player Stats at Player ID Level. Will be useful for building models and further analysis on the data

# In[22]:


last_3_gw_stats = past_gw_player_stats[past_gw_player_stats.gw.isin(range(next_gameweek-3, next_gameweek))]
last_3_gw_stats = last_3_gw_stats.pivot(
    index = 'player_id',
    columns = 'gw',
    values = [
        'minutes', 'goals_scored', 'assists', 'clean_sheets', 'saves', 'bonus', 'influence',
        'creativity', 'threat', 'ict_index', 'total_points'
    ]
)

temp = last_3_gw_stats.columns
last_3_gw_stats.columns = ['t_minus_' + str((next_gameweek-1) - int(i[1])) + '_gw_' + i[0] for i in temp]
last_3_gw_stats = last_3_gw_stats.reset_index()
last_3_gw_stats['calculated_at_gw'] = next_gameweek - 1
last_3_gw_stats['season'] = CURRENT_SEASON


# In[23]:


last_3_gw_stats.head()


# In[24]:


last_3_gw_stats.to_sql('last_3_gameweeks_player_stats', db_conn, if_exists='append', index=False)


# ### Cleaning Required Data and Subsetting Columns
# 
# Clean up the Player Information fetched from the Base API (elements property)  
# This data will serve as the base for most models built on top of this data

# In[25]:


elements_list = base_url_response_dict['elements']


# In[28]:


### sample
[i for i in elements_list if i['second_name'] == 'Salah']


# In[26]:


elements_df = pd.DataFrame(elements_list)


# In[27]:


elements_df.head()


# Stauts Field:  
# s = suspended  
# i = injury (major)  
# u = transferred  
# d = injury (75% chance of playing)  
# n = not included in squad for some reason  
# a = normal  

# In[29]:


PLAYER_INFO = ['web_name', 'id', 'first_name', 'second_name', 'team', 'team_code', 'now_cost', 'cost_change_start', 'selected_by_percent']


# In[30]:


FORM_INFO = [
    'form', 'points_per_game', 'total_points', 'value_form', 'value_season', 'minutes',
    'goals_scored', 'assists', 'clean_sheets', 'goals_conceded', 'saves',
    'bonus', 'bps', 'influence', 'creativity', 'threat', 'ict_index',
    'penalties_missed', 'penalties_saved'
]

ADDITIONAL_FORM_INFO = [
    'influence_rank', 'influence_rank_type', 'creativity_rank', 'creativity_rank_type', 'threat_rank', 
    'threat_rank_type', 'ict_index_rank', 'ict_index_rank_type',
    'own_goals', 'yellow_cards', 'red_cards', 
    'transfers_in_event', 'transfers_out_event'
]


# In[31]:


elements_df_subset = elements_df[elements_df['status'].isin(['a', 'd'])].copy().reset_index(drop=True)
elements_df_subset = elements_df_subset[
    PLAYER_INFO + FORM_INFO + ADDITIONAL_FORM_INFO
].copy()


# In[32]:


elements_df_subset['calculated_at_gw'] = next_gameweek - 1
elements_df_subset['season'] = CURRENT_SEASON


# In[33]:


elements_df_subset.head()


# In[34]:


elements_df_subset.to_sql('cummumative_player_info', db_conn, if_exists='append', index=False)


# ### Get Historical Player Stats
# Historical Stats of Past Seasons for All Players  
# `Note: Need to run this only at the begining of the season`

# In[36]:


def historical_player_stats_helper(url):
    '''
    helper function for async requests for fetching historical player stats
    
    Inputs:
        - url: url string
        
    Returns:
        - hisorical_player_info: dataframe with player stats
    '''
    try:
        historical_player_info = rq.request('GET', url[0])
    except:
        return None
        
    historical_player_info = json.loads(historical_player_info.text)
    historical_player_info = pd.DataFrame(historical_player_info['history_past'])
    historical_player_info['player_id'] = url[1]
    return historical_player_info


if NEW_SEASON:
    player_ids_main_list = elements_df_subset['id'].unique()
    subset_size = 50

    player_ids_main_list_sublist = []

    for i in range(1, int(np.ceil(len(player_ids_main_list)/subset_size))+1):
        player_ids_main_list_sublist.append(player_ids_main_list[subset_size * (i-1) : subset_size * i])

    historical_player_results_list = []

    for player_id_list in tqdm(player_ids_main_list_sublist):
        url_list = [
            ('https://fantasy.premierleague.com/api/element-summary/' + str(player_id) + '/', player_id) for player_id in player_id_list
        ]

        #print(url_list)

        ### asyncio calls - fetch data for multiple urls parallely for faster processing
        event_loop = asyncio.get_event_loop()
        Executor = ThreadPoolExecutor(max_workers=len(url_list))
        tasks = [event_loop.run_in_executor(Executor, historical_player_stats_helper, url) for url in url_list]

        historical_player_results = await asyncio.gather(*tasks)
        historical_player_results_list.extend(historical_player_results)

    historical_stats_player_df = pd.concat(historical_player_results_list)
    try:
        existing_info = pd.read_sql_query('select * from historical_seasons_player_stats', db_conn)
        historical_stats_player_df = pd.concat([historical_stats_player_df, existing_info]).drop_duplicates().reset_index(drop=True)
    except Exception as e:
        print(str(e))
        
    historical_stats_player_df.to_sql('historical_seasons_player_stats', db_conn, if_exists='replace', index=False)


# ### Authenticate and Fetch My Team
# 
# - Perform Authentication
# - Fetch My Current Team Information, Available Chips and Transfers

# In[37]:


sessions = rq.session()

url = 'https://users.premierleague.com/accounts/login/'

login_details = {
    'login': os.environ['USERNAME'],
    'password': os.environ['PASSWORD'],
    'redirect_uri': 'https://fantasy.premierleague.com/a/login',
    'app': 'plfpl-web'
}

sessions.post(url, data=login_details)


# In[38]:


my_team_url = 'https://fantasy.premierleague.com/api/my-team/' + str(os.environ['TEAM_ID']) + '/'

my_team_response = sessions.get(my_team_url)
my_team_response = json.loads(my_team_response.text)


# In[39]:


my_team = pd.DataFrame(my_team_response['picks'])
my_chips = pd.DataFrame(my_team_response['chips'])
my_transfers = pd.DataFrame([my_team_response['transfers']])


# In[40]:


my_team['caclulated_at_gw'] = next_gameweek - 1
my_chips['caclulated_at_gw'] = next_gameweek - 1
my_transfers['caclulated_at_gw'] = next_gameweek - 1

my_team['season'] = CURRENT_SEASON
my_chips['season'] = CURRENT_SEASON
my_transfers['season'] = CURRENT_SEASON

my_chips['played_by_entry'] = my_chips['played_by_entry'].apply(lambda x: ' - '.join(x))


# In[41]:


print(my_team.to_string(), end="\n\n")

print(my_chips.to_string(), end="\n\n")

print(my_transfers.to_string(), end="\n\n")


# In[42]:


my_team.to_sql('my_team_info', db_conn, if_exists='append', index=False)
my_chips.to_sql('latest_chips_info', db_conn, if_exists='replace', index=False)
my_transfers.to_sql('latest_transfer_info', db_conn, if_exists='replace', index=False)

