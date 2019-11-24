import os
import json
import requests
import threading
from base64 import b64encode
from collections import deque
from discord_webhooks import DiscordWebhooks

class DiscordWebhook():
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def sendMessage(self, Message):
        if 'description' not in Message:
            raise ValueError('Discord messages requires a description')

        if 'title' not in Message:
            Message['title'] = ''

        message = DiscordWebhooks(self.webhook_url)
        message.set_content(color=0xc8702a, description=Message['description'], title=Message['title'])
        message.set_footer(text='https://example.com', ts=True)
        if 'image' in Message:
            message.set_image(url=Message['image'])
        message.send()

class Twitter():
    def __init__(self, ConsumerApiKey, APISecretKey, AuthTTL):
        self.ConsumerApiKey = ConsumerApiKey
        self.APISecretKey = APISecretKey
        self.token = ''
        self.authTTL = AuthTTL

    def auth(self):
        threading.Timer(self.authTTL, self.auth).start()
        userAndPass = b64encode(bytes(self.ConsumerApiKey + ':' + self.APISecretKey, 'utf-8')).decode('utf-8')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'api.twitter.com',
            'Authorization': 'Basic %s' % userAndPass}
        response = requests.post(url='https://twitter.com/oauth2/token',data={'grant_type':'client_credentials'},headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
        else:
            print('Twitter auth failed.')

    def getTimeline(self, ScreenName, Retry = True):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'api.twitter.com',
            'Authorization': 'Bearer %s' % self.token}
        response = requests.get('https://twitter.com//1.1/statuses/user_timeline.json', params={'screen_name': ScreenName}, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif Retry and response.status_code == 401:
            self.auth()
            return self.getTimeline(ScreenName, False)
        return null

    def getDiscordMessageFromTweet(self, Tweet):
        post = {'title': 'Twitter'}

        if 'text' in Tweet:
            post['description'] = Tweet['text']
        
        if 'entities' in Tweet:
            try:
                post['image'] =  Tweet['entities']['media'][0]['media_url_https']
            except KeyError:
                pass
        return post

class SocialMediaBot():
    def __init__(self, DISCORD_WEBHOOK_URL, TwitterConfig, StateFileConfig):
        self.discord = DiscordWebhook(DISCORD_WEBHOOK_URL)
        self.twitter = Twitter(TwitterConfig['ConsumerAPIKey'], TwitterConfig['APISecretKey'], TwitterConfig['AuthTTL'])
        self.twitter.auth()
        self.checkTwitterInterval = 60
        self.stateFile = StateFileConfig['Path']
        try: 
            f = open(self.stateFile)
        except IOError:
            f = open(self.stateFile, 'w+')
        finally:
            f.close()

    def getSentMessageUids(self):
        content = []
        try:
            f = open(self.stateFile)
            content = f.readlines()
        finally:
            f.close()
        content = [x.strip() for x in content]
        return content

    def storeSentMessageUid(self, uid):
        try: 
            f = open(self.stateFile,'a+')
            f.write(uid+'\n')
        finally:
            f.close()

    def reduceStateFile(self, NumberlinesToReduceTo):
        lines = deque()
        try: 
            f = open(self.stateFile)
            lines = deque(f,NumberlinesToReduceTo)
        finally:
            f.close()
        try:
            f = open(self.stateFile, 'w+')
            f.writelines(lines)
        finally:
            f.close()

    def sendRecentTweets(self):
        recentTweets = self.twitter.getTimeline(TwitterConfig['ScreenName'])
        for tweet in reversed(recentTweets):
            try:
                uid='twitter' + str(tweet['id'])
                if uid not in self.getSentMessageUids():
                    try:
                        self.discord.sendMessage(self.twitter.getDiscordMessageFromTweet(tweet))
                        self.storeSentMessageUid(uid)
                    except ValueError:
                        pass
            except KeyError:
                pass

    def checkTwitter(self):
        threading.Timer(TwitterConfig['Interval'], self.checkTwitter).start()
        self.sendRecentTweets()

    def cleanup(self):
        threading.Timer(StateFileConfig['CleanupInterval'], self.checkTwitter).start()
        reduceStateFile(StateFileConfig['MaxEntries'])

    def start(self):
        threading.Timer(StateFileConfig['CleanupInterval'], self.cleanup).start()
        self.checkTwitter()

if __name__ == "__main__":
    DiscordWebhookURL = os.environ.get('SOCIALMEDIABOT_DISCORD_WEBHOOK_URL')
    TwitterConfig = {'ScreenName': os.environ.get('SOCIALMEDIABOT_TWITTER_SCREENNAME'), 'ConsumerAPIKey': os.environ.get('SOCIALMEDIABOT_TWITTER_CONSUMER_API_KEY'), 'APISecretKey': os.environ.get('SOCIALMEDIABOT_TWITTER_API_SECRET_KEY'), 'Interval': 30, 'AuthTTL': 3600 }
    StateFileConfig = { 'Path': 'socialmediabot.data', 'CleanupInterval': 3600*24, 'MaxEntries': 1000}

    newsbot = SocialMediaBot(DiscordWebhookURL, TwitterConfig, StateFileConfig)
    newsbot.start()
    print("🚀  Social Media Bot is running...")
