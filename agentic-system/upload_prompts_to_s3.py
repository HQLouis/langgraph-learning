#!/usr/bin/env python3
"""
Utility script for uploading worker prompts to AWS S3.

This script can be used by administrators to upload or update prompt files
in the S3 bucket. It can be integrated into an admin UI for prompt management.

Usage:
    python upload_prompts_to_s3.py [--prompt-type TYPE] [--dry-run]

Examples:
    # Upload all prompts
    python upload_prompts_to_s3.py

    # Upload specific prompt
    python upload_prompts_to_s3.py --prompt-type speech_vocabulary_worker

    # Dry run to see what would be uploaded
    python upload_prompts_to_s3.py --dry-run
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# S3 CONFIGURATION - Hardcoded for admin operations
# ============================================================================
S3_BUCKET_NAME = "prompt-repository"
S3_PROMPTS_PREFIX = "prompts/"
S3_REGION = "eu-central-1"


class PromptUploader:
    """Handles uploading prompts to S3."""

    # Map prompt types to their local content
    PROMPTS = {
        'speech_vocabulary_worker': None,
        'speech_grammar_worker': None,
        'speech_interaction_worker': None,
        'speech_comprehension_worker': None,
        'boredom_worker': None,
        'master_prompt': None,
    }

    # File names for S3
    FILE_NAMES = {
        'speech_vocabulary_worker': 'speech_vocabulary_worker.txt',
        'speech_grammar_worker': 'speech_grammar_worker.txt',
        'speech_interaction_worker': 'speech_interaction_worker.txt',
        'speech_comprehension_worker': 'speech_comprehension_worker.txt',
        'boredom_worker': 'boredom_worker.txt',
        'master_prompt': 'master_prompt.txt',
    }

    def __init__(self, dry_run: bool = False):
        """
        Initialize the uploader.

        :param dry_run: If True, don't actually upload, just show what would be done
        """
        self.dry_run = dry_run
        self.s3_client = None
        self._load_prompts()

    def _load_prompts(self):
        """Load prompts from worker_prompts.py and master_prompts.py."""
        try:
            # Import the local prompt constants
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from prompts import (
                speechVocabularyWorker_prompt,
                speechGrammarWorker_prompt,
                speechInteractionWorker_prompt,
                speechComprehensionWorker_prompt,
                boredomWorker_prompt
            )
            from master_prompts import master_prompt

            self.PROMPTS['speech_vocabulary_worker'] = speechVocabularyWorker_prompt
            self.PROMPTS['speech_grammar_worker'] = speechGrammarWorker_prompt
            self.PROMPTS['speech_interaction_worker'] = speechInteractionWorker_prompt
            self.PROMPTS['speech_comprehension_worker'] = speechComprehensionWorker_prompt
            self.PROMPTS['boredom_worker'] = boredomWorker_prompt
            self.PROMPTS['master_prompt'] = master_prompt

            logger.info("Successfully loaded all prompts from worker_prompts.py and master_prompts.py")
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            raise

    def _init_s3_client(self):
        """
        Initialize S3 client for upload operations.
        Uses unsigned requests (no credentials) for public bucket with anonymous write access.
        """
        if self.s3_client is not None:
            return

        try:
            import boto3
            from botocore import UNSIGNED
            from botocore.config import Config

            # Use unsigned requests for public bucket with anonymous write access
            self.s3_client = boto3.client(
                's3',
                region_name=S3_REGION,
                config=Config(signature_version=UNSIGNED)
            )

            logger.info(f"S3 client initialized for public bucket: {S3_BUCKET_NAME}")
            logger.info("Using unsigned requests (no credentials needed)")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise

    def upload_prompt(self, prompt_type: str) -> bool:
        """
        Upload a specific prompt to S3.

        :param prompt_type: Type of prompt to upload
        :return: True if successful, False otherwise
        """
        if prompt_type not in self.PROMPTS:
            logger.error(f"Unknown prompt type: {prompt_type}")
            return False

        prompt_content = self.PROMPTS[prompt_type]
        file_name = self.FILE_NAMES[prompt_type]
        s3_key = f"{S3_PROMPTS_PREFIX}{file_name}"

        if self.dry_run:
            logger.info(f"[DRY RUN] Would upload {len(prompt_content)} bytes to s3://{S3_BUCKET_NAME}/{s3_key}")
            return True

        try:
            self._init_s3_client()

            logger.info(f"Uploading {prompt_type} to s3://{S3_BUCKET_NAME}/{s3_key}")

            self.s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=prompt_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'prompt-type': prompt_type,
                    'uploaded-by': 'upload_prompts_to_s3.py'
                }
            )

            logger.info(f"✓ Successfully uploaded {prompt_type} ({len(prompt_content)} bytes)")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to upload {prompt_type}: {e}")
            return False

    def upload_all(self) -> Dict[str, bool]:
        """
        Upload all prompts to S3.

        :return: Dictionary mapping prompt types to success status
        """
        results = {}

        logger.info("=" * 70)
        logger.info("Starting upload of all prompts to S3")
        logger.info(f"Bucket: {S3_BUCKET_NAME}")
        logger.info(f"Prefix: {S3_PROMPTS_PREFIX}")
        logger.info(f"Region: {S3_REGION}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 70)

        for prompt_type in self.PROMPTS.keys():
            results[prompt_type] = self.upload_prompt(prompt_type)

        # Print summary
        logger.info("=" * 70)
        logger.info("Upload Summary:")
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info("=" * 70)

        return results

    def list_s3_prompts(self) -> list:
        """
        List all prompt files currently in S3.

        :return: List of S3 keys
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would list S3 objects")
            return []

        try:
            self._init_s3_client()

            response = self.s3_client.list_objects_v2(
                Bucket=S3_BUCKET_NAME,
                Prefix=S3_PROMPTS_PREFIX
            )

            if 'Contents' not in response:
                logger.info("No prompts found in S3")
                return []

            keys = [obj['Key'] for obj in response['Contents']]
            logger.info(f"Found {len(keys)} prompt files in S3:")
            for key in keys:
                size = next(obj['Size'] for obj in response['Contents'] if obj['Key'] == key)
                logger.info(f"  - {key} ({size} bytes)")

            return keys

        except Exception as e:
            logger.error(f"Failed to list S3 prompts: {e}")
            return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Upload worker prompts to AWS S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
S3 Configuration (hardcoded):
  Bucket: {S3_BUCKET_NAME}
  Prefix: {S3_PROMPTS_PREFIX}
  Region: {S3_REGION}

Examples:
  # Upload all prompts
  python upload_prompts_to_s3.py
  
  # Upload specific prompt
  python upload_prompts_to_s3.py --prompt-type speech_vocabulary_worker
  
  # Dry run to see what would be uploaded
  python upload_prompts_to_s3.py --dry-run
  
  # List current prompts in S3
  python upload_prompts_to_s3.py --list
        """
    )

    parser.add_argument(
        '--prompt-type',
        type=str,
        choices=['speech_vocabulary_worker', 'speech_grammar_worker',
                 'speech_interaction_worker', 'speech_comprehension_worker',
                 'boredom_worker', 'master_prompt'],
        help='Specific prompt type to upload (if not specified, uploads all)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be uploaded without actually uploading'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List current prompts in S3'
    )

    args = parser.parse_args()

    try:
        uploader = PromptUploader(dry_run=args.dry_run)

        if args.list:
            uploader.list_s3_prompts()
            return

        if args.prompt_type:
            # Upload specific prompt
            success = uploader.upload_prompt(args.prompt_type)
            sys.exit(0 if success else 1)
        else:
            # Upload all prompts
            results = uploader.upload_all()
            all_success = all(results.values())
            sys.exit(0 if all_success else 1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
