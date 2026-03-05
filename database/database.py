


import time
import pymongo, os
import motor
from config import DB_URI, DB_NAME

import logging
from datetime import datetime, timedelta

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]

logging.basicConfig(level=logging.INFO)

collection = database['premium-users']

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }



class Rohit:

    def __init__(self, DB_URI, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
        self.database = self.dbclient[DB_NAME]

        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.user_data = self.database['users']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        self.shortener_data = self.database['shortener']
        self.settings_data = self.database['settings']
        self.free_data = self.database['free']
        self.for_data = self.database['for']
        self.login_data = self.database['login']
        
        self.auto_delete_data = self.database['auto_delete']
        self.hide_caption_data = self.database['hide_caption']
        self.protect_content_data = self.database['protect_content']
        self.channel_button_data = self.database['channel_button']

        self.settings_data = self.database['settings']
        self.del_timer_data = self.database['del_timer']
        self.channel_button_link_data = self.database['channelButton_link']
        self.custom_caption_data = self.database['custom_caption']

        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.store_reqLink_data = self.database['store_reqLink']

      
        self.videos_collection = self.database["vids"]
        self.photos_collection = self.database["pics"]  
        self.users_collection = self.database["user_subs"]  
        self.spam_protection_data = self.database["spam_protection"]  
        self.referrals_collection = self.database["referrals"]  


    
    async def set_shortener_url(self, url):
        try:
        
            existing = await self.shortener_data.find_one({"active": True})
            if existing:
            
                await self.shortener_data.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"shortener_url": url, "updated_at": datetime.utcnow()}}
                )
            else:
            
                await self.shortener_data.insert_one({
                    "shortener_url": url,
                    "api_key": None,
                    "active": True,
                    "created_at": datetime.utcnow()
                })
            return True
        except Exception as e:
            logging.error(f"Error setting shortener URL: {e}")
            return False

    async def set_shortener_api(self, api):
        try:
        
            existing = await self.shortener_data.find_one({"active": True})
            if existing:
            
                await self.shortener_data.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"api_key": api, "updated_at": datetime.utcnow()}}
                )
            else:
            
                await self.shortener_data.insert_one({
                    "shortener_url": None,
                    "api_key": api,
                    "active": True,
                    "created_at": datetime.utcnow()
                })
            return True
        except Exception as e:
            logging.error(f"Error setting shortener API key: {e}")
            return False

    async def get_shortener_url(self):
        try:
        
            shortener = await self.shortener_data.find_one({"active": True}, {"_id": 0, "shortener_url": 1})
            return shortener.get("shortener_url") if shortener else None
        except Exception as e:
            logging.error(f"Error fetching shortener URL: {e}")
            return None

    async def get_shortener_api(self):
        try:
        
            shortener = await self.shortener_data.find_one({"active": True}, {"_id": 0, "api_key": 1})
            return shortener.get("api_key") if shortener else None
        except Exception as e:
            logging.error(f"Error fetching shortener API key: {e}")
            return None


    async def deactivate_shortener(self):
        try:
            
            await self.shortener_data.update_many({"active": True}, {"$set": {"active": False}})
            return True
        except Exception as e:
            logging.error(f"Error deactivating shorteners: {e}")
            return False

    async def set_verified_time(self, verified_time: int):
        try:
            
            result = await self.settings_data.update_one(
                {"_id": "verified_time"},  
                {"$set": {"verified_time": verified_time}},
                upsert=True  
            )
            return result.modified_count > 0  
        except Exception as e:
            logging.error(f"Error updating verified time: {e}")
            return False

    async def get_verified_time(self):
        try:
            
            settings = await self.settings_data.find_one({"_id": "verified_time"})
            return settings.get("verified_time", None) if settings else None
        except Exception as e:
            logging.error(f"Error fetching verified time: {e}")
            return None

    async def set_tut_video(self, video_url: str):
        try:
            
            result = await self.settings_data.update_one(
                {"_id": "tutorial_video"},  
                {"$set": {"tutorial_video_url": video_url}},
                upsert=True  
            )
            return result.modified_count > 0  
        except Exception as e:
            logging.error(f"Error updating tutorial video URL: {e}")
            return False

    async def get_tut_video(self):
        try:
            
            settings = await self.settings_data.find_one({"_id": "tutorial_video"})
            return settings.get("tutorial_video_url", None) if settings else None
        except Exception as e:
            logging.error(f"Error fetching tutorial video URL: {e}")
            return None

    
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})
        return

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in user_docs]
        return user_ids

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        return

    
    async def update_shortener(self, user_id: int, site: str, api_key: str):
        """
        Update the shortener site and API key for a user.
        """
        await self.shortener_data.update_one(
            {'_id': user_id},
            {'$set': {'site': site, 'api': api_key}},
            upsert=True  
        )

    
    async def toggle_shortener(self, user_id: int, enable: bool):
        """
        Enable or disable the shortener functionality for a user.
        """
        await self.shortener_data.update_one(
            {'_id': user_id},
            {'$set': {'enabled': enable}},
            upsert=True  
        )

    
    async def fetch_shortener(self, user_id: int):
        """
        Fetch the shortener settings for a user.
        Returns a dictionary or None if no settings are found.
        """
        user = await self.shortener_data.find_one({'_id': user_id})
        if user:
            return {
                'site': user.get('site'),
                'api': user.get('api'),
                'enabled': user.get('enabled', False)
            }
        return None


    
    async def db_verify_status(self, user_id):
        user = await self.user_data.find_one({'_id': user_id})
        if user:
            return user.get('verify_status', default_verify)
        return default_verify

    async def db_update_verify_status(self, user_id, verify):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

    async def get_verify_status(self, user_id):
        verify = await self.db_verify_status(user_id)
        return verify

    async def update_verify_status(self, user_id, verify_token="", is_verified=False, verified_time=0, link=""):
        current = await self.db_verify_status(user_id)
        current['verify_token'] = verify_token
        current['is_verified'] = is_verified
        current['verified_time'] = verified_time
        current['link'] = link
        await self.db_update_verify_status(user_id, current)

    
    async def set_channel_button_link(self, button_name: str, button_link: str):
        await self.channel_button_link_data.delete_many({})  
        await self.channel_button_link_data.insert_one({'button_name': button_name, 'button_link': button_link}) 
    
    async def set_channel_button_links(self, button_name: str, button_link: str, button_name2: str = None, button_link2: str = None):
        """Set both channel buttons (button1 and button2)"""
        data = {'button_name': button_name, 'button_link': button_link}
        if button_name2 and button_link2:
            data['button_name2'] = button_name2
            data['button_link2'] = button_link2
        await self.channel_button_link_data.delete_many({})  
        await self.channel_button_link_data.insert_one(data)  

    async def get_channel_button_link(self):
        data = await self.channel_button_link_data.find_one({})
        if data:
            return data.get('button_name'), data.get('button_link')
        return ' Channel', 'https://t.me/Javpostr'
    
    async def get_channel_button_links(self):
        """Get both channel buttons (button1 and button2)"""
        data = await self.channel_button_link_data.find_one({})
        if data:
            return (
                data.get('button_name'), data.get('button_link'),
                data.get('button_name2'), data.get('button_link2')
            )
        return ' Channel', 'https://t.me/Javpostr', None, None


    
    async def set_del_timer(self, value: int):        
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})

    async def get_del_timer(self):
        data = await self.del_timer_data.find_one({})
        if data:
            return data.get('value', 600)
        return 600

    

    async def set_auto_delete(self, value: bool):
        existing = await self.auto_delete_data.find_one({})
        if existing:
            await self.auto_delete_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.auto_delete_data.insert_one({'value': value})

    async def set_hide_caption(self, value: bool):
        existing = await self.hide_caption_data.find_one({})
        if existing:
            await self.hide_caption_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.hide_caption_data.insert_one({'value': value})

    async def set_protect_content(self, value: bool):
        existing = await self.protect_content_data.find_one({})
        if existing:
            await self.protect_content_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.protect_content_data.insert_one({'value': value})

    async def set_channel_button(self, value: bool):
        existing = await self.channel_button_data.find_one({})
        if existing:
            await self.channel_button_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.channel_button_data.insert_one({'value': value})

    async def set_request_forcesub(self, value: bool):
        existing = await self.rqst_fsub_data.find_one({})
        if existing:
            await self.rqst_fsub_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.rqst_fsub_data.insert_one({'value': value})


    

    async def get_auto_delete(self):
        data = await self.auto_delete_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_hide_caption(self):
        data = await self.hide_caption_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_protect_content(self):
        data = await self.protect_content_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_channel_button(self):
        data = await self.channel_button_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_request_forcesub(self):
        data = await self.rqst_fsub_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    
    async def channel_exist(self, channel_id: int):
        found = await self.channel_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.channel_data.insert_one({'_id': channel_id})
            return

    async def del_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.channel_data.delete_one({'_id': channel_id})
            return

    async def get_all_channels(self):
        channel_docs = await self.channel_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
            return

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
            return

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})
            return

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            return

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    

    
    async def add_reqChannel(self, channel_id: int):
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$setOnInsert': {'user_ids': []}},  
            upsert=True  
        )

    
    async def set_request_forcesub_channel(self, channel_id: int, fsub_mode: bool):
        await self.rqst_fsub_Channel_data.update_one(
        {'_id': channel_id},
        {'$set': {'fsub_mode': fsub_mode}},
        upsert=True
    )

    
    async def reqSent_user(self, channel_id: int, user_id: int):
        
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$addToSet': {'user_ids': user_id}}, 
            upsert=True
        )

    
    async def del_reqSent_user(self, channel_id: int, user_id: int):
        
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$pull': {'user_ids': user_id}}
        )

    
    async def clear_reqSent_user(self, channel_id: int):
        if await self.reqChannel_exist(channel_id):
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': channel_id}, 
                {'$set': {'user_ids': []}}  
            )

    
    async def reqSent_user_exist(self, channel_id: int, user_id: int):
        
        found = await self.rqst_fsub_Channel_data.find_one(
            {'_id': channel_id, 'user_ids': user_id}
        )
        return bool(found)

    
    async def del_reqChannel(self, channel_id: int):
        
        await self.rqst_fsub_Channel_data.delete_one({'_id': channel_id})

    
    async def reqChannel_exist(self, channel_id: int):
        
        found = await self.rqst_fsub_Channel_data.find_one({'_id': channel_id})
        return bool(found)

    
    async def get_reqSent_user(self, channel_id: int):
        
        data = await self.rqst_fsub_Channel_data.find_one({'_id': channel_id})
        if data:
            return data.get('user_ids', [])
        return []

    
    async def get_reqChannel(self):
        
        channel_docs = await self.rqst_fsub_Channel_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids


    
    async def get_reqLink_channels(self):
        
        channel_docs = await self.store_reqLink_data.find().to_list(length=None)
        
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    
    async def get_stored_reqLink(self, channel_id: int):
        
        data = await self.store_reqLink_data.find_one({'_id': channel_id})
        if data:
            return data.get('link')
        return None

    
    async def store_reqLink(self, channel_id: int, link: str):
        
        await self.store_reqLink_data.update_one(
            {'_id': channel_id}, 
            {'$set': {'link': link}}, 
            upsert=True
        )

    
    async def del_stored_reqLink(self, channel_id: int):
        
        await self.store_reqLink_data.delete_one({'_id': channel_id})

    
    
    async def get_free_settings(self):
        settings = await self.free_data.find_one({"_id": "free_usage"})
        if not settings:
            settings = {"limit": 5, "enabled": True}
            await self.free_data.insert_one({"_id": "free_usage", **settings})
        return settings

    
    async def update_free_settings(self, limit=None, enabled=None):
        updates = {}
        if limit is not None:
            updates["limit"] = limit
        if enabled is not None:
            updates["enabled"] = enabled
        if updates:
            await self.free_data.update_one({"_id": "free_usage"}, {"$set": updates}, upsert=True)

    
    async def set_free_limit(self, limit: int):
        try:
            await self.free_data.update_one(
                {"_id": "free_usage"},  
                {"$set": {"limit": limit}},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"Error updating limit: {e}")
            return False

    
    async def check_free_usage(self, user_id):
        try:
        
            data = await self.free_data.find_one({"user_id": user_id})

            if not data:
                return 0  

        
            usage_count = int(data.get("count", 0))  
            return usage_count  
        except Exception as e:
            logging.error(f"Error checking free usage for user {user_id}: {e}")
            return 0  

    
    async def get_free_limit(self, user_id):
        try:
            settings = await self.free_data.find_one({"_id": "free_usage"})  
            if settings:
                return int(settings.get("limit", 5))  
            return None
        except Exception as e:
            logging.error(f"Error fetching limit: {e}")
            return None

    
    async def update_free_usage(self, user_id):
        try:
            
            data = await self.free_data.find_one({"user_id": user_id})

            current_time = time.time()

            if not data:
                
                await self.free_data.insert_one({"user_id": user_id, "count": 1, "last_reset": current_time})
            else:
                
                last_reset = data.get("last_reset", 0)
                if current_time - last_reset > 86400:  
                    await self.free_data.update_one({"user_id": user_id}, {"$set": {"count": 1, "last_reset": current_time}})
                else:
                    
                    await self.free_data.update_one({"user_id": user_id}, {"$inc": {"count": 1}})
        except Exception as e:
            logging.error(f"Error incrementing free usage for user {user_id}: {e}")

    
    async def reset_free_usage(self, user_id):
        try:
            data = await self.free_data.find_one({"user_id": user_id})
            if data and (time.time() - data.get("last_reset", 0) > 86400):
                await self.free_data.update_one(
                    {"user_id": user_id}, {"$set": {"count": 0, "last_reset": time.time()}}
                )
        except Exception as e:
            logging.error(f"Error resetting free usage for user {user_id}: {e}")

    async def reset_all_free_usage(self):
        """Reset free usage counts for all users (run daily)."""
        try:
            current_time = time.time()
            await self.free_data.update_many({"user_id": {"$exists": True}}, {"$set": {"count": 0, "last_reset": current_time}})
            logging.info("All free usage counts reset.")
        except Exception as e:
            logging.error(f"Error resetting all free usage: {e}")

    
    async def set_spam_notify_flag(self, user_id: int, action_type: str):
        try:
            key = f"{user_id}_{action_type}"
            await self.spam_protection_data.update_one({"_id": key}, {"$set": {"notify_scheduled": True}}, upsert=True)
        except Exception as e:
            logging.error(f"Error setting spam notify flag: {e}")

    async def clear_spam_notify_flag(self, user_id: int, action_type: str):
        try:
            key = f"{user_id}_{action_type}"
            await self.spam_protection_data.update_one({"_id": key}, {"$unset": {"notify_scheduled": ""}})
        except Exception as e:
            logging.error(f"Error clearing spam notify flag: {e}")

    async def get_spam_notify_flag(self, user_id: int, action_type: str) -> bool:
        try:
            key = f"{user_id}_{action_type}"
            data = await self.spam_protection_data.find_one({"_id": key})
            return bool(data and data.get("notify_scheduled", False))
        except Exception as e:
            logging.error(f"Error getting spam notify flag: {e}")
            return False

    
    async def update_verification_time(self, user_id):
        data = await self.for_data.find_one({"user_id": user_id})
        if not data:
            await self.for_data.insert_one({"user_id": user_id, "last_verified_time": time.time()})
        else:
            await self.for_data.update_one({"user_id": user_id}, {"$set": {"last_verified_time": time.time()}})
        return True  

    
    async def was_verified_in_last_24hrs(self, user_id):
        data = await self.for_data.find_one({"user_id": user_id})
        if not data or not data.get("last_verified_time"):
            return False

        last_verified_time = data["last_verified_time"]
        return (time.time() - last_verified_time) < 86400  

    
    async def get_free_state(self, user_id):
        user_data = await self.login_data.find_one({"user_id": user_id})
        return user_data.get("free_state", True) if user_data else True  

    
    async def set_free_state(self, user_id, state):
        user_data = await self.login_data.find_one({"user_id": user_id})

        if user_data:
            await self.login_data.update_one({"user_id": user_id}, {"$set": {"free_state": state}})
        else:
            await self.login_data.insert_one({"user_id": user_id, "free_state": state})





    
    
    
    async def video_exists(self, file_id: str):
        
        return await self.videos_collection.find_one({"$or": [{"file_id": file_id}, {"file_unique_id": file_id}]})

    async def insert_videos(self, video_list: list):
        if video_list:
            return await self.videos_collection.insert_many(video_list)

    async def get_videos(self):
        cursor = self.videos_collection.find({})
        return await cursor.to_list(length=None)

    
    
    
    async def photo_exists(self, file_id: str):
        
        return await self.photos_collection.find_one({"$or": [{"file_id": file_id}, {"file_unique_id": file_id}]})

    async def insert_photos(self, photo_list: list):
        if photo_list:
            return await self.photos_collection.insert_many(photo_list)

    async def get_photos(self):
        cursor = self.photos_collection.find({})
        return await cursor.to_list(length=None)

    
    
    
    async def check_spam_limit(self, user_id: int, action_type: str = "default", max_requests: int = 5, time_window: int = 60):
        """Check if user has exceeded spam limit. Returns (is_allowed, remaining_time)"""
        try:
            current_time = time.time()
            key = f"{user_id}_{action_type}"
            
            data = await self.spam_protection_data.find_one({"_id": key})
            
            if not data:
                
                await self.spam_protection_data.insert_one({
                    "_id": key,
                    "requests": [current_time],
                    "last_reset": current_time
                })
                return True, 0
            
            
            requests = [req_time for req_time in data.get("requests", []) if current_time - req_time < time_window]
            
            if len(requests) >= max_requests:
                
                oldest_request = min(requests) if requests else current_time
                remaining_time = int(time_window - (current_time - oldest_request))
                return False, remaining_time
            
            
            requests.append(current_time)
            await self.spam_protection_data.update_one(
                {"_id": key},
                {"$set": {"requests": requests, "last_reset": current_time}},
                upsert=True
            )
            return True, 0
            
        except Exception as e:
            logging.error(f"Error checking spam limit: {e}")
            return True, 0  

    async def reset_spam_protection(self, user_id: int, action_type: str = "default"):
        """Reset spam protection for a user"""
        try:
            key = f"{user_id}_{action_type}"
            await self.spam_protection_data.delete_one({"_id": key})
        except Exception as e:
            logging.error(f"Error resetting spam protection: {e}")


    
    
    
    async def get_user(self, user_id: int):
        return await self.users_collection.find_one({"user_id": user_id})

    async def create_user(self, user_id: int, daily_limit: int, last_access: str, subscription="free"):
        return await self.users_collection.insert_one({
            "user_id": user_id,
            "subscription": subscription,
            "subscription_expiry": None,
            "daily_limit": daily_limit,
            "last_access": last_access
        })

    async def update_user(self, user_id: int, data: dict):
        return await self.users_collection.update_one({"user_id": user_id}, {"$set": data})

    async def decrement_daily_limit(self, user_id: int):
        return await self.users_collection.update_one({"user_id": user_id}, {"$inc": {"daily_limit": -1}})

    
    
    
    async def get_referrer(self, user_id: int):
        """Get the user who referred this user"""
        data = await self.referrals_collection.find_one({"referred_user_id": user_id})
        return data.get("referrer_user_id") if data else None

    async def add_referral(self, referrer_user_id: int, referred_user_id: int):
        """Add a referral relationship"""
        
        existing = await self.referrals_collection.find_one({"referred_user_id": referred_user_id})
        if existing:
            return False  
        
        await self.referrals_collection.insert_one({
            "referrer_user_id": referrer_user_id,
            "referred_user_id": referred_user_id,
            "created_at": datetime.utcnow()
        })
        return True  

    async def get_referral_count(self, user_id: int):
        """Get total number of referrals for a user"""
        count = await self.referrals_collection.count_documents({"referrer_user_id": user_id})
        return count

    async def get_referrals(self, user_id: int):
        """Get list of all users referred by this user"""
        cursor = self.referrals_collection.find({"referrer_user_id": user_id})
        referrals = await cursor.to_list(length=None)
        return [ref.get("referred_user_id") for ref in referrals]

    async def check_referral_exists(self, referred_user_id: int):
        """Check if user was already referred"""
        data = await self.referrals_collection.find_one({"referred_user_id": referred_user_id})
        return bool(data)

    async def get_referral_stats(self, user_id: int):
        """Get referral statistics for a user"""
        total_referrals = await self.get_referral_count(user_id)
        referrals = await self.get_referrals(user_id)
        return {
            "total_referrals": total_referrals,
            "referred_users": referrals
        }

    
    
    
    async def set_custom_caption(self, caption: str):
        """Set custom caption in database"""
        try:
            await self.custom_caption_data.update_one(
                {"_id": "custom_caption"},
                {"$set": {"caption": caption}},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"Error setting custom caption: {e}")
            return False

    async def get_custom_caption(self):
        """Get custom caption from database"""
        try:
            data = await self.custom_caption_data.find_one({"_id": "custom_caption"})
            if data:
                return data.get("caption", None)
            return None
        except Exception as e:
            logging.error(f"Error getting custom caption: {e}")
            return None

    
db = Rohit(DB_URI, DB_NAME)

        

