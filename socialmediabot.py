import os
import sys
import json
import datetime
import requests
import threading
from base64 import b64encode
from collections import deque
from InstagramAPI import InstagramAPI
from discord_webhooks import DiscordWebhooks


class DiscordWebhook():
    def __init__(self, webhook_url, dry_run):
        self.webhook_url = webhook_url
        self.dry_run = dry_run

    def sendMessage(self, Message):
        if 'description' not in Message:
            raise ValueError('Discord messages requires a description')

        if 'content' not in Message:
            Message['content'] = ''

        if 'title' not in Message:
            Message['title'] = ''

        if 'color' not in Message:
            Message['color'] = 0xFFFFFF

        if 'author' not in Message:
            Message['author'] = {}
        if 'name' not in Message['author']:
            Message['author']['name'] = ''
        if 'url' not in Message['author']:
            Message['author']['url'] = ''
        if 'icon_url' not in Message['author']:
            Message['author']['icon_url'] = ''

        if 'footer' not in Message:
            Message['footer'] = {}
        if 'text' not in Message['footer']:
            Message['footer']['text'] = ''
        if 'icon_url' not in Message['footer']:
            Message['footer']['icon_url'] = ''

        message = DiscordWebhooks(self.webhook_url)
        message.set_content(
            color=Message['color'], content=Message['content'], description=Message['description'], title=Message['title'])
        message.set_footer(
            text=Message['footer']['text'], icon_url=Message['footer']['icon_url'])
        message.set_author(url=Message['author']['url'], name=Message['author']
                           ['name'], icon_url=Message['author']['icon_url'])
        if 'image' in Message:
            message.set_image(url=Message['image'])

        if not self.dry_run:
            message.send()


class Twitter():
    def __init__(self, consumerApiKey, APISecretKey, authTTL):
        self.consumerApiKey = consumerApiKey
        self.APISecretKey = APISecretKey
        self.token = ''
        self.authTTL = authTTL

    def auth(self):
        threading.Timer(self.authTTL, self.auth).start()
        userAndPass = b64encode(
            bytes(self.consumerApiKey + ':' + self.APISecretKey, 'utf-8')).decode('utf-8')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'api.twitter.com',
            'Authorization': 'Basic %s' % userAndPass}
        response = requests.post(url='https://twitter.com/oauth2/token',
                                 data={'grant_type': 'client_credentials'}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
        else:
            print('Twitter auth failed.')

    def getTimeline(self, ScreenName, Retry=True):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'api.twitter.com',
            'Authorization': 'Bearer %s' % self.token}
        response = requests.get('https://twitter.com//1.1/statuses/user_timeline.json',
                                params={'screen_name': ScreenName}, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif Retry and response.status_code == 401:
            self.auth()
            return self.getTimeline(ScreenName, False)
        return []

    def getDiscordMessageFromTweet(self, Tweet):
        message = {'title': '', 'color': 0x1DA1F2}
        message['footer'] = {
            'text': 'Twitter', 'icon_url': 'https://abs.twimg.com/responsive-web/web/icon-ios.8ea219d4.png'}
        if 'text' in Tweet:
            message['description'] = Tweet['text']
        try:
            url = 'https://twitter.com/' + \
                Tweet['user']['screen_name'] + '/status/' + Tweet['id_str']
            username = Tweet['user']['name']
            message['author'] = {'name': username, 'icon_url': Tweet['user']['profile_image_url_https'],
                                 'url': url}
            message['content'] = '<@&647992314530103346> ' + \
                username + ' just tweeted! ' + url
            message['image'] = Tweet['entities']['media'][0]['media_url_https']
        except KeyError:
            pass
        return message


class Instagram():
    def __init__(self, login, password, authTTL):
        self.authTTL = authTTL
        self.login = login
        self.password = password

    def auth(self):
        threading.Timer(self.authTTL, self.auth).start()
        self.api = InstagramAPI(self.login, self.password)
        if not self.api.login():
            print("Failed to login")

    def getUserFeed(self, Retry=True):
        if self.api.getSelfUserFeed():
            response = self.api.LastJson
            if 'items' in response:
                return response['items']
        elif Retry:
            print("Retrying after auth")
            self.auth()
            return self.getUserFeed(False)
        return []

    def getDiscordMessageFromPost(self, Post):
        message = {'title': '', 'color': 0xCF2C94}
        message['footer'] = {
            'text': 'Instagram', 'icon_url': 'https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png'}
        try:
            message['description'] = Post['caption']['text']
            username = Post['user']['username']
            url = 'https://www.instagram.com/p/'+Post['code']
            message['content'] = '<@&647992314530103346> ' + \
                username + ' just posted on Instagram! ' + url
            message['author'] = {'name': username, 'icon_url': Post['user']
                                 ['profile_pic_url'], 'url': url}
            message['image'] = Post['image_versions2']['candidates'][0]['url']
        except KeyError:
            pass
        return message


def ReduceFile(Path, NumberlinesToReduceTo):
    lines = deque()
    try:
        f = open(Path)
        lines = deque(f, NumberlinesToReduceTo)
    finally:
        f.close()
    try:
        f = open(Path, 'w+')
        f.writelines(lines)
    finally:
        f.close()


class SocialMediaBot():
    def __init__(self, DiscordConfig, TwitterConfig, InstagramConfig, StateConfig):
        self.discord = DiscordWebhook(
            DiscordConfig['WebhookURL'], DiscordConfig['DryRun'])
        self.twitter = Twitter(
            TwitterConfig['ConsumerAPIKey'], TwitterConfig['APISecretKey'], TwitterConfig['AuthTTL'])
        self.twitter.auth()
        self.instagram = Instagram(
            InstagramConfig['Login'], InstagramConfig['Password'], InstagramConfig['AuthTTL'])
        self.instagram.auth()
        self.checkTwitterInterval = 60
        self.stateFile = StateConfig['FilePath']
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
            f = open(self.stateFile, 'a+')
            f.write(uid+'\n')
        finally:
            f.close()

    def sendRecentTweets(self):
        recentTweets = self.twitter.getTimeline(TwitterConfig['ScreenName'])
        for tweet in reversed(recentTweets):
            try:
                uid = 'twitter' + str(tweet['id'])
                if uid not in self.getSentMessageUids():
                    try:
                        self.discord.sendMessage(
                            self.twitter.getDiscordMessageFromTweet(tweet))
                        self.storeSentMessageUid(uid)
                    except ValueError:
                        pass
            except KeyError:
                pass

    def checkTwitter(self):
        threading.Timer(TwitterConfig['Interval'], self.checkTwitter).start()
        self.sendRecentTweets()

    def sendRecentInstagramPosts(self):
        recentPosts = self.instagram.getUserFeed()
        for post in reversed(recentPosts):
            try:
                uid = 'instagram'+str(post['id'])
                if uid not in self.getSentMessageUids():
                    try:
                        self.discord.sendMessage(
                            self.instagram.getDiscordMessageFromPost(post))
                        self.storeSentMessageUid(uid)
                    except ValueError:
                        pass
            except KeyError:
                pass

    def checkInstagram(self):
        threading.Timer(InstagramConfig['Interval'],
                        self.checkInstagram).start()
        self.sendRecentInstagramPosts()

    def cleanup(self):
        threading.Timer(
            StateConfig['CleanupInterval'], self.cleanup).start()
        ReduceFile(StateConfig['FilePath'], StateConfig['MaxEntries'])
        ReduceFile('socialmediabot.logs', 1000)

    def start(self):
        threading.Timer(
            StateConfig['CleanupInterval'], self.cleanup).start()
        self.checkTwitter()
        self.checkInstagram()


if __name__ == "__main__":
    dryRun = len(sys.argv) == 2 and sys.argv[1] == 'dryRun'
    DiscordConfig = {'WebhookURL': os.environ.get(
        'SOCIALMEDIABOT_DISCORD_WEBHOOK_URL'), 'DryRun': dryRun}
    TwitterConfig = {'ScreenName': os.environ.get('SOCIALMEDIABOT_TWITTER_SCREENNAME'), 'ConsumerAPIKey': os.environ.get(
        'SOCIALMEDIABOT_TWITTER_CONSUMER_API_KEY'), 'APISecretKey': os.environ.get('SOCIALMEDIABOT_TWITTER_API_SECRET_KEY'), 'Interval': 30, 'AuthTTL': 60*60}
    StateConfig = {'FilePath': 'socialmediabot.data',
                   'CleanupInterval': 3600*24, 'MaxEntries': 1000}
    InstagramConfig = {'Login': os.environ.get(
        'SOCIALMEDIABOT_INSTAGRAM_LOGIN'), 'Password': os.environ.get('SOCIALMEDIABOT_INSTAGRAM_PASSWORD'), 'Interval': 30, 'AuthTTL': 60*45}

    socialMediaBot = SocialMediaBot(
        DiscordConfig, TwitterConfig, InstagramConfig, StateConfig)
    socialMediaBot.start()
    if dryRun:
        print(
            "🚀  Social Media Bot - Dry Run. Creating state files but not sending messages")
        os._exit(0)
    print("🚀  Social Media Bot is running...")
