# Telegram File Extractor Bot

A modern, interactive Telegram bot for extracting compressed files .

## Features

- **Multi-format Support**: Extract ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ and many more archive formats
- **Interactive UI**: Beautiful, responsive interface with progress bars and status updates
- **Password Protection**: Support for password-protected archives
- **File Management**: Download individual files or all extracted content in one go
- **Progress Tracking**: Live updates on extraction progress with animated indicators
- **Security**: Automatic cleanup of temporary files for privacy and storage efficiency

## Demo

Here's how the bot works:

1. **Upload a file**: Send any supported compressed file to the bot
2. **View file info**: See details about your file (name, size, format)
3. **Watch extraction**: See real-time progress with a visual progress bar
4. **Browse files**: Navigate through extracted files with pagination
5. **Download options**: Get individual files or download everything as a recompressed archive

## Setup

### Prerequisites

- Python 3.8 or higher
- A Telegram bot token from @BotFather
- Required extraction tools (patool and dependent tools)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/AnonAmit/tele-extractor-bot.git
cd tele-extractor-bot
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Install additional system tools (needed for various archive formats):
```bash
# On Ubuntu/Debian
sudo apt-get update
sudo apt-get install unrar p7zip-full unzip

# On macOS
brew install p7zip unrar

# On Windows
# Download and install 7-Zip from https://www.7-zip.org/
# Download and install WinRAR from https://www.rarlab.com/
```

4. Create a `.env` file by copying the example:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your configuration:
```
BOT_TOKEN=your_bot_token_from_botfather
TEMP_DIR=./temp_files
CLEANUP_TIME=24
MAX_FILE_SIZE=100
```

### Running the Bot

```bash
python bot.py
```

For deployment, consider using a system service or Docker for better reliability.

## Commands

- `/start` - Start the bot
- `/help` - Show help information
- `/cancel` - Cancel ongoing extraction
- `/cleanup` - Delete your temporary files
- `/status` - Check bot status

## Project Structure

```
tele-extractor-bot/
├── bot.py                  # Main entry point
├── config/
│   └── config.py           # Configuration and constants
├── handlers/
│   ├── callback_handlers.py # Handlers for button interactions
│   ├── command_handlers.py  # Handlers for bot commands
│   └── file_handlers.py     # Handlers for file processing
├── utils/
│   ├── extractor.py         # Archive extraction functionality
│   ├── file_manager.py      # File download and management
│   └── ui_helper.py         # UI message formatting
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variables template
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Thanks to [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the Telegram Bot API wrapper
- [patool](https://github.com/wummel/patool) for the archive extraction capabilities