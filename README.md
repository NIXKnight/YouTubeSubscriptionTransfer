# YouTube Subscription Transfer Tool

A Python script that allows you to transfer YouTube channel subscriptions from one account to another using the YouTube Data API v3.

## Features

- **Extract Subscriptions**: Get a complete list of channels you're subscribed to
- **Backup Data**: Save subscription data to JSON format for portability
- **Import Subscriptions**: Subscribe a different account to the same channels
- **Smart Handling**: Automatically detects and skips already subscribed channels
- **Rate Limiting**: Built-in delays to respect YouTube API quotas
- **Comprehensive Logging**: Detailed logs of all operations
- **Error Handling**: Robust error handling for various scenarios

## Prerequisites

### 1. Google Cloud Project Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **YouTube Data API v3**:
   - Go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click on it and press "Enable"

### 2. OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application" as the application type
4. Give it a name (e.g., "YouTube Subscription Transfer")
5. Download the JSON file and rename it to `credentials.json`
6. Place `credentials.json` in the same directory as the script

### 3. Python Environment

- Python 3.7 or higher
- Virtual environment (recommended)

## Installation

```bash
# Clone or download the script files
# Navigate to the project directory

# Create virtual environment
python3 -m venv youtube_transfer_env

# Activate virtual environment
source youtube_transfer_env/bin/activate

# Install required packages
pip install -r requirements.txt
```

## Usage

### Basic Workflow

1. **Extract subscriptions from your source account**
2. **Import subscriptions to your destination account**

### Running the Script

```bash
# Make sure virtual environment is activated
source youtube_transfer_env/bin/activate

# Run the script
python youtube_subscription_transfer.py
```

### Step-by-Step Guide

#### Step 1: Extract Subscriptions

1. Run the script and choose option `1`
2. Your browser will open for OAuth authentication
3. Sign in with your **source account** (the account you want to copy subscriptions FROM)
4. Grant the required permissions
5. The script will extract all subscriptions and save them to `subscriptions_backup.json`

#### Step 2: Import Subscriptions

1. Run the script and choose option `2`
2. Your browser will open for OAuth authentication
3. Sign in with your **destination account** (the account you want to copy subscriptions TO)
4. Grant the required permissions
5. Confirm the import when prompted
6. The script will subscribe to all channels from the backup file

## File Structure

```
├── youtube_subscription_transfer.py    # Main script
├── requirements.txt                    # Python dependencies
├── credentials.json                    # OAuth2 credentials (you need to add this)
├── subscriptions_backup.json           # Generated subscription data
├── token_source.json                   # Generated auth token for source account
├── token_destination.json              # Generated auth token for destination account
├── youtube_transfer.log                # Operation logs
└── README.md                           # This file
```

## Configuration

### API Quotas

The YouTube Data API has daily quotas. The script includes rate limiting to stay within limits:
- Default quota: 10,000 units per day
- Each subscription operation costs ~50 units
- You can subscribe to ~200 channels per day with default quota

### Customization

You can modify these variables in the script:

```python
SUBSCRIPTIONS_DATA_FILE = 'subscriptions_backup.json'  # Backup filename
LOG_FILE = 'youtube_transfer.log'                      # Log filename
```

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**
   - Make sure `credentials.json` is in the same directory as the script
   - Verify you downloaded the correct OAuth2 credentials

2. **"quotaExceeded" error**
   - You've hit the daily API quota limit
   - Wait until the next day or request quota increase

3. **"subscriptionDuplicate" warnings**
   - This is normal - the script skips channels you're already subscribed to

4. **"channelNotFound" errors**
   - Some channels may have been deleted or made private
   - These errors are logged but don't stop the process

### Authentication Issues

- Delete token files (`token_source.json`, `token_destination.json`) to force re-authentication
- Make sure you're signing in with the correct Google account
- Check that your Google account has access to YouTube

### Rate Limiting

If you encounter rate limit errors:
- The script includes built-in delays between requests
- For large subscription lists, consider running in smaller batches
- Check your API quota usage in Google Cloud Console

## Security Notes

- Keep your `credentials.json` file secure and don't share it
- Token files contain access tokens - treat them as passwords
- The script only requests necessary permissions (read subscriptions, manage subscriptions)
- No subscription data is sent to external servers

## API Permissions

The script requests these YouTube API scopes:
- `https://www.googleapis.com/auth/youtube.readonly` - Read your subscriptions
- `https://www.googleapis.com/auth/youtube` - Manage your subscriptions

## Limitations

- Cannot transfer private/unlisted channels
- Subject to YouTube API quotas and rate limits
- Requires active internet connection
- Both accounts must have YouTube channels created

## License

This tool is provided as-is for educational and personal use. Please respect YouTube's Terms of Service and API usage policies.

## Support

For issues related to:
- **Google Cloud/API setup**: Check Google Cloud Console documentation
- **Script errors**: Check the log file (`youtube_transfer.log`) for detailed error messages
- **Rate limiting**: Monitor your API usage in Google Cloud Console

---

**Note**: This tool is not affiliated with YouTube or Google. Use responsibly and in accordance with YouTube's Terms of Service.
