from telegram import Update, ParseMode
from telegram.ext import CallbackContext
import os

from config.config import WELCOME_MESSAGE, HELP_MESSAGE, MAX_FILE_SIZE, CLEANUP_TIME, logger
from utils.extractor import Extractor
from utils.file_manager import FileManager

# Store active extraction processes
active_extractions = {}

async def start_command(update: Update, context: CallbackContext):
    """Handle the /start command"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    welcome_msg = f"Hello, {user_name}! 👋\n\n" + WELCOME_MESSAGE
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Clean up old files for this user if any
    FileManager.cleanup_user_files(user_id)

async def help_command(update: Update, context: CallbackContext):
    """Handle the /help command"""
    help_msg = HELP_MESSAGE.format(max_size=MAX_FILE_SIZE)
    
    await update.message.reply_text(
        help_msg,
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel_command(update: Update, context: CallbackContext):
    """Handle the /cancel command to cancel ongoing extraction"""
    user_id = update.effective_user.id
    
    if user_id in active_extractions:
        extractor = active_extractions[user_id].get("extractor")
        if extractor:
            extractor.cancel()
            await update.message.reply_text(
                "🛑 Extraction process canceled. You can send another file when ready.",
                parse_mode=ParseMode.MARKDOWN
            )
        del active_extractions[user_id]
    else:
        await update.message.reply_text(
            "No active extraction process to cancel. You can send a file to extract.",
            parse_mode=ParseMode.MARKDOWN
        )

async def cleanup_command(update: Update, context: CallbackContext):
    """Handle the /cleanup command to delete temporary files"""
    user_id = update.effective_user.id
    
    # Cancel any active extraction
    if user_id in active_extractions:
        extractor = active_extractions[user_id].get("extractor")
        if extractor:
            extractor.cancel()
        del active_extractions[user_id]
    
    # Clean up files
    result = FileManager.cleanup_user_files(user_id)
    
    if result.get("success", False):
        await update.message.reply_text(
            "🧹 All your temporary files have been cleaned up.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"❌ Error cleaning up files: {result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )

async def status_command(update: Update, context: CallbackContext):
    """Handle the /status command to check bot status"""
    # Get system stats
    try:
        import psutil
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_usage = f"{memory.percent}%"
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_usage = f"{disk.percent}%"
        
        # Count active extractions
        active_count = len(active_extractions)
        
        # Count temporary files
        temp_files_count = 0
        temp_files_size = 0
        
        for root, dirs, files in os.walk(os.path.expanduser(os.getenv("TEMP_DIR", "./temp_files"))):
            temp_files_count += len(files)
            for f in files:
                file_path = os.path.join(root, f)
                temp_files_size += os.path.getsize(file_path)
                
        temp_files_size_str = Extractor.human_readable_size(temp_files_size)
        
        status_msg = (
            f"🤖 *Bot Status*\n\n"
            f"*Memory Usage:* {memory_usage}\n"
            f"*Disk Usage:* {disk_usage}\n"
            f"*Active Extractions:* {active_count}\n"
            f"*Temporary Files:* {temp_files_count} ({temp_files_size_str})\n"
            f"*Cleanup Time:* {CLEANUP_TIME} hours\n"
            f"*Max File Size:* {MAX_FILE_SIZE} MB\n\n"
            f"Bot is running normally."
        )
        
        await update.message.reply_text(
            status_msg,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in status command: {str(e)}")
        await update.message.reply_text(
            f"❌ Error getting bot status: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        ) 