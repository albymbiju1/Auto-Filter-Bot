import os
import time as _time
import asyncio
import uvloop
from pyrogram import Client
from pyrogram.errors import FloodWait
from aiohttp import web
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from info import LOG_CHANNEL, API_ID, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, DATABASE_URL

uvloop.install()

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
        """Initialize bot components and connect to MongoDB"""
        temp.START_TIME = _time.time()

        # MongoDB connection with retry mechanism
        client = MongoClient(DATABASE_URL, server_api=ServerApi('1'))
        retries = 5
        while retries > 0:
            try:
                client.admin.command('ping')
                print("Connected to MongoDB!")
                break
            except Exception as e:
                print(f"MongoDB connection failed, retrying in 5 seconds... ({retries} attempts left)")
                retries -= 1
                await asyncio.sleep(5)
                if retries == 0:
                    await self.send_message(LOG_CHANNEL, f"Failed to connect to MongoDB after multiple attempts. Error: {e}")
                    exit()

        # Start the bot properly
        await super().start()

        # Web server setup
        try:
            app = web.AppRunner(web_app)
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", PORT).start()
            print(f"Web server running on port {PORT}")
        except Exception as e:
            print(f"Failed to start web server: {e}")
            await self.send_message(LOG_CHANNEL, f"Failed to start web server: {e}")
            exit()

        # Check permissions in BIN_CHANNEL
        try:
            chat_member = await self.get_chat_member(BIN_CHANNEL, self.me.id)
            if not chat_member.can_send_messages:
                print("Bot does not have permission to send messages in BIN_CHANNEL.")
                await self.send_message(LOG_CHANNEL, "Bot does not have permission to send messages in BIN_CHANNEL.")
                exit()

            # Send test message and delete
            test_message = await self.send_message(chat_id=BIN_CHANNEL, text="Test")
            await test_message.delete()
        except Exception as e:
            print(f"Error with BIN_CHANNEL: {e}")
            await self.send_message(LOG_CHANNEL, f"Error with BIN_CHANNEL: {e}")
            exit()

        # Notify admins about bot restart
        for admin in ADMINS:
            await self.send_message(chat_id=admin, text="<b>✅ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ</b>")

    async def stop(self, *args):
        """Handle bot stop logic gracefully"""
        await super().stop()
        print("Bot stopped!")

    async def iter_messages(self, chat_id, limit, offset=0):
        """Iterate through messages in a chat."""
        current = offset
        while current < limit:
            new_diff = min(200, limit - current)
            messages = await self.get_messages(chat_id, list(range(current, current + new_diff)))
            for message in messages:
                yield message
                current += 1

# Function to handle bot start with flood wait handling
async def start_bot():
    while True:
        try:
            app = Bot()
            await app.start()
            break  # exit the loop once the bot starts successfully
        except FloodWait as e:
            wait_time = e.x
            print(f"Flood wait encountered, sleeping for {wait_time} seconds.")
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"An error occurred: {e}")
            await asyncio.sleep(5)  # Retry after a brief delay

if __name__ == "__main__":
    asyncio.run(start_bot())
