from telethon import TelegramClient, events
import aiohttp
import nextcord
from langdetect import detect
from deep_translator import GoogleTranslator
import textwrap
import os
import requests
import json
import random
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("WEBHOOK")
appid = os.environ.get("APPID")
apihash = os.environ.get("APIHASH")
apiname = os.environ.get("APINAME")
dlloc = os.environ.get("DLLOC")
input_channels_entities = os.environ.get("INPUT_CHANNELS_ENTITIES")
channels_avatars=os.environ.get("CHANNELS_AVATARS")
channels_avatars=json.loads(channels_avatars)
text_to_prepend=os.environ.get("TEXT_TO_PREPEND")

if input_channels_entities is not None:
  input_channels_entities = list(map(int, input_channels_entities.split(',')))
  
async def imgurimg(mediafile): # Uploads image to imgur
    url = "https://api.imgur.com/3/upload"

    payload = {
    'type': 'file'}
    files = [
    ('image', open(mediafile, 'rb'))
    ]
    headers = {
    'Authorization': str(random.randint(1,10000000000))
    }
    response = requests.request("POST", url, headers=headers, data = payload, files = files)
    return(json.loads(response.text))

async def imgur(mediafile): # Uploads video to imgur
    url = "https://api.imgur.com/3/upload"

    payload = {'album': 'ALBUMID',
    'type': 'file',
    'disable_audio': '0'}
    files = [
    ('video', open(mediafile,'rb'))
    ]
    headers = {
    'Authorization': str(random.randint(1,10000000000))
    }
    response = requests.request("POST", url, headers=headers, data = payload, files = files)
    return(json.loads(response.text))

def start():
    client = TelegramClient(apiname, 
                            appid, 
                            apihash)
    client.start()
    print('Started')
    
    @client.on(events.NewMessage(chats=input_channels_entities))
    async def handler(event):
        #if( str(event.chat.id) not in input_channels_entities):#Checking if the message is comming from one of the specified Telegram channels
         # return;
        
        #checking if the channel avatar is already specified on the .env file
        if(str(event.chat.id) in channels_avatars):
          channelAvatarUrl=channels_avatars[str(event.chat.id)]
        else: # if not we download it and upload it to imgur (since discord accept only avartar urls)
          channel = await client.get_entity(event.chat.id)
          channelAvatar = await client.download_profile_photo(channel,dlloc, download_big=False)
          channelAvatarUrl=await imgurimg(channelAvatar)
          os.remove(channelAvatar)  
          channelAvatarUrl = channelAvatarUrl['data']['link']
          channels_avatars[str(event.chat.id)]=channelAvatarUrl # we store it on the channels avatars array so we can use it another time without reuploading to imgur


        msg = event.message.message
        #Looking for href urls in the text message and appending them to the message
        try:
          for entity in event.message.entities:
            if ('MessageEntityTextUrl' in type(entity).__name__):
              msg +=f"\n\n{entity.url}" 
        except:
          print("no url captured, forwording message")

        if event.message.media is not None:
            
            if('MessageMediaWebPage' in type(event.message.media).__name__):# directly send message if the media attached is a webpage embed 
              await send_to_webhook(msg,event.chat.title,channelAvatarUrl)
            else:
              dur = event.message.file.duration # Get duration
              if dur is None:
                dur=1 # Set duration to 1 if media has no duration ex. photo
              # If duration is greater than 60 seconds or file size is greater than 8MB
              if dur>60 or event.message.file.size > 8388609: # Duration greater than 60s send link to media
                print('Media too long!')
                msg +=f"\n\nLink to Video: https://t.me/c/{event.chat.id}/{event.message.id}" 
                await send_to_webhook(msg,event.chat.title,channelAvatarUrl)
                return
              else: # Duration less than 60s send media
                path = await event.message.download_media(dlloc)
                await pic(path,msg,event.chat.title,channelAvatarUrl)
                os.remove(path)
        else: # No media text message
            await send_to_webhook(msg,event.chat.title,channelAvatarUrl)
        
    client.run_until_disconnected()

async def pic(filem,message,username,channelAvatarUrl): # Send media to webhook
    async with aiohttp.ClientSession() as session:
        print('Sending w media')
        webhook = nextcord.Webhook.from_url(url, session=session)
        try: # Try sending to discord
          f = nextcord.File(filem)
          await webhook.send(file=f,username=username,avatar_url=channelAvatarUrl)
        except: # If it fails upload to imgur
          print('File too big..')
          try:
            image = await imgur(filem) # Upload to imgur
            #print(image)
            image = image['data']['link']
            print(f'Imgur: {image}') 
            await webhook.send(content=image,username=username,avatar_url=channelAvatarUrl) # Send imgur link to discord
          except Exception as ee:
            print(f'Error {ee.args}') 
        for line in textwrap.wrap(message, 2000, replace_whitespace=False): # Send message to discord
            await webhook.send(content=line,username=username,avatar_url=channelAvatarUrl) 

async def send_to_webhook(message,username,channelAvatarUrl): # Send message to webhook
    if(text_to_prepend is not None):
      message=text_to_prepend+message
    async with aiohttp.ClientSession() as session:
        print('Sending w/o media')
        webhook = nextcord.Webhook.from_url(url, session=session)
        for line in textwrap.wrap(message, 2000, replace_whitespace=False): # Send message to discord
            await webhook.send(content=line,username=username,avatar_url=channelAvatarUrl)

if __name__ == "__main__":
    start()