
import asyncio
import base64
import logging
import os
import random
import re
import string
import time

from datetime import datetime, timedelta
from pytz import timezone
import pytz

from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus
from pyrogram.types import (
    Message,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    ReplyKeyboardMarkup,
)
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from plugins.autoDelete import auto_del_notification, delete_message
from bot import Bot
from config import *
from helper.helper_func import is_admin, subscribed, banUser, is_subscribed, check_subscription
from helper_func import *
from database.database import db
from database.db_premium import *
from plugins.FORMATS import *


from helper.helper_func import get_messages, decode, batch_auto_del_notification, force_sub
from plugins.shortner import get_short


logging.basicConfig(level=logging.INFO)
IST = timezone("Asia/Kolkata")


@Bot.on_message(filters.command("start") & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    user_id = id
    text = message.text or ""
    logging.info(f"Received /start command from user ID: {id}")




    if await db.ban_user_exist(user_id):
        return await message.reply_text(BAN_TXT, quote=True)


    is_banned = await client.mongodb.is_banned(user_id)
    if is_banned:
        return await message.reply("**You have been banned from using this bot!**")


    try:
        if not await db.present_user(id):
            await db.add_user(id)
    except Exception as e:
        logging.error(f"Error ensuring user exists ({id}): {e}")


    present = await client.mongodb.present_user(user_id)
    if not present:
        try:
            await client.mongodb.add_user(user_id)
        except Exception as e:
            client.LOGGER(__name__).warning(f"Error adding a user to new DB:\n{e}")


    try:
        verify_status = await db.get_verify_status(id) or {}
    except Exception as e:
        logging.error(f"Error fetching verify status for {id}: {e}")
        verify_status = {"is_verified": False, "verified_time": 0, "verify_token": "", "link": ""}

    try:
        VERIFY_EXPIRE = await db.get_verified_time()
    except Exception as e:
        logging.error(f"Error fetching verify expiry config: {e}")
        VERIFY_EXPIRE = None


    try:
        if verify_status.get("is_verified") and VERIFY_EXPIRE:
            verified_time = verify_status.get("verified_time", 0)
            if (time.time() - verified_time) > VERIFY_EXPIRE:
                await db.update_verify_status(id, is_verified=False)
                verify_status["is_verified"] = False
    except Exception as e:
        logging.error(f"Error while checking/refreshing verify expiry for {id}: {e}")




    if len(text) > 7:

        if "ref_" in text:
            try:
                _, ref_user_id_str = text.split("_", 1)
                ref_user_id = int(ref_user_id_str)
            except (ValueError, IndexError):
                ref_user_id = None

            if ref_user_id and ref_user_id != user_id:
                try:
                    already_referred = await db.check_referral_exists(user_id)
                except Exception as e:
                    logging.error(f"Error checking existing referral for {user_id}: {e}")
                    already_referred = False

                if not already_referred:
                    try:
                        referral_added = await db.add_referral(ref_user_id, user_id)
                    except Exception as e:
                        logging.error(f"Error adding referral ({ref_user_id} -> {user_id}): {e}")
                        referral_added = False

                    if referral_added:
                        try:
                            referral_count = await db.get_referral_count(ref_user_id)
                        except Exception as e:
                            logging.error(f"Error fetching referral count for {ref_user_id}: {e}")
                            referral_count = 0


                        if REFERRAL_COUNT and referral_count > 0 and (referral_count % REFERRAL_COUNT == 0):
                            try:
                                is_prem = await is_premium_user(ref_user_id)
                            except Exception as e:
                                logging.error(f"Error checking premium for {ref_user_id}: {e}")
                                is_prem = False

                            try:
                                if not is_prem:
                                    await add_premium(ref_user_id, REFERRAL_PREMIUM_DAYS, "d")
                                    try:
                                        await client.send_message(
                                            ref_user_id,
                                            f"🎉 Cᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! Yᴏᴜ'ᴠᴇ ʀᴇᴄᴇɪᴠᴇᴅ {REFERRAL_PREMIUM_DAYS} ᴅᴀʏs ᴏғ Pʀᴇᴍɪᴜᴍ!"
                                        )
                                    except Exception:
                                        pass
                                else:
                                    user_data = await collection.find_one({"user_id": ref_user_id})
                                    if user_data and user_data.get("expiration_timestamp"):
                                        try:
                                            ist = timezone("Asia/Kolkata")
                                            current_expiry = datetime.fromisoformat(user_data["expiration_timestamp"])
                                            if current_expiry.tzinfo is None:
                                                current_expiry = ist.localize(current_expiry)
                                            new_expiry = current_expiry + timedelta(days=REFERRAL_PREMIUM_DAYS)
                                            await collection.update_one(
                                                {"user_id": ref_user_id},
                                                {"$set": {"expiration_timestamp": new_expiry.isoformat()}}
                                            )
                                            try:
                                                await client.send_message(
                                                    ref_user_id,
                                                    f"🎉 Yᴏᴜʀ Pʀᴇᴍɪᴜᴍ ᴇxᴛᴇɴᴅᴇᴅ ʙʏ {REFERRAL_PREMIUM_DAYS} ᴅᴀʏs!"
                                                )
                                            except Exception:
                                                pass
                                        except Exception as e:
                                            logging.error(f"Error extending premium expiry: {e}")
                                    else:
                                        await add_premium(ref_user_id, REFERRAL_PREMIUM_DAYS, "d")
                                        try:
                                            await client.send_message(
                                                ref_user_id,
                                                f"🎉 Yᴏᴜ'ᴠᴇ ʀᴇᴄᴇɪᴠᴇᴅ {REFERRAL_PREMIUM_DAYS} ᴅᴀʏs ᴏғ Pʀᴇᴍɪᴜᴍ!"
                                            )
                                        except Exception:
                                            pass
                            except Exception as e:
                                logging.error(f"Error while granting/extending premium: {e}")


        if "verify_" in text:
            try:
                _, token = text.split("_", 1)
            except ValueError:
                token = None

            if token:
                if verify_status.get("verify_token") != token:
                    return await message.reply("⚠️ Invalid/Expired Token. Use /start again.")

                try:
                    await db.update_verify_status(user_id, is_verified=True, verified_time=time.time())
                except Exception as e:
                    logging.error(f"Error updating verify status: {e}")

                expiry_text = get_exp_time(VERIFY_EXPIRE) if VERIFY_EXPIRE else "the configured duration"
                return await message.reply(
                    f"✅ Token Verified Successfully!\n\n🔑 Valid For: {expiry_text}.",
                    quote=True
                )


        if text.startswith("/start get_photo_") or "get_photo_" in text:
            try:
                if "get_photo_" in text:
                    _, user_id_str = text.split("get_photo_", 1)
                else:
                    _, user_id_str = text.split("_", 2)


                return await get_photo(client, message)
            except:
                pass

        if text.startswith("/start get_video_") or "get_video_" in text:
            try:
                return await get_video(client, message)
            except:
                pass

        if text.startswith("/start get_batch_") or "get_batch_" in text:
            try:
                return await get_batch(client, message)
            except:
                pass



        if not any(x in text for x in ["verify_", "ref_", "get_photo_", "get_video_", "get_batch_"]):
            try:

                if " " in text:
                    original_payload = text.split(" ", 1)[1]
                else:
                    original_payload = text

                base64_string = original_payload
                is_short_link = False

                if base64_string.startswith("yu3elk"):
                    base64_string = base64_string[6:-1]
                    is_short_link = True


                is_user_pro = await client.mongodb.is_pro(user_id)


                shortner_enabled = getattr(client, 'shortner_enabled', True)



                if not is_user_pro and user_id != OWNER_ID and not is_short_link and shortner_enabled:
                    try:
                        short_link = get_short(f"https://t.me/{client.username}?start=yu3elk{base64_string}7", client)
                    except Exception as e:
                        client.LOGGER(__name__).warning(f"Shortener failed: {e}")
                        return await message.reply("Couldn't generate short link.")

                    short_photo = client.messages.get("SHORT_PIC", "")
                    short_caption = client.messages.get("SHORT_MSG", "")
                    tutorial_link = getattr(client, 'tutorial_link', "https://t.me/How_to_Download_7x/26")

                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=short_photo,
                        caption=short_caption,
                        reply_markup=InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("• ᴏᴘᴇɴ ʟɪɴᴋ", url=short_link),
                                InlineKeyboardButton("ᴛᴜᴛᴏʀɪᴀʟ •", url=tutorial_link)
                            ],
                            [
                                InlineKeyboardButton(" • ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data='buy_prem')
                            ]
                        ])
                    )
                    return


                try:
                    string = await decode(base64_string)
                    argument = string.split("-")
                    ids = []
                    source_channel_id = None

                    if len(argument) == 3:

                        encoded_start = int(argument[1])
                        encoded_end = int(argument[2])


                        primary_multiplier = abs(client.db)
                        start_primary = int(encoded_start / primary_multiplier)
                        end_primary = int(encoded_end / primary_multiplier)


                        if encoded_start % primary_multiplier == 0 and encoded_end % primary_multiplier == 0:
                            source_channel_id = client.db
                            start = start_primary
                            end = end_primary
                        else:

                            db_channels = getattr(client, 'db_channels', {})
                            for channel_id_str in db_channels.keys():
                                channel_id = int(channel_id_str)
                                channel_multiplier = abs(channel_id)
                                start_test = int(encoded_start / channel_multiplier)
                                end_test = int(encoded_end / channel_multiplier)

                                if encoded_start % channel_multiplier == 0 and encoded_end % channel_multiplier == 0:
                                    source_channel_id = channel_id
                                    start = start_test
                                    end = end_test
                                    break


                            if source_channel_id is None:
                                source_channel_id = client.db
                                start = start_primary
                                end = end_primary

                        ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))

                    elif len(argument) == 2:

                        encoded_msg = int(argument[1])


                        primary_multiplier = abs(client.db)
                        msg_id_primary = int(encoded_msg / primary_multiplier)

                        if encoded_msg % primary_multiplier == 0:
                            source_channel_id = client.db
                            ids = [msg_id_primary]
                        else:

                            db_channels = getattr(client, 'db_channels', {})
                            for channel_id_str in db_channels.keys():
                                channel_id = int(channel_id_str)
                                channel_multiplier = abs(channel_id)
                                msg_id_test = int(encoded_msg / channel_multiplier)

                                if encoded_msg % channel_multiplier == 0:
                                    source_channel_id = channel_id
                                    ids = [msg_id_test]
                                    break


                            if source_channel_id is None:
                                source_channel_id = client.db
                                ids = [msg_id_primary]

                except Exception as e:
                    client.LOGGER(__name__).warning(f"Error decoding base64: {e}")

                    if not "ref_" in text and not "verify_" in text:
                        return await message.reply("⚠️ Invalid or expired link.")
                    return


                temp_msg = await message.reply("Wait A Sec..")
                messages = []

                try:

                    if source_channel_id:
                        try:
                            msgs = await client.get_messages(
                                chat_id=source_channel_id,
                                message_ids=list(ids)
                            )

                            valid_msgs = [msg for msg in msgs if msg is not None]
                            messages.extend(valid_msgs)


                            if len(valid_msgs) < len(list(ids)):
                                missing_ids = [mid for mid in ids if mid not in {msg.id for msg in valid_msgs}]
                                if missing_ids:

                                    additional_messages = await get_messages(client, missing_ids)
                                    messages.extend(additional_messages)
                        except Exception as e:
                            client.LOGGER(__name__).warning(f"Error getting messages from source channel {source_channel_id}: {e}")

                            messages = await get_messages(client, ids)
                    else:

                        messages = await get_messages(client, ids)
                except Exception as e:
                    await temp_msg.edit_text("Something went wrong!")
                    client.LOGGER(__name__).warning(f"Error getting messages: {e}")
                    return

                if not messages:
                    return await temp_msg.edit("Couldn't find the files in the database.")
                await temp_msg.delete()

                yugen_msgs = []

                custom_caption = await db.get_custom_caption()
                hide_caption = await db.get_hide_caption()
                if not custom_caption:
                    from config import CUSTOM_CAPTION
                    custom_caption = CUSTOM_CAPTION

                for msg in messages:
                    if hide_caption:
                        caption = ""
                    elif custom_caption:
                        caption = custom_caption
                    else:
                        caption = (
                            client.messages.get('CAPTION', '').format(
                                previouscaption=msg.caption.html if msg.caption else msg.document.file_name
                            ) if bool(client.messages.get('CAPTION', '')) and bool(msg.document)
                            else ("" if not msg.caption else msg.caption.html)
                        )

                    reply_markup = msg.reply_markup if not client.disable_btn else None

                    try:
                        chnl_btn = await db.get_channel_button()
                        if chnl_btn:
                            button_name, button_link, button_name2, button_link2 = await db.get_channel_button_links()
                            buttons = []
                            if button_name and button_link:
                                buttons.append(InlineKeyboardButton(text=button_name, url=button_link))
                            if button_name2 and button_link2:
                                buttons.append(InlineKeyboardButton(text=button_name2, url=button_link2))
                            if buttons:
                                if reply_markup and hasattr(reply_markup, 'inline_keyboard'):
                                    new_keyboard = reply_markup.inline_keyboard.copy()
                                    new_keyboard.append(buttons)
                                    reply_markup = InlineKeyboardMarkup(new_keyboard)
                                else:
                                    reply_markup = InlineKeyboardMarkup([buttons])
                    except Exception as e:
                        client.LOGGER(__name__).warning(f"Error appending custom button: {e}")

                    try:
                        copied_msg = await msg.copy(
                            chat_id=message.from_user.id,
                            caption=caption,
                            reply_markup=reply_markup,
                            protect_content=client.protect
                        )
                        yugen_msgs.append(copied_msg)
                    except FloodWait as e:
                        await asyncio.sleep(e.x)
                        copied_msg = await msg.copy(
                            chat_id=message.from_user.id,
                            caption=caption,
                            reply_markup=reply_markup,
                            protect_content=client.protect
                        )
                        yugen_msgs.append(copied_msg)
                    except Exception as e:
                        client.LOGGER(__name__).warning(f"Failed to send message: {e}")
                        pass


                if messages and client.auto_del > 0:

                    transfer_link = original_payload


                    asyncio.create_task(batch_auto_del_notification(
                        bot_username=client.username,
                        messages=yugen_msgs,
                        delay_time=client.auto_del,
                        transfer_link=transfer_link,
                        chat_id=message.from_user.id,
                        client=client
                    ))
                return

            except IndexError:
                pass







    is_admin_user = user_id in client.admins or user_id == OWNER_ID

    keyboard_buttons = [
        [KeyboardButton("Get Photo 📸"), KeyboardButton("Get Batch 📦")],
        [KeyboardButton("Get Video 🍒"), KeyboardButton("Plan Status 🔖")],
    ]

    if is_admin_user:
        keyboard_buttons.append([KeyboardButton("Settings ⚙️")])

    reply_kb = ReplyKeyboardMarkup(
        keyboard_buttons,
        resize_keyboard=True,
    )


    referral_link = f"https://telegram.dog/{client.username}?start=ref_{user_id}"



    inline_buttons = []
    if is_admin_user:
        inline_buttons.append([InlineKeyboardButton("⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", callback_data="settings")])


    inline_buttons.append([InlineKeyboardButton("Help", callback_data="about"), InlineKeyboardButton("Close", callback_data='close')])


    try:

        start_caption = client.messages.get('START', START_MSG).format(
                first=message.from_user.first_name or "",
                last=message.from_user.last_name or "",
                username=None if not message.from_user.username else "@" + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id,
            )


        start_caption += f"\n\n🎁 <b>Referral System:</b>\n"
        start_caption += f"🔗 Your Link: <code>{referral_link}</code>\n"
        start_caption += f"📊 Refer {REFERRAL_COUNT} users = {REFERRAL_PREMIUM_DAYS} Days Premium!"

        photo = client.messages.get("START_PHOTO", START_PIC)

        if photo:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=start_caption,
                reply_markup=reply_kb
            )










            if is_admin_user:
                 await client.send_message(
                    chat_id=message.chat.id,
                    text="<b>Admin Controls:</b>",
                    reply_markup=InlineKeyboardMarkup(inline_buttons)
                 )

        else:
            await client.send_message(
                chat_id=message.chat.id,
                text=start_caption,
                reply_markup=reply_kb
            )
            if is_admin_user:
                 await client.send_message(
                    chat_id=message.chat.id,
                    text="<b>Admin Controls:</b>",
                    reply_markup=InlineKeyboardMarkup(inline_buttons)
                 )

    except Exception as e:
        logging.error(f"Error sending start message: {e}")
        await message.reply(
            START_MSG.format(
                first=message.from_user.first_name or "",
                last=message.from_user.last_name or "",
                username=None if not message.from_user.username else "@" + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id,
            ),
            reply_markup=reply_kb
        )






@Bot.on_message(filters.command('check') & filters.private)
async def check_command(client: Client, message: Message):
    user_id = message.from_user.id


    is_premium = await is_premium_user(user_id)

    if is_premium:

        return await message.reply_text(
            "✅ Yᴏᴜ ᴀʀᴇ ᴀ Pʀᴇᴍɪᴜᴍ Usᴇʀ.\n\n🔓 Nᴏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ɴᴇᴇᴅᴇᴅ!",
            protect_content=False,
            quote=True
        )


    try:
        verify_status = await db.get_verify_status(user_id) or {}
        VERIFY_EXPIRE = await db.get_verified_time()
    except Exception as e:
        logging.error(f"Error fetching verify status: {e}")
        verify_status = {"is_verified": False}
        VERIFY_EXPIRE = None

    if verify_status.get("is_verified", False):
        expiry_text = get_exp_time(VERIFY_EXPIRE) if VERIFY_EXPIRE else "the configured duration"
        return await message.reply_text(
            f"✅ Yᴏᴜ ᴀʀᴇ ᴠᴇʀɪғɪᴇᴅ.\n\n🔑 Vᴀʟɪᴅ ғᴏʀ: {expiry_text}.",
            protect_content=False,
            quote=True
        )


    try:
        shortener_url = await db.get_shortener_url()
        shortener_api = await db.get_shortener_api()
    except Exception as e:
        logging.error(f"Error fetching shortener settings: {e}")
        shortener_url = None
        shortener_api = None

    if shortener_url and shortener_api:

        try:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            await db.update_verify_status(user_id, verify_token=token, link="")

            long_url = f"https://telegram.dog/{client.username}?start=verify_{token}"
            short_link = await get_shortlink(long_url)

            tut_vid_url = await db.get_tut_video() or TUT_VID

            btn = [
                [InlineKeyboardButton("Click here", url=short_link),
                 InlineKeyboardButton('How to use the bot', url=tut_vid_url)],
                [InlineKeyboardButton('BUY PREMIUM', callback_data='buy_prem')]
            ]

            expiry_text = get_exp_time(VERIFY_EXPIRE) if VERIFY_EXPIRE else "the configured duration"
            return await message.reply(
                f"Your ads token is expired or invalid. Please verify to access the files.\n\n"
                f"Token Timeout: {expiry_text}\n\n"
                f"What is the token?\n\n"
                f"This is an ads token. By passing 1 ad, you can use the bot for {expiry_text}.",
                reply_markup=InlineKeyboardMarkup(btn),
                protect_content=False,
                quote=True
            )
        except Exception as e:
            logging.error(f"Error in verification process: {e}")
            return await message.reply_text(
                "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.",
                protect_content=False,
                quote=True
            )
    else:

        return await message.reply_text(
            "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.",
            protect_content=False,
            quote=True
        )


@Bot.on_message(filters.regex("Plan Status 🔖"))
async def on_plan_status(client: Client, message: Message):
    from pytz import timezone
    ist = timezone("Asia/Kolkata")

    user_id = message.from_user.id

    if await db.ban_user_exist(user_id):
        return await message.reply_text(BAN_TXT, quote=True)



    if not await is_subscribed(client, message):
        return await not_joined(client, message)

    is_premium = await is_premium_user(user_id)


    free_limit = await db.get_free_limit(user_id)
    free_enabled = await db.get_free_state(user_id)
    free_count = await db.check_free_usage(user_id)

    if is_premium:

        user_data = await collection.find_one({"user_id": user_id})
        expiration_timestamp = user_data.get("expiration_timestamp") if user_data else None

        if expiration_timestamp:
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
            remaining_time = expiration_time - datetime.now(ist)

            days = remaining_time.days
            hours = remaining_time.seconds // 3600
            minutes = (remaining_time.seconds // 60) % 60
            seconds = remaining_time.seconds % 60
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

            status_message = (
                f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Pʀᴇᴍɪᴜᴍ ✅\n\n"
                f"Rᴇᴍᴀɪɴɪɴɢ Tɪᴍᴇ: {expiry_info}\n\n"
                f"Vɪᴅᴇᴏs Rᴇᴍᴀɪɴɪɴɢ Tᴏᴅᴀʏ: Uɴʟɪᴍɪᴛᴇᴅ 🎉"
            )
        else:
            status_message = (
                f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Pʀᴇᴍɪᴜᴍ ✅\n\n"
                f"Pʟᴀɴ Exᴘɪʀʏ: N/A"
            )


        await message.reply_text(
            status_message,
            reply_markup=ReplyKeyboardMarkup(
                [["Plan Status 🔖", "Get Video 🍒"]],
                resize_keyboard=True
            ),
            protect_content=False,
            quote=True
        )

    elif free_enabled:

        remaining_attempts = free_limit - free_count
        status_message = (
            f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Fʀᴇᴇ (ᘜᗩᖇᗴᗴᗷ) 🆓\n\n"
            f"Vɪᴅᴇᴏs Rᴇᴍᴀɪɴɪɴɢ Tᴏᴅᴀʏ: {remaining_attempts}/{free_limit}"
        )

        await message.reply_text(
            status_message,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            ),
            protect_content=False,
            quote=True
        )

    else:

        status_message = (
            f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Fʀᴇᴇ (ᘜᗩᖇᗴᗴᗷ) (Dɪsᴀʙʟᴇᴅ)\n\n"
            f"Vɪᴅᴇᴏs Rᴇᴍᴀɪɴɪɴɢ Tᴏᴅᴀʏ: 0/{free_limit}"
        )

        await message.reply_text(
            status_message,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            ),
            protect_content=False,
            quote=True
        )


@Bot.on_message(filters.regex("Get Video 🍒"))
async def on_get_video(client: Client, message: Message):
    user_id = message.from_user.id

    if await db.ban_user_exist(user_id):
        return await message.reply_text(BAN_TXT, quote=True)



    if not await is_subscribed(client, message):
        return await not_joined(client, message)

    await get_video(client, message)


@Bot.on_message(filters.regex("Get Photo 📸"))
async def on_get_photo(client: Client, message: Message):
    user_id = message.from_user.id

    if await db.ban_user_exist(user_id):
        return await message.reply_text(BAN_TXT, quote=True)



    if not await is_subscribed(client, message):
        return await not_joined(client, message)

    await get_photo(client, message)


@Bot.on_message(filters.regex("Get Batch 📦"))
async def on_get_batch(client: Client, message: Message):
    user_id = message.from_user.id

    if await db.ban_user_exist(user_id):
        return await message.reply_text(BAN_TXT, quote=True)



    if not await is_subscribed(client, message):
        return await not_joined(client, message)
    await get_batch(client, message)



async def store_videos(app: Client):
    full, part = divmod(len(VIDEOS_RANGE), 200)
    all_videos = []

    for i in range(full):
        messages = await try_until_get(
            app.get_messages(CHANNEL_ID, VIDEOS_RANGE[i * 11470: (i + 1) * 11470])
        )
        for msg in messages:
            if msg and msg.video:
                file_id = msg.video.file_id
                exists = await db.video_exists(file_id)
                if not exists:
                    all_videos.append({"file_id": file_id})

    remaining_messages = await try_until_get(
        app.get_messages(CHANNEL_ID, VIDEOS_RANGE[full * 11470:])
    )
    for msg in remaining_messages:
        if msg and msg.video:
            file_id = msg.video.file_id
            exists = await db.video_exists(file_id)
            if not exists:
                all_videos.append({"file_id": file_id})

    if all_videos:
        await db.insert_videos(all_videos)



async def send_random_video(client: Client, chat_id, protect=True, caption="", reply_markup=None, hide_caption=False):
    vids = await db.get_videos()
    if not vids:
        await store_videos(client)
        vids = await db.get_videos()

    # Filter out empty file_ids
    valid_vids = [v for v in vids if v.get("file_id")]
    if valid_vids:
        random_video = random.choice(valid_vids)

        final_caption = "" if hide_caption else (caption if caption else None)
        try:
            sent_msg = await client.send_video(
                chat_id,
                random_video["file_id"],
                caption=final_caption,
                parse_mode=ParseMode.HTML if final_caption else None,
                reply_markup=reply_markup,
                protect_content=protect
            )
            return sent_msg
        except FloodWait as e:
            await asyncio.sleep(e.x)
            sent_msg = await client.send_video(
                chat_id,
                random_video["file_id"],
                caption=final_caption,
                parse_mode=ParseMode.HTML if final_caption else None,
                reply_markup=reply_markup,
                protect_content=protect
            )
            return sent_msg
    else:
        await client.send_message(chat_id, "No videos available right now.")
        return None



async def store_photos(app: Client):

    batch_size = 100
    all_photos = []
    full, part = divmod(len(VIDEOS_RANGE), batch_size)


    for i in range(full):
        try:
            batch_ids = VIDEOS_RANGE[i * batch_size: (i + 1) * batch_size]
            messages = await try_until_get(
                app.get_messages(CHANNEL_ID, batch_ids)
            )
            for msg in messages:
                if msg and msg.photo:
                    file_id = msg.photo.file_id
                    exists = await db.photo_exists(file_id)
                    if not exists:
                        all_photos.append({"file_id": file_id})


            if i < full - 1:
                await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Error fetching photos batch {i}: {e}")
            await asyncio.sleep(2)
            continue


    if part > 0:
        try:
            remaining_ids = VIDEOS_RANGE[full * batch_size:]
            messages = await try_until_get(
                app.get_messages(CHANNEL_ID, remaining_ids)
            )
            for msg in messages:
                if msg and msg.photo:
                    file_id = msg.photo.file_id
                    exists = await db.photo_exists(file_id)
                    if not exists:
                        all_photos.append({"file_id": file_id})
        except Exception as e:
            logging.error(f"Error fetching remaining photos: {e}")

    if all_photos:
        try:
            await db.insert_photos(all_photos)
            logging.info(f"Stored {len(all_photos)} new photos")
        except Exception as e:
            logging.error(f"Error inserting photos: {e}")



async def send_random_photo(client: Client, chat_id, protect=True, caption="", reply_markup=None, hide_caption=False):
    photos = await db.get_photos()

    if not photos:

        asyncio.create_task(store_photos(client))

        await asyncio.sleep(2)
        photos = await db.get_photos()

    valid_photos = [p for p in photos if p.get("file_id")]
    if valid_photos:

        final_caption = "" if hide_caption else (caption if caption else None)
        random_photo = random.choice(valid_photos)
        try:
            sent_msg = await client.send_photo(
                chat_id,
                random_photo["file_id"],
                caption=final_caption,
                parse_mode=ParseMode.HTML if final_caption else None,
                reply_markup=reply_markup,
                protect_content=protect
            )
            return sent_msg
        except FloodWait as e:
            await asyncio.sleep(e.x)
            sent_msg = await client.send_photo(
                chat_id,
                random_photo["file_id"],
                caption=final_caption,
                parse_mode=ParseMode.HTML if final_caption else None,
                reply_markup=reply_markup,
                protect_content=protect
            )
            return sent_msg
    else:
        await client.send_message(chat_id, "No photos available right now.")
        return None



async def get_photo(client: Client, message: Message):
    from pytz import timezone
    ist = timezone("Asia/Kolkata")

    user_id = message.from_user.id
    current_time = datetime.now(ist)


    is_allowed, remaining_time = await db.check_spam_limit(user_id, "get_photo", max_requests=5, time_window=60)
    if not is_allowed:

        try:
            asyncio.create_task(schedule_spam_notification(client, user_id, "get_photo", remaining_time))
        except Exception:
            pass
        return await message.reply_text(
            f"⏳ Pʟᴇᴀsᴇ ᴡᴀɪᴛ {remaining_time} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ʀᴇǫᴜᴇsᴛɪɴɢ ᴀɢᴀɪɴ.",
            protect_content=False,
            quote=True
        )


    is_premium = await is_premium_user(user_id)

    if is_premium:

        user_data = await collection.find_one({"user_id": user_id})
        expiration_timestamp = user_data.get("expiration_timestamp") if user_data else None


        if expiration_timestamp:
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
            if current_time > expiration_time:
                await collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"expiration_timestamp": None}}
                )

                is_premium = False

        if is_premium:


            try:
                AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
                    db.get_auto_delete(),
                    db.get_del_timer(),
                    db.get_hide_caption(),
                    db.get_channel_button(),
                    db.get_protect_content(),
                )
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
                AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = False, 0, False, None, False


            custom_caption = await db.get_custom_caption()
            if not custom_caption:
                from config import CUSTOM_CAPTION
                custom_caption = CUSTOM_CAPTION


            caption = custom_caption if custom_caption else ""


            reply_markup = None
            if CHNL_BTN:
                try:
                    button_name, button_link, button_name2, button_link2 = await db.get_channel_button_links()
                    buttons = []
                    if button_name and button_link:
                        buttons.append([InlineKeyboardButton(text=button_name, url=button_link)])
                    if button_name2 and button_link2:
                        if buttons:
                            buttons[0].append(InlineKeyboardButton(text=button_name2, url=button_link2))
                        else:
                            buttons.append([InlineKeyboardButton(text=button_name2, url=button_link2)])
                    if buttons:
                        reply_markup = InlineKeyboardMarkup(buttons)
                except Exception:
                    pass

            try:
                sent_msg = await send_random_photo(
                    client,
                    message.chat.id,
                    protect=PROTECT_MODE,
                    caption=caption,
                    reply_markup=reply_markup,
                    hide_caption=HIDE_CAPTION
                )
                if AUTO_DEL and sent_msg:

                    asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_photo_{user_id}"))
                return sent_msg
            except FloodWait as e:
                await asyncio.sleep(e.x)
                sent_msg = await send_random_photo(
                    client,
                    message.chat.id,
                    protect=PROTECT_MODE,
                    caption=caption,
                    reply_markup=reply_markup,
                    hide_caption=HIDE_CAPTION
                )
                if AUTO_DEL and sent_msg:
                    asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_photo_{user_id}"))
                return sent_msg



    free_limit = await db.get_free_limit(user_id)
    free_enabled = await db.get_free_state(user_id)
    free_count = await db.check_free_usage(user_id)

    if not free_enabled:

        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        return await message.reply_text(
            "Yᴏᴜʀ ғʀᴇᴇ ᴘʟᴀɴ ɪs ᴅɪsᴀʙʟᴇᴅ. 🚫\n\nUɴʟᴏᴄᴋ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ Pʀᴇᴍɪᴜᴍ!",
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    remaining_attempts = free_limit - free_count

    if remaining_attempts <= 0:

        try:
            VERIFY_EXPIRE = await db.get_verified_time()
        except Exception as e:
            logging.error(f"Error fetching verify expiry config: {e}")
            VERIFY_EXPIRE = None

        if VERIFY_EXPIRE is not None:

            try:
                verify_status = await db.get_verify_status(user_id) or {}
            except Exception as e:
                logging.error(f"Error fetching verify status for {user_id}: {e}")
                verify_status = {"is_verified": False, "verified_time": 0, "verify_token": "", "link": ""}


            try:
                if verify_status.get("is_verified") and VERIFY_EXPIRE:
                    verified_time = verify_status.get("verified_time", 0)
                    if (time.time() - verified_time) > VERIFY_EXPIRE:
                        await db.update_verify_status(user_id, is_verified=False)
                        verify_status["is_verified"] = False
            except Exception as e:
                logging.error(f"Error while checking/refreshing verify expiry for {user_id}: {e}")


            if not verify_status.get("is_verified", False):
                try:
                    shortener_url = await db.get_shortener_url()
                    shortener_api = await db.get_shortener_api()

                    if shortener_url and shortener_api:
                        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        await db.update_verify_status(user_id, verify_token=token, link="")

                        long_url = f"https://telegram.dog/{client.username}?start=verify_{token}"
                        short_link = await get_shortlink(long_url)

                        tut_vid_url = await db.get_tut_video() or TUT_VID

                        btn = [
                            [InlineKeyboardButton("Click here", url=short_link),
                             InlineKeyboardButton('How to use the bot', url=tut_vid_url)],
                            [InlineKeyboardButton('BUY PREMIUM', callback_data='buy_prem')]
                        ]

                        return await message.reply(
                            f"Your ads token is expired or invalid. Please verify to access the files.\n\n"
                            f"Token Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\n"
                            f"What is the token?\n\n"
                            f"This is an ads token. By passing 1 ad, you can use the bot for  {get_exp_time(VERIFY_EXPIRE)}.",
                            reply_markup=InlineKeyboardMarkup(btn),
                            protect_content=False
                        )
                except Exception as e:
                    logging.error(f"Error in verification process: {e}")
                    buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
                    return await message.reply_text(
                        "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ ʏᴏᴜʀ ᴛᴏᴋᴇɴ ғɪʀsᴛ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.",
                        reply_markup=InlineKeyboardMarkup(buttons),
                        protect_content=False,
                        quote=True
                    )


        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        return await message.reply_text(
            f"Yᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ {free_limit} ғʀᴇᴇ ᴘʜᴏᴛᴏs ғᴏʀ ᴛᴏᴅᴀʏ. 📸\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!",
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    if remaining_attempts == 1:

        await message.reply_text(
            "⚠️ Tʜɪs ɪs ʏᴏᴜʀ ʟᴀsᴛ ғʀᴇᴇ ᴘʜᴏᴛᴏ ғᴏʀ ᴛᴏᴅᴀʏ.\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴘʜᴏᴛᴏs!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            ),
            protect_content=False,
            quote=True
        )


    try:
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
            db.get_auto_delete(),
            db.get_del_timer(),
            db.get_hide_caption(),
            db.get_channel_button(),
            db.get_protect_content(),
        )
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = False, 0, False, None, True


    custom_caption = await db.get_custom_caption()
    if not custom_caption:
        from config import CUSTOM_CAPTION
        custom_caption = CUSTOM_CAPTION


    caption = custom_caption if custom_caption else ""


    reply_markup = None
    if CHNL_BTN:
        try:
            button_name, button_link = await db.get_channel_button_link()
            if button_name and button_link:
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text=button_name, url=button_link)]])
        except Exception:
            pass


    await db.update_free_usage(user_id)
    try:
        sent_msg = await send_random_photo(
            client,
            message.chat.id,
            protect=PROTECT_MODE,
            caption=caption,
            reply_markup=reply_markup,
            hide_caption=HIDE_CAPTION
        )
        if AUTO_DEL and sent_msg:
            asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_photo_{user_id}"))
    except FloodWait as e:
        await asyncio.sleep(e.x)
        sent_msg = await send_random_photo(
            client,
            message.chat.id,
            protect=PROTECT_MODE,
            caption=caption,
            reply_markup=reply_markup,
            hide_caption=HIDE_CAPTION
        )
        if AUTO_DEL and sent_msg:
            asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_photo_{user_id}"))



async def get_batch(client: Client, message: Message):
    from pytz import timezone
    ist = timezone("Asia/Kolkata")

    user_id = message.from_user.id
    current_time = datetime.now(ist)


    is_allowed, remaining_time = await db.check_spam_limit(user_id, "get_batch", max_requests=3, time_window=120)
    if not is_allowed:
        try:
            asyncio.create_task(schedule_spam_notification(client, user_id, "get_batch", remaining_time))
        except Exception:
            pass
        return await message.reply_text(
            f"⏳ Pʟᴇᴀsᴇ ᴡᴀɪᴛ {remaining_time} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ʀᴇǫᴜᴇsᴛɪɴɢ ᴀ ʙᴀᴛᴄʜ ᴀɢᴀɪɴ.",
            protect_content=False,
            quote=True
        )


    is_premium = await is_premium_user(user_id)

    if is_premium:

        user_data = await collection.find_one({"user_id": user_id})
        expiration_timestamp = user_data.get("expiration_timestamp") if user_data else None


        if expiration_timestamp:
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
            if current_time > expiration_time:
                await collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"expiration_timestamp": None}}
                )

                is_premium = False

        if is_premium:


            try:
                AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
                    db.get_auto_delete(),
                    db.get_del_timer(),
                    db.get_hide_caption(),
                    db.get_channel_button(),
                    db.get_protect_content(),
                )
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
                AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = False, 0, False, None, False


            custom_caption = await db.get_custom_caption()
            if not custom_caption:
                from config import CUSTOM_CAPTION
                custom_caption = CUSTOM_CAPTION

            try:
                sent_msgs = await send_batch_media(
                    client,
                    message.chat.id,
                    protect=PROTECT_MODE,
                    caption=custom_caption if custom_caption and not HIDE_CAPTION else None,
                    hide_caption=HIDE_CAPTION
                )
                if AUTO_DEL and sent_msgs:

                    if isinstance(sent_msgs, list) and len(sent_msgs) > 0:
                        last_msg = sent_msgs[-1]
                        asyncio.create_task(auto_del_notification(client.username, last_msg, DEL_TIMER, f"get_batch_{user_id}", is_batch=True, all_messages=sent_msgs))
                    elif sent_msgs:
                        asyncio.create_task(auto_del_notification(client.username, sent_msgs, DEL_TIMER, f"get_batch_{user_id}"))
                return sent_msgs
            except FloodWait as e:
                await asyncio.sleep(e.x)
                sent_msgs = await send_batch_media(
                    client,
                    message.chat.id,
                    protect=PROTECT_MODE,
                    caption=custom_caption if custom_caption and not HIDE_CAPTION else None,
                    hide_caption=HIDE_CAPTION
                )
                if AUTO_DEL and sent_msgs:

                    if isinstance(sent_msgs, list) and len(sent_msgs) > 0:
                        last_msg = sent_msgs[-1]
                        asyncio.create_task(auto_del_notification(client.username, last_msg, DEL_TIMER, f"get_batch_{user_id}", is_batch=True, all_messages=sent_msgs))
                    elif sent_msgs:
                        asyncio.create_task(auto_del_notification(client.username, sent_msgs, DEL_TIMER, f"get_batch_{user_id}"))
                return sent_msgs



    free_limit = await db.get_free_limit(user_id)
    free_enabled = await db.get_free_state(user_id)
    free_count = await db.check_free_usage(user_id)

    if not free_enabled:

        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        return await message.reply_text(
            "Yᴏᴜʀ ғʀᴇᴇ ᴘʟᴀɴ ɪs ᴅɪsᴀʙʟᴇᴅ. 🚫\n\nUɴʟᴏᴄᴋ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ Pʀᴇᴍɪᴜᴍ!",
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    remaining_attempts = free_limit - free_count

    if remaining_attempts <= 0:

        try:
            VERIFY_EXPIRE = await db.get_verified_time()
        except Exception as e:
            logging.error(f"Error fetching verify expiry config: {e}")
            VERIFY_EXPIRE = None

        if VERIFY_EXPIRE is not None:

            try:
                verify_status = await db.get_verify_status(user_id) or {}
            except Exception as e:
                logging.error(f"Error fetching verify status for {user_id}: {e}")
                verify_status = {"is_verified": False, "verified_time": 0, "verify_token": "", "link": ""}


            try:
                if verify_status.get("is_verified") and VERIFY_EXPIRE:
                    verified_time = verify_status.get("verified_time", 0)
                    if (time.time() - verified_time) > VERIFY_EXPIRE:
                        await db.update_verify_status(user_id, is_verified=False)
                        verify_status["is_verified"] = False
            except Exception as e:
                logging.error(f"Error while checking/refreshing verify expiry for {user_id}: {e}")


            if not verify_status.get("is_verified", False):
                try:
                    shortener_url = await db.get_shortener_url()
                    shortener_api = await db.get_shortener_api()

                    if shortener_url and shortener_api:
                        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        await db.update_verify_status(user_id, verify_token=token, link="")

                        long_url = f"https://telegram.dog/{client.username}?start=verify_{token}"
                        short_link = await get_shortlink(long_url)

                        tut_vid_url = await db.get_tut_video() or TUT_VID

                        btn = [
                            [InlineKeyboardButton("Click here", url=short_link),
                             InlineKeyboardButton('How to use the bot', url=tut_vid_url)],
                            [InlineKeyboardButton('BUY PREMIUM', callback_data='buy_prem')]
                        ]

                        return await message.reply(
                            f"Your ads token is expired or invalid. Please verify to access the files.\n\n"
                            f"Token Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\n"
                            f"What is the token?\n\n"
                            f"This is an ads token. By passing 1 ad, you can use the bot for  {get_exp_time(VERIFY_EXPIRE)}.",
                            reply_markup=InlineKeyboardMarkup(btn),
                            protect_content=False
                        )
                except Exception as e:
                    logging.error(f"Error in verification process: {e}")
                    buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
                    return await message.reply_text(
                        "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ ʏᴏᴜʀ ᴛᴏᴋᴇɴ ғɪʀsᴛ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.",
                        reply_markup=InlineKeyboardMarkup(buttons),
                        protect_content=False,
                        quote=True
                    )


        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        return await message.reply_text(
            f"Yᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ {free_limit} ғʀᴇᴇ ʙᴀᴛᴄʜᴇs ғᴏʀ ᴛᴏᴅᴀʏ. 📦\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!",
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    if remaining_attempts == 1:

        await message.reply_text(
            "⚠️ Tʜɪs ɪs ʏᴏᴜʀ ʟᴀsᴛ ғʀᴇᴇ ʙᴀᴛᴄʜ ғᴏʀ ᴛᴏᴅᴀʏ.\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ʙᴀᴛᴄʜᴇs!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            ),
            protect_content=False,
            quote=True
        )


    try:
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
            db.get_auto_delete(),
            db.get_del_timer(),
            db.get_hide_caption(),
            db.get_channel_button(),
            db.get_protect_content(),
        )
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = False, 0, False, None, True


    custom_caption = await db.get_custom_caption()
    if not custom_caption:
        from config import CUSTOM_CAPTION
        custom_caption = CUSTOM_CAPTION


    await db.update_free_usage(user_id)
    try:
        sent_msgs = await send_batch_media(
            client,
            message.chat.id,
            protect=PROTECT_MODE,
            caption=custom_caption if custom_caption and not HIDE_CAPTION else None,
            hide_caption=HIDE_CAPTION
        )
        if AUTO_DEL and sent_msgs:
            last_msg = sent_msgs[-1] if isinstance(sent_msgs, list) and len(sent_msgs) > 0 else sent_msgs
            if last_msg:
                asyncio.create_task(auto_del_notification(client.username, last_msg, DEL_TIMER, f"get_batch_{user_id}"))
    except FloodWait as e:
        await asyncio.sleep(e.x)
        sent_msgs = await send_batch_media(
            client,
            message.chat.id,
            protect=PROTECT_MODE,
            caption=custom_caption if custom_caption and not HIDE_CAPTION else None,
            hide_caption=HIDE_CAPTION
        )
        if AUTO_DEL and sent_msgs:
            last_msg = sent_msgs[-1] if isinstance(sent_msgs, list) and len(sent_msgs) > 0 else sent_msgs
            if last_msg:
                asyncio.create_task(auto_del_notification(client.username, last_msg, DEL_TIMER, f"get_batch_{user_id}"))



async def send_batch_media(client: Client, chat_id, protect=True, caption=None, hide_caption=False):

    photos = await db.get_photos()
    videos = await db.get_videos()


    if not photos:
        asyncio.create_task(store_photos(client))
        await asyncio.sleep(1)
        photos = await db.get_photos()

    if not videos:
        asyncio.create_task(store_videos(client))
        await asyncio.sleep(1)
        videos = await db.get_videos()

    if not photos and not videos:
        await client.send_message(chat_id, "No media available right now.")
        return None


    media_group = []
    total_needed = 10


    all_media = []
    if photos:
        for photo in photos:
            if photo.get("file_id"):
                all_media.append(("photo", photo["file_id"]))
    if videos:
        for video in videos:
            if video.get("file_id"):
                all_media.append(("video", video["file_id"]))

    if not all_media:
        await client.send_message(chat_id, "No media available right now.")
        return None


    random.shuffle(all_media)
    selected = all_media[:min(total_needed, len(all_media))]


    for idx, (media_type, file_id) in enumerate(selected):
        if media_type == "photo":
            if idx == 0 and caption and not hide_caption:
                media_group.append(InputMediaPhoto(file_id, caption=caption, parse_mode=ParseMode.HTML))
            else:
                media_group.append(InputMediaPhoto(file_id))
        else:
            if idx == 0 and caption and not hide_caption:
                media_group.append(InputMediaVideo(file_id, caption=caption, parse_mode=ParseMode.HTML))
            else:
                media_group.append(InputMediaVideo(file_id))

    if media_group:
        try:
            sent_msgs = await client.send_media_group(chat_id, media_group, protect_content=protect)
            return sent_msgs
        except FloodWait as e:
            await asyncio.sleep(e.x)
            sent_msgs = await client.send_media_group(chat_id, media_group, protect_content=protect)
            return sent_msgs
    return None



async def try_until_get(func):
    try:
        result = await func
        return result if result else []
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await try_until_get(func)
    except Exception as e:
        print(f'Cannot get videos: {e}')
        return []



async def get_video(client: Client, message: Message):
    from pytz import timezone
    ist = timezone("Asia/Kolkata")

    user_id = message.from_user.id
    current_time = datetime.now(ist)


    is_allowed, remaining_time = await db.check_spam_limit(user_id, "get_video", max_requests=5, time_window=60)
    if not is_allowed:
        try:
            asyncio.create_task(schedule_spam_notification(client, user_id, "get_video", remaining_time))
        except Exception:
            pass
        return await message.reply_text(
            f"⏳ Pʟᴇᴀsᴇ ᴡᴀɪᴛ {remaining_time} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ʀᴇǫᴜᴇsᴛɪɴɢ ᴀɢᴀɪɴ.",
            protect_content=False,
            quote=True
        )


    is_premium = await is_premium_user(user_id)

    if is_premium:

        user_data = await collection.find_one({"user_id": user_id})
        expiration_timestamp = user_data.get("expiration_timestamp") if user_data else None


        if expiration_timestamp:
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
            if current_time > expiration_time:
                await collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"expiration_timestamp": None}}
                )

                is_premium = False

        if is_premium:


            try:
                AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
                    db.get_auto_delete(),
                    db.get_del_timer(),
                    db.get_hide_caption(),
                    db.get_channel_button(),
                    db.get_protect_content(),
                )
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
                AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = False, 0, False, None, False


            custom_caption = await db.get_custom_caption()
            if not custom_caption:
                from config import CUSTOM_CAPTION
                custom_caption = CUSTOM_CAPTION


            caption = custom_caption if custom_caption else ""


            reply_markup = None
            if CHNL_BTN:
                try:
                    button_name, button_link, button_name2, button_link2 = await db.get_channel_button_links()
                    buttons = []
                    if button_name and button_link:
                        buttons.append([InlineKeyboardButton(text=button_name, url=button_link)])
                    if button_name2 and button_link2:
                        if buttons:
                            buttons[0].append(InlineKeyboardButton(text=button_name2, url=button_link2))
                        else:
                            buttons.append([InlineKeyboardButton(text=button_name2, url=button_link2)])
                    if buttons:
                        reply_markup = InlineKeyboardMarkup(buttons)
                except Exception:
                    pass

            try:
                sent_msg = await send_random_video(
                    client,
                    message.chat.id,
                    protect=PROTECT_MODE,
                    caption=caption,
                    reply_markup=reply_markup,
                    hide_caption=HIDE_CAPTION
                )
                if AUTO_DEL and sent_msg:
                    asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_video_{user_id}"))
                return sent_msg
            except FloodWait as e:
                await asyncio.sleep(e.x)
                sent_msg = await send_random_video(
                    client,
                    message.chat.id,
                    protect=PROTECT_MODE,
                    caption=caption,
                    reply_markup=reply_markup,
                    hide_caption=HIDE_CAPTION
                )
                if AUTO_DEL and sent_msg:
                    asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_video_{user_id}"))
                return sent_msg



    free_limit = await db.get_free_limit(user_id)
    free_enabled = await db.get_free_state(user_id)
    free_count = await db.check_free_usage(user_id)

    if not free_enabled:

        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        return await message.reply_text(
            "Yᴏᴜʀ ғʀᴇᴇ ᴘʟᴀɴ ɪs ᴅɪsᴀʙʟᴇᴅ. 🚫\n\nUɴʟᴏᴄᴋ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ Pʀᴇᴍɪᴜᴍ!",
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    remaining_attempts = free_limit - free_count

    if remaining_attempts <= 0:

        try:
            VERIFY_EXPIRE = await db.get_verified_time()
        except Exception as e:
            logging.error(f"Error fetching verify expiry config: {e}")
            VERIFY_EXPIRE = None

        if VERIFY_EXPIRE is not None:

            try:
                verify_status = await db.get_verify_status(user_id) or {}
            except Exception as e:
                logging.error(f"Error fetching verify status for {user_id}: {e}")
                verify_status = {"is_verified": False, "verified_time": 0, "verify_token": "", "link": ""}


            try:
                if verify_status.get("is_verified") and VERIFY_EXPIRE:
                    verified_time = verify_status.get("verified_time", 0)
                    if (time.time() - verified_time) > VERIFY_EXPIRE:
                        await db.update_verify_status(user_id, is_verified=False)
                        verify_status["is_verified"] = False
            except Exception as e:
                logging.error(f"Error while checking/refreshing verify expiry for {user_id}: {e}")


            if not verify_status.get("is_verified", False):
                try:
                    shortener_url = await db.get_shortener_url()
                    shortener_api = await db.get_shortener_api()

                    if shortener_url and shortener_api:
                        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        await db.update_verify_status(user_id, verify_token=token, link="")

                        long_url = f"https://telegram.dog/{client.username}?start=verify_{token}"
                        short_link = await get_shortlink(long_url)

                        tut_vid_url = await db.get_tut_video() or TUT_VID

                        btn = [
                            [InlineKeyboardButton("Click here", url=short_link),
                             InlineKeyboardButton('How to use the bot', url=tut_vid_url)],
                            [InlineKeyboardButton('BUY PREMIUM', callback_data='buy_prem')]
                        ]

                        return await message.reply(
                            f"Your ads token is expired or invalid. Please verify to access the files.\n\n"
                            f"Token Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\n"
                            f"What is the token?\n\n"
                            f"This is an ads token. By passing 1 ad, you can use the bot for  {get_exp_time(VERIFY_EXPIRE)}.",
                            reply_markup=InlineKeyboardMarkup(btn),
                            protect_content=False
                        )
                except Exception as e:
                    logging.error(f"Error in verification process: {e}")
                    buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
                    return await message.reply_text(
                        "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ ʏᴏᴜʀ ᴛᴏᴋᴇɴ ғɪʀsᴛ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.",
                        reply_markup=InlineKeyboardMarkup(buttons),
                        protect_content=False,
                        quote=True
                    )


        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        return await message.reply_text(
            f"Yᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ {free_limit} ғʀᴇᴇ ᴠɪᴅᴇᴏs ғᴏʀ ᴛᴏᴅᴀʏ. 🍒\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!",
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    if remaining_attempts == 1:

        await message.reply_text(
            "⚠️ Tʜɪs ɪs ʏᴏᴜʀ ʟᴀsᴛ ғʀᴇᴇ ᴠɪᴅᴇᴏ ғᴏʀ ᴛᴏᴅᴀʏ.\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴠɪᴅᴇᴏs!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            ),
            protect_content=False,
            quote=True
        )


    try:
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
            db.get_auto_delete(),
            db.get_del_timer(),
            db.get_hide_caption(),
            db.get_channel_button(),
            db.get_protect_content(),
        )
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = False, 0, False, None, True


    custom_caption = await db.get_custom_caption()
    if not custom_caption:
        from config import CUSTOM_CAPTION
        custom_caption = CUSTOM_CAPTION


    caption = custom_caption if custom_caption else ""


    reply_markup = None
    if CHNL_BTN:
        try:
            button_name, button_link = await db.get_channel_button_link()
            if button_name and button_link:
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text=button_name, url=button_link)]])
        except Exception:
            pass


    await db.update_free_usage(user_id)
    try:
        sent_msg = await send_random_video(
            client,
            message.chat.id,
            protect=PROTECT_MODE,
            caption=caption,
            reply_markup=reply_markup,
            hide_caption=HIDE_CAPTION
        )
        if AUTO_DEL and sent_msg:
            asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_video_{user_id}"))
    except FloodWait as e:
        await asyncio.sleep(e.x)
        sent_msg = await send_random_video(
            client,
            message.chat.id,
            protect=PROTECT_MODE,
            caption=caption,
            reply_markup=reply_markup,
            hide_caption=HIDE_CAPTION
        )
        if AUTO_DEL and sent_msg:
            asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_video_{user_id}"))



WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""





chat_data_cache = {}

async def schedule_spam_notification(client: Client, user_id: int, action_type: str, wait_time: int):
    """Schedule a single notification to be sent to the user when rate-limit expires."""
    try:

        if await db.get_spam_notify_flag(user_id, action_type):
            return
        await db.set_spam_notify_flag(user_id, action_type)

        async def _notify():
            try:
                await asyncio.sleep(wait_time)


                if await db.get_spam_notify_flag(user_id, action_type):

                    await db.reset_spam_protection(user_id, action_type)
                    try:
                        await client.send_message(user_id, f"✅ You can now request {action_type.replace('_',' ')} again.")
                    except Exception:
                        pass
                    await db.clear_spam_notify_flag(user_id, action_type)
            except Exception as e:
                logging.error(f"Error in spam-notify task: {e}")
                await db.clear_spam_notify_flag(user_id, action_type)

        asyncio.create_task(_notify())

    except Exception as e:
        logging.error(f"Failed to schedule spam notification: {e}")

async def not_joined(client: Client, message: Message):
    if not client.fsub_dict:
        return

    temp = await message.reply("<code><b>ᴡᴀɪᴛ ᴀ sᴇᴄᴏɴᴅ.....</b></code>")

    user_id = message.from_user.id
    statuses = await check_subscription(client, user_id)

    buttons = []

    for channel_id, (channel_name, channel_link, request, timer) in client.fsub_dict.items():
        status = statuses.get(channel_id, None)

        if timer > 0:
            expire_time = datetime.now() + timedelta(minutes=timer)
            try:
                invite = await client.create_chat_invite_link(
                    chat_id=channel_id,
                    expire_date=expire_time,
                    creates_join_request=request
                )
                channel_link = invite.invite_link
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Error creating invite link for {channel_name}: {e}")

        if status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
            button_text = channel_name
            if request:
                try:
                    if await client.mongodb.has_submitted_join_request(user_id, channel_id):
                        request_status = await client.mongodb.get_join_request_status(user_id, channel_id)
                        if request_status == "pending":
                            continue
                except Exception:
                    pass
            buttons.append([InlineKeyboardButton(text=button_text, url=channel_link)])

    try:
        from_link = message.text.split(" ")
        if len(from_link) > 1:
            try_again_link = f"https://t.me/{client.username}/?start={from_link[1]}"
            buttons.append([InlineKeyboardButton("🔄 Try Again", url=try_again_link)])
        else:
            buttons.append([
                InlineKeyboardButton(text="🔄 Try Again", callback_data=f"get_again_get_batch_{user_id}"),
                InlineKeyboardButton(text="Close ✖️", callback_data="close")
            ])
    except Exception:
        pass

    try:
        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        await temp.delete()

    except Exception as e:
        print(f"Error: {e}")
        await temp.edit(f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @rohit_1888</i></b>\n<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")


@Bot.on_message(filters.command('users') & filters.private & filters.user(OWNER_ID))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await db.full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")


@Bot.on_message(filters.command('status') & filters.private & is_admin)
async def info(client: Bot, message: Message):
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("• Close •", callback_data="close")]]
    )


    start_time = time.time()
    temp_msg = await message.reply(
        "<b><i>Processing...</i></b>",
        quote=True,
        parse_mode=ParseMode.HTML
    )
    end_time = time.time()
    ping_time = (end_time - start_time) * 1000


    users = await db.full_userbase()


    try:
        ist = timezone("Asia/Kolkata")
        now = datetime.now(ist)

        if hasattr(client, 'uptime') and client.uptime:
            uptime = client.uptime
            if uptime.tzinfo is None:
                uptime = ist.localize(uptime)
            delta = now - uptime
            bottime = get_readable_time(int(delta.total_seconds()))
        else:
            bottime = "N/A"
    except Exception as e:
        logging.error(f"Error calculating uptime: {e}")
        bottime = "N/A"


    await temp_msg.edit(
        f"<b>Users: {len(users)}\n\n"
        f"Uptime: {bottime}\n\n"
        f"Ping: {ping_time:.2f} ms</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )



cancel_lock = asyncio.Lock()
is_canceled = False


@Bot.on_message(filters.command('cancel') & filters.private & is_admin)
async def cancel_broadcast(client: Bot, message: Message):
    global is_canceled
    async with cancel_lock:
        is_canceled = True

@Bot.on_message(filters.private & filters.command('broadcast') & is_admin)
async def broadcast(client: Bot, message: Message):
    global is_canceled
    args = message.text.split()[1:]

    if not message.reply_to_message:
        msg = await message.reply(
            "Reply to a message to broadcast.\n\nUsage examples:\n"
            "`/broadcast normal`\n"
            "`/broadcast pin`\n"
            "`/broadcast delete 30`\n"
            "`/broadcast pin delete 30`\n"
            "`/broadcast silent`\n"
        )
        await asyncio.sleep(8)
        return await msg.delete()


    do_pin = False
    do_delete = False
    duration = 0
    silent = False
    mode_text = []

    i = 0
    while i < len(args):
        arg = args[i].lower()
        if arg == "pin":
            do_pin = True
            mode_text.append("PIN")
        elif arg == "delete":
            do_delete = True
            try:
                duration = int(args[i + 1])
                i += 1
            except (IndexError, ValueError):
                return await message.reply("<b>Provide valid duration for delete mode.</b>\nUsage: `/broadcast delete 30`")
            mode_text.append(f"DELETE({duration}s)")
        elif arg == "silent":
            silent = True
            mode_text.append("SILENT")
        else:
            mode_text.append(arg.upper())
        i += 1

    if not mode_text:
        mode_text.append("NORMAL")


    async with cancel_lock:
        is_canceled = False

    query = await db.full_userbase()
    broadcast_msg = message.reply_to_message
    total = len(query)
    successful = blocked = deleted = unsuccessful = 0

    pls_wait = await message.reply(f"<i>Broadcasting in <b>{' + '.join(mode_text)}</b> mode...</i>")

    bar_length = 20
    progress_bar = ''
    last_update_percentage = 0
    update_interval = 0.05

    for i, chat_id in enumerate(query, start=1):
        async with cancel_lock:
            if is_canceled:
                await pls_wait.edit(f"›› BROADCAST ({' + '.join(mode_text)}) CANCELED ❌")
                return

        try:
            sent_msg = await broadcast_msg.copy(chat_id, disable_notification=silent)

            if do_pin:
                await client.pin_chat_message(chat_id, sent_msg.id, both_sides=True)
            if do_delete:
                asyncio.create_task(auto_delete(sent_msg, duration))

            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                sent_msg = await broadcast_msg.copy(chat_id, disable_notification=silent)
                if do_pin:
                    await client.pin_chat_message(chat_id, sent_msg.id, both_sides=True)
                if do_delete:
                    asyncio.create_task(auto_delete(sent_msg, duration))
                successful += 1
            except:
                unsuccessful += 1
        except UserIsBlocked:
            await db.del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await db.del_user(chat_id)
            deleted += 1
        except:
            unsuccessful += 1
            await db.del_user(chat_id)


        percent_complete = i / total
        if percent_complete - last_update_percentage >= update_interval or last_update_percentage == 0:
            num_blocks = int(percent_complete * bar_length)
            progress_bar = "●" * num_blocks + "○" * (bar_length - num_blocks)
            status_update = f"""<b>›› BROADCAST ({' + '.join(mode_text)}) IN PROGRESS...

<blockquote>⏳:</b> [{progress_bar}] <code>{percent_complete:.0%}</code></blockquote>

<b>›› Total Users: <code>{total}</code>
›› Successful: <code>{successful}</code>
›› Blocked: <code>{blocked}</code>
›› Deleted: <code>{deleted}</code>
›› Unsuccessful: <code>{unsuccessful}</code></b>

<i>➪ To stop broadcasting click: <b>/cancel</b></i>"""
            await pls_wait.edit(status_update)
            last_update_percentage = percent_complete


    final_status = f"""<b>›› BROADCAST ({' + '.join(mode_text)}) COMPLETED ✅

<blockquote>Dᴏɴᴇ:</b> [{progress_bar}] {percent_complete:.0%}</blockquote>

<b>›› Total Users: <code>{total}</code>
›› Successful: <code>{successful}</code>
›› Blocked: <code>{blocked}</code>
›› Deleted: <code>{deleted}</code>
›› Unsuccessful: <code>{unsuccessful}</code></b>"""
    return await pls_wait.edit(final_status)



async def auto_delete(sent_msg, duration):
    await asyncio.sleep(duration)
    try:
        await sent_msg.delete()
    except:
        pass




@Bot.on_message(filters.command('addpaid') & filters.private & is_admin)
async def add_premium_user_command(client, msg):
    if len(msg.command) != 4:
        await msg.reply_text("Usage: /addpaid (user_id) time_value time_unit (m/d)")
        return

    try:
        user_id = int(msg.command[1])
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()


        expiration_time = await add_premium(user_id, time_value, time_unit)


        await msg.reply_text(
            f"User {user_id} added as a premium user for {time_value} {time_unit}.\n"
            f"Expiration Time: {expiration_time}"
        )


        await client.send_message(
            chat_id=user_id,
            text=(
                f"🎉 Congratulations! You have been upgraded to premium for {time_value} {time_unit}.\n\n"
                f"Expiration Time: {expiration_time}.\n\n"
                f"Happy Downloading 💦"
            ),
        )

    except ValueError:
        await msg.reply_text("Invalid input. Please check the user_id, time_value, and time_unit.")
    except Exception as e:
        await msg.reply_text(f"An error occurred: {str(e)}")



@Bot.on_message(filters.command('removepaid') & filters.private & is_admin)
async def pre_remove_user(client: Client, msg: Message):
    if len(msg.command) != 2:
        await msg.reply_text("useage: /removeuser user_id ")
        return
    try:
        user_id = int(msg.command[1])
        await remove_premium(user_id)
        await msg.reply_text(f"User {user_id} has been removed.")
    except ValueError:
        await msg.reply_text("user_id must be an integer or not available in database.")



@Bot.on_message(filters.command('listpaid') & filters.private & is_admin)
async def list_premium_users_command(client, message):

    ist = timezone("Asia/Kolkata")


    premium_users_cursor = collection.find({})
    premium_user_list = ['<b>Active Premium Users in database:</b>']
    current_time = datetime.now(ist)


    async for user in premium_users_cursor:
        user_id = user.get("user_id")
        expiration_timestamp = user.get("expiration_timestamp")

        if not expiration_timestamp:

            await collection.delete_one({"user_id": user_id})
            continue

        try:

            expiration_time = datetime.fromisoformat(str(expiration_timestamp)).astimezone(ist)
            remaining_time = expiration_time - current_time

            if remaining_time.total_seconds() <= 0:

                await collection.delete_one({"user_id": user_id})
                continue


            try:
                user_info = await client.get_users(user_id)
                username = f"@{user_info.username}" if user_info.username else "No Username"
                first_name = user_info.first_name or "N/A"
            except Exception:
                username = "Unknown"
                first_name = "Unknown"


            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"


            premium_user_list.append(
                f"👤 <b>UserID:</b> <code>{user_id}</code>\n"
                f"🔗 <b>User:</b> {username}\n"
                f"📛 <b>Name:</b> <code>{first_name}</code>\n"
                f"⏳ <b>Expiry:</b> {expiry_info}"
            )

        except Exception as e:

            premium_user_list.append(
                f"⚠️ <b>UserID:</b> <code>{user_id}</code>\n"
                f"Error: Unable to fetch details ({str(e)})"
            )

    if len(premium_user_list) == 1:
        await message.reply_text("I found 0 active premium users in my DB")
    else:
        await message.reply_text("\n\n".join(premium_user_list), parse_mode=ParseMode.HTML)

@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id


    status_message = await check_user_plan(user_id)


    await message.reply(status_message)

@Bot.on_message(filters.command('forcesub') & filters.private & ~banUser)
async def fsub_commands(client: Client, message: Message):
    button = [[InlineKeyboardButton("Cʟᴏsᴇ ✖️", callback_data="close")]]
    await message.reply(text=FSUB_CMD_TXT, reply_markup=InlineKeyboardMarkup(button), quote=True)


@Bot.on_message(filters.command('help') & filters.private & ~banUser)
async def help(client: Client, message: Message):
    buttons = [
        [
            InlineKeyboardButton("🤖 Oᴡɴᴇʀ", url=f"tg://openmessage?user_id={OWNER_ID}"),
            InlineKeyboardButton("🥰 Dᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/rohit1888")
        ]
    ]

    try:
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo = FORCE_PIC,
            caption = HELP_TEXT.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
            reply_markup = reply_markup

        )
    except Exception as e:
        return await message.reply(f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @rohit_1888</i></b>\n<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")

@Bot.on_message(filters.command('short') & filters.private & is_admin)
async def shorten_link_command(client, message):
    id = message.from_user.id

    try:

        set_msg = await client.ask(
            chat_id=id,
            text="<b><blockquote>⏳ Sᴇɴᴅ ᴀ ʟɪɴᴋ ᴛᴏ ʙᴇ sʜᴏʀᴛᴇɴᴇᴅ</blockquote>\n\nFᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>https://example.com/long_url</code></b>",
            timeout=60
        )


        original_url = set_msg.text.strip()

        if original_url.startswith("http") and "://" in original_url:
            try:

                short_link = await get_shortlink(original_url)


                await set_msg.reply(f"<b>🔗 Lɪɴᴋ Cᴏɴᴠᴇʀᴛᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ ✅</b>\n\n<blockquote>🔗 Sʜᴏʀᴛᴇɴᴇᴅ Lɪɴᴋ: <code>{short_link}</code></blockquote>")
            except ValueError as ve:

                await set_msg.reply(f"<b>❌ Error: {ve}</b>")
            except Exception as e:

                await set_msg.reply(f"<b>❌ Error while shortening the link:\n<code>{e}</code></b>")
        else:

            await set_msg.reply("<b>❌ Invalid URL. Please send a valid link that starts with 'http'.</b>")

    except asyncio.TimeoutError:

        await client.send_message(
            id,
            text="<b>⏳ Tɪᴍᴇᴏᴜᴛ. Yᴏᴜ ᴛᴏᴏᴋ ᴛᴏᴏ ʟᴏɴɢ ᴛᴏ ʀᴇsᴘᴏɴᴅ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.</b>",
            disable_notification=True
        )
        print(f"! Timeout occurred for user ID {id} while processing '/shorten' command.")

    except Exception as e:

        await client.send_message(
            id,
            text=f"<b>❌ Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:\n<code>{e}</code></b>",
            disable_notification=True
        )
        print(f"! Error occurred on '/short' command: {e}")


@Bot.on_message(filters.command("set_free_limit") & is_admin)
async def set_free_limit(client: Client, message: Message):
    try:
        limit = int(message.text.split()[1])
        await db.set_free_limit(limit=limit)
        await message.reply(f"✅ Free usage limit has been set to {limit}.")
    except (IndexError, ValueError):
        await message.reply("❌ Invalid usage. Use the command like this:\n`/set_free_limit 10`")


@Bot.on_message(filters.command('free') & filters.private & is_admin)
async def toggle_freemode(client: Client, message: Message):
    await message.reply_chat_action(ChatAction.TYPING)


    current_state = await db.get_free_state(message.from_user.id)


    new_state = not current_state
    await db.set_free_state(message.from_user.id, new_state)


    caption_button = InlineKeyboardButton(
        text="✅ Free Enabled" if new_state else "❌ Free  Disabled",
        callback_data="toggle_caption"
    )


    await message.reply_text(
        f"Free Mode is now {'enabled' if new_state else 'disabled'}.",
        reply_markup=InlineKeyboardMarkup([
            [caption_button]
        ])
    )


@Bot.on_message(filters.command("stats") & is_admin)
async def stats_command(client, message):
    total_users = await db.full_userbase()
    verified_users = await db.full_userbase({"verify_status.is_verified": True})
    unverified_users = total_users - verified_users

    free_settings = await db.get_free_settings()
    free_limit = free_settings["limit"]
    free_enabled = free_settings["enabled"]

    status = f"""<b><u>Verification Stats</u></b>

Total Users: <code>{total_users}</code>
Verified Users: <code>{verified_users}</code>
Unverified Users: <code>{unverified_users}</code>

<b><u>Free Usage Settings</u></b>
Free Usage Limit: <code>{free_limit}</code>
Free Usage Enabled: <code>{free_enabled}</code>"""

    await message.reply(status)


@Bot.on_message(filters.command("referral") & filters.private)
async def referral_command(client: Client, message: Message):
    user_id = message.from_user.id


    stats = await db.get_referral_stats(user_id)
    total_referrals = stats["total_referrals"]


    referral_link = f"https://telegram.dog/{client.username}?start=ref_{user_id}"


    remaining = max(0, REFERRAL_COUNT - total_referrals)
    progress_percent = min(100, (total_referrals / REFERRAL_COUNT) * 100) if REFERRAL_COUNT > 0 else 0


    is_premium = await is_premium_user(user_id)

    status_message = f"""🎁 <b>Rᴇғᴇʀʀᴀʟ Sᴛᴀᴛs</b>

📊 <b>Tᴏᴛᴀʟ Rᴇғᴇʀʀᴀʟs:</b> <code>{total_referrals}</code>
🎯 <b>Rᴇǫᴜɪʀᴇᴅ:</b> <code>{REFERRAL_COUNT}</code>
📈 <b>Pʀᴏɢʀᴇss:</b> <code>{progress_percent:.1f}%</code>

"""

    if total_referrals >= REFERRAL_COUNT:
        if is_premium:
            status_message += f"✅ <b>Yᴏᴜ'ᴠᴇ ᴇᴀʀɴᴇᴅ {REFERRAL_PREMIUM_DAYS} ᴅᴀʏs ᴏғ Pʀᴇᴍɪᴜᴍ!</b>\n\n"
        else:
            status_message += f"🎉 <b>Cᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! Yᴏᴜ'ᴠᴇ ᴇᴀʀɴᴇᴅ {REFERRAL_PREMIUM_DAYS} ᴅᴀʏs ᴏғ Pʀᴇᴍɪᴜᴍ!</b>\n\n"
    else:
        status_message += f"⏳ <b>Rᴇᴍᴀɪɴɪɴɢ:</b> <code>{remaining}</code> ᴍᴏʀᴇ ʀᴇғᴇʀʀᴀʟs ᴛᴏ ɢᴇᴛ {REFERRAL_PREMIUM_DAYS} ᴅᴀʏs ᴏғ Pʀᴇᴍɪᴜᴍ!\n\n"

    status_message += f"🔗 <b>Yᴏᴜʀ Rᴇғᴇʀʀᴀʟ Lɪɴᴋ:</b>\n<code>{referral_link}</code>\n\n"
    status_message += f"💡 <b>Hᴏᴡ ɪᴛ ᴡᴏʀᴋs:</b>\n"
    status_message += f"1. Sʜᴀʀᴇ ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟ ʟɪɴᴋ\n"
    status_message += f"2. Wʜᴇɴ {REFERRAL_COUNT} ᴜsᴇʀs ᴊᴏɪɴ ᴜsɪɴɢ ʏᴏᴜʀ ʟɪɴᴋ\n"
    status_message += f"3. Yᴏᴜ ɢᴇᴛ {REFERRAL_PREMIUM_DAYS} ᴅᴀʏs ᴏғ Pʀᴇᴍɪᴜᴍ! 🎁"

    buttons = [
        [InlineKeyboardButton("📤 Sʜᴀʀᴇ Lɪɴᴋ", url=f"https://t.me/share/url?url={referral_link}&text=Join%20this%20amazing%20bot!")],
        [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]
    ]

    await message.reply_text(
        status_message,
        reply_markup=InlineKeyboardMarkup(buttons),
        protect_content=False,
        quote=True
    )


@Bot.on_message(filters.command("set_caption") & filters.private & is_admin)
async def set_caption_command(client: Client, message: Message):
    try:
        if len(message.command) < 2:
            await message.reply_text(
                "❌ Invalid usage. Use the command like this:\n`/set_caption Your custom caption text here`\n\n"
                "To remove caption, use: `/set_caption None`"
            )
            return

        caption_text = message.text.split("/set_caption", 1)[1].strip()

        if caption_text.lower() == "none":
            caption_text = None

        success = await db.set_custom_caption(caption_text)

        if success:
            if caption_text:
                await message.reply_text(
                    f"✅ Custom caption has been set successfully!\n\n"
                    f"<b>Caption:</b> {caption_text}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.reply_text("✅ Custom caption has been removed.")
        else:
            await message.reply_text("❌ Failed to set custom caption. Please try again.")
    except Exception as e:
        logging.error(f"Error setting caption: {e}")
        await message.reply_text(f"❌ An error occurred: {e}")


@Bot.on_message(filters.command("get_caption") & filters.private & is_admin)
async def get_caption_command(client: Client, message: Message):
    try:
        caption = await db.get_custom_caption()

        if caption:
            await message.reply_text(
                f"📝 <b>Current Custom Caption:</b>\n\n{caption}",
                parse_mode=ParseMode.HTML
            )
        else:

            from config import CUSTOM_CAPTION
            if CUSTOM_CAPTION:
                await message.reply_text(
                    f"📝 <b>No custom caption set in database.</b>\n\n"
                    f"<b>Using config caption:</b> {CUSTOM_CAPTION}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.reply_text("📝 No custom caption is currently set.")
    except Exception as e:
        logging.error(f"Error getting caption: {e}")
        await message.reply_text(f"❌ An error occurred: {e}")

async def store_videos_dynamic(app: Client):
    all_videos = []
    try:
        last_msgs = await try_until_get(app.get_history(CHANNEL_ID, limit=1))
        if not last_msgs:
            logging.info("No messages found in channel when storing videos (dynamic).")
            return
        last_id = last_msgs[0].message_id
    except Exception as e:
        logging.error(f"Error fetching channel last message id: {e}")
        return

    batch_size = 200
    for start in range(1, last_id + 1, batch_size):
        batch_ids = list(range(start, min(start + batch_size, last_id + 1)))
        try:
            messages = await try_until_get(app.get_messages(CHANNEL_ID, batch_ids))
        except Exception as e:
            logging.error(f"Error fetching video messages {start}-{start + batch_size - 1}: {e}")
            await asyncio.sleep(1)
            continue
        for msg in messages:
            if msg and msg.video:
                file_id = msg.video.file_id
                exists = await db.video_exists(file_id)
                if not exists:
                    all_videos.append({"file_id": file_id})
        await asyncio.sleep(0.2)

    if all_videos:
        try:
            await db.insert_videos(all_videos)
        except Exception as e:
            logging.error(f"Error inserting videos: {e}")



async def store_photos_dynamic(app: Client):
    batch_size = 100
    all_photos = []
    try:
        last_msgs = await try_until_get(app.get_history(CHANNEL_ID, limit=1))
        if not last_msgs:
            logging.info("No messages found in channel when storing photos (dynamic).")
            return
        last_id = last_msgs[0].message_id
    except Exception as e:
        logging.error(f"Error fetching channel last message id: {e}")
        return

    for start in range(1, last_id + 1, batch_size):
        batch_ids = list(range(start, min(start + batch_size, last_id + 1)))
        try:
            messages = await try_until_get(app.get_messages(CHANNEL_ID, batch_ids))
        except Exception as e:
            logging.error(f"Error fetching photos messages {start}-{start + batch_size - 1}: {e}")
            await asyncio.sleep(1)
            continue
        for msg in messages:
            if msg and msg.photo:
                file_id = msg.photo.file_id
                exists = await db.photo_exists(file_id)
                if not exists:
                    all_photos.append({"file_id": file_id})
        await asyncio.sleep(0.2)

    if all_photos:
        try:
            await db.insert_photos(all_photos)
            logging.info(f"Stored {len(all_photos)} new photos")
        except Exception as e:
            logging.error(f"Error inserting photos: {e}")
