import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8387996820:AAHZ6YN_HIYdHG6nJ4QXR7bZmFXL9fBiAg4")


APP_ID = int(os.environ.get("APP_ID", "9698652"))


API_HASH = os.environ.get("API_HASH", "b354710ab18b84e00b65c62ba7a9c043")


CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1002568581749"))

MIN_ID = int(os.getenv("MIN_ID", 1))
MAX_ID = int(os.getenv("MAX_ID", 150))

VIDEOS_RANGE = list(range(MIN_ID, MAX_ID + 1))


OWNER_ID = int(os.environ.get("OWNER_ID", "7678562257"))


PORT = os.environ.get("PORT", "3435")
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://obito:umaid2008@cluster0.engyc.mongodb.net/?retryWrites=true&w=majority")

DB_NAME = os.environ.get("DATABASE_NAME", "orion")

IS_VERIFY = os.environ.get("IS_VERIFY", "false")

TUT_VID = os.environ.get("TUT_VID", "https://t.me/delight_link/2")

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "200"))

START_PIC = os.environ.get("START_PIC", "https://telegra.ph/file/ec17880d61180d3312d6a.jpg")

FORCE_PIC = os.environ.get("FORCE_PIC", "https://telegra.ph/file/e292b12890b8b4b9dcbd1.jpg")

QR_PIC = os.environ.get("QR_PIC", "https://envs.sh/B7w.png")



PICS = (os.environ.get("PICS", "https://envs.sh/4Iq.jpg https://envs.sh/4IW.jpg https://envs.sh/4IB.jpg https://envs.sh/4In.jpg")).split() 


CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "<b>ʙʏ @Javpostr</b>")



DISABLE_CHANNEL_BUTTON = os.environ.get("True", True) == 'True'




PREMIUM_BUTTON = reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("Remove Ads In One Click", callback_data="buy_prem")]]
)
PREMIUM_BUTTON2 = reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("Remove Ads In One Click", callback_data="buy_prem")]]
) 

OWNER_TAG = os.environ.get("OWNER_TAG", "rohit_1888")


UPI_ID = os.environ.get("UPI_ID", "rohit23pnb@axl")


UPI_IMAGE_URL = os.environ.get("UPI_IMAGE_URL", "https://t.me/paymentbot6/2")


SCREENSHOT_URL = os.environ.get("SCREENSHOT_URL", f"t.me/rohit_1888")



PRICE1 = os.environ.get("PRICE1", "0 rs")

PRICE2 = os.environ.get("PRICE2", "60 rs")

PRICE3 = os.environ.get("PRICE3", "150 rs")

PRICE4 = os.environ.get("PRICE4", "280 rs")

PRICE5 = os.environ.get("PRICE5", "550 rs")





REFERRAL_COUNT = int(os.environ.get("REFERRAL_COUNT", "5"))  

REFERRAL_PREMIUM_DAYS = int(os.environ.get("REFERRAL_PREMIUM_DAYS", "7"))  




USER_REPLY_TEXT = os.environ.get("USER_REPLY_TEXT", "⚠️ Pʟᴇᴀsᴇ ᴜsᴇ ᴛʜᴇ ᴘʀᴏᴘᴇʀ ᴄᴏᴍᴍᴀɴᴅs ᴏʀ ʙᴜᴛᴛᴏɴs ᴛᴏ ɪɴᴛᴇʀᴀᴄᴛ ᴡɪᴛʜ ᴛʜᴇ ʙᴏᴛ.\n\nUse /help to see available commands.")

LOG_FILE_NAME = "testingbot.txt"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)




FSUBS = []


SHORT_URL = os.environ.get("SHORT_URL", "linkshortify.com")
SHORT_API = os.environ.get("SHORT_API", "")
SHORT_TUT = os.environ.get("SHORT_TUT", "https://t.me/How_to_Download_7x/26")


AUTO_DEL = int(os.environ.get("AUTO_DEL", 300))


DISABLE_BTN = os.environ.get("DISABLE_BTN", "False") == "True"
PROTECT = os.environ.get("PROTECT", "True") == "True"


MESSAGES = {
    "START": os.environ.get("START_MSG", "<b>›› ʜᴇʏ!!, {first} ~ <blockquote>ʟᴏᴠᴇ ᴘᴏʀɴʜᴡᴀ? ɪ ᴀᴍ ᴍᴀᴅᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴛᴏ ғɪɴᴅ ᴡʜᴀᴛ ʏᴏᴜ ᴀʀᴇ ʟᴏᴏᴋɪɴɢ ꜰᴏʀ.</blockquote></b>"),
    "FSUB": os.environ.get("FSUB_MSG", "<b><blockquote>›› ʜᴇʏ ×</blockquote>\n  ʏᴏᴜʀ ғɪʟᴇ ɪs ʀᴇᴀᴅʏ ‼️ ʟᴏᴏᴋs ʟɪᴋᴇ ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ sᴜʙsᴄʀɪʙᴇᴅ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ʏᴇᴛ</b>"),
    "ABOUT": os.environ.get("ABOUT_MSG", "<b>›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @cosmic_freak</b>"),
    "REPLY": os.environ.get("REPLY_MSG", "<b>For More Join - @Hanime_Arena</b>"),
    "SHORT_MSG": os.environ.get("SHORT_MSG", "<b>📊 ʜᴇʏ {first}, ʏᴏᴜʀ ʟɪɴᴋ ɪꜱ ʀᴇᴀᴅʏ</b>"),
    "START_PHOTO": os.environ.get("START_PHOTO", "https://graph.org/file/510affa3d4b6c911c12e3.jpg"),
    "FSUB_PHOTO": os.environ.get("FSUB_PHOTO", "https://telegra.ph/file/7a16ef7abae23bd238c82-b8fbdcb05422d71974.jpg"),
    "SHORT_PIC": os.environ.get("SHORT_PIC", "https://telegra.ph/file/7a16ef7abae23bd238c82-b8fbdcb05422d71974.jpg"),
    "SHORT": os.environ.get("SHORT", "https://telegra.ph/file/8aaf4df8c138c6685dcee-05d3b183d4978ec347.jpg"),
    "CAPTION": os.environ.get("CAPTION", "{previouscaption}")
}
ADMINS = []
MSG_EFFECT = 0
