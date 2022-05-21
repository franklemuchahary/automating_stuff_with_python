### Automatic Strava Weather Update in Activity Description

[Strava](https://www.strava.com/features) - Strava is an activity tracking app for tracking a variety of outdoor and indoor activities. 
It is quite popular mainly among runners and cyclists for tracking these activities. It records and let's us analyze tons of data points which
can be used for training and improvement. Strava also provides APIs for fetching the recorded data points.
<br><br>
There are a few features which are available only for paid subscribers on strava. One of these is the ability to record the weather conditions
during the activity. So, to work around this, I have created a python script which uses the coordinates of the activity location and the start timestamp, 
feeds it to the [Open Weather API](https://openweathermap.org/) to fetch the weather condtions based on the location and time. This information is finally updated in the descripton field
available for all strava activities.
<br><br>
In order to use the script, please create a `.env` file with the following variables:
OPEN_WEATHER_API_KEY, STRAVA_AUTH_CODE, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET
<br><br>
[STRAVA API DOCUMENTATION](https://developers.strava.com/)<br>
[OPEN WEATHER API DOCUMENTATION](https://openweathermap.org/api)
