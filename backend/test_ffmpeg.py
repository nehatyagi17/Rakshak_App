import pydub
import imageio_ffmpeg
print("FFMPEG PATH:", imageio_ffmpeg.get_ffmpeg_exe())
pydub.AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
print("PYDUB CONVERTER:", pydub.AudioSegment.converter)
