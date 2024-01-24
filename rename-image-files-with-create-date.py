#!/usr/bin/env python3

# Rename Image & Video Files
# Renames according to Creation date or File Modified Date


import os
import sys
from PIL import Image
from PIL.ExifTags import TAGS
import datetime

def get_date_taken(path):
    try:
        img = Image.open(path)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                if TAGS.get(tag) == "DateTimeOriginal":
                    return datetime.datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        return None
    except IOError:
        return None

def get_creation_time(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path))

def unique_filename(directory, base_filename, extension):
    counter = 1
    new_filename = base_filename + extension
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base_filename}-{counter}{extension}"
        counter += 1
    return new_filename

def rename_files(directory):
    renamed_files = {}
    for filename in os.listdir(directory):
        original_filepath = os.path.join(directory, filename)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.heic', '.PNG', '.JPG', '.JPEG', '.HEIC', '.mov', '.MOV')):
            date_taken = get_date_taken(original_filepath) or get_creation_time(original_filepath)
            base_filename = date_taken.strftime("%Y-%m-%d_%H.%M.%S")
            extension = os.path.splitext(filename)[1]
            new_filename = unique_filename(directory, base_filename, extension)
            new_filepath = os.path.join(directory, new_filename)
            os.rename(original_filepath, new_filepath)
            print(f"Renamed {filename} to {new_filename}")

            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.heic', '.PNG', '.JPG', '.JPEG', '.HEIC')):
                renamed_files[os.path.splitext(filename)[0]] = os.path.splitext(new_filename)[0]

if len(sys.argv) != 2:
    print("Usage: python script.py [directory]")
    sys.exit(1)

directory = sys.argv[1]
rename_files(directory)
