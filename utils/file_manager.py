import os
import aiofiles
import shutil
import time
import uuid
from pathlib import Path
from config.config import TEMP_DIR, MAX_FILE_SIZE_BYTES, logger

class FileManager:
    """Class to handle file download and management operations"""
    
    @staticmethod
    async def download_file(bot, file_id, user_id):
        """
        Download a file from Telegram
        
        Args:
            bot: Telegram bot instance
            file_id: ID of the file to download
            user_id: ID of the user who requested the download
            
        Returns:
            Dictionary with download results
        """
        try:
            # Create user-specific directory
            user_dir = os.path.join(TEMP_DIR, f"user_{user_id}")
            os.makedirs(user_dir, exist_ok=True)
            
            # Get file info
            file_info = await bot.get_file(file_id)
            file_path = file_info.file_path
            
            # Check file size
            if file_info.file_size > MAX_FILE_SIZE_BYTES:
                return {
                    "success": False,
                    "error": f"File size exceeds the maximum allowed ({MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB)"
                }
            
            # Create a unique filename
            file_name = os.path.basename(file_path)
            unique_id = str(uuid.uuid4())[:8]
            local_filename = f"{unique_id}_{file_name}"
            local_path = os.path.join(user_dir, local_filename)
            
            # Download the file
            await bot.download_file(file_path, local_path)
            
            return {
                "success": True,
                "file_path": local_path,
                "original_name": file_name,
                "size": os.path.getsize(local_path)
            }
        except Exception as e:
            logger.error(f"File download error: {str(e)}")
            return {
                "success": False,
                "error": f"Error downloading file: {str(e)}"
            }
    
    @staticmethod
    def create_extraction_dir(user_id, file_name):
        """Create a directory for extracted files"""
        try:
            # Create a unique directory for extraction
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            unique_id = str(uuid.uuid4())[:8]
            extract_dir = os.path.join(TEMP_DIR, f"user_{user_id}", f"extract_{base_name}_{unique_id}")
            os.makedirs(extract_dir, exist_ok=True)
            
            return {
                "success": True,
                "extract_dir": extract_dir
            }
        except Exception as e:
            logger.error(f"Error creating extraction directory: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def list_extracted_files(extract_dir):
        """
        List all files in the extraction directory
        
        Returns a structured representation of the directory
        """
        try:
            result = {
                "success": True,
                "files": [],
                "dirs": [],
                "total_size": 0,
                "file_count": 0
            }
            
            # Get all files recursively
            for root, dirs, files in os.walk(extract_dir):
                # Add directories (relative to extract_dir)
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(dir_path, extract_dir)
                    result["dirs"].append({
                        "name": dir_name,
                        "path": rel_path,
                        "full_path": dir_path
                    })
                
                # Add files (relative to extract_dir)
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(file_path, extract_dir)
                    size = os.path.getsize(file_path)
                    
                    result["files"].append({
                        "name": file_name,
                        "path": rel_path,
                        "full_path": file_path,
                        "size": size
                    })
                    
                    result["total_size"] += size
                    result["file_count"] += 1
            
            return result
        except Exception as e:
            logger.error(f"Error listing extracted files: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_file_path(extract_dir, file_path):
        """Get the full path for a file in the extraction directory"""
        try:
            full_path = os.path.join(extract_dir, file_path)
            
            # Security check: make sure the path is within the extract_dir
            if not os.path.abspath(full_path).startswith(os.path.abspath(extract_dir)):
                return {
                    "success": False,
                    "error": "Invalid file path (path traversal attempt)"
                }
            
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": "File not found"
                }
            
            return {
                "success": True,
                "file_path": full_path
            }
        except Exception as e:
            logger.error(f"Error getting file path: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def cleanup_user_files(user_id):
        """Delete all files for a specific user"""
        try:
            user_dir = os.path.join(TEMP_DIR, f"user_{user_id}")
            
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir, ignore_errors=True)
                
            return {"success": True}
        except Exception as e:
            logger.error(f"Error cleaning up user files: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_extraction_dir(extract_dir):
        """Delete an extraction directory"""
        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
                
            return {"success": True}
        except Exception as e:
            logger.error(f"Error deleting extraction directory: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 