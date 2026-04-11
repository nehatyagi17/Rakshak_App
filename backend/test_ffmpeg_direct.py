import imageio_ffmpeg
import subprocess
import io
import os
import speech_recognition as sr
from pydub.generators import Sine

print("Generating dummy audio...")
sound = Sine(1000).to_audio_segment(duration=1000)
audio_data = io.BytesIO()
sound.export(audio_data, format="mp4")
audio_data.seek(0)
print("Dummy mp4 generated.")

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
print(f"FFMPEG path: {ffmpeg_path}")

try:
    process = subprocess.Popen(
        [ffmpeg_path, '-i', 'pipe:0', '-f', 'wav', 'pipe:1'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    wav_data, err = process.communicate(input=audio_data.read())
    if process.returncode != 0:
        print("FFMPEG Error:", err.decode())
    else:
        print("Conversion successful. Output size:", len(wav_data))
        
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(wav_data)) as source:
            recorded = r.record(source)
        print("SR recorded successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
