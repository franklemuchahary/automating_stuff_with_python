sudo apt-get update;
sudo apt-get install python3-pip;
sudo apt-get install python3-pandas;

### set cron job
crontab -l > mycron;
#echo new cron into cron file
echo "0,30 * * * * /usr/bin/python3 /home/franklemuchahary/vaccine_automatic_notification/notifier_script.py" >> mycron;
#install new cron file
crontab mycron;
rm mycron;
