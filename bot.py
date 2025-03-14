from telethon import TelegramClient, events
import asyncio
import os
import time
import math
import psutil
import requests

# Replace these with your own values
API_ID = 23048702
API_HASH = '2ce9a07cc844e09922a39c654c2fc9fa'
BOT_TOKEN = '7526802238:AAHTd-lU6F-mDY0AuKgBVae9etep2F_vS2Y'

# Initialize the Telegram client
client = TelegramClient('mirror_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Local storage directory
DOWNLOAD_DIR = r"C:\koustubh\New folder"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Function to format file size
def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# Function to format time
def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

# Function to get system stats
def get_system_stats():
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/')
    uptime = time.time() - psutil.boot_time()
    return cpu_usage, ram_usage, disk_usage, uptime

# Function to generate a clean UI message
def generate_ui_message(header, body=None):
    cpu_usage, ram_usage, disk_usage, uptime = get_system_stats()
    message = (
        f"{header}\n\n"
        f"• Bot Stats\n"
        f"  CPU: {cpu_usage}% | Disk: {format_size(disk_usage.used)} [{disk_usage.percent}%]\n"
        f"  RAM: {ram_usage}% | Uptime: {format_time(uptime)}\n"
        f"  DL: 0B/s | UL: 0B/s"
    )
    if body:
        message = f"{header}\n\n{body}\n\n{message}"
    return message

# Progress callback function for URL downloads
async def progress_url(current, total, event, start_time, file_name, progress_message):
    elapsed_time = time.time() - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    # Progress bar (using Unicode block characters)
    progress_bar_length = 20
    percent = (current / total) * 100
    filled_length = int(progress_bar_length * current // total)

    # Determine the progress bar style based on the percentage
    if percent < 50:
        progress_bar = '▤' * filled_length + '□' * (progress_bar_length - filled_length)
    elif percent < 85:
        progress_bar = '▩' * filled_length + '□' * (progress_bar_length - filled_length)
    elif percent < 100:
        progress_bar = '■' + '▤' * (filled_length - 1) + '□' * (progress_bar_length - filled_length)
    else:
        progress_bar = '■' * progress_bar_length  # Fully black bar

    # Generate progress message
    progress_text = (
        f"{file_name}\n"
        f"  [{progress_bar}] {percent:.1f}%\n"
        f"  Processed: {format_size(current)} of {format_size(total)}\n"
        f"  Status: Downloading | ETA: {format_time(eta)}\n"
        f"  Speed: {format_size(speed)}/s | Elapsed: {format_time(elapsed_time)}\n"
        f"  Engine: NebulaDrive v3.0\n"
        f"  Mode: #URL | #Tg\n"
        f"  User: {event.sender.first_name} | ID: {event.sender_id}\n"
        f"  /cancel_{event.message.id}"
    )

    # Add Bot Stats
    full_message = generate_ui_message(progress_text)
    await progress_message.edit(full_message)

# Function to download files from URLs
async def download_url(url, file_path, event, progress_message):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        start_time = time.time()

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                downloaded_size += len(chunk)
                await progress_url(downloaded_size, total_size, event, start_time, os.path.basename(file_path), progress_message)
                return True
    except Exception as e:
        await event.reply(f"Error downloading file: {str(e)}")
        return False

# Handle /mirror command
@client.on(events.NewMessage(pattern='/mirror'))
async def handle_mirror_command(event):
    try:
        # Check if the message contains a URL
        if event.message.message.startswith('/mirror http'):
            url = event.message.message.split(' ')[1]
            file_name = url.split('/')[-1] or f"file_{int(time.time())}"
            file_path = os.path.join(DOWNLOAD_DIR, file_name)

            # Notify the user
            progress_message = await event.reply(generate_ui_message(f"Starting download: {file_name}"))

            # Download the file from the URL
            if await download_url(url, file_path, event, progress_message):
                await event.reply(
                    f"Download Complete!\n"
                    f"  File: {file_name}\n"
                    f"  Size: {format_size(os.path.getsize(file_path))}\n"
                    f"  Saved successfully. 🚀"
                )
        # Check if the message is a reply to a file
        elif event.is_reply:
            replied_message = await event.get_reply_message()
            if replied_message.media:
                # Get file name or assign a default name
                if replied_message.file:
                    file_name = replied_message.file.name or f"file_{int(time.time())}.{replied_message.file.ext}"
                else:
                    file_name = f"file_{int(time.time())}.jpg"  # Default name for photos

                file_path = os.path.join(DOWNLOAD_DIR, file_name)

                # Notify the user
                progress_message = await event.reply(generate_ui_message(f"Starting download: {file_name}"))

                # Download the file with progress updates
                start_time = time.time()
                await client.download_media(
                    replied_message,
                    file=file_path,
                    progress_callback=lambda d, t: asyncio.create_task(progress_url(d, t, event, start_time, file_name, progress_message))
                )

                # Notify the user of completion
                await event.reply(
                    f"Download Complete!\n"
                    f"  File: {file_name}\n"
                    f"  Size: {format_size(os.path.getsize(file_path))}\n"
                    f"  Saved successfully. 🚀"
                )
            else:
                await event.reply("The replied message does not contain any media.")
        else:
            await event.reply("Please reply to a file or provide a valid URL with /mirror.")
    except Exception as e:
        await event.reply(f"An error occurred: {str(e)}")
# Start the bot
if __name__ == '__main__':
    print("Bot is running...")
    client.run_until_disconnected()