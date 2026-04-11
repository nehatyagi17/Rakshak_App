import imageio_ffmpeg
import subprocess

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
print(f"Executing: {ffmpeg_path} -version")
try:
    process = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
    print("Return code:", process.returncode)
    print("Stdout:", process.stdout[:100])
except Exception as e:
    import traceback
    traceback.print_exc()
