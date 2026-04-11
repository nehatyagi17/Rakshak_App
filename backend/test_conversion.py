import pydub
import imageio_ffmpeg
import io
import sys
import speech_recognition as sr
import os

print("Testing voice conversion...")
try:
    pydub.AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
    print("Converter path:", pydub.AudioSegment.converter)
    
    # Create a small dummy m4a or let's just make a dummy aac bytes if possible?
    # Or just use pydub to generate a sine wave and export it to m4a
    from pydub.generators import Sine
    sound = Sine(1000).to_audio_segment(duration=1000)
    print("Sound segment generated")
    
    audio_file = io.BytesIO()
    sound.export(audio_file, format="mp4") # m4a/mp4 container
    audio_file.seek(0)
    print("Exported to mp4 in memory")
    
    # Now simulate the view's conversion
    audio_segment = pydub.AudioSegment.from_file(audio_file)
    wav_io = io.BytesIO()
    audio_segment.export(wav_io, format="wav")
    wav_io.seek(0)
    print("Converted to wav")
    
    r = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        audio_data = r.record(source)
    print("Audio recorded by SR")
except Exception as e:
    import traceback
    traceback.print_exc()
