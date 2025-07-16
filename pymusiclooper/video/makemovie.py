from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import os
import imageio
import numpy as np
from PIL import Image

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

# Define your paths
input_video = "/Users/taylor/Documents/Projects/python/PyMusicLooper/glitch-gifs/261597.gif"  # Your gif file path
input_audio = "/Users/taylor/Documents/Projects/python/PyMusicLooper/output/Pharoah Sanders - Pharoah (1976)/Pharoah Sanders - Pharoah (1976)_0-looped.mp3"  # Your audio file path
output_file = "/Users/taylor/Documents/Projects/python/PyMusicLooper/finished/pharoah.mp4"  # The name and location of the output file

# Adjust video length to match audio duration and speed
adjusted_video, audio = adjust_gif_length(input_video, input_audio)

# Export the final video
export_video(adjusted_video, audio, output_file)