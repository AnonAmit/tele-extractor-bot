import os
from dotenv import load_dotenv
import logging
from pathlib import Path

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables")

# File Handling Settings
TEMP_DIR = os.getenv("TEMP_DIR", "./temp_files")
CLEANUP_TIME = int(os.getenv("CLEANUP_TIME", "24"))  # In hours
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100"))  # In MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE * 1024 * 1024  # Convert to bytes

# Create temp directory if it doesn't exist
Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)

# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Archive formats supported
SUPPORTED_FORMATS = [
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', 
    '.tar.gz', '.tar.bz2', '.tar.xz'
]

# Messages and UI text
WELCOME_MESSAGE = """
Welcome to File Extractor Bot! 🎉

Send me any compressed file and I'll extract its contents for you.
Supported formats: zip, rar, 7z, tar, gz, bz2, and more.

💡 *Features*:
- Extract any compatible archive
- View extraction progress in real-time
- Download extracted files individually or as a group
- Handles password-protected archives

Simply send me a file to get started!
"""

HELP_MESSAGE = """
*How to use this bot:*

1️⃣ Send me any compressed file (up to {max_size}MB)
2️⃣ I'll automatically start the extraction process
3️⃣ You'll see real-time progress updates
4️⃣ Once complete, you can download individual files or all files

*Supported formats:*
ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ and combinations

*Commands:*
/start - Start the bot
/help - Show this help message
/cancel - Cancel ongoing extraction
/cleanup - Delete your temporary files

*Need assistance?*
If you encounter any issues, please try again or contact the bot admin.
"""

# UI Button texts
BUTTONS = {
    "DOWNLOAD_ALL": "📦 Download All Files",
    "DELETE": "🗑️ Delete Files",
    "EXTRACT_ANOTHER": "📤 Extract Another File",
    "PASSWORD": "🔑 Enter Password",
    "CANCEL": "❌ Cancel",
}

# Status messages
STATUS = {
    "DOWNLOADING": "⬇️ Downloading your file...",
    "PREPARING": "🔍 Preparing for extraction...",
    "EXTRACTING": "📤 Extracting files...",
    "COMPLETE": "✅ Extraction complete!",
    "ERROR": "❌ An error occurred",
    "CANCELED": "🛑 Process canceled",
    "PASSWORD_REQUIRED": "🔒 This archive is password-protected",
    "PASSWORD_INCORRECT": "❌ Incorrect password. Please try again.",
    "CLEANUP": "🧹 Cleaning up temporary files...",
} 