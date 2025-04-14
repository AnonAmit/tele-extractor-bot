#!/usr/bin/env python3
"""
Telegram Bot for Extracting Compressed Files with Visual Progress
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from config.config import BOT_TOKEN, CLEANUP_TIME, logger
from handlers.command_handlers import (
    start_command,
    help_command,
    cancel_command,
    cleanup_command,
    status_command
)
from handlers.file_handlers import handle_document
from handlers.callback_handlers import (
    handle_callback_query,
    handle_password_input,
    cancel_password_input,
    PASSWORD_INPUT
)
from utils.extractor import Extractor

async def setup_commands(application: Application):
    """Set up bot commands in the menu"""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help information"),
        BotCommand("cancel", "Cancel ongoing extraction"),
        BotCommand("cleanup", "Delete your temporary files"),
        BotCommand("status", "Check bot status")
    ]
    
    await application.bot.set_my_commands(commands)

async def scheduled_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Periodically clean up old files"""
    logger.info("Running scheduled cleanup...")
    try:
        result = Extractor.cleanup_old_files(CLEANUP_TIME)
        if result.get("success", False):
            logger.info("Scheduled cleanup completed successfully")
        else:
            logger.error(f"Scheduled cleanup failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error during scheduled cleanup: {str(e)}")

def main():
    """Main function to start the bot"""
    # Setup application with the bot token
    application = Application.builder().token(BOT_TOKEN).build()

    # Create conversation handler for password input
    password_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback_query, pattern="^enter_password$")],
        states={
            PASSWORD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_password_input)],
        name="password_conversation"
    )

    # Setup command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("cleanup", cleanup_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Add password conversation handler
    application.add_handler(password_conv_handler)
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add document handler for file uploads
    application.add_handler(MessageHandler(filters.ATTACHMENT, handle_document))
    
    # Setup job for periodic cleanup (every 3 hours)
    job_queue = application.job_queue
    job_queue.run_repeating(scheduled_cleanup, interval=timedelta(hours=3), first=timedelta(minutes=5))
    
    # Setup bot commands
    asyncio.run(setup_commands(application))
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == "__main__":
    main()