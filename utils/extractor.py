import os
import shutil
import tempfile
import zipfile
import patoolib
import time
import threading
from pathlib import Path
from tqdm import tqdm
from config.config import TEMP_DIR, logger, SUPPORTED_FORMATS

class ExtractionProgress:
    """Class to track extraction progress"""
    def __init__(self):
        self.total_files = 0
        self.current_file = ""
        self.extracted_files = 0
        self.percentage = 0
        self.is_complete = False
        self.is_error = False
        self.error_message = ""
        self.is_password_required = False
        self.is_canceled = False
        self.start_time = time.time()
        self.total_size = 0
        self.extracted_size = 0
        
    def update(self, file_name=None, increment=True):
        """Update extraction progress"""
        if file_name:
            self.current_file = file_name
        
        if increment:
            self.extracted_files += 1
            
        if self.total_files > 0:
            self.percentage = min(int((self.extracted_files / self.total_files) * 100), 100)
        
        return self

class Extractor:
    """Class to handle file extraction operations"""
    def __init__(self, file_path, extract_dir, password=None):
        self.file_path = file_path
        self.extract_dir = extract_dir
        self.password = password
        self.progress = ExtractionProgress()
        self.stop_event = threading.Event()
        
    def is_archive(self):
        """Check if the file is a recognized archive format"""
        file_ext = Path(self.file_path).suffix.lower()
        # Handle special cases like .tar.gz
        if file_ext == '.gz' and self.file_path.lower().endswith('.tar.gz'):
            file_ext = '.tar.gz'
        elif file_ext == '.bz2' and self.file_path.lower().endswith('.tar.bz2'):
            file_ext = '.tar.bz2'
        elif file_ext == '.xz' and self.file_path.lower().endswith('.tar.xz'):
            file_ext = '.tar.xz'
            
        return file_ext in SUPPORTED_FORMATS
    
    def get_archive_info(self):
        """Get information about the archive"""
        try:
            archive_info = {
                "format": Path(self.file_path).suffix.lower(),
                "size": os.path.getsize(self.file_path),
                "file_name": os.path.basename(self.file_path)
            }
            
            # Handle special cases like .tar.gz
            if archive_info["format"] == '.gz' and self.file_path.lower().endswith('.tar.gz'):
                archive_info["format"] = '.tar.gz'
            elif archive_info["format"] == '.bz2' and self.file_path.lower().endswith('.tar.bz2'):
                archive_info["format"] = '.tar.bz2'
            elif archive_info["format"] == '.xz' and self.file_path.lower().endswith('.tar.xz'):
                archive_info["format"] = '.tar.xz'
                
            # Try to get file count for supported formats
            if archive_info["format"] == '.zip':
                with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                    archive_info["file_count"] = len(zip_ref.namelist())
                    # Check if password-protected
                    for zip_info in zip_ref.infolist():
                        if zip_info.flag_bits & 0x1:
                            archive_info["password_protected"] = True
                            break
            else:
                # For other formats, we'll estimate during extraction
                archive_info["file_count"] = -1  # Unknown at this point
                
            return archive_info
        except Exception as e:
            logger.error(f"Error getting archive info: {str(e)}")
            return {
                "format": "unknown",
                "size": os.path.getsize(self.file_path),
                "file_name": os.path.basename(self.file_path),
                "file_count": -1
            }
    
    def count_files_in_dir(self, directory):
        """Count files in a directory recursively"""
        count = 0
        for root, dirs, files in os.walk(directory):
            count += len(files)
        return count
    
    def calculate_dir_size(self, directory):
        """Calculate the total size of files in a directory"""
        total_size = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
        return total_size
    
    def extract(self, progress_callback=None):
        """
        Extract the archive file
        
        Args:
            progress_callback: Callback function to report progress
            
        Returns:
            Dictionary with extraction results
        """
        try:
            # Create extraction directory if it doesn't exist
            os.makedirs(self.extract_dir, exist_ok=True)
            
            # Get archive info first
            archive_info = self.get_archive_info()
            self.progress.total_files = archive_info.get("file_count", -1)
            
            # Special handling for zip files
            if archive_info["format"] == '.zip':
                result = self._extract_zip(progress_callback)
            else:
                # Use patool for other archive types
                result = self._extract_with_patool(progress_callback)
                
            # Calculate total extracted size
            self.progress.total_size = self.calculate_dir_size(self.extract_dir)
            
            # If we didn't know file count before, update it now
            if self.progress.total_files == -1:
                self.progress.total_files = self.count_files_in_dir(self.extract_dir)
                self.progress.extracted_files = self.progress.total_files
                self.progress.percentage = 100
                
            self.progress.is_complete = True
            
            return {
                "success": True,
                "extract_dir": self.extract_dir,
                "total_files": self.progress.total_files,
                "total_size": self.progress.total_size,
                "duration": time.time() - self.progress.start_time
            }
            
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            self.progress.is_error = True
            self.progress.error_message = str(e)
            
            if "password" in str(e).lower():
                self.progress.is_password_required = True
            
            return {
                "success": False,
                "error": str(e),
                "password_required": self.progress.is_password_required
            }
    
    def _extract_zip(self, progress_callback):
        """Extract ZIP files with progress tracking"""
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                # Check if password protected and password provided
                if any(zip_info.flag_bits & 0x1 for zip_info in zip_ref.infolist()):
                    if not self.password:
                        self.progress.is_password_required = True
                        return {
                            "success": False,
                            "error": "Password required",
                            "password_required": True
                        }
                
                # Get file list
                files = zip_ref.namelist()
                self.progress.total_files = len(files)
                
                # Extract files with progress tracking
                for i, file in enumerate(files):
                    if self.stop_event.is_set():
                        self.progress.is_canceled = True
                        return {"success": False, "error": "Extraction canceled"}
                    
                    # Zip Slip prevention: sanitize filename
                    safe_path = os.path.normpath(file)
                    if safe_path.startswith("..") or safe_path.startswith("/"):
                        logger.warning(f"Rejected path traversal attempt: {file}")
                        raise Exception(f"Unsafe file path in archive: {file}")
                    
                    self.progress.current_file = file
                    self.progress.extracted_files = i + 1
                    self.progress.percentage = int((i + 1) / len(files) * 100)
                    
                    # Extract the file
                    try:
                        if self.password:
                            zip_ref.extract(file, self.extract_dir, pwd=self.password.encode())
                        else:
                            zip_ref.extract(file, self.extract_dir)
                    except Exception as e:
                        if "password" in str(e).lower():
                            self.progress.is_password_required = True
                            return {
                                "success": False, 
                                "error": "Incorrect password", 
                                "password_required": True
                            }
                        else:
                            raise
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(self.progress)
                
                return {"success": True}
                
        except zipfile.BadZipFile as e:
            logger.error(f"Bad ZIP file: {str(e)}")
            return {"success": False, "error": f"Invalid ZIP file: {str(e)}"}
        except Exception as e:
            logger.error(f"ZIP extraction error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_with_patool(self, progress_callback):
        """Extract various archive formats using patool"""
        try:
            # Use patool for extraction
            patoolib.extract_archive(
                self.file_path, 
                outdir=self.extract_dir,
                password=self.password,
                interactive=False
            )
            
            # Since patool doesn't provide progress, estimate by counting files afterwards
            total_files = self.count_files_in_dir(self.extract_dir)
            self.progress.total_files = total_files
            self.progress.extracted_files = total_files
            self.progress.percentage = 100
            
            # Call progress callback with final state
            if progress_callback:
                progress_callback(self.progress)
                
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Patool extraction error: {str(e)}")
            error_msg = str(e).lower()
            
            if "password" in error_msg:
                self.progress.is_password_required = True
                return {
                    "success": False,
                    "error": "Password required or incorrect",
                    "password_required": True
                }
            else:
                return {"success": False, "error": str(e)}
    
    def cancel(self):
        """Cancel the extraction process"""
        self.stop_event.set()
        self.progress.is_canceled = True
        
    def create_zip_from_directory(self, output_path=None):
        """Create a zip file from the extracted directory"""
        try:
            if not output_path:
                base_name = os.path.splitext(os.path.basename(self.file_path))[0]
                output_path = os.path.join(TEMP_DIR, f"{base_name}_recompressed.zip")
            
            shutil.make_archive(
                os.path.splitext(output_path)[0], 
                'zip', 
                self.extract_dir
            )
            
            return {
                "success": True,
                "zip_path": f"{os.path.splitext(output_path)[0]}.zip"
            }
        except Exception as e:
            logger.error(f"Error creating zip: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def cleanup_old_files(max_age_hours=24):
        """Clean up old temporary files"""
        try:
            current_time = time.time()
            for root, dirs, files in os.walk(TEMP_DIR):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    # Skip if it's the root temp directory
                    if dir_path == TEMP_DIR:
                        continue
                    
                    # Check if directory is older than max_age_hours
                    dir_modified_time = os.path.getmtime(dir_path)
                    if current_time - dir_modified_time > max_age_hours * 3600:
                        logger.info(f"Cleaning up old directory: {dir_path}")
                        shutil.rmtree(dir_path, ignore_errors=True)
                        
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    # Check if file is older than max_age_hours
                    file_modified_time = os.path.getmtime(file_path)
                    if current_time - file_modified_time > max_age_hours * 3600:
                        logger.info(f"Cleaning up old file: {file_path}")
                        os.remove(file_path)
                        
            return {"success": True}
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def human_readable_size(size_bytes):
        """Convert bytes to human-readable format"""
        if size_bytes == 0:
            return "0B"
        
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size_bytes >= 1024 and i < len(size_name) - 1:
            size_bytes /= 1024
            i += 1
            
        return f"{size_bytes:.2f} {size_name[i]}" 