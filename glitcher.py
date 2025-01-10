import os
from randimage import get_random_image 
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from PIL import Image
from glitch_this import ImageGlitcher
import random

# Function to generate a random image
def create_random_img(img_size):
    img = get_random_image(img_size)     # returns numpy array
    # return Image.fromarray(np.uint8(img)).convert('RGB')
    return img

# Function to apply glitch effect on an image and save it as gif 
def create_glitched_gif(src, glitch_amount, color_offset=True):
    glitcher = ImageGlitcher()
    img = create_random_img(src)
    
    matplotlib.image.imsave('temp.png', img) # Save the image temporarily
    
    # Create a unique filename with .gif extension in ./glitch-gifs directory
    os.makedirs("./glitch-gifs", exist_ok=True)
    filename = f'./glitch-gifs/{random.randint(10**5, 10**6)}.gif'
    
    # img.save('temp.png') # Save the image temporarily
    
    # Applying glitch effects
    img = Image.open('temp.png')
    glitched_imgs = glitcher.glitch_image(img, glitch_amount=glitch_amount, color_offset=color_offset, gif=True)
    
    # Random duration between 50 and 500 centiseconds
    DURATION = random.randint(50, 500)  
    LOOP = 0         # loop forever
    
    # Saving the GIF file with unique filename in ./glitch-gifs directory
    glitched_imgs[0].save(filename, format='GIF', append_images=glitched_imgs[1:], save_all=True, duration=DURATION, loop=LOOP)
    
    # os.remove('temp.png') # Remove the temporary image file
    
# Fixed image size
img_size = (1920, 1080)

# Random glitch amount between 0.1 and 10.0
glitch_amount = random.uniform(0.1, 10.0)

create_glitched_gif(img_size, glitch_amount, color_offset=True)