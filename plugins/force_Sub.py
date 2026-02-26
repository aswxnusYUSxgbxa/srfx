
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

MAX_CHANNELS = 5  



async def check_force_sub(client, user_id: int):

    
    all_channels = list(client.fsub_dict.keys())[:MAX_CHANNELS]

    if not all_channels:
        return True

    buttons = []

    for channel_id in all_channels:
        try:
            member = await client.get_chat_member(channel_id, user_id)

            if member.status in ["member", "administrator", "creator"]:
                continue

            invite = await client.create_chat_invite_link(channel_id)
            link = invite.invite_link

            buttons.append([
                InlineKeyboardButton("Join Channel", url=link)
            ])

        except:
            continue

    if not buttons:
        return True

    buttons.append([
        InlineKeyboardButton("🔄 Try Again", callback_data="recheck_fsub")
    ])

    return InlineKeyboardMarkup(buttons)


@Client.on_callback_query(filters.regex("^recheck_fsub$"))
async def recheck_fsub(client: Client, query: CallbackQuery):

    user_id = query.from_user.id
    all_channels = list(client.fsub_dict.keys())[:MAX_CHANNELS]

    all_joined = True

    for channel_id in all_channels:
        try:
            member = await client.get_chat_member(channel_id, user_id)

            if member.status not in ["member", "administrator", "creator"]:
                all_joined = False

        except:
            all_joined = False

    if all_joined:
        await query.message.edit_text("✅ All required channels joined successfully!")
    else:
        markup = await check_force_sub(client, user_id)
        await query.message.edit_reply_markup(markup)
