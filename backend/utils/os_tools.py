import re
import os
import shutil
from fastapi import UploadFile


def sanitize_label(label: str) -> str:
    return re.sub(r'\W+', '_', label).lower()


def remove_file_extension(filename: str) -> str:
    return re.sub(r'\.\w+$', '', filename)



def create_folder_by_location(location: str):
    """
    Creates a folder if it doesn't exist.
    """
    os.makedirs(location, exist_ok=True)


def extract_table_name(file_name: str) -> str:
    """
    Removes file extension and sanitizes it for safe table naming.
    """
    return sanitize_label(remove_file_extension(file_name))


def save_uploaded_file(file: UploadFile, upload_dir: str) -> str:
    """
    Saves the uploaded file to the given directory.
    Returns the full file path.
    """
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, file.filename)
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return file_location
