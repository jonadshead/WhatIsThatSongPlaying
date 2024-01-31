import requests
import webbrowser
import urllib.parse
import asyncio
from flask import Flask, redirect, request
from datetime import datetime
from twitchio.ext import commands
from threading import Thread
import json
import os

app = Flask(__name__)
app.secret_key = 'EnWL9aqh-oAmD-9yOc-HRFH-57MYt33xacNA'

session = {}
config = {}

def read_config(filename="config.json"):
    if not os.path.exists(filename):
        print(f"Config file '{filename}' not found.")
        return None

    with open(filename, 'r') as file:
        config = json.load(file)

    if not config.get("Twitch Channel Name (required)"):
        print("Twitch Channel Name is required. Please fill it in the config file.")
        return None

    # YOU MUST FILL THESE VALUES IN FOR THE APPLICATION TO WORK VIA PYTHON SCRIPT. VALUES ARE PROVIDED ONLY IN COMPILED EXECUTABLE FOR SECURITY PURPOSES.
    default_values = {
        "Spotify App Client Id (optional)": "",
        "Spotify App Client Secret (optional)": "",
        "Twitch Chat Bot OAuth (optional)": ""
    }
    for key, value in default_values.items():
        if not config.get(key):
            config[key] = value

    return config

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=config['Twitch Chat Bot OAuth (optional)'], prefix='!', initial_channels=[config['Twitch Channel Name (required)']])

    async def event_ready(self):
        print(f'Logged in as {self.nick}')

    @commands.command()
    async def song(self, ctx: commands.Context):
        current_track_info = currently_playing()
        if current_track_info == "No track is currently playing.":
            await ctx.send(f'{current_track_info}')
        else:
            track_name = current_track_info['track_name']
            artists = current_track_info['artists']
            link = current_track_info['link']
            await ctx.send(f'{track_name} by {artists} - {link}')

@app.route('/login')
def login():
    params = {
        'client_id': config['Spotify App Client Id (optional)'],
        'response_type': 'code',
        'scope': 'user-read-currently-playing',
        'redirect_uri': 'http://localhost:5000/callback',
        'show_dialog': True
    }

    auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return redirect('/login')
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:5000/callback',
            'client_id': config['Spotify App Client Id (optional)'],
            'client_secret': config['Spotify App Client Secret (optional)']
        }

        response = requests.post('https://accounts.spotify.com/api/token', data=req_body)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        return "Login Successful."
    
def currently_playing():
    if 'access_token' not in session:
        webbrowser.open_new_tab('http://127.0.0.1:5000/login')
        return
    
    if datetime.now().timestamp() > session['expires_at']:
        refresh_token()
        return
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get('https://api.spotify.com/v1/me/player/currently-playing', headers=headers)
    
    if response.status_code == 200:
        currently_playing = response.json()

        track_name = currently_playing['item']['name']
        artists = [artist for artist in currently_playing['item']['artists']]
        link = currently_playing['item']['external_urls']['spotify']

        artist_names = ', '.join([artist['name'] for artist in artists])

        current_track_info = {"track_name": track_name, "artists": artist_names, "link": link}

        if currently_playing['is_playing']:
            return current_track_info
    
    return "No track is currently playing."

def refresh_token():
    if 'refresh_token' not in session:
        webbrowser.open_new_tab('http://127.0.0.1:5000/login')
        return
    
    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': config['Spotify App Client Id (optional)'],
            'client_secret': config['Spotify App Client Secret (optional)']
        }

        response = requests.post('https://accounts.spotify.com/api/token', data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

async def run_bot():
    bot = Bot()
    await bot.start()

def run_twitch_bot():
    asyncio.run(run_bot())
    
if __name__ == '__main__':
    config = read_config()
    if config:
        webbrowser.open_new_tab('http://127.0.0.1:5000/login')
        thread = Thread(target=run_twitch_bot)
        thread.start()
        app.run(host='0.0.0.0')
    