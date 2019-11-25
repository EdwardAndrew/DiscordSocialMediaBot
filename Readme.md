This DiscordSocialMedia bot will take your tweets and Instagram posts and repost them into your channel. It uses Discord-Webhooks :smile:

Install dependencies: `pip install -r requirements.txt`

Add environment variables:

```sh
  export SOCIALMEDIABOT_DISCORD_WEBHOOK_URL=<your_discord_webhook_url>
  export SOCIALMEDIABOT_TWITTER_SCREENNAME=<your_twitter_screenname>
  export SOCIALMEDIABOT_TWITTER_CONSUMER_API_KEY=<your_twitter_consumer_api_key>
  export SOCIALMEDIABOT_TWITTER_API_SECRET_KEY=<your_twitter_api_secret_key>
  export SOCIALMEDIABOT_INSTAGRAM_LOGIN=<your_instagram_username>
  export SOCIALMEDIABOT_INSTAGRAM_PASSWORD=<your_instagrame_password>
```

Run the server: `./start.sh`

This script perfroms a 'DryRun' which will persist the ids of the posts and tweets that have already been posted. This prevents a spam of messages going into the channel when you first start the server.

Stop the server: `./stop.sh`

State is persisted in `socialmediabot.data` which is created the first time the script runs. This is necessary to know which of the posts / tweets from the apis have already been posted in the discord channel.

Logs are stored in `socialmediabot.logs` which is created when the app is launched from the start script.
