with open("plugins/start.py", "r") as f:
    text = f.read()

search = """        if text.startswith("/start get_photo_") or "get_photo_" in text:
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
                pass"""

replace = """        payload = text.split(" ", 1)[1] if " " in text else text

        if payload.startswith("get_photo_"):
            try:
                _, _, user_id_str = text.split("_", 2)
                if int(user_id_str) == user_id:
                    return await get_photo(client, message)
            except:
                pass

        if payload.startswith("get_video_"):
            try:
                _, _, user_id_str = text.split("_", 2)
                if int(user_id_str) == user_id:
                    return await get_video(client, message)
            except:
                pass

        if payload.startswith("get_batch_"):
            try:
                _, _, user_id_str = text.split("_", 2)
                if int(user_id_str) == user_id:
                    return await get_batch(client, message)
            except:
                pass"""

if search in text:
    print("Replacing command matching...")
    with open("plugins/start.py", "w") as f:
        f.write(text.replace(search, replace))
else:
    print("Could not find matching block.")
