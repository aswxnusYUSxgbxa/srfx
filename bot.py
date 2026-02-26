import asyncio
from aiohttp import web
from flask import Flask
from threading import Thread
import os
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
import pytz
import aria2p
from config import *
from dotenv import load_dotenv
from database.db_premium import remove_expired_users
from database.database import db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from helper.db import MongoDB

# Silence APScheduler logs completely
logging.getLogger("apscheduler").setLevel(logging.CRITICAL)

load_dotenv(".env")

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Rohit")

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

import pyrogram.utils


def get_indian_time():
    """Returns the current time in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)

aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)

# Scheduler (shared)
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(remove_expired_users, "interval", seconds=10)


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER
        self.scheduler = AsyncIOScheduler()
        
        # New Mongo instance for new features
        self.mongodb = MongoDB(DB_URI, DB_NAME)
        
        # Attributes for new features
        self.fsub_dict = {}
        self.req_channels = []
        self.db_channels = {}  # Initialize DB channels dictionary
        self.primary_db_channel = CHANNEL_ID  # Set initial primary DB channel
        
        # These are used by new plugins, need to be populated from config or defaults
        self.messages = {} # Will be populated in start() or from config
        self.auto_del = 0 # Will be populated
        self.protect = False
        self.disable_btn = False
        self.reply_text = ""
        self.short_url = ""
        self.short_api = ""
        self.tutorial_link = ""
        self.shortner_enabled = True

    async def start(self):
        await super().start()
        scheduler.start()
        # Schedule daily reset of free usage at midnight IST
        try:
            scheduler.add_job(db.reset_all_free_usage, 'cron', hour=0, minute=0)
        except Exception as e:
            self.LOGGER(__name__).warning(f"Failed to schedule daily free reset: {e}")

        usr_bot_me = await self.get_me()
        self.uptime = get_indian_time()

        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(
                f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, Current Value {CHANNEL_ID}"
            )
            self.LOGGER(__name__).info("\nBot Stopped. @rohithinte thandha  for support")

            # --- DEBUGGING STEP ---
            self.LOGGER(__name__).info("Attempting to list visible channels/chats...")
            try:
                async for dialog in self.get_dialogs():
                    chat = dialog.chat
                    self.LOGGER(__name__).info(f"Seen Chat: {chat.title} (ID: {chat.id}, Type: {chat.type})")
            except Exception as inner_e:
                self.LOGGER(__name__).error(f"Failed to list dialogs: {inner_e}")
            # --- END DEBUGGING ---

            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        bot_name = usr_bot_me.first_name
        bot_id = usr_bot_me.id
        
        # --- NEW LOGIC: Load Settings from MongoDB ---
        # Load bot settings
        try:
            bot_settings = await self.mongodb.get_bot_settings()
            # If settings not in DB, use config defaults (which should be added to config.py later)
            # For now using some defaults or values from config if available
            self.disable_btn = bot_settings.get('disable_btn', getattr(sys.modules['config'], 'DISABLE_BTN', False))
            self.protect = bot_settings.get('protect', getattr(sys.modules['config'], 'PROTECT', False))
            self.auto_del = bot_settings.get('auto_del', getattr(sys.modules['config'], 'AUTO_DEL', 0))
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error loading bot settings: {e}")

        # Load messages
        try:
            self.messages = await self.mongodb.get_messages_settings()
            if not self.messages:
                 self.messages = getattr(sys.modules['config'], 'MESSAGES', {})
            self.reply_text = self.messages.get('REPLY', getattr(sys.modules['config'], 'USER_REPLY_TEXT', ''))
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error loading messages: {e}")

        # Load admins
        try:
            db_admins = await self.mongodb.get_admins_list()
            self.admins = db_admins
            if OWNER_ID not in self.admins:
                self.admins.append(OWNER_ID)
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error loading admins: {e}")
            self.admins = [OWNER_ID]
            
        # Load fsub channels (static first then dynamic)
        # Static loading (from config if FSUBS exists)
        if hasattr(sys.modules['config'], 'FSUBS'):
            for channel in sys.modules['config'].FSUBS:
                try:
                    chat = await self.get_chat(channel[0])
                    name = chat.title
                    link = None
                    if not channel[1]: # request_enabled is False
                        link = chat.invite_link
                    if not link and not channel[2]: # timer is 0
                        # Try to create link if bot is admin
                        try:
                            chat_link = await self.create_chat_invite_link(channel[0], creates_join_request=channel[1])
                            link = chat_link.invite_link
                        except: pass
                    
                    if not channel[1]:
                        self.fsub_dict[channel[0]] = [name, link, False, 0]
                    if channel[1]:
                        self.fsub_dict[channel[0]] = [name, link, True, 0]
                        self.req_channels.append(channel[0])
                    if channel[2] > 0:
                        self.fsub_dict[channel[0]] = [name, None, channel[1], channel[2]]
                except Exception as e:
                     self.LOGGER(__name__).warning(f"Error loading static fsub channel {channel[0]}: {e}")

        # Dynamic loading
        try:
            db_fsub_channels = await self.mongodb.get_fsub_channels()
            for channel_id_str, channel_data in db_fsub_channels.items():
                channel_id = int(channel_id_str)
                # Skip if already loaded from static config
                if channel_id in self.fsub_dict:
                    continue
                try:
                    chat = await self.get_chat(channel_id)
                    name = chat.title
                    # Update name in case it changed
                    channel_data[0] = name
                    self.fsub_dict[channel_id] = channel_data
                    if channel_data[2]:  # if request is True
                        self.req_channels.append(channel_id)
                except Exception as e:
                    self.LOGGER(__name__).warning(f"Could not load dynamic fsub channel {channel_id}: {e}")
                    # Remove invalid channel from database
                    await self.mongodb.remove_fsub_channel(channel_id)
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error loading dynamic fsub channels: {e}")
            
        await self.mongodb.set_channels(self.req_channels)

        # Load DB channels
        try:
            db_channels_data = await self.mongodb.get_db_channels()
            self.db_channels = {}
            # Don't overwrite self.db (which is Rohit instance), but new plugins use self.db as primary channel ID.
            # Wait, existing plugins use `from database.database import db` directly.
            # New plugins use `client.db` as PRIMARY CHANNEL ID (int).
            # I must ensure `self.db` is not overwritten if it breaks existing logic, but `Client` doesn't have `db` attribute by default.
            # Existing `bot.py` didn't have `self.db`. Existing plugins import `db` from module.
            # So I can safely set `self.db` to channel ID for new plugins!
            
            self.db = CHANNEL_ID # Default
            self.primary_db_channel = CHANNEL_ID
            
            for channel_id_str, channel_data in db_channels_data.items():
                channel_id = int(channel_id_str)
                try:
                    # Verify channel still exists and is accessible
                    chat = await self.get_chat(channel_id)
                    # Update name in case it changed
                    channel_data['name'] = chat.title
                    self.db_channels[channel_id_str] = channel_data
                    
                    # Set primary channel if marked as primary
                    if channel_data.get('is_primary', False):
                        self.primary_db_channel = channel_id
                        self.db = channel_id  # Update current db reference
                        
                except Exception as e:
                    self.LOGGER(__name__).warning(f"Could not load DB channel {channel_id}: {e}")
                    # Remove invalid channel from database
                    await self.mongodb.remove_db_channel(channel_id)
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error loading DB channels: {e}")

        # Load shortner settings
        try:
            shortner_settings = await self.mongodb.get_shortner_settings()
            self.short_url = shortner_settings.get('short_url', getattr(sys.modules['config'], 'SHORT_URL', ''))
            self.short_api = shortner_settings.get('short_api', getattr(sys.modules['config'], 'SHORT_API', ''))
            self.tutorial_link = shortner_settings.get('tutorial_link', getattr(sys.modules['config'], 'SHORT_TUT', ''))
            self.shortner_enabled = shortner_settings.get('enabled', True)
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error loading shortner settings: {e}")

        # ---------------------------------------------
        
        # Print bot information clearly
        print("\n" + "="*50)
        print("🤖 BOT SUCCESSFULLY STARTED!")
        print("="*50)
        print(f"Bot Username: @{self.username}")
        print(f"Bot Name: {bot_name}")
        print(f"Bot ID: {bot_id}")
        print(f"Channel ID: {CHANNEL_ID}")
        print(f"Video Range: {MIN_ID} to {MAX_ID} ({len(VIDEOS_RANGE)} videos)")
        print("="*50)
        print("Bot is now active and ready to receive commands!")
        print("="*50 + "\n")
        
        self.LOGGER(__name__).info(f"Bot Running..! Made by @rohithinte thandha ")
        self.LOGGER(__name__).info(f"Bot Username: @{self.username}")

        # Start Web Server
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        try:
            await self.send_message(
                OWNER_ID,
                text=f"<b><blockquote>🤖 Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @rohithinte thandha </blockquote></b>"
            )
        except:
            pass

    async def stop(self, *args):
        self.scheduler.shutdown(wait=False)  
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        """Run the bot."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running. Thanks to @rohithinte thandha ")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())


if __name__ == "__main__":
    Bot().run()
