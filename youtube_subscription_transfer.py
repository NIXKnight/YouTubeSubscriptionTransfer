#!/usr/bin/env python3
"""
YouTube Subscription Transfer Script

This script transfers YouTube channel subscriptions from one account to another.
It uses the YouTube Data API v3 to:
1. Extract all subscriptions from the source account
2. Save the subscription data to a JSON file
3. Subscribe the destination account to those same channels

Requirements:
- Google Cloud Project with YouTube Data API v3 enabled
- OAuth2 credentials (credentials.json)
- Two YouTube accounts for source and destination
"""

import os
import json
import time
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# YouTube Data API v3 scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly',
          'https://www.googleapis.com/auth/youtube']

# API service name and version
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# Configuration
CREDENTIALS_FILE = 'credentials.json'
SUBSCRIPTIONS_DATA_FILE = 'subscriptions_backup.json'
PROGRESS_FILE = 'transfer_progress.json'
LOG_FILE = 'youtube_transfer.log'

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class YouTubeSubscriptionTransfer:
    """Main class for handling YouTube subscription transfers."""

    def __init__(self, resume_mode=False, wait_time=0.5):
        """Initialize the YouTube subscription transfer tool."""
        self.youtube_service = None
        self.credentials = None
        self.resume_mode = resume_mode
        self.wait_time = wait_time

    def authenticate(self, account_name: str) -> bool:
        """
        Authenticate with YouTube Data API using OAuth2.

        Args:
            account_name: Name identifier for the account (e.g., 'source', 'destination')

        Returns:
            bool: True if authentication successful, False otherwise
        """
        token_file = f'token_{account_name}.json'
        creds = None

        # Check if token file exists
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # If there are no valid credentials, run the OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info(f"Refreshed credentials for {account_name}")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials for {account_name}: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error(f"Credentials file {CREDENTIALS_FILE} not found!")
                    logger.error("Please download credentials.json from Google Cloud Console")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info(f"Completed OAuth flow for {account_name}")

            # Save credentials for future use
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
                logger.info(f"Saved credentials for {account_name}")

        self.credentials = creds
        self.youtube_service = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
        logger.info(f"Successfully authenticated {account_name} account")
        return True

    def get_channel_info(self) -> Optional[Dict]:
        """
        Get information about the authenticated channel.

        Returns:
            Dict: Channel information or None if failed
        """
        try:
            request = self.youtube_service.channels().list(
                part='snippet',
                mine=True
            )
            response = request.execute()

            if response['items']:
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet'].get('description', ''),
                    'customUrl': channel['snippet'].get('customUrl', '')
                }
        except HttpError as e:
            logger.error(f"Failed to get channel info: {e}")

        return None

    def extract_subscriptions(self) -> List[Dict]:
        """
        Extract all subscriptions from the authenticated account.

        Returns:
            List[Dict]: List of subscription data
        """
        subscriptions = []
        next_page_token = None

        logger.info("Starting subscription extraction...")

        while True:
            try:
                request = self.youtube_service.subscriptions().list(
                    part='snippet',
                    mine=True,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()

                for item in response.get('items', []):
                    subscription_data = {
                        'channel_id': item['snippet']['resourceId']['channelId'],
                        'channel_title': item['snippet']['title'],
                        'channel_description': item['snippet'].get('description', ''),
                        'published_at': item['snippet']['publishedAt'],
                        'subscription_id': item['id']
                    }
                    subscriptions.append(subscription_data)

                logger.info(f"Extracted {len(response.get('items', []))} subscriptions (Total: {len(subscriptions)})")

                # Check if there are more pages
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break

                # Add small delay to respect rate limits
                time.sleep(min(0.1, self.wait_time))

            except HttpError as e:
                logger.error(f"Error extracting subscriptions: {e}")
                break

        logger.info(f"Successfully extracted {len(subscriptions)} total subscriptions")
        return subscriptions

    def save_subscriptions(self, subscriptions: List[Dict], filename: str = None) -> bool:
        """
        Save subscription data to JSON file.

        Args:
            subscriptions: List of subscription data
            filename: Optional custom filename

        Returns:
            bool: True if saved successfully
        """
        if filename is None:
            filename = SUBSCRIPTIONS_DATA_FILE

        try:
            backup_data = {
                'export_date': datetime.now().isoformat(),
                'total_subscriptions': len(subscriptions),
                'subscriptions': subscriptions
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Successfully saved {len(subscriptions)} subscriptions to {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to save subscriptions: {e}")
            return False

    def load_subscriptions(self, filename: str = None) -> List[Dict]:
        """
        Load subscription data from JSON file.

        Args:
            filename: Optional custom filename

        Returns:
            List[Dict]: List of subscription data
        """
        if filename is None:
            filename = SUBSCRIPTIONS_DATA_FILE

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            subscriptions = data.get('subscriptions', [])
            logger.info(f"Successfully loaded {len(subscriptions)} subscriptions from {filename}")
            return subscriptions

        except Exception as e:
            logger.error(f"Failed to load subscriptions: {e}")
            return []

    def subscribe_to_channel(self, channel_id: str, channel_title: str, max_retries: int = 3) -> bool:
        """
        Subscribe to a specific channel with retry logic.

        Args:
            channel_id: YouTube channel ID
            channel_title: Channel title for logging
            max_retries: Maximum number of retry attempts

        Returns:
            bool: True if successful
        """
        for attempt in range(max_retries):
            try:
                request_body = {
                    'snippet': {
                        'resourceId': {
                            'kind': 'youtube#channel',
                            'channelId': channel_id
                        }
                    }
                }

                request = self.youtube_service.subscriptions().insert(
                    part='snippet',
                    body=request_body
                )
                response = request.execute()

                logger.info(f"Successfully subscribed to: {channel_title}")
                return True

            except HttpError as e:
                error_details = e.error_details[0] if e.error_details else {}
                reason = error_details.get('reason', 'unknown')

                if reason == 'subscriptionDuplicate':
                    logger.info(f"Already subscribed to: {channel_title}")
                    return True
                elif reason == 'channelNotFound':
                    logger.warning(f"Channel not found: {channel_title}")
                    return False  # Don't retry for missing channels
                elif reason == 'quotaExceeded':
                    logger.error("API quota exceeded. Please try again later.")
                    return False  # Don't retry quota exceeded immediately
                elif reason in ['rateLimitExceeded', 'userRateLimitExceeded']:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                        logger.warning(f"Rate limit hit for {channel_title}. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded for {channel_title} after {max_retries} attempts")
                        return False
                else:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # Linear backoff: 2s, 4s, 6s
                        logger.warning(f"Error subscribing to {channel_title}: {reason}. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Failed to subscribe to {channel_title} after {max_retries} attempts: {e}")

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Unexpected error subscribing to {channel_title}: {e}. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Unexpected error subscribing to {channel_title} after {max_retries} attempts: {e}")

        return False

    def save_progress(self, index: int, channel_id: str, total: int) -> None:
        """
        Save current progress to file.

        Args:
            index: Current subscription index
            channel_id: Current channel ID being processed
            total: Total number of subscriptions
        """
        progress_data = {
            'last_processed_index': index,
            'last_channel_id': channel_id,
            'total_subscriptions': total,
            'timestamp': datetime.now().isoformat()
        }

        try:
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save progress: {e}")

    def load_progress(self) -> Dict:
        """
        Load progress from file.

        Returns:
            Dict: Progress data or empty dict if no progress found
        """
        try:
            if os.path.exists(PROGRESS_FILE):
                with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load progress: {e}")

        return {}

    def clear_progress(self) -> None:
        """
        Clear the progress file.
        """
        try:
            if os.path.exists(PROGRESS_FILE):
                os.remove(PROGRESS_FILE)
                logger.info("Progress file cleared")
        except Exception as e:
            logger.warning(f"Failed to clear progress: {e}")

    def import_subscriptions(self, subscriptions: List[Dict]) -> Dict[str, int]:
        """
        Subscribe to all channels from the subscription list.

        Args:
            subscriptions: List of subscription data

        Returns:
            Dict: Statistics about the import process
        """
        stats = {
            'total': len(subscriptions),
            'successful': 0,
            'failed': 0,
            'already_subscribed': 0,
            'skipped': 0
        }

        # Load progress if in resume mode
        start_index = 0
        if self.resume_mode:
            progress = self.load_progress()
            if progress:
                start_index = progress.get('last_processed_index', 0) + 1
                logger.info(f"Resuming from index {start_index} (channel: {progress.get('last_channel_id', 'unknown')})")
                stats['skipped'] = start_index
            else:
                logger.info("No previous progress found, starting from beginning")
        else:
            # Clear any existing progress if not in resume mode
            self.clear_progress()

        logger.info(f"Starting import of {stats['total']} subscriptions (starting from index {start_index})...")

        for i, subscription in enumerate(subscriptions):
            # Skip already processed subscriptions in resume mode
            if i < start_index:
                continue

            channel_id = subscription['channel_id']
            channel_title = subscription['channel_title']

            logger.info(f"Processing {i+1}/{stats['total']}: {channel_title}")

            # Save progress before processing
            self.save_progress(i, channel_id, stats['total'])

            # Check if already subscribed first
            if self.is_already_subscribed(channel_id):
                stats['already_subscribed'] += 1
                logger.info(f"Already subscribed to: {channel_title}")
                continue

            # Attempt to subscribe
            if self.subscribe_to_channel(channel_id, channel_title):
                stats['successful'] += 1
            else:
                stats['failed'] += 1

            # Rate limiting - pause between requests
            time.sleep(self.wait_time)

            # Log progress every 10 subscriptions
            processed = i + 1 - start_index
            if processed % 10 == 0:
                remaining = stats['total'] - (i + 1)
                logger.info(f"Progress: {i+1}/{stats['total']} processed, {remaining} remaining")

        # Clear progress file on successful completion
        self.clear_progress()

        logger.info("Import completed!")
        logger.info(f"Results: {stats['successful']} successful, {stats['failed']} failed, "
                   f"{stats['already_subscribed']} already subscribed, {stats['skipped']} skipped")

        return stats

    def is_already_subscribed(self, channel_id: str) -> bool:
        """
        Check if already subscribed to a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            bool: True if already subscribed
        """
        try:
            request = self.youtube_service.subscriptions().list(
                part='snippet',
                forChannelId=channel_id,
                mine=True
            )
            response = request.execute()
            return len(response.get('items', [])) > 0

        except HttpError:
            return False


def main():
    """Main function to run the YouTube subscription transfer tool."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='YouTube Subscription Transfer Tool')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from last processed subscription')
    parser.add_argument('--interactive', action='store_true', default=True,
                       help='Run in interactive mode (default)')
    parser.add_argument('--wait', type=float, default=0.5, metavar='SECONDS',
                       help='Wait time in seconds between API calls (default: 0.5)')
    args = parser.parse_args()

    # Validate wait time
    if args.wait < 0:
        print("Error: Wait time cannot be negative")
        return
    if args.wait > 60:
        print("Warning: Wait time > 60 seconds may cause very slow imports")

    print("=== YouTube Subscription Transfer Tool ===")
    print("This tool helps transfer subscriptions between YouTube accounts.")
    if args.resume:
        print("[RESUME MODE ENABLED]")
    if args.wait != 0.5:
        print(f"[CUSTOM WAIT TIME: {args.wait}s between API calls]")
    print()

    transfer_tool = YouTubeSubscriptionTransfer(resume_mode=args.resume, wait_time=args.wait)

    # Check if there's existing progress
    existing_progress = transfer_tool.load_progress()

    while True:
        print("\nChoose an option:")
        print("1. Extract subscriptions from source account")
        print("2. Import subscriptions to destination account")
        if existing_progress and not args.resume:
            print("3. Resume previous import (recommended)")
            print("4. View saved subscription data")
            print("5. Clear saved progress")
            print("6. Exit")
        else:
            print("3. View saved subscription data")
            if existing_progress:
                print("4. Clear saved progress")
                print("5. Exit")
            else:
                print("4. Exit")

        max_choice = 6 if existing_progress and not args.resume else (5 if existing_progress else 4)
        choice = input(f"\nEnter your choice (1-{max_choice}): ").strip()

        if choice == '1':
            # Extract subscriptions
            print("\n--- Extracting Subscriptions ---")
            print("You'll be prompted to authenticate with your SOURCE account")
            input("Press Enter to continue...")

            if transfer_tool.authenticate('source'):
                channel_info = transfer_tool.get_channel_info()
                if channel_info:
                    print(f"Authenticated as: {channel_info['title']}")

                subscriptions = transfer_tool.extract_subscriptions()
                if subscriptions:
                    if transfer_tool.save_subscriptions(subscriptions):
                        print(f"\nSuccess! Extracted and saved {len(subscriptions)} subscriptions")
                    else:
                        print("Failed to save subscription data")
                else:
                    print("No subscriptions found or extraction failed")
            else:
                print("Authentication failed")

        elif choice == '2':
            # Import subscriptions
            print("\n--- Importing Subscriptions ---")

            # Load subscription data
            subscriptions = transfer_tool.load_subscriptions()
            if not subscriptions:
                print("No subscription data found. Please extract subscriptions first.")
                continue

            print(f"Found {len(subscriptions)} subscriptions to import")
            print("You'll be prompted to authenticate with your DESTINATION account")
            input("Press Enter to continue...")

            if transfer_tool.authenticate('destination'):
                channel_info = transfer_tool.get_channel_info()
                if channel_info:
                    print(f"Authenticated as: {channel_info['title']}")

                confirm = input(f"\nProceed to subscribe to {len(subscriptions)} channels? (y/n): ")
                if confirm.lower() == 'y':
                    stats = transfer_tool.import_subscriptions(subscriptions)
                    print(f"\nImport completed!")
                    print(f"Successful: {stats['successful']}")
                    print(f"Already subscribed: {stats['already_subscribed']}")
                    print(f"Failed: {stats['failed']}")
                else:
                    print("Import cancelled")
            else:
                print("Authentication failed")

        elif choice == '3' and existing_progress and not args.resume:
            # Resume previous import
            print("\n--- Resuming Previous Import ---")
            transfer_tool.resume_mode = True

            # Load subscription data
            subscriptions = transfer_tool.load_subscriptions()
            if not subscriptions:
                print("No subscription data found. Please extract subscriptions first.")
                continue

            progress = existing_progress
            last_index = progress.get('last_processed_index', -1)
            remaining = len(subscriptions) - (last_index + 1)

            print(f"Found {len(subscriptions)} total subscriptions")
            print(f"Last processed: {progress.get('last_channel_id', 'unknown')} (index {last_index})")
            print(f"Remaining to process: {remaining}")
            print("You'll be prompted to authenticate with your DESTINATION account")
            input("Press Enter to continue...")

            if transfer_tool.authenticate('destination'):
                channel_info = transfer_tool.get_channel_info()
                if channel_info:
                    print(f"Authenticated as: {channel_info['title']}")

                confirm = input(f"\nProceed to resume importing {remaining} remaining channels? (y/n): ")
                if confirm.lower() == 'y':
                    stats = transfer_tool.import_subscriptions(subscriptions)
                    print(f"\nImport completed!")
                    print(f"Successful: {stats['successful']}")
                    print(f"Already subscribed: {stats['already_subscribed']}")
                    print(f"Failed: {stats['failed']}")
                    print(f"Skipped: {stats['skipped']}")
                else:
                    print("Resume cancelled")
            else:
                print("Authentication failed")

        elif (choice == '3' and not existing_progress) or (choice == '4' and existing_progress and not args.resume) or (choice == '3' and args.resume):
            # View saved data
            print("\n--- Subscription Data ---")
            subscriptions = transfer_tool.load_subscriptions()
            if subscriptions:
                print(f"Total subscriptions: {len(subscriptions)}")
                if existing_progress:
                    last_index = existing_progress.get('last_processed_index', -1)
                    remaining = len(subscriptions) - (last_index + 1)
                    print(f"Progress: {last_index + 1}/{len(subscriptions)} processed, {remaining} remaining")
                print("\nFirst 10 channels:")
                for i, sub in enumerate(subscriptions[:10], 1):
                    print(f"{i}. {sub['channel_title']}")
                if len(subscriptions) > 10:
                    print(f"... and {len(subscriptions) - 10} more")
            else:
                print("No subscription data found")

        elif (choice == '5' and existing_progress and not args.resume) or (choice == '4' and existing_progress and args.resume):
            # Clear saved progress
            print("\n--- Clear Progress ---")
            confirm = input("Are you sure you want to clear saved progress? (y/n): ")
            if confirm.lower() == 'y':
                transfer_tool.clear_progress()
                existing_progress = None
                print("Progress cleared successfully.")
            else:
                print("Operation cancelled.")

        elif (choice == '6' and existing_progress and not args.resume) or (choice == '5' and existing_progress and args.resume) or (choice == '4' and not existing_progress):
            print("Goodbye!")
            break

        else:
            print(f"Invalid choice. Please enter 1-{max_choice}.")


if __name__ == '__main__':
    main()
