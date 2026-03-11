with open("plugins/start.py", "r") as f:
    text = f.read()

import re

# Since simple exact text replacement failed to find differences, we will use regex to find the whole function body.
def replace_func_regex(source, new_source, func_name):
    pattern = r"(async def " + func_name + r"\(.*?\):.*?)(?=\n(?:async def |def |@Bot\.on_message|@Client\.on_message|WAIT_MSG =|# --- Send Batch Media Group))"
    match = re.search(pattern, source, re.DOTALL)
    new_match = re.search(pattern, new_source, re.DOTALL)

    if match and new_match:
        return source.replace(match.group(1), new_match.group(1))
    return source

with open("/tmp/sarabot/plugins/start.py", "r") as f:
    sarabot_content = f.read()

functions_to_replace = ["get_photo", "get_video", "get_batch", "send_batch_media", "store_photos", "store_videos"]

for func in functions_to_replace:
    text = replace_func_regex(text, sarabot_content, func)

with open("plugins/start.py", "w") as f:
    f.write(text)
