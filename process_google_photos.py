#!/usr/bin/env python3

#########################################################################
# File      process-google-photos.py                                    #
# Author    Adlai Gordon                                                #
# Purpose   Process a directory from Google Photos Takeout              #
#             Repopulate metadata from json sidecars                    #
#             Modify file created date to best guess match original     #
#             Handle "Live Photos" (TODO)                               #
# Dependencies                                                          #
#           exiftool, pytz, python-dateutil, and more (check imports)                    #
#########################################################################

import os
import re
import shutil
import sys
import json
import subprocess
from datetime import datetime, timedelta
from dateutil import parser
import pytz
from timezonefinder import TimezoneFinder
import pdb
from pprint import pprint

# Set this to be the desired output format for the new filenames
desired_datetime_format = '%Y-%m-%d_%H-%M-%S'

dst_dates = {
    1994: ('April 03', 'September 18'),
    1995: ('April 02', 'September 17'),
    1996: ('April 07', 'September 22'),
    1997: ('April 06', 'September 21'),
    1998: ('April 05', 'September 20'),
    1999: ('April 04', 'September 19'),
    2000: ('April 02', 'September 17'),
    2001: ('April 01', 'September 23'),
    2002: ('April 07', 'September 22'),
    2003: ('April 06', 'September 21'),
    2004: ('April 04', 'September 19'),
    2005: ('April 03', 'September 18'),
    2006: ('April 02', 'September 17'),
    2007: ('March 11', 'November 04'),
    2008: ('March 09', 'November 02'),
    2009: ('March 08', 'November 01'),
    2010: ('March 14', 'November 07'),
    2011: ('March 13', 'November 06'),
    2012: ('March 11', 'November 04'),
    2013: ('March 10', 'November 03'),
    2014: ('March 09', 'November 02'),
    2015: ('March 08', 'November 01'),
    2016: ('March 13', 'November 06'),
    2017: ('March 12', 'November 05'),
    2018: ('March 11', 'November 04'),
    2019: ('March 10', 'November 03'),
    2020: ('March 08', 'November 01'),
    2021: ('March 14', 'November 07'),
    2022: ('March 13', 'November 06'),
    2023: ('March 12', 'November 05')
}

def is_daylight_savings_time(dt):
    year = dt.year
    start_date_str, end_date_str = dst_dates.get(year, (None, None))
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(f"{year} {start_date_str}", "%Y %B %d")
        end_date = datetime.strptime(f"{year} {end_date_str}", "%Y %B %d")
        
        return start_date <= dt <= end_date
    
    return False

def read_sidecar_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def determine_timezone(latitude, longitude):
    try:
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
        
        # Use the pytz library to get the UTC offset
        timezone = pytz.timezone(timezone_str)
        utc_offset = timezone.utcoffset(datetime.utcnow()).total_seconds() / 3600
        
        return int(utc_offset)
    except Exception as e:
        print(f"Error determining timezone: {e}")
        return None

def get_original_created_date(file_path, metadata, modification_info):
    exiftool_output = ""
    try:
        exiftool_command = ['exiftool', '-CreationDate', '-CreateDate', '-DateTimeOriginal', '-DateCreated', file_path]
        result = subprocess.run(exiftool_command, capture_output=True, text=True, check=True)
        modification_info['exiftool-output'] += (result.stdout.replace("\n", "").strip() + ";")

        # Parse the output to extract the original created date
        exif_output = result.stdout.strip().split('\n')
        modification_info['exif-created-output'] = exif_output
        for line in exif_output:
            if ': ' in line:
                tag, value = line.split(': ', 1)
                if tag.lower().strip() in ['creation date', 'create date', 'date/time original', 'date created']:
                    created_datetime_str = value.strip()

                    # Use dateutil.parser to parse datetime with timezone
                    dt_obj = datetime.strptime(created_datetime_str, '%Y:%m:%d %H:%M:%S')

                    # Format datetime object back to string in the desired format
                    formatted_datetime_str = dt_obj.strftime(desired_datetime_format)
                    return formatted_datetime_str
        return None

    except subprocess.CalledProcessError as e:
        modification_info['exiftool-output'] += str(e).replace("\n", "").strip() + ";"
        print(f"Error extracting created date from {file_path}: {e}")
        return None

def update_exif_data_with_exiftool(file_path, metadata, error_directory, error_files):
    exiftool_output = ""  # Initialize an empty string to store exiftool outputs
    try:
        filename = os.path.basename(file_path)
        extension = os.path.splitext(file_path)[1].strip('.').upper()
        print(filename)

        modification_info = {
            'filename': filename,
            'gps-updated': False,  # Default value if no GPS update
            'existing_description': None,
            'new-description': None,  # Default value for new description
            'created_datetime': None,  # Default value for created datetime
            'sidecar_created_datetime': None,  # Default value for sidecar created datetime
            'timezone': None,  # Default value for timezone
            'dst': None,  # Default value for daylight savings
            'sidecar_calculated_datetime': None,  # Calculated datetime based on timezone & dst
            'exiftool-output': ''  # To capture exiftool command outputs
        }

        created_datetime = get_original_created_date(file_path, metadata, modification_info)
        if created_datetime:
            modification_info['created_datetime'] = created_datetime

        read_description_command = ['exiftool', '-Description', file_path]
        result = subprocess.run(read_description_command, capture_output=True, text=True, check=True)
        existing_description = result.stdout.strip()
        exiftool_output += result.stdout.replace("\n", "").strip() + ";"

        new_description = {'original_filename': filename}

        if existing_description.startswith('{'):
            new_description = json.loads(existing_description)
        else:
            if existing_description:
                new_description['original_description'] = existing_description

            if 'people' in metadata and isinstance(metadata['people'], list) and len(metadata['people']) > 0:
                new_description['people'] = [person['name'] for person in metadata['people']]

        if not existing_description.startswith('{'):
            new_description_json = json.dumps(new_description)
            exiftool_commands = ['exiftool', '-overwrite_original', f"-Description={new_description_json}"]
        else:
            exiftool_commands = []

        modification_info['existing_description'] = existing_description
        modification_info['new-description'] = new_description

        geo_data = metadata.get('geoData') or metadata.get('geoDataExif')
        if geo_data:
            latitude = geo_data['latitude']
            longitude = geo_data['longitude']

            if not (latitude == 0.0 and longitude == 0.0):
                exiftool_commands.extend([f"-GPSLatitude={latitude}", f"-GPSLongitude={longitude}"])
                timezone = determine_timezone(latitude, longitude)
                if timezone:
                    modification_info['timezone'] = timezone

        if 'photoTakenTime' in metadata:
            try:
                timestamp = metadata['photoTakenTime']['timestamp']
                photo_taken_time = datetime.utcfromtimestamp(int(timestamp))
                modification_info['sidecar_created_datetime'] = photo_taken_time.strftime(desired_datetime_format)
                is_dst = is_daylight_savings_time(photo_taken_time)
                modification_info['dst'] = is_dst

                utc_offset = -5  # Default timezone (America/New York)

                if 'timezone' in modification_info and modification_info['timezone'] is not None:
                    utc_offset = modification_info['timezone']
                
                adjusted_datetime = photo_taken_time + timedelta(hours=utc_offset)

                if 'dst' in modification_info and modification_info['dst']:
                    adjusted_datetime += timedelta(hours=1)

                modification_info['sidecar_calculated_datetime'] = adjusted_datetime.strftime(desired_datetime_format)

            except (ValueError, KeyError, TypeError):
                pass

        if exiftool_commands:
            exiftool_commands.append(file_path)
            result = subprocess.run(exiftool_commands, capture_output=True, text=True, check=True)
            exiftool_output += result.stdout.replace("\n", "").strip() + ";"

        # Assign the captured output to modification_info
        modification_info['exiftool-output'] = exiftool_output

        return extension, modification_info

    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        modification_info['exiftool-output'] += str(e).replace("\n", "").strip() + ";"
        print(f"Error updating metadata for {file_path}: {e}")
        if not os.path.exists(error_directory):
            os.makedirs(error_directory)
        error_file_path = os.path.join(error_directory, os.path.basename(file_path))
        error_files.append(modification_info)
        shutil.move(file_path, error_file_path)
        return None, None

def change_system_file_datetime(file_path, modification_info):
    try:
        # Convert the new filename to a datetime object
        dt_obj = datetime.strptime(modification_info['new_filename_base'], desired_datetime_format)

        # Convert datetime object to a timestamp
        timestamp = dt_obj.timestamp()

        os.utime(file_path, (timestamp, timestamp))
        modification_info['file_mtime_updated'] = True

    except Exception as e:
        modification_info['file_mtime_updated'] = False
        print(f"Error in change_system_file_datetime for {file_path}: {e}")

    return modification_info

def rename_file_based_on_datetime(file_path, modification_info, error_renaming_directory, error_renaming_files, processed_sidecars_directory, sidecar_path, success_directory):
    try:
        # datetime_format = desired_datetime_format
        extension = os.path.splitext(file_path)[1].strip('.').lower()

        new_filename_base = None
        
        # Try using the sidecar calcualted datetime first
        if modification_info['sidecar_calculated_datetime']:
            try:
                new_filename_base = modification_info['sidecar_calculated_datetime']
            except ValueError:
                pass


        # If this fails use the file time found in the file
        if not new_filename_base and modification_info['created_datetime']:
            try:
                new_filename_base = modification_info['created_datetime']
            except ValueError:
                pass

        if new_filename_base:
            modification_info['new_filename_base'] = new_filename_base
            new_filename = f"{new_filename_base}.{extension}"
            new_file_path = os.path.join(os.path.dirname(file_path), new_filename)

            counter = 1
            while os.path.exists(new_file_path):
                new_filename = f"{new_filename_base}_{counter}.{extension}"
                new_file_path = os.path.join(os.path.dirname(file_path), new_filename)
                counter += 1

            os.rename(file_path, new_file_path)

            modification_info['new_filename'] = new_filename
            modification_info = change_system_file_datetime(new_file_path, modification_info)

            # Move the renamed file to the success directory
            success_file_path = os.path.join(success_directory, new_filename)
            if not os.path.exists(success_directory):
                os.makedirs(success_directory)
            shutil.move(new_file_path, success_file_path)

            # Move the sidecar file
            if sidecar_path and os.path.exists(sidecar_path):
                if not os.path.exists(processed_sidecars_directory):
                    os.makedirs(processed_sidecars_directory)
                shutil.move(sidecar_path, os.path.join(processed_sidecars_directory, os.path.basename(sidecar_path)))

            print('    renamed to', new_filename)
            return new_file_path

        return file_path

    except Exception as e:
        print(f"Error renaming file {file_path}: {e}")
        if not os.path.exists(error_renaming_directory):
            os.makedirs(error_renaming_directory)
        error_file_path = os.path.join(error_renaming_directory, os.path.basename(file_path))
        error_renaming_files.append(modification_info)
        shutil.move(file_path, error_file_path)
        return None

def create_matched_file_list(file_list):
    matched_files = {}
    json_file_list = []

    # Loop through the file list
    for file in file_list:
        if file.startswith('.'):  # Skip system files like .DS_Store
            continue

        base_name, extension = os.path.splitext(file)

        # Handle JSON files
        if extension.lower() == '.json':
            json_file_list.append(file)
        else:
            # Initialize the dictionary for this base_name if it doesn't exist
            if base_name not in matched_files:
                matched_files[base_name] = {'img': [], 'json': None}
            # Add the image file to the list under its base_name
            matched_files[base_name]['img'].append(file)


    # Combine keys that are off by one letter at the end and longer than 10 characters
    keys_to_combine = [(key, key[:-1]) for key in matched_files if len(key) > 10 and key[:-1] in matched_files]
    for long_key, short_key in keys_to_combine:
        matched_files[short_key]['img'].extend(matched_files[long_key]['img'])
        del matched_files[long_key]  # Remove the longer key entry

    for json_file in json_file_list:
        
        possible_matches = []
        partial_name = os.path.splitext(json_file)[0] # img123.json -> img123
        possible_matches.append(partial_name)

        # Check and extract the parenthetical component # img123.jpg(1).json -> (1)
        parenthetical_match = re.search(r'\(\d+\)$', partial_name)
        parenthetical = parenthetical_match.group(0) if parenthetical_match else None

        base_name = os.path.splitext(partial_name)[0] # img123.jpg.json -> img123

        if parenthetical:
            possible_matches.append(f"{base_name}{parenthetical}")
        else:
            possible_matches.append(f"{base_name}")

        # Loop through possible matches
        for possible_match in possible_matches:
            if possible_match in matched_files:
                matched_files[possible_match]['json'] = json_file

    return matched_files


def process_directory(directory, report_number):
    report_timestamp = datetime.now().strftime(desired_datetime_format)
    os.makedirs(sidecar_directory := os.path.join(directory, "error-missing-sidecar"), exist_ok=True)
    processed_sidecars_directory = os.path.join(directory, "processed-sidecars")
    error_renaming_directory = os.path.join(directory, "error-renaming")
    error_directory = os.path.join(directory, "processing-errors")
    success_directory = os.path.join(directory, "successfully-processed")
    missing_files = []
    error_files = []
    error_renaming_files = []
    files_examined = 0
    extension_modifications = {}  # To group modifications by file extension

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    matched_files = create_matched_file_list(files)

    for base_name, file_group in matched_files.items():
        sidecar_path = None
        if file_group['json']:
            sidecar_path = os.path.join(directory, file_group['json'])
            sidecar_metadata = read_sidecar_json(sidecar_path)
        else:
            # Move images to missing sidecar directory
            for img_file in file_group['img']:
                file_path = os.path.join(directory, img_file)
                missing_files.append(file_path)
                shutil.move(file_path, os.path.join(sidecar_directory, img_file))
            continue

        modification_info_list = []
        for img_file in file_group['img']: # Loop through all files with the same base name
            file_path = os.path.join(directory, img_file)

            extension, modification_info = update_exif_data_with_exiftool(file_path, sidecar_metadata, error_directory, error_files)

            if modification_info:
                file_path = rename_file_based_on_datetime(file_path, modification_info, error_renaming_directory, error_renaming_files, processed_sidecars_directory, sidecar_path, success_directory)
                
                if file_path is None:
                    # File renaming failed, move to the next file
                    write_report(report_timestamp, directory, missing_files, error_files, error_renaming_files, extension_modifications)
                    continue


                modification_info_list.append(modification_info)
                if len(file_group['img']) > 1:
                    # Group under "LIVE" if more than one image in the group
                    extension = "LIVE"
                    if extension not in extension_modifications:
                        extension_modifications[extension] = {}
                    if base_name not in extension_modifications[extension]:
                        extension_modifications[extension][base_name] = []
                    extension_modifications[extension][base_name].append(modification_info)
                else:
                    if extension not in extension_modifications:
                        extension_modifications[extension] = []
                    extension_modifications[extension].append(modification_info)

                write_report(report_timestamp, directory, missing_files, error_files, error_renaming_files, extension_modifications)

            files_examined += 1
            if files_examined % report_number == 0:
                print_report(missing_files, error_files, error_renaming_files, extension_modifications)
        

    return missing_files, error_files, error_renaming_files, extension_modifications


def write_report(timestamp, directory, missing_files, error_files, error_renaming_files, extension_modifications):
    # timestamp = datetime.now().strftime(desired_datetime_format)
    report_filename = f"report_{timestamp}.json"
    report_path = os.path.join(directory, report_filename)

    # Function to convert datetime objects to strings
    def datetime_converter(o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")

    report_data = {
        "run-datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error-missing-sidecars": {
            "total": len(missing_files),
            "filelist": missing_files
        },
        "error-processing": {
            "total": len(error_files),
            "filelist": error_files
        },
        "error-renaming": {
            "total": len(error_renaming_files),
            "filelist": error_renaming_files
        },
        "modifications": extension_modifications  # Add the grouped modifications
    }

    with open(report_path, 'w') as report_file:
        json.dump(report_data, report_file, indent=4, default=datetime_converter)

    return report_path

def print_report(missing_files, error_files, error_renaming_files, extension_modifications):
    print("")
    modification_counts = {}
    modification_counts['missing-sidecar'] = len(missing_files)
    modification_counts['error_files'] = len(error_files)
    modification_counts['error_renaming_files'] = len(error_renaming_files)
    for extension, modifications in extension_modifications.items():
        modification_counts[extension] = len(modifications)

    success_count = 0
    for ext, count in modification_counts.items():
        success_count += count
        pprint({ext: count})

    fail_count = len(missing_files)+len(error_files)+len(error_renaming_files)
    print(f"\n{success_count + fail_count} files processed ({success_count} success, {fail_count} fail)\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ./script.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    report_number = 10
    missing_files, error_files, error_renaming_files, extension_modifications = process_directory(directory, report_number)
    # report_path = write_report(directory, missing_files, error_files, error_renaming_files, extension_modifications)
    print(f"\n\nCOMPLETE: {directory}\n\n")
    print_report(missing_files, error_files, error_renaming_files, extension_modifications)

