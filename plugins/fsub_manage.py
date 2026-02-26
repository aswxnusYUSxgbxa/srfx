from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMINS






@Client.on_message(filters.command("add_fsub") & filters.user(ADMINS))
async def add_fsub_cmd(client, message: Message):
    await message.reply(
        "📢 Please forward any message from the channel you want to add as Force Subscribe."
    )






@Client.on_message(filters.forwarded & filters.user(ADMINS))
async def save_fsub_channel(client, message: Message):

    if not message.forward_from_chat:
        return

    channel = message.forward_from_chat
    channel_id = channel.id
    channel_username = channel.username
    channel_title = channel.title

    
    data = await client.mongodb.get_fsub_channels()

    
    data[str(channel_id)] = {
        "username": channel_username,
        "title": channel_title
    }

    
    await client.mongodb.set_fsub_channels(data)

    await message.reply(
        f"✅ Force Subscribe Channel Added Successfully!\n\n"
        f"📌 Title: {channel_title}\n"
        f"🆔 ID: `{channel_id}`"
    )
