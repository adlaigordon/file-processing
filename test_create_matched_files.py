#!/usr/bin/env python3

from process_google_photos import create_matched_file_list

def test_create_matched_file_list(test_cases):
    for i, (file_list, expected_output) in enumerate(test_cases):
        print(f"Test Case {i+1}:")
        print("Input file list:", file_list)
        actual_output = create_matched_file_list(file_list)
        print("Expected output:", expected_output)
        print("Actual output:", actual_output)
        print("Test Passed:", expected_output == actual_output)
        print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    test_cases = [
        
        # without extension on sidecar
        (
            ['IMG_7309.HEIC', 'IMG_7309.json', 'IMG_7309.MP4'], 
            {'IMG_7309': {'img': ['IMG_7309.HEIC', 'IMG_7309.MP4'], 'json': 'IMG_7309.json'}}
        ),


        # Standard Live Photo
        (
            ['IMG_7309.HEIC', 'IMG_7309.HEIC.json', 'IMG_7309.MP4'], 
            {'IMG_7309': {'img': ['IMG_7309.HEIC', 'IMG_7309.MP4'], 'json': 'IMG_7309.HEIC.json'}}
        ),


        # (n) format
        (
            ['IMG_1739.JPG', 'IMG_1739(1).JPG', 'IMG_1739.JPG.json', 'IMG_1739.JPG(1).json'],
            {
                'IMG_1739': {'img' :['IMG_1739.JPG'], 'json': 'IMG_1739.JPG.json'},
                'IMG_1739(1)': {'img' :['IMG_1739(1).JPG'], 'json': 'IMG_1739.JPG(1).json'}
            }
        ),

        # One letter added to the end of one of the img files
        (
            ['70759752381.HEIC', '70759752381.json', '70759752381C.MP4'], 
            {'70759752381': {'img': ['70759752381.HEIC', '70759752381C.MP4'], 'json': '70759752381.json'}}
        ),



    ]

    test_create_matched_file_list(test_cases)
