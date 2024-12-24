import os
import time as _time  # Alias `time` to `_time`
import asyncio
import uvloop

# pyrogram imports
from pyrogram import types
from pyrogram import Client
from pyrogram.errors import FloodWait

# aiohttp imports
from aiohttp import web
from typing import Union, Optional, AsyncGenerator

# local imports
from web import web_app
from info import LOG_CHANNEL, API_ID, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, DATABASE_URL
from utils import temp, get_readable_time

# pymongo and database imports
from database.users_chats_db import db
from database.ia_filterdb import Media
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

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
        temp.START_TIME = _time.time()  # Use `_time` instead of `time`
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        client = MongoClient(DATABASE_URL, server_api=ServerApi('1'))
        try:
            client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print("Something Went Wrong While Connecting To Database!", e)
            exit()

        # Start the bot properly
        await super().start()

        if os.path.exists('restart.txt'):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file)
            try:
                await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
            except:
                pass
            os.remove('restart.txt')
        
        temp.BOT = self
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        username = '@' + me.username
        print(f"{me.first_name} is started now 🤗")
        
        # Setup web app
        app = web.AppRunner(web_app)
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>")
        except Exception as e:
            print(f"Error while sending message to LOG_CHANNEL: {e}")
            exit()
        
        # Checking permissions in BIN_CHANNEL
        try:
            chat_member = await self.get_chat_member(BIN_CHANNEL, me.id)
            if not chat_member.can_send_messages:
                print("Bot does not have permission to send messages in BIN_CHANNEL")
                await self.send_message(chat_id=LOG_CHANNEL, text="Bot does not have permission to send messages in BIN_CHANNEL")
                exit()
            # Send test message and delete
            m = await self.send_message(chat_id=BIN_CHANNEL, text="Test")
            await m.delete()
        except Exception as e:
            print(f"Error while sending message to BIN_CHANNEL: {e}")
            await self.send_message(chat_id=LOG_CHANNEL, text=f"Error while sending message to BIN_CHANNEL: {e}")
            exit()

        # Send restart notifications to admins
        for admin in ADMINS:
            await self.send_message(chat_id=admin, text="<b>✅ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ</b>")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped! Bye...")

    async def iter_messages(self: Client, chat_id: Union[int, str], limit: int, offset: int = 0) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially."""
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current + new_diff + 1)))
            for message in messages:
                yield message
                current += 1

# Function to handle the bot start with flood wait handling
async def start_bot():
    while True:
        try:
            app = Bot()
            await app.start()
            break  # exit the loop once the bot starts successfully
        except FloodWait as vp:
            wait_time = get_readable_time(vp.value)
            print(f"Flood Wait Occurred, Sleeping For {wait_time}")
            await asyncio.sleep(vp.value)  # Await asyncio sleep to handle delay
            print("Now Ready For Deploying!")
        except Exception as e:
            print(f"An error occurred: {e}")
            break  # Exit the loop on any other error

# Start the bot
if __name__ == "__main__":
    asyncio.run(start_bot())
