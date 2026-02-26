import logging
from datetime import datetime
from bot import Bot
from pyrogram import filters
from database.database import db
from config import CHANNEL_ID

logging.basicConfig(level=logging.INFO)

@Bot.on_message(filters.chat(CHANNEL_ID) & (filters.photo | filters.video | filters.document | filters.animation))
async def store_db_channel_media(client, message):
    """Store incoming media posted in configured DB channel into the database collections."""
    try:
        if message.photo:
            photo = message.photo[-1]
            file_id = photo.file_id
            file_unique_id = photo.file_unique_id
            exists = await db.photo_exists(file_id) or await db.photo_exists(file_unique_id)
            if not exists:
                await db.insert_photos([{
                    "file_id": file_id,
                    "file_unique_id": file_unique_id,
                    "caption": message.caption or "",
                    "message_id": message.message_id,
                    "chat_id": message.chat.id,
                    "added_at": datetime.utcnow()
                }])
                logging.info(f"Inserted photo {file_id} from channel {message.chat.id}")

        elif message.video:
            vid = message.video
            file_id = vid.file_id
            file_unique_id = vid.file_unique_id
            exists = await db.video_exists(file_id) or await db.video_exists(file_unique_id)
            if not exists:
                await db.insert_videos([{
                    "file_id": file_id,
                    "file_unique_id": file_unique_id,
                    "duration": vid.duration,
                    "mime_type": vid.mime_type,
                    "caption": message.caption or "",
                    "message_id": message.message_id,
                    "chat_id": message.chat.id,
                    "added_at": datetime.utcnow()
                }])
                logging.info(f"Inserted video {file_id} from channel {message.chat.id}")

        elif message.document or message.animation:
            doc = message.document or message.animation
            file_id = doc.file_id
            file_unique_id = doc.file_unique_id
            exists = await db.video_exists(file_id) or await db.video_exists(file_unique_id)
            if not exists:
                await db.insert_videos([{
                    "file_id": file_id,
                    "file_unique_id": file_unique_id,
                    "mime_type": getattr(doc, 'mime_type', None),
                    "caption": message.caption or "",
                    "message_id": message.message_id,
                    "chat_id": message.chat.id,
                    "added_at": datetime.utcnow()
                }])
                logging.info(f"Inserted document/animation {file_id} from channel {message.chat.id}")

    except Exception as e:
        logging.error(f"Error storing channel media: {e}")
