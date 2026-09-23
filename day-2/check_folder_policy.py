def is_folder_name_valid(folder_name):
    # Check if the folder name starts with '/', '..', or '~'
    blacklisted_prefixes = ['/', '..', '~']
    for prefix in blacklisted_prefixes:
        if folder_name.startswith(prefix):
            return False
    return True
