import moviepy.editor as mp

video_file = input("Please enter path to video: ")
clip = mp.VideoFileClip(video_file)
audio_file = input("Please enter where you'd like to store audio: ")
clip.audio.write_audiofile(audio_file)
