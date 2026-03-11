import re

with open("plugins/start.py", "r") as f:
    target_content = f.read()

with open("/tmp/sarabot/plugins/start.py", "r") as f:
    source_content = f.read()

def get_function_body(content, func_name):
    pattern = re.compile(rf"^(async def {func_name}\(.*?\):.*?)^\w", re.MULTILINE | re.DOTALL)
    match = pattern.search(content)
    if match:
        return match.group(1)

    # fallback for end of file
    pattern_eof = re.compile(rf"^(async def {func_name}\(.*?\):.*?)$", re.MULTILINE | re.DOTALL)
    match_eof = pattern_eof.search(content)
    if match_eof:
        return match_eof.group(1)
    return None

functions_to_replace = ["get_photo", "get_video", "get_batch", "send_batch_media", "store_photos", "store_videos"]

for func in functions_to_replace:
    source_body = get_function_body(source_content, func)
    target_body = get_function_body(target_content, func)

    if source_body and target_body:
        target_content = target_content.replace(target_body, source_body)
        print(f"Replaced {func}")
    else:
        print(f"Failed to find {func}")

with open("plugins/start.py", "w") as f:
    f.write(target_content)
