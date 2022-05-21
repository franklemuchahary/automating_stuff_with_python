# AUTOMATE STUFF WITH PYTHON

Python is a beautiful language and a part of what makes it beautiful is its use for automating the repetitive and boring everyday tasks.
In this repo, I will be pushing all the handy little python scripts I have written to help make my life a little easier by letting me remove manual intervention
from tedious and repetitive tasks so that I can spend more time doing useful stuff like browsing reddit.
<br><br>  

**Automated so far:**  
- [COWIN COVID-19 Vaccine Availability Notifier](vaccine_automatic_notification):   
  Automatically notify user when vaccine for 18-45 age group is available. Libraries: `requests`, `beautifulsoup`, `asyncio`, `pandas`
- [Voice to Word Definition from `vocabulary.com`](voice_to_word_definition):   
  Get word definition and pronunciation from https://www.vocabulary.com/ by converting the spoken word to text (voice search feature). Libraries: `speech_recognition`
- [Fetching Latest Fantasy Premier League Data](fantasy_permier_league_data):
  Python script for automatically fetching [Fantasy Premier League](https://www.premierleague.com/news/2173986) Data every gameweek (including my own team information, chips available, transfers available etc) and storing it in a SQLite DB. Libraries: `requests`, `pandas`, `json`, `asyncio`, `sqlalchemy`
- [Strava Weather Update in Description](strava-weather-update):
  Python script for automatically updating weather conditions for [Strava Activities](https://www.strava.com/dashboard) in the activity descripton field. Strava API is used for fetching and updating the strava activities and Open Weather API is used for fetching the latest weather conditions. Libraries: `requests`, `logging`, `datetime`

