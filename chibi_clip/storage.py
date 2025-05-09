"""
S3 Storage integration for Dog Reels application.
This module handles uploading and managing files in S3.
"""

import os
import uuid
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse

class S3Storage:
    """Storage handler for AWS S3."""
    
    def __init__(self, bucket_name=None, aws_region=None):
        """
        Initialize S3 storage handler.
        
        Args:
            bucket_name: S3 bucket name (defaults to env var S3_BUCKET_NAME)
            aws_region: AWS region (defaults to env var AWS_REGION)
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        self.region = aws_region or os.getenv('AWS_REGION', 'us-east-1')
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name not provided. Set S3_BUCKET_NAME environment variable.")
        
        # Initialize S3 client
        self.s3 = boto3.client('s3')
        
        # Public URL format
        self.url_format = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{{}}"
    
    def upload_file(self, file_path, key_prefix='uploads'):
        """
        Upload a file to S3 bucket.
        
        Args:
            file_path: Path to the local file
            key_prefix: Prefix for the S3 key (folder)
            
        Returns:
            URL of the uploaded file
        """
        try:
            # Generate a unique filename with original extension
            _, ext = os.path.splitext(file_path)
            unique_name = f"{uuid.uuid4().hex}{ext}"
            
            # Create the full S3 key
            key = f"{key_prefix}/{unique_name}"
            
            # Upload the file
            self.s3.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=key,
                ExtraArgs={'ContentType': self._get_content_type(ext)}
            )
            
            # Return the URL
            return self.url_format.format(key), key
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            raise
    
    def upload_data(self, file_data, filename, key_prefix='uploads'):
        """
        Upload file data directly to S3.
        
        Args:
            file_data: Binary data to upload
            filename: Original filename for content type detection
            key_prefix: Prefix for the S3 key (folder)
            
        Returns:
            URL of the uploaded file
        """
        try:
            # Generate a unique filename with original extension
            _, ext = os.path.splitext(filename)
            unique_name = f"{uuid.uuid4().hex}{ext}"
            
            # Create the full S3 key
            key = f"{key_prefix}/{unique_name}"
            
            # Upload the data
            self.s3.put_object(
                Body=file_data,
                Bucket=self.bucket_name,
                Key=key,
                ContentType=self._get_content_type(ext)
            )
            
            # Return the URL
            return self.url_format.format(key), key
        except ClientError as e:
            print(f"Error uploading data to S3: {e}")
            raise
    
    def delete_file(self, url_or_key):
        """
        Delete a file from S3.
        
        Args:
            url_or_key: Either the full URL or just the S3 key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract the key if a URL was provided
            if url_or_key.startswith("http"):
                parsed = urlparse(url_or_key)
                key = parsed.path.lstrip('/')
            else:
                key = url_or_key
            
            # Delete the object
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            print(f"Error deleting file from S3: {e}")
            return False
    
    def _get_content_type(self, extension):
        """
        Determine the content type based on file extension.
        
        Args:
            extension: File extension including the dot
            
        Returns:
            MIME type as string
        """
        extension = extension.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
        }
        return content_types.get(extension, 'application/octet-stream') 