import os
import sys
import xml.etree.ElementTree as ET

### rename_gpx.py ###
### Adlai Gordon - March 2025 ###
### Renames a directory of gpx files with their datestamps ###
### Optional Suffix argument to add additional text to the end ###

def format_timestamp(timestamp):
    """Convert timestamp by replacing 'T' with '_' and ':' with '-'"""
    return timestamp.replace('T', '_').replace(':', '-')

def rename_gpx_files(directory, suffix=None):
    # Check if directory exists
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist")
        sys.exit(1)

    # Change to directory
    os.chdir(directory)

    # Counter for processed files
    processed = 0
    errors = 0

    # Loop through all .gpx files
    for filename in os.listdir('.'):
        if not filename.endswith('.gpx'):
            continue

        processed += 1
        old_filepath = filename

        try:
            # Check if file is readable and has content
            if not os.path.getsize(old_filepath) > 0:
                print(f"Skipping {filename}: File is empty")
                errors += 1
                continue

            # Parse the XML file
            tree = ET.parse(old_filepath)
            root = tree.getroot()

            # Define namespace
            namespace = {'gpx': 'http://www.topografix.com/GPX/1/1'}
            
            # Try to find the time element
            time_element = root.find('.//gpx:metadata/gpx:time', namespace)
            
            if time_element is None:
                # Try without namespace as a fallback
                time_element = root.find('.//metadata/time')
                
            if time_element is not None:
                timestamp = time_element.text
                formatted_timestamp = format_timestamp(timestamp)
                # Build new filename with optional suffix
                new_filename = f"{formatted_timestamp}{'_' + suffix if suffix else ''}.gpx"
                os.rename(old_filepath, new_filename)
                print(f"Renamed: {old_filepath} -> {new_filename}")
            else:
                print(f"Error: No timestamp found in {filename}")
                # Print the XML structure for debugging
                print("XML structure preview:")
                for elem in root.iter():
                    print(f"  {elem.tag}")
                    if elem.text and elem.text.strip():
                        print(f"    Text: {elem.text.strip()}")
                errors += 1

        except ET.ParseError as e:
            print(f"Error parsing XML in {filename}: {str(e)}")
            errors += 1
        except Exception as e:
            print(f"Unexpected error processing {filename}: {str(e)}")
            errors += 1

    print(f"\nProcessing complete!")
    print(f"Files processed: {processed}")
    print(f"Files with errors: {errors}")

if __name__ == "__main__":
    # Check arguments
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: {sys.argv[0]} <directory_path> [suffix]")
        sys.exit(1)
    
    directory = sys.argv[1]
    suffix = sys.argv[2] if len(sys.argv) == 3 else None
    rename_gpx_files(directory, suffix)