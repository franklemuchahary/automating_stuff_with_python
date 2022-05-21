#!/usr/bin/env python
# coding: utf-8

# In[1]:


import logging
import time
import traceback
import os
import requests as rq
from datetime import datetime, timedelta
from dotenv import load_dotenv


# In[2]:


load_dotenv()


# ### Constants

# In[3]:


DT_FORMAT = '%Y-%m-%d %H:%M:%S'

ERROR_LOG_STRING_FORMAT = '''
    {section_title}
    ---
    {description}
    ---
    {error_message}
''' + '='*60 + '\n\n'

COMPLETE_WEATHER_STRING = '''
Temperature {temp}°C; Feels Like {feels}°C; Humidity {humidity}%; 
Cloudiness {cloudiness}%; Wind Speed {wind_speed} m/s; {weather_desc} 
'''

OPEN_WEATHER_API_KEY = os.environ['OPEN_WEATHER_API_KEY']
STRAVA_AUTH_CODE = os.environ['STRAVA_AUTH_CODE']
STRAVA_CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
STRAVA_CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']


# ### Logging Helper

# In[4]:


def error_logging_helper(log_filename:str = 'all_logs.log', logger_name:str = 'error_logger'):
    '''
    helper function for logging errors
    '''
    logger = logging.getLogger(logger_name)
    handler = logging.FileHandler(
        filename=log_filename,
        mode='a+'
    )
    log_format = logging.Formatter('%(asctime)s - %(message)s')
    handler.setLevel(logging.INFO)
    handler.setFormatter(log_format)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    print(logger.getEffectiveLevel())
    
    return logger

logger = error_logging_helper('all_logs.log')


# ### Auth

# In[5]:


def refresh_access_token(refresh_token:bool = True):
    '''
    get access token and refresh token
    providing either the refresh token or the authorization code
    
    Inputs:
        - refresh_token: 
            True/False value for whether to use the refresh token to get a new auth token
            if set to false will use the initial auth code prodvided in the env file
    '''
    try:
        if refresh_token:
            ### read last saved refresh token from file
            with open('refresh_token.txt', 'r') as f:
                refresh_token = f.read()

            access_code = {
                'grant_type' : 'refresh_token',
                'refresh_token' : refresh_token
            }
        else:
            access_code = {
                'grant_type' : 'authorization_code',
                'code' : STRAVA_AUTH_CODE
            }

        ### api parameters and api request
        api_params = {
            **{
                'client_id' : STRAVA_CLIENT_ID,
                'client_secret' : STRAVA_CLIENT_SECRET
            },
            **access_code
        }
        auth_request = rq.post(
            url = "https://www.strava.com/api/v3/oauth/token",
            data = api_params
        )

        ### check response
        if auth_request.status_code == 200:
            auth_token, refresh_token = auth_request.json()['access_token'], auth_request.json()['refresh_token']
            ### write back the latest refresh token to the same file
            with open('refresh_token.txt', 'w+') as f:
                f.write(refresh_token)
        else:
            auth_token = 'ERROR'
            logger.error(
                ERROR_LOG_STRING_FORMAT.format(
                    section_title = 'STRAVA AUTH API',
                    description = 'An error was returned from the strava authentication API for the request: \n'+str(api_params),
                    error_message = auth_request.text
                )
            )
    
    except Exception as e:
        auth_token = 'ERROR'
        logger.error(
            ERROR_LOG_STRING_FORMAT.format(
                section_title = 'Error Occured in Strava Authentication function',
                description = str(e),
                error_message = str(traceback.format_exc())
            )
        )
        
    return auth_token


# ### Get Acitivities

# In[6]:


def list_activities_strava(auth_token:str = '', page:int = 1, per_page:int = 30):
    '''
    get a list of activities from strava and store their ids
    
    Inputs: 
        - auth_token: auth token for the api
        - page: page number to fetch
        - per_page: number of activities per page
    '''
    try:
        api_params = {
            'page' : page,
            'per_page' : per_page,
            'access_token' : auth_token
        }
        list_activities = rq.get(
            url = 'https://www.strava.com/api/v3/athlete/activities',
            params = api_params
        )

        ### check response
        if list_activities.status_code == 200:
            ### get list of activity ids
            all_fetched_activity_ids = []
            for i in list_activities.json():
                ### condition required for open weather api - last 5 days
                date_is_in_last_5_days_check = datetime.strptime(
                    i['start_date_local'].replace('T', ' ').replace('Z', ''), 
                    DT_FORMAT
                ) >= (datetime.now() - timedelta(days = 5))

                if date_is_in_last_5_days_check:
                    all_fetched_activity_ids.append(i['id'])

            ### compare with last fetched activity ids and check if any new activity was created
            with open('last_fetched_ids.txt', 'r') as f:
                last_fetched_ids = f.read()
            
            if last_fetched_ids != '':
                last_fetched_ids_list = list(map(int, last_fetched_ids.split(',')))
            else:
                last_fetched_ids_list = []
                
            new_ids_fetched = [i for i in all_fetched_activity_ids if i not in last_fetched_ids_list]

            if len(new_ids_fetched) > 0:
                ### write the latest activity ids fetched into the file
                with open('last_fetched_ids.txt', 'w+') as f:
                    f.write(','.join(map(str, all_fetched_activity_ids)))

        else:
            new_ids_fetched = []
            logger.error(
                ERROR_LOG_STRING_FORMAT.format(
                    section_title = 'STRAVA LIST ACTIVITIES API',
                    description = 'An error was returned from the strava list activities api for the request: \n'+str(api_params),
                    error_message = list_activities.text
                )
            )
    except Exception as e:
        new_ids_fetched = []
        logger.error(
            ERROR_LOG_STRING_FORMAT.format(
                section_title = 'Error Occured in Strava List Activities Function',
                description = str(e),
                error_message = str(traceback.format_exc())
            )
        )
    
    return new_ids_fetched    


# ### Open Weather

# In[7]:


def get_weather_conditions(start_dt_local:str = '', 
                           start_lat:float = 0.0,
                           start_lng:float = 0.0
                           ):
    '''
    function for fetching the weather conditions using the openweather api
    
    Inputs: 
        - start_dt_local: start date string obtained from strava api
        - start_lat: start latitude obtained from strava api
        - start_lng: start longitude obtained from strava api
        
    Returns:
        list with all weather parameters
        first element is a boolean value indicating whether the request was successful or not
        order of the remaining elements: temp, feels_like_temp, humidity, cloudiness, wind_speed_mps, weather_desc
    '''
    try:
        unix_timestamp = datetime.strptime(start_dt_local.replace('T', ' ').replace('Z', ''), DT_FORMAT).timestamp()

        api_params = {
            'lat' : start_lat,
            'lon' : start_lng,
            'dt' : round(unix_timestamp),
            'units' : 'metric',
            'appid' : OPEN_WEATHER_API_KEY
        }

        weather_api_req = rq.get(
            url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine',
            params = api_params
        )

        if weather_api_req.status_code == 200:
            temp = weather_api_req.json()['current']['temp']
            feels_like_temp = weather_api_req.json()['current']['feels_like']
            humidity = weather_api_req.json()['current']['humidity']
            cloudiness = weather_api_req.json()['current']['clouds']
            uv_index = weather_api_req.json()['current']['uvi']
            wind_speed_mps = weather_api_req.json()['current']['wind_speed']
            weather_desc = weather_api_req.json()['current']['weather'][0]['description'].title()

            return [True, temp, feels_like_temp, humidity, cloudiness, wind_speed_mps, weather_desc]
        else:
            logger.error(
                ERROR_LOG_STRING_FORMAT.format(
                    section_title = 'OPEN WEATHER API',
                    description = 'An error was returned from the open weather api for the request: \n'+str(api_params),
                    error_message = weather_api_req.text
                )
            )
            return [False]
        
    except Exception as e:
        logger.error(
            ERROR_LOG_STRING_FORMAT.format(
                section_title = 'Error Occured in Open Weather API function',
                description = str(e),
                error_message = str(traceback.format_exc())
            )
        )
        return [False]


# ### Authenticate and Call APIs sequentially

# In[15]:


auth_token = refresh_access_token(refresh_token = True)


# In[10]:


new_activity_ids = list_activities_strava(
    auth_token=auth_token,
    page=1,
    per_page=30
)
print(new_activity_ids)


# In[11]:


for single_activity_id in new_activity_ids:
    ### get detailed activity info
    single_activity_rq = rq.get(
        url = 'https://www.strava.com/api/v3/activities/' + str(single_activity_id),
        params = {
            'access_token' : auth_token
        }
    )

    if single_activity_rq.status_code == 200:
        single_activity = single_activity_rq.json()
        start_lat = single_activity['start_latlng'][0]
        start_lng = single_activity['start_latlng'][1]
        start_dt_local = single_activity['start_date_local']
        start_dt_utc = single_activity['start_date']
        act_descr = single_activity['description']
        act_name = single_activity['name']
    
        print(act_descr)
        print(act_descr.strip()=='')
        print(act_descr==None, end='\n\n')
        
        ### for cases which do not currently have any description - update description with weather
        if act_descr is None or act_descr.strip() == '':
            
            ### fetch weather details from open weather api
            weather_conditions_result = get_weather_conditions(
                start_dt_local=start_dt_local,
                start_lat=start_lat,
                start_lng=start_lng
            )
            
            if weather_conditions_result[0]:
                ### generate formatted weather string
                formatted_weather_string = COMPLETE_WEATHER_STRING.format(
                    temp = round(weather_conditions_result[1]),
                    feels = round(weather_conditions_result[2]),
                    humidity = weather_conditions_result[3],
                    cloudiness = weather_conditions_result[4],
                    wind_speed = weather_conditions_result[5],
                    weather_desc = weather_conditions_result[6]
                )

                print(formatted_weather_string)
                
                ### call the strava update activity api - replace operation by default
                update_api_params = {
                    'access_token' : auth_token,
                    'description': formatted_weather_string
                }

                update_api_rq = rq.put(
                    url = "https://www.strava.com/api/v3/activities/"+str(single_activity_id),
                    data = update_api_params
                )
                if update_api_rq.status_code == 200:
                    logger.info(
                        "Succesfully Updated Description for " + str(single_activity_id) + "\n" + "="*60 + "\n\n"
                    )
                else:
                    logger.error(
                        ERROR_LOG_STRING_FORMAT.format(
                            section_title = 'STARVA UPDATE ACTIVITY API',
                            description = 'An error was returned from the strava update activity api for the id: \n' + \
                                        str(single_activity_id) + '; Request: ' + str(update_api_params),
                            error_message = update_api_rq.text
                        )
                    )
                    continue
                
            else:
                continue
    else:
        logger.error(
            ERROR_LOG_STRING_FORMAT.format(
                section_title = 'STARVA DETAILED ACTIVITY API',
                description = 'An error was returned from the strava detailed activity for the id: \n'+str(single_activity_id),
                error_message = single_activity_rq.text
            )
        )
        continue

