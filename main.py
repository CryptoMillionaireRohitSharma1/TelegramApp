import os
import logging
from telethon import TelegramClient, errors
from dotenv import load_dotenv
import asyncio

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SOURCE_CHANNEL = os.getenv('SOURCE_CHANNEL')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')
SESSION_NAME = os.getenv('SESSION_NAME')

LAST_MSG_FILE = 'last_message_id.txt'

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Get Channel Names and IDs
async def get_channel_info():
    """Print all channel IDs that the user has access to"""
    logger.info("Retrieving channel information...")
    
    print("\n=== CHANNELS YOU HAVE ACCESS TO ===")
    print("Format: Channel Name | Channel ID")
    print("-------------------------------------")
    
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            print(f"{dialog.name} | {dialog.id}")
    
    print("-------------------------------------")
    print("Use these IDs in your .env file")
    print("SOURCE_CHANNEL=<id from above>")
    print("TARGET_CHANNEL=<id from above>")
    print("=====================================\n")

async def get_last_message_id():
    try:
        with open(LAST_MSG_FILE, 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 0
    except ValueError:
        logger.warning("Invalid content in last_message_id.txt. Starting from 0.")
        return 0

async def set_last_message_id(msg_id):
    with open(LAST_MSG_FILE, 'w') as f:
        f.write(str(msg_id))

async def forward_new_messages():
    # Convert channel IDs to integers if they're not None
    source_channel = int(SOURCE_CHANNEL) if SOURCE_CHANNEL else None
    target_channel = int(TARGET_CHANNEL) if TARGET_CHANNEL else None
    
    if not source_channel or not target_channel:
        logger.error("Source or target channel ID is missing. Please check your .env file.")
        return
    
    # Try to get channel entities to verify they exist and are accessible
    try:
        source_entity = await client.get_entity(source_channel)
        logger.info(f"Source channel: {source_entity.title}")
    except Exception as e:
        logger.error(f"Error accessing source channel: {str(e)}")
        return
        
    try:
        target_entity = await client.get_entity(target_channel)
        logger.info(f"Target channel: {target_entity.title}")
    except Exception as e:
        logger.error(f"Error accessing target channel: {str(e)}")
        return
    
    last_msg_id = await get_last_message_id()
    logger.info(f"Looking for messages newer than ID {last_msg_id}")
    
    messages = []
    
    try:
        async for msg in client.iter_messages(source_channel, min_id=last_msg_id):
            messages.append(msg)
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        return
    
    if not messages:
        logger.info("No new messages to forward.")
        return
    
    logger.info(f"Found {len(messages)} new messages to forward")
    messages.reverse()  # Process older messages first
    
    for msg in messages:
        try:
            await client.forward_messages(target_channel, msg)
            logger.info(f"Forwarded message ID {msg.id}")
            await set_last_message_id(msg.id)
        except errors.FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"Rate limit exceeded. Need to wait {wait_time} seconds.")
            break
        except Exception as e:
            logger.error(f"Error forwarding message ID {msg.id}: {str(e)}")

async def main():
    await client.start()
    logger.info("Client started successfully")
    
    # First, let's get channel information to help with setup
    await get_channel_info()
    
    # Only proceed with forwarding if environment variables are set
    if SOURCE_CHANNEL and TARGET_CHANNEL:
        await forward_new_messages()
    else:
        logger.info("Channel IDs not configured. Please set SOURCE_CHANNEL and TARGET_CHANNEL in your .env file.")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
