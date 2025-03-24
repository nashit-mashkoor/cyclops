"""Google Cloud Storage wrapper for handling cloud storage operations."""

import os
from typing import List, Optional, Union
from google.cloud import storage
from google.cloud.storage import Blob


class GoogleCloudStorage:
    """A wrapper class for Google Cloud Storage operations.
    
    This class provides a high-level interface for common Google Cloud Storage
    operations like uploading, downloading, and managing files and directories.
    
    Args:
        bucket_id (Optional[str]): The ID of the Google Cloud Storage bucket.
        root_folder (Optional[str]): The root folder path in the bucket.
    """
    
    def __init__(self, bucket_id: Optional[str] = None, root_folder: Optional[str] = None):
        """Initialize the Google Cloud Storage wrapper.
        
        Args:
            bucket_id (Optional[str]): The ID of the Google Cloud Storage bucket.
            root_folder (Optional[str]): The root folder path in the bucket.
        """
        self.bucket_id = bucket_id
        self.root_folder = root_folder
        self.client = storage.Client()
        
    def update_bucket(self, bucket_id: str) -> None:
        """Update the bucket ID.
        
        Args:
            bucket_id (str): The new bucket ID.
        """
        self.bucket_id = bucket_id
        
    def get_bucket_name(self) -> Optional[str]:
        """Get the current bucket ID.
        
        Returns:
            Optional[str]: The current bucket ID.
        """
        return self.bucket_id
        
    def list_files(self, path: str, get_abs: bool = False, recurse: bool = False) -> List[str]:
        """List all files in the specified path.
        
        Args:
            path (str): The path to list files from.
            get_abs (bool): Whether to return absolute paths (gs://...).
            recurse (bool): Whether to recursively list files in subdirectories.
            
        Returns:
            List[str]: List of file paths.
        """
        delimiter = None if recurse else '/'
        blobs = self.client.list_blobs(self.bucket_id, prefix=path, delimiter=delimiter)
        return [
            f'gs://{self.bucket_id}/{blob.name}' if get_abs else blob.name
            for blob in blobs
            if not blob.name.endswith('/')
        ]
        
    def rename_file(self, file_name: str, new_name: str) -> str:
        """Rename a file in the bucket.
        
        Args:
            file_name (str): Current name of the file.
            new_name (str): New name for the file.
            
        Returns:
            str: The new file name.
        """
        bucket = self.client.bucket(self.bucket_id)
        blob = bucket.blob(file_name)
        new_blob = bucket.rename_blob(blob, new_name)
        return new_blob.name
        
    def copy_file(self, source_name: str, destination_name: str, delete_original: bool = False) -> str:
        """Copy a file to a new location.
        
        Args:
            source_name (str): Name of the source file.
            destination_name (str): Name for the destination file.
            delete_original (bool): Whether to delete the original file after copying.
            
        Returns:
            str: The name of the copied file.
        """
        bucket = self.client.bucket(self.bucket_id)
        source_file = bucket.blob(source_name)
        copied = bucket.copy_blob(source_file, bucket, destination_name)
        if delete_original:
            bucket.delete_blob(source_name)
        return copied.name
        
    def delete_file(self, file_name: str) -> None:
        """Delete a file from the bucket.
        
        Args:
            file_name (str): Name of the file to delete.
        """
        bucket = self.client.bucket(self.bucket_id)
        bucket.delete_blob(file_name)
        
    def is_file(self, file_name: str) -> bool:
        """Check if a file exists in the bucket.
        
        Args:
            file_name (str): Name of the file to check.
            
        Returns:
            bool: True if the file exists, False otherwise.
        """
        bucket = self.client.bucket(self.bucket_id)
        return Blob(bucket=bucket, name=file_name).exists(self.client)
        
    def is_dir(self, dir_name: str) -> bool:
        """Check if a directory exists in the bucket.
        
        Args:
            dir_name (str): Name of the directory to check.
            
        Returns:
            bool: True if the directory exists, False otherwise.
        """
        blobs = list(self.client.list_blobs(self.bucket_id, prefix=dir_name))
        return bool(blobs)
        
    def rmdir(self, dir_name: str) -> None:
        """Delete a directory and all its contents from the bucket.
        
        Args:
            dir_name (str): Name of the directory to delete.
        """
        bucket = self.client.bucket(self.bucket_id)
        for blob in bucket.list_blobs(prefix=dir_name):
            blob.delete()
            
    def mkdir(self, destination_folder_name: str) -> None:
        """Create a new directory in the bucket.
        
        Args:
            destination_folder_name (str): Name of the directory to create.
        """
        if not destination_folder_name.endswith('/'):
            destination_folder_name += '/'
        bucket = self.client.bucket(self.bucket_id)
        bucket.blob(destination_folder_name).upload_from_string('')
        
    def upload_from_memory(self, contents: Union[str, bytes], destination_file_name: str, 
                          content_type: Optional[str] = None) -> bool:
        """Upload content from memory to the bucket.
        
        Args:
            contents (Union[str, bytes]): The content to upload.
            destination_file_name (str): Name for the destination file.
            content_type (Optional[str]): The content type of the file.
            
        Returns:
            bool: True if upload was successful.
        """
        bucket = self.client.bucket(self.bucket_id)
        blob = bucket.blob(destination_file_name)
        blob.upload_from_string(contents, content_type=content_type)
        return True
        
    def upload_file_local(self, source_file_name: str, dest_file_path: str) -> None:
        """Upload a local file to the bucket.
        
        Args:
            source_file_name (str): Path to the local file.
            dest_file_path (str): Destination path in the bucket.
        """
        bucket = self.client.bucket(self.bucket_id)
        bucket.blob(dest_file_path).upload_from_filename(source_file_name)
        
    def upload_folder(self, source_folder_path: str, destination_path: str) -> bool:
        """Upload a local folder to the bucket.
        
        Args:
            source_folder_path (str): Path to the local folder.
            destination_path (str): Destination path in the bucket.
            
        Returns:
            bool: True if upload was successful.
        """
        if destination_path and not destination_path.endswith('/'):
            destination_path += '/'
            
        bucket = self.client.bucket(self.bucket_id)
        file_paths = [
            os.path.join(folder, f).replace('\\', '/')
            for folder, _, files in os.walk(source_folder_path)
            for f in files
        ]
        
        for file_path in file_paths:
            try:
                blob = bucket.blob(destination_path + file_path)
                blob.upload_from_filename(file_path)
            except Exception as e:
                print(f'Failed saving file: {file_path}, Error: {str(e)}')
        return True
        
    def download_file_local(self, cloud_file_name: str, dest_file_path: str) -> None:
        """Download a file from the bucket to local storage.
        
        Args:
            cloud_file_name (str): Name of the file in the bucket.
            dest_file_path (str): Local path to save the file.
        """
        bucket = self.client.bucket(self.bucket_id)
        bucket.blob(cloud_file_name).download_to_filename(dest_file_path)
        
    def download_into_memory(self, file_name: str) -> bytes:
        """Download a file from the bucket into memory.
        
        Args:
            file_name (str): Name of the file to download.
            
        Returns:
            bytes: The contents of the file.
        """
        bucket = self.client.bucket(self.bucket_id)
        return bucket.blob(file_name).download_as_bytes()
