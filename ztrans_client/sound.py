import playsound
import base64
import io

class SoundPlayer:
    @classmethod
    def play(cls, b64_sound_data, block=False):
        byte_data = base64.b64decode(b64_sound_data)
        s = playsound.playsound(io.BytesIO(byte_data), block=block)
