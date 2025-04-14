from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, ConversationHandler
import re

from config.config import logger
from utils.file_manager import FileManager
from utils.ui_helper import UIHelper
from handlers.command_handlers import active_extractions
from handlers.file_handlers import (
    download_file, 
    download_all_files, 
    delete_extraction, 
    handle_password
)

# Conversation states
PASSWORD_INPUT = 1

async def handle_callback_query(update: Update, context: CallbackContext):
    """Handle callbacks from inline keyboards"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Answer callback query to remove loading state
    await query.answer()
    
    callback_data = query.data
    
    # Handle file download
    if callback_data.startswith("file:"):
        file_path = callback_data[5:]  # Remove "file:" prefix
        await download_file(update, context, user_id, file_path)
        return
    
    # Handle page navigation
    if callback_data.startswith("page:"):
        await handle_page_navigation(update, context, user_id, callback_data)
        return
    
    # Handle other actions
    if callback_data == "download_all":
        await download_all_files(update, context, user_id)
        
    elif callback_data == "delete":
        await delete_extraction(update, context, user_id)
        
    elif callback_data == "extract_another":
        # Clean up current extraction
        if user_id in active_extractions:
            del active_extractions[user_id]
            
        await query.message.reply_text(
            "📥 You can now send another file to extract.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    elif callback_data == "enter_password":
        # Start password conversation
        await query.message.reply_text(
            "🔑 Please enter the password for this archive:",
            parse_mode=ParseMode.MARKDOWN
        )
        return PASSWORD_INPUT
        
    elif callback_data == "cancel":
        # Cancel current extraction
        if user_id in active_extractions:
            extractor = active_extractions[user_id].get("extractor")
            if extractor:
                extractor.cancel()
                
            await query.message.edit_text(
                "🛑 Extraction canceled. You can send another file when ready.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            del active_extractions[user_id]
        else:
            await query.message.edit_text(
                "No active extraction to cancel.",
                parse_mode=ParseMode.MARKDOWN
            )

async def handle_page_navigation(update: Update, context: CallbackContext, user_id, callback_data):
    """Handle pagination for file list"""
    query = update.callback_query
    
    # Extract page number
    match = re.match(r"page:(\d+)", callback_data)
    if not match:
        return
    
    page = int(match.group(1))
    
    if user_id not in active_extractions:
        await query.message.edit_text(
            "⚠️ No active extraction found. Please upload a file first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    extraction_data = active_extractions[user_id]
    file_list_result = extraction_data.get("file_list_result")
    
    if not file_list_result:
        await query.message.edit_text(
            "⚠️ File list not available.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Create new file list message for the requested page
    message, keyboard = UIHelper.create_file_list_message(file_list_result, page)
    
    await query.message.edit_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

async def handle_password_input(update: Update, context: CallbackContext):
    """Handle password input from user"""
    user_id = update.effective_user.id
    password = update.message.text
    
    # Delete the message with the password for security
    await update.message.delete()
    
    await handle_password(update, context, user_id, password)
    
    return ConversationHandler.END

async def cancel_password_input(update: Update, context: CallbackContext):
    """Cancel password input conversation"""
    await update.message.reply_text(
        "Password input canceled. You can try again or send another file.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END 