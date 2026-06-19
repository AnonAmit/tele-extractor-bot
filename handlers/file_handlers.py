from telegram import Update, ParseMode
from telegram.ext import CallbackContext
import os
import asyncio
import threading

from config.config import MAX_FILE_SIZE_BYTES, logger
from utils.extractor import Extractor
from utils.file_manager import FileManager
from utils.ui_helper import UIHelper

from handlers.command_handlers import active_extractions

async def handle_document(update: Update, context: CallbackContext):
    """Handle document uploads (compressed files)"""
    user_id = update.effective_user.id
    
    # Check if user already has an active extraction
    if user_id in active_extractions:
        await update.message.reply_text(
            "⚠️ You already have an active extraction process. Please wait for it to complete or use /cancel to cancel it.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    document = update.message.document
    file_id = document.file_id
    file_name = document.file_name
    file_size = document.file_size
    
    # Check file size
    if file_size > MAX_FILE_SIZE_BYTES:
        await update.message.reply_text(
            f"⚠️ File is too large. Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Send initial message
    progress_message = await update.message.reply_text(
        f"📥 Received file: `{file_name}`\n\n{UIHelper.format_size(file_size)}\n\nPreparing to download...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Download the file
    await progress_message.edit_text(
        f"⬇️ Downloading `{file_name}`...\n\n{UIHelper.format_size(file_size)}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    download_result = await FileManager.download_file(context.bot, file_id, user_id)
    
    if not download_result.get("success", False):
        await progress_message.edit_text(
            f"❌ Download failed: {download_result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    file_path = download_result.get("file_path")
    
    # Create extractor and gather file info
    extractor = Extractor(file_path, "")  # Temporary, will set extract_dir later
    
    if not extractor.is_archive():
        await progress_message.edit_text(
            f"❌ The file does not appear to be a supported archive format.\n\nSupported formats: ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ, etc.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get archive info
    archive_info = extractor.get_archive_info()
    archive_info.update({
        "original_name": download_result.get("original_name", file_name),
        "size": download_result.get("size", file_size)
    })
    
    # Create directory for extraction
    extract_dir_result = FileManager.create_extraction_dir(user_id, file_name)
    
    if not extract_dir_result.get("success", False):
        await progress_message.edit_text(
            f"❌ Failed to prepare extraction: {extract_dir_result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    extract_dir = extract_dir_result.get("extract_dir")
    
    # Update extractor with proper extraction directory
    extractor = Extractor(file_path, extract_dir)
    
    # Store extraction data
    active_extractions[user_id] = {
        "file_info": archive_info,
        "extract_dir": extract_dir,
        "extractor": extractor,
        "progress_message": progress_message
    }
    
    # Show file info while preparing
    file_info_message = UIHelper.create_file_info_message(archive_info)
    
    await progress_message.edit_text(
        file_info_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=UIHelper.create_extraction_cancel_keyboard()
    )
    
    # Start extraction in a separate thread
    asyncio.create_task(extract_archive(update, context, user_id))

async def extract_archive(update: Update, context: CallbackContext, user_id):
    """Extract the archive in a non-blocking way"""
    if user_id not in active_extractions:
        return
    
    extraction_data = active_extractions[user_id]
    file_info = extraction_data.get("file_info")
    extractor = extraction_data.get("extractor")
    progress_message = extraction_data.get("progress_message")
    
    # Function to update progress message
    async def update_progress(progress):
        message = UIHelper.create_extraction_progress_message(file_info, progress)
        
        try:
            await progress_message.edit_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=UIHelper.create_extraction_cancel_keyboard()
            )
        except Exception as e:
            logger.error(f"Error updating progress message: {str(e)}")
    
    # Create a wrapper for progress callback to work with asyncio
    def progress_callback(progress):
        asyncio.run_coroutine_threadsafe(
            update_progress(progress),
            asyncio.get_event_loop()
        )
    
    # Run extraction in a separate thread
    def run_extraction():
        try:
            result = extractor.extract(progress_callback)
            # Signal completion through the event loop
            asyncio.run_coroutine_threadsafe(
                extraction_complete(user_id, result),
                asyncio.get_event_loop()
            )
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            # Signal error through the event loop
            asyncio.run_coroutine_threadsafe(
                extraction_error(user_id, str(e)),
                asyncio.get_event_loop()
            )
    
    # Start extraction thread
    extraction_thread = threading.Thread(target=run_extraction)
    extraction_thread.daemon = True
    extraction_thread.start()

async def extraction_complete(user_id, result):
    """Handle extraction completion"""
    if user_id not in active_extractions:
        return
    
    extraction_data = active_extractions[user_id]
    file_info = extraction_data.get("file_info")
    extract_dir = extraction_data.get("extract_dir")
    progress_message = extraction_data.get("progress_message")
    
    if not result.get("success", False):
        # Check if password required
        if result.get("password_required", False):
            await progress_message.edit_text(
                f"🔒 This archive is password-protected.\nPlease use the button below to enter the password.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=UIHelper.create_password_request_keyboard()
            )
            return
        
        # General extraction error
        await progress_message.edit_text(
            f"❌ Extraction failed: {result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Clean up
        del active_extractions[user_id]
        return
    
    # Get extracted files list
    file_list_result = FileManager.list_extracted_files(extract_dir)
    
    # Show completion message
    completion_message = UIHelper.create_extraction_complete_message(file_info, result)
    
    await progress_message.edit_text(
        completion_message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Show file list
    file_list_message, keyboard = UIHelper.create_file_list_message(file_list_result)
    
    file_list_msg = await progress_message.reply_text(
        file_list_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    
    # Update extraction data
    extraction_data["file_list_message"] = file_list_msg
    extraction_data["extraction_result"] = result
    extraction_data["file_list_result"] = file_list_result

async def extraction_error(user_id, error_message):
    """Handle extraction errors"""
    if user_id not in active_extractions:
        return
    
    extraction_data = active_extractions[user_id]
    progress_message = extraction_data.get("progress_message")
    
    await progress_message.edit_text(
        f"❌ Extraction failed: {error_message}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Clean up
    del active_extractions[user_id]

async def handle_password(update: Update, context: CallbackContext, user_id):
    """Handle password entry for password-protected archives"""
    if user_id not in active_extractions:
        await update.callback_query.message.reply_text(
            "⚠️ No active extraction found. Please upload a file first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Retrieve password from conversation context
    password = context.user_data.pop("archive_password", "")
    if not password:
        await update.callback_query.message.reply_text(
            "⚠️ No password provided. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    extraction_data = active_extractions[user_id]
    file_info = extraction_data.get("file_info")
    file_path = extraction_data.get("extractor").file_path
    extract_dir = extraction_data.get("extract_dir")
    progress_message = extraction_data.get("progress_message")
    
    # Create new extractor with password
    extractor = Extractor(file_path, extract_dir, password)
    
    # Update extraction data
    extraction_data["extractor"] = extractor
    
    # Show preparing message
    await progress_message.edit_text(
        f"🔑 Password entered. Trying to extract with the provided password...",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=UIHelper.create_extraction_cancel_keyboard()
    )
    
    # Start extraction again
    asyncio.create_task(extract_archive(update, context, user_id))

async def download_file(update: Update, context: CallbackContext, user_id, file_path):
    """Send an extracted file to the user"""
    if user_id not in active_extractions:
        await update.callback_query.message.reply_text(
            "⚠️ No active extraction found. Please upload a file first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    extraction_data = active_extractions[user_id]
    extract_dir = extraction_data.get("extract_dir")
    
    # Get full file path
    file_path_result = FileManager.get_file_path(extract_dir, file_path)
    
    if not file_path_result.get("success", False):
        await update.callback_query.message.reply_text(
            f"❌ File not found: {file_path_result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    full_path = file_path_result.get("file_path")
    file_name = os.path.basename(full_path)
    
    # Send the file
    try:
        with open(full_path, 'rb') as file:
            await update.callback_query.message.reply_document(
                document=file,
                filename=file_name,
                caption=f"📂 File: `{file_name}`",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Error sending file: {str(e)}")
        await update.callback_query.message.reply_text(
            f"❌ Error sending file: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )

async def download_all_files(update: Update, context: CallbackContext, user_id):
    """Create a zip of all extracted files and send it to the user"""
    if user_id not in active_extractions:
        await update.callback_query.message.reply_text(
            "⚠️ No active extraction found. Please upload a file first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    extraction_data = active_extractions[user_id]
    extractor = extraction_data.get("extractor")
    file_info = extraction_data.get("file_info")
    
    # Show processing message
    processing_message = await update.callback_query.message.reply_text(
        "📦 Creating a ZIP file with all extracted files...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Create zip file
    zip_result = extractor.create_zip_from_directory()
    
    if not zip_result.get("success", False):
        await processing_message.edit_text(
            f"❌ Error creating ZIP file: {zip_result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    zip_path = zip_result.get("zip_path")
    
    # Send the zip file
    try:
        base_name = os.path.splitext(file_info.get("original_name", "files"))[0]
        zip_name = f"{base_name}_extracted.zip"
        
        with open(zip_path, 'rb') as file:
            await processing_message.edit_text(
                "✅ ZIP file created! Sending...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await update.callback_query.message.reply_document(
                document=file,
                filename=zip_name,
                caption=f"📦 All extracted files from `{file_info.get('original_name', 'archive')}`",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"Error sending ZIP file: {str(e)}")
        await processing_message.edit_text(
            f"❌ Error sending ZIP file: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        # Clean up zip file
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except Exception as e:
            logger.error(f"Error cleaning up ZIP file: {str(e)}")

async def delete_extraction(update: Update, context: CallbackContext, user_id):
    """Delete the extraction directory and cleanup"""
    if user_id not in active_extractions:
        await update.callback_query.message.reply_text(
            "⚠️ No active extraction found. Please upload a file first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    extraction_data = active_extractions[user_id]
    extract_dir = extraction_data.get("extract_dir")
    
    # Delete extraction directory
    result = FileManager.delete_extraction_dir(extract_dir)
    
    if result.get("success", False):
        await update.callback_query.message.reply_text(
            "🗑️ Extraction files deleted. You can now upload another file.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.callback_query.message.reply_text(
            f"❌ Error deleting files: {result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Clean up
    del active_extractions[user_id] 