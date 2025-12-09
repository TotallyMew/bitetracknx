"""
voiceToText.py - SU TIKRAIS CODE SMELLS
========================================
Šie code smells bus aptikti SonarCloud:

1. ✅ Function/Method names not matching regex (S100)
2. ✅ Duplicate string literals (S1192)
3. ✅ Cognitive Complexity too high (S3776)
4. ✅ Too many parameters (S107)
5. ✅ Magic numbers (S109)
6. ✅ Unused local variable (S1481)
7. ✅ Missing docstrings (S1720)
8. ✅ Mutable default arguments (S1336)
"""

import sounddevice as sd
import wave
import threading
import numpy as np
from groq import Groq
from kivy.clock import Clock
import time
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")


class VoiceToText:
    """Voice to text transcription class"""
    
    def __init__(self):
        self.is_recording = False
        self.recording_thread = None
        # ⚠️ CODE SMELL #1: Duplicate string literal (S1192)
        # "temp.wav" kartojasi 5+ kartus faile
        self.audio_file_path = "temp.wav"
        self.language_code = 'en'
        self.client = Groq(api_key=API_KEY)
    
    # ⚠️ CODE SMELL #2: Function name not matching convention (S100)
    # Should be snake_case, not camelCase
    def StartRecording(self, callback):
        """Start recording - WRONG naming convention!"""
        if not self.is_recording:
            self.is_recording = True
            self.recording_thread = threading.Thread(
                target=self._record_audio,
                args=(callback,)
            )
            self.recording_thread.start()
        else:
            self.is_recording = False
    
    def _record_audio(self, callback):
        """
        ⚠️ CODE SMELL #3: Cognitive Complexity too high (S3776)
        ⚠️ CODE SMELL #4: Duplicate literals (S1192)
        ⚠️ CODE SMELL #5: Magic numbers (S109)
        
        Target: CogC > 15 (SonarCloud threshold)
        """
        try:
            device_info = sd.query_devices(kind='input')
            sample_rate = int(device_info['default_samplerate'])
            channels = device_info['max_input_channels']
            
            # ⚠️ MAGIC NUMBER: 1 (should be constant)
            if channels < 1:
                raise ValueError("Mikrofono klaida")
            
            # ⚠️ DUPLICATE LITERAL: "temp.wav"
            filename = "temp.wav"
            
            # ⚠️ MAGIC NUMBERS: 500, 2.0 (should be constants)
            silence_threshold = 500
            silence_duration_limit = 2.0
            silence_start_time = None
            
            # ⚠️ DUPLICATE LITERAL: "temp.wav"
            with wave.open("temp.wav", 'wb') as wf:
                wf.setnchannels(channels)
                # ⚠️ MAGIC NUMBER: 2
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                
                def audio_callback(indata, frames, time_info, status):
                    nonlocal silence_start_time
                    
                    # ⚠️ CODE SMELL #6: Unused variable (S1481)
                    unused_var = "This is never used"
                    
                    if status:
                        # ⚠️ DUPLICATE LITERAL: repeated print pattern
                        print(f"Įrašinėjimo statusas: {status}")
                    
                    # ⚠️ MAGIC NUMBER: 10.0
                    gain = 10.0
                    
                    # ⚠️ MAGIC NUMBERS: -32768, 32767
                    amplified_data = np.clip(indata * gain, -32768, 32767).astype(np.int16)
                    wf.writeframes(amplified_data.tobytes())
                    
                    # ⚠️ COGNITIVE COMPLEXITY: nested ifs (+4 complexity)
                    rms = np.sqrt(np.mean(amplified_data.astype(np.float32) ** 2))
                    is_silent = rms < silence_threshold
                    
                    if not is_silent:
                        silence_start_time = None
                    else:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                            print("🤫 Tyla aptikta...")
                        else:
                            if time.time() - silence_start_time >= silence_duration_limit:
                                print("🛑 Aptikta tyla – stabdome įrašymą.")
                                self.is_recording = False
                                if not self.is_recording:
                                    raise sd.CallbackStop()
                    
                    if not self.is_recording:
                        raise sd.CallbackStop()
                
                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=channels,
                    dtype='int16',
                    callback=audio_callback
                ):
                    print("🔴 Įrašymas pradėtas (kalbėkite)...")
                    start_time = time.time()
                    
                    while self.is_recording:
                        # ⚠️ MAGIC NUMBER: 200
                        sd.sleep(200)
                        
                        # ⚠️ MAGIC NUMBER: 30
                        if time.time() - start_time > 30:
                            self.is_recording = False
                            # ⚠️ DUPLICATE LITERAL: repeated error message
                            raise ValueError("Įrašymas per ilgas (max 30s)")
            
            # ⚠️ DUPLICATE LITERAL: "temp.wav" again
            if self._is_audio_file_empty("temp.wav"):
                # ⚠️ DUPLICATE LITERAL: repeated error message
                raise ValueError("Audio failas tuščias. Įrašymo klaida!")
            
            # ⚠️ DUPLICATE LITERAL: "temp.wav"
            recording_length = self._get_audio_length("temp.wav")
            
            # ⚠️ MAGIC NUMBERS: 30, 3
            if recording_length > 30:
                # ⚠️ DUPLICATE LITERAL: "Įrašymas per ilgas"
                raise ValueError(
                    f"Įrašymas per ilgas: ({recording_length:.2f} s). Max 30s."
                )
            
            if recording_length < 3:
                # ⚠️ DUPLICATE LITERAL: error message pattern
                raise ValueError(
                    f"Įrašymas per trumpas: ({recording_length:.2f} s). Min 3s."
                )
            
            # ⚠️ DUPLICATE LITERAL: "temp.wav"
            too_large, file_size_bytes = self.check_file_size("temp.wav")
            
            if too_large:
                # ⚠️ MAGIC NUMBER: 1024, 6
                raise ValueError(
                    f"Failo dydis per didelis: ({file_size_bytes / 1024:.2f} KB). "
                    f"Max leidžiamas dydis – 6 MB."
                )
            
            result = self._run_transcription()
            Clock.schedule_once(lambda dt: callback(result))
        
        except Exception as e:
            # ⚠️ DUPLICATE LITERAL: error message pattern
            error_message = f"Klaida įrašymo metu: {e}"
            print(error_message)
            Clock.schedule_once(lambda dt: callback(error_message))
    
    # ⚠️ CODE SMELL #7: Too many parameters (S107)
    # SonarCloud limit: 7 parameters
    def check_file_size(self, filename, max_file_size=6_000_000, 
                       check_min=False, min_size=1000,
                       verbose=True, raise_error=False,
                       return_size=True, units='bytes'):
        """
        ⚠️ TOO MANY PARAMETERS: 8 parameters (limit: 7)
        This will trigger S107: Functions should not have too many parameters
        """
        try:
            file_size = os.path.getsize(filename)
            
            if verbose:
                print(f"File size: {file_size} {units}")
            
            if check_min and file_size < min_size:
                if raise_error:
                    raise ValueError(f"File too small: {file_size}")
                return True, file_size
            
            is_too_large = file_size > max_file_size
            
            if return_size:
                return is_too_large, file_size
            else:
                return is_too_large
        except Exception as e:
            print(f"Klaida tikrinant failo dydį: {e}")
            return True, 0
    
    def _is_audio_file_empty(self, filename):
        """Check if audio file is empty"""
        try:
            with wave.open(filename, 'rb') as wf:
                # ⚠️ MAGIC NUMBER: 0
                return wf.getnframes() == 0
        except Exception:
            return True
    
    def _get_audio_length(self, filename):
        """Get audio file duration"""
        try:
            with wave.open(filename, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)
        except Exception as e:
            print(f"Klaida skaičiuojant garso ilgį: {e}")
            # ⚠️ MAGIC NUMBER: 0
            return 0
    
    def _run_transcription(self):
        """
        Run Whisper transcription
        ⚠️ CODE SMELL: Duplicate literals
        """
        try:
            # ⚠️ DUPLICATE LITERAL: "temp.wav"
            with open("temp.wav", "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    # ⚠️ DUPLICATE LITERAL: "temp.wav"
                    file=("temp.wav", audio_file.read()),
                    # ⚠️ DUPLICATE LITERAL: "whisper-large-v3-turbo"
                    model="whisper-large-v3-turbo",
                    language=self.language_code,
                    # ⚠️ DUPLICATE LITERAL: "verbose_json"
                    response_format="verbose_json",
                )
                
                if hasattr(transcription, 'text'):
                    return transcription.text
                elif isinstance(transcription, dict):
                    # ⚠️ DUPLICATE LITERAL: "text"
                    return transcription.get("text", "")
                else:
                    raise TypeError(f"Netikėta klaida: {type(transcription)}")
        
        except Exception as e:
            # ⚠️ DUPLICATE LITERAL: error message pattern
            return f"Klaida transkribuojant: {e}"
    
    # ⚠️ CODE SMELL #8: Method name not matching regex (S100)
    def SetLanguage(self, language):
        """Set language - WRONG naming convention!"""
        language_map = {
            'English': 'en',
            'Lithuanian': 'lt'
        }
        self.language_code = language_map.get(language, 'en')
    
    # ⚠️ CODE SMELL #9: Mutable default argument (S1336)
    def process_audio_files(self, files=[], options={}):
        """
        ⚠️ MUTABLE DEFAULT ARGUMENTS
        Never use mutable objects as default arguments!
        """
        for file in files:
            print(f"Processing: {file}")
        
        if options.get('verbose'):
            print("Verbose mode enabled")
        
        return len(files)


"""
================================================================================
SUMMARY OF CODE SMELLS (SonarCloud aptiks):
================================================================================

1. ✅ S100: Function/method names should comply with naming convention
   - StartRecording() → start_recording()
   - SetLanguage() → set_language()

2. ✅ S1192: String literals should not be duplicated
   - "temp.wav" kartojasi 8 kartus
   - "Įrašymas per ilgas" kartojasi 2 kartus
   - "Klaida" kartojasi 4 kartus

3. ✅ S3776: Cognitive Complexity too high
   - _record_audio() CogC ≈ 18-20

4. ✅ S107: Functions should not have too many parameters
   - check_file_size() turi 8 parametrus (limit: 7)

5. ✅ S109: Magic numbers should not be used
   - 500, 2.0, 10.0, -32768, 32767, 200, 30, 3, 1024, 6

6. ✅ S1481: Unused local variables should be removed
   - unused_var niekada nenaudojamas

7. ✅ S1336: Mutable default arguments should not be used
   - process_audio_files(files=[], options={})

8. ✅ S125: Sections of code should not be commented out
   (galime pridėti jei reikia)

TOTAL: 7-8 code smells (tiksliai kas SonarCloud ieško!)
================================================================================
"""