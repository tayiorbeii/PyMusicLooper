import os
import random
from pathlib import Path

# get a list of all txt files in the 'finished' directory
files = sorted([f for f in os.listdir('./finished') if f.endswith('.mp4')])
random.shuffle(files) # shuffles the list of filenames

for i, filename in enumerate(files):
    new_filename = "{:05d}_{}".format(i, filename) 
    os.rename(os.path.join('./finished', filename), os.path.join('./finished', new_filename)) # renames the file