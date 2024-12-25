import os
import time as _time
import asyncio
import uvloop
from pyrogram import Client
from pyrogram.errors import FloodWait
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from info import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL, LOG_CHANNEL

uvloop.install()

class Temp:
    START_TIME = None
    BOT = None
    ME = None
    U_NAME = None
    B_NAME = None

temp = Temp()

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        temp.START_TIME = _time.time()
        
        # Enhanced logging to see where the failure is
        print("Starting bot... Checking MongoDB connection.")
        client = MongoClient(DATABASE_URL, server_api=ServerApi('1'))
        
        try:
            client.admin.command('ping')
            print("Pinged MongoDB successfully!")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            exit()

        retries = 5
        for attempt in range(retries):
            try:
                print(f"Attempt {attempt+1}/{retries}: Starting the bot...")
                await super().start()  # Attempt to start the bot
                break
            except FloodWait as e:
                wait_time = 0
                try:
                    # Attempt to parse the wait time correctly
                    if isinstance(e.x, str):
                        wait_time = int(e.x.split()[0])  # Extract numeric value if the message contains the wait time
                    else:
                        wait_time = int(e.x)
                except Exception as parse_error:
                    print(f"Error parsing FloodWait: {parse_error}")
                    wait_time = 60  # Default wait time if parsing fails
                
                print(f"FloodWait encountered. Waiting for {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f"Error during bot start attempt {attempt+1}: {e}")
                if attempt == retries - 1:
                    print("Bot failed to start after maximum retries.")
                    return
                await asyncio.sleep(5)  # Small wait before retry

        # If the bot starts, perform the usual operations
        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        print(f"Bot {me.first_name} started successfully!")

        # More logic to handle channels and additional functionality goes here
        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=f"Bot started successfully: {me.first_name}")
        except Exception as e:
            print(f"Failed to send log message: {e}")

    async def stop(self, *args):
        await super().stop()
        print("Bot stopped!")

    async def iter_messages(self, chat_id, limit: int, offset: int = 0):
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current + new_diff + 1)))
            for message in messages:
                yield message
                current += 1

async def start_bot():
    try:
        app = Bot()
        await app.start()
    except Exception as e:
        print(f"An error occurred while starting the bot: {e}")

if __name__ == "__main__":
    asyncio.run(start_bot())
