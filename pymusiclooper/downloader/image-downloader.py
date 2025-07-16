import os
from google_images_search import GoogleImagesSearch

# You may need to add your own API key and CX here
gis = GoogleImagesSearch('AIzaSyCO_P48xJGp8vJlpgU_YCNHYaf4Na6Adi0', '22d65fa86497d4ca2')

basepath = '/Users/taylor/Documents/Projects/python/PyMusicLooper/output'  # Specify the base directory where you want to start searching

for folder in os.listdir(basepath):
    if not os.path.isfile(os.path.join(basepath, folder)):
        _search_params = {
            'q': folder,
            'num': 3,
            'safe': 'active',
            'fileType': 'jpg',
        }

        gis.results().clear()  # Clear previous results for next search

        # Search and download images
        try:
            gis.search(search_params=_search_params, path_to_dir=os.path.join(basepath, folder))
        except Exception as e:
            print("Error occurred during search or download for '{}'".format(folder), str(e))