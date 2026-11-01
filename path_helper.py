import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
TARGET_DIR = PUBLIC_DIR if os.path.isdir(PUBLIC_DIR) else BASE_DIR

def get_target_path(filename: str) -> str:
    """Returns the full path pointing inside public/ if present, otherwise root."""
    return os.path.join(TARGET_DIR, filename)

def get_target_dir() -> str:
    """Returns the public directory or base directory path."""
    return TARGET_DIR