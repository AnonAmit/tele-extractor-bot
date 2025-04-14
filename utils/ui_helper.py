from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
import math
from config.config import BUTTONS, STATUS

class UIHelper:
    """Helper class for creating UI elements"""
    
    @staticmethod
    def create_file_info_message(file_info):
        """
        Create a message with file information
        
        Args:
            file_info: Dict with file info
            
        Returns:
            Formatted message string
        """
        file_size = file_info.get("size", 0)
        file_size_str = UIHelper.format_size(file_size)
        file_name = file_info.get("original_name", file_info.get("file_name", "Unknown"))
        file_format = file_info.get("format", "Unknown")
        
        message = (
            f"📁 *File Information*\n\n"
            f"*Name:* `{file_name}`\n"
            f"*Size:* {file_size_str}\n"
            f"*Format:* {file_format}\n\n"
            f"*Status:* {STATUS['PREPARING']}"
        )
        
        return message
    
    @staticmethod
    def create_extraction_progress_message(file_info, progress):
        """
        Create a message showing extraction progress
        
        Args:
            file_info: Dict with file info
            progress: ExtractionProgress object
            
        Returns:
            Formatted message string
        """
        file_name = file_info.get("original_name", file_info.get("file_name", "Unknown"))
        file_format = file_info.get("format", "Unknown")
        
        # Create progress bar
        progress_bar = UIHelper.create_progress_bar(progress.percentage)
        
        # Message for different states
        if progress.is_error:
            status = f"{STATUS['ERROR']}\n{progress.error_message}"
        elif progress.is_password_required:
            status = STATUS['PASSWORD_REQUIRED']
        elif progress.is_canceled:
            status = STATUS['CANCELED']
        elif progress.is_complete:
            status = STATUS['COMPLETE']
        else:
            status = f"{STATUS['EXTRACTING']} ({progress.percentage}%)"
            
        current_file = progress.current_file
        if len(current_file) > 30:
            current_file = "..." + current_file[-27:]
            
        message = (
            f"📁 *Extracting:* `{file_name}`\n"
            f"*Format:* {file_format}\n\n"
            f"*Progress:* {progress.percentage}%\n"
            f"{progress_bar}\n"
            f"*Current File:* `{current_file}`\n"
            f"*Files Extracted:* {progress.extracted_files}"
        )
        
        if progress.total_files > 0:
            message += f"/{progress.total_files}"
            
        message += f"\n\n*Status:* {status}"
        
        return message
    
    @staticmethod
    def create_extraction_complete_message(file_info, extraction_result):
        """
        Create a message showing extraction completion
        
        Args:
            file_info: Dict with file info
            extraction_result: Dict with extraction results
            
        Returns:
            Formatted message string
        """
        file_name = file_info.get("original_name", file_info.get("file_name", "Unknown"))
        file_format = file_info.get("format", "Unknown")
        
        total_files = extraction_result.get("total_files", 0)
        total_size = extraction_result.get("total_size", 0)
        total_size_str = UIHelper.format_size(total_size)
        duration = extraction_result.get("duration", 0)
        duration_str = UIHelper.format_duration(duration)
        
        message = (
            f"✅ *Extraction Complete!*\n\n"
            f"*Original File:* `{file_name}`\n"
            f"*Format:* {file_format}\n\n"
            f"*Files Extracted:* {total_files}\n"
            f"*Total Size:* {total_size_str}\n"
            f"*Duration:* {duration_str}\n\n"
            f"Use the buttons below to download files or perform other actions."
        )
        
        return message
    
    @staticmethod
    def create_file_list_message(file_list_result, page=1, per_page=5):
        """
        Create a message showing a list of extracted files
        
        Args:
            file_list_result: Dict with file list from FileManager
            page: Current page number
            per_page: Files per page
            
        Returns:
            Tuple of (message string, keyboard markup)
        """
        if not file_list_result.get("success", False):
            return f"❌ Error listing files: {file_list_result.get('error', 'Unknown error')}", None
            
        files = file_list_result.get("files", [])
        total_files = len(files)
        total_pages = math.ceil(total_files / per_page)
        
        if total_files == 0:
            return "No files found in the extraction directory.", None
        
        # Calculate pagination
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_files)
        
        message = f"📂 *Extracted Files ({total_files} total)*\n\n"
        
        # Add files for current page
        for i, file in enumerate(files[start_idx:end_idx], start=start_idx+1):
            file_size = UIHelper.format_size(file.get("size", 0))
            file_name = file.get("name", "Unknown")
            
            message += f"{i}. `{file_name}` - {file_size}\n"
            
        message += f"\n*Page {page}/{total_pages}*"
        
        # Create keyboard with pagination and file buttons
        keyboard = []
        
        # File buttons for current page
        for i, file in enumerate(files[start_idx:end_idx], start=1):
            file_path = file.get("path", "")
            keyboard.append([
                InlineKeyboardButton(f"📄 {i}", callback_data=f"file:{file_path}")
            ])
            
        # Pagination buttons
        pagination_row = []
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton("◀️ Previous", callback_data=f"page:{page-1}")
            )
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton("Next ▶️", callback_data=f"page:{page+1}")
            )
            
        if pagination_row:
            keyboard.append(pagination_row)
            
        # Action buttons
        keyboard.append([
            InlineKeyboardButton(
                BUTTONS["DOWNLOAD_ALL"], 
                callback_data="download_all"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                BUTTONS["DELETE"], 
                callback_data="delete"
            ),
            InlineKeyboardButton(
                BUTTONS["EXTRACT_ANOTHER"], 
                callback_data="extract_another"
            )
        ])
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_password_request_keyboard():
        """Create keyboard for password request"""
        keyboard = [
            [
                InlineKeyboardButton(
                    BUTTONS["PASSWORD"], 
                    callback_data="enter_password"
                )
            ],
            [
                InlineKeyboardButton(
                    BUTTONS["CANCEL"], 
                    callback_data="cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_extraction_cancel_keyboard():
        """Create keyboard for extraction cancellation"""
        keyboard = [
            [
                InlineKeyboardButton(
                    BUTTONS["CANCEL"], 
                    callback_data="cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_progress_bar(percentage, length=10):
        """
        Create a text-based progress bar
        
        Args:
            percentage: Progress percentage (0-100)
            length: Length of the progress bar
            
        Returns:
            Text-based progress bar string
        """
        filled_length = int(length * percentage / 100)
        bar = '█' * filled_length + '▒' * (length - filled_length)
        return f"[{bar}]"
    
    @staticmethod
    def format_size(size_bytes):
        """
        Format bytes to human-readable size
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0B"
            
        size_names = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
            
        return f"{size_bytes:.2f} {size_names[i]}"
    
    @staticmethod
    def format_duration(seconds):
        """
        Format seconds to human-readable duration
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours" 