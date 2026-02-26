
from pyrogram import Client, filters
from pyrogram.types import Message
import logging

@Client.on_message(filters.all, group=-100)
async def log_channel_id(client: Client, message: Message):
    """
    Log channel ID of incoming messages to help user debug incorrect CHANNEL_ID config.
    """
    try:
        if message.chat:
            logging.info(f"[DEBUG] Received message in Chat: {message.chat.title} (ID: {message.chat.id}, Type: {message.chat.type})")

        if message.forward_from_chat:
             logging.info(f"[DEBUG] Message Forwarded from Chat: {message.forward_from_chat.title} (ID: {message.forward_from_chat.id}, Type: {message.forward_from_chat.type})")
    except Exception as e:
        logging.error(f"Error in debug logger: {e}")
