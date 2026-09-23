import os

def check_folder_exists(folder_path):
    """
    Check if the given folder exists.

    Args:
        folder_path (str): The path of the folder to check.

    Returns:
        bool: True if the folder exists, False otherwise.
    """
    return os.path.isdir(folder_path)