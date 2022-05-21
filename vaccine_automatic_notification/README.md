# COWIN PORTAL VACCINE AVAILABILITY NOTIFICATION VIA EMAIL

This is a script that helps automatically notify the availability of vaccines for your district of choice for the 18-45 age group via email.

**How to Use:**
- Create a `.env` file and add the following variables to it:  
  `EMAIL_SENDER`: email id using which you want to send the email.   
  `EMAIL_SENDER_PASS`: password of the above email id (you will have to allow less secure apps for it)  
  `RECEIVER_EMAIL`: email id where you want to receive the notification.   
- Check the `district_id` of the districts you want to get the availability for using the file `district_ids.csv`. Add these district ids to the list variable `DISTRICT_IDS_LIST` in the `cowin_notification.ipynb` notebook or `notifier_script.py` file. 
- Execute the `notifier_script.py` file to test
- Modify the cron job and paths in the `cron_job_bash_script.sh` file and run it
