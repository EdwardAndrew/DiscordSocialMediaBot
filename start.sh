if [ ! -f socialmediabot.data ]
then
    python3 socialmediabot.py dryRun
fi

nohup python3 socialmediabot.py >> socialmediabot.logs 2>&1 &
echo $! > pid.txt
echo "🚀  Social Media Bot is now running in the background."