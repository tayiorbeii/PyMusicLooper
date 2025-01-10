import os
import random
import subprocess
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from PIL import Image
from randimage import get_random_image 
from glitch_this import ImageGlitcher
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import imageio
import shutil

# Function to generate a random image
def create_random_img(img_size):
    img = get_random_image(img_size)     # returns numpy array
    return img

# Function to apply glitch effect on an image and save it as gif 
def create_glitched_gif(src, glitch_amount, color_offset=True):
    glitcher = ImageGlitcher()
    img = create_random_img(src)
    
    matplotlib.image.imsave('temp.png', img) # Save the image temporarily
    
    # Create a unique filename with .gif extension in ./glitch-gifs directory
    os.makedirs("./glitch-gifs", exist_ok=True)
    filename = f'./glitch-gifs/{random.randint(10**5, 10**6)}.gif'
    
    # Applying glitch effects
    img = Image.open('temp.png')
    glitched_imgs = glitcher.glitch_image(img, glitch_amount=glitch_amount, color_offset=color_offset, gif=True)
    
    # Random duration between 50 and 500 centiseconds
    DURATION = random.randint(50, 500)  
    LOOP = 0         # loop forever
    
    # Saving the GIF file with unique filename in ./glitch-gifs directory
    glitched_imgs[0].save(filename, format='GIF', append_images=glitched_imgs[1:], save_all=True, duration=DURATION, loop=LOOP)
    
    return filename

def gif_to_mp4(input_gif, output_name):
    # Load the gif file
    reader = imageio.get_reader(input_gif)
    
    new_frames = []
    for i, im in enumerate(reader):
        img = Image.fromarray(im)
        
        if img.mode == 'RGBA':  
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])   
        else:    
            background = img
        
        new_frames.append(np.array(background))
    
    # Convert the list of frames to an mp4 file
    imageio.mimsave(output_name, new_frames)

def adjust_gif_length(input_video, input_audio):
    gif_to_mp4(input_video, 'temp.mp4')

    # Load the video and audio clips
    video = VideoFileClip('temp.mp4')
    audio = AudioFileClip(input_audio)

    # Get the duration of the audio and video clips
    audio_duration = audio.duration
    video_duration = video.duration

    # Calculate how many times to loop the video
    loops_required = int(audio_duration / video_duration) + 1

    # Loop the video
    video_clips = [video] * loops_required
    looped_video = concatenate_videoclips(video_clips)

    # Set the duration of the looped video to match the audio
    looped_video = looped_video.set_duration(audio_duration)

    return looped_video, audio

def export_video(video, audio, output):
    final = video.set_audio(audio)
    
    # Export the video with the same name as the input video but with a different extension
    final.write_videofile(output, codec='libx264', audio_codec='aac')

# Fixed image size
img_size = (1920, 1080)

# Get a list of all subdirectories in the output directory
output_dir = "/Users/taylor/Documents/Projects/python/PyMusicLooper/output"
subdirs = [os.path.join(output_dir, d) for d in sorted(os.listdir(output_dir)) if os.path.isdir(os.path.join(output_dir, d))]

# Process each subdirectory
for chosen_subdir in subdirs:
    # Get a list of all .wav files in the chosen subdirectory
    wav_files = [f for f in os.listdir(chosen_subdir) if f.endswith('-loop.wav')]

    # Process each .wav file
    for chosen_file in wav_files:
        # Construct the full path to the chosen .wav file
        chosen_file_path = os.path.join(chosen_subdir, chosen_file)

        # Run the sox command
        output_filename = chosen_file.replace('-loop.wav', '-3-loops.mp3')
        sox_command = ['sox', chosen_file_path, os.path.join(chosen_subdir, output_filename), 'repeat', '3']
        try:
            subprocess.run(sox_command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running sox command for file {chosen_file}: {e}")

        # Now you can use the output_filename as your input_audio
        input_audio = os.path.join(chosen_subdir, output_filename)

        # the output file should have the same name as output_filename but with an mp4 extension
        output_file = os.path.join("/Users/taylor/Documents/Projects/python/PyMusicLooper/finished/", output_filename.replace('.mp3', '.mp4'))

        # Random glitch amount between 0.1 and 10.0
        glitch_amount = random.uniform(1, 10.0)

        # Create a glitched gif
        input_video = create_glitched_gif(img_size, glitch_amount, color_offset=True)

        # Adjust video length to match audio duration and speed
        adjusted_video, audio = adjust_gif_length(input_video, input_audio)

        # Export the final video
        export_video(adjusted_video, audio, output_file)

    # After processing all files, delete the subdir
    shutil.rmtree(chosen_subdir)
