import re
import os
import shutil
from fastapi import UploadFile


def sanitize_label(label: str) -> str:
    return re.sub(r'\W+', '_', label).lower()


def remove_file_extension(filename: str) -> str:
    return re.sub(r'\.\w+$', '', filename)

def split_words_by_spaces(words: str):
    return re.split(r"[,\s]+", words.strip())

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

def set_abs_path(path: str) -> str:
    """
    Returns the absolute path of the given path.
    """
    return os.path.abspath(path)


def if_path_exists(file_path: str) -> bool:
    """
    Returns True if the file exists, False otherwise.
    """
    return os.path.exists(file_path)
