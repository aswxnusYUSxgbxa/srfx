import re

with open("plugins/start.py", "r") as f:
    content = f.read()

with open("/tmp/sarabot/plugins/start.py", "r") as f:
    sarabot_content = f.read()

def extract_func(source, func_name, stop_keywords=None):
    if stop_keywords is None:
        stop_keywords = ["async def ", "def ", "@Client.on_message", "@Bot.on_message"]

    lines = source.split("\n")
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith(f"async def {func_name}(") or line.startswith(f"def {func_name}("):
            start_idx = i
            break

    if start_idx == -1:
        return None

    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        # Ignore decorators and nested definitions
        if any(line.startswith(kw) for kw in stop_keywords):
            # Special case for lines starting with 'def' inside a docstring or something, but usually fine
            end_idx = i
            break

    # Include some empty lines if there are any
    while end_idx > 0 and lines[end_idx - 1].strip() == "":
        end_idx -= 1

    return "\n".join(lines[start_idx:end_idx])

functions_to_replace = ["get_photo", "get_video", "get_batch", "send_batch_media", "store_photos", "store_videos"]

for func in functions_to_replace:
    old_func = extract_func(content, func, ["async def ", "@Bot.on_message", "@Client.on_message", "WAIT_MSG =", "# --- Send Batch Media Group"])
    new_func = extract_func(sarabot_content, func, ["async def ", "@Bot.on_message", "@Client.on_message", "WAIT_MSG =", "# --- Send Batch Media Group"])

    if old_func and new_func:
        content = content.replace(old_func, new_func)
        print(f"Replaced {func}")
    else:
        print(f"Failed to find {func} in one of the files")

with open("plugins/start.py", "w") as f:
    f.write(content)
