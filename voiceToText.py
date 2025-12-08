# Constants
AUDIO_FILE_PATH = "temp.wav"
SILENCE_THRESHOLD = 500
SILENCE_DURATION_LIMIT = 2.0
GAIN_MULTIPLIER = 10.0
MIN_INT16 = -32768
MAX_INT16 = 32767
SLEEP_INTERVAL_MS = 200
MAX_RECORDING_DURATION = 30
MIN_RECORDING_DURATION = 3
SAMPLE_WIDTH = 2
MIN_CHANNELS = 1

class VoiceToText:
    def __init__(self):
        self.is_recording = False
        self.recording_thread = None
        self.audio_file_path = AUDIO_FILE_PATH
        self.language_code = 'en'
        self.client = Groq(api_key=API_KEY)
    
    def start_recording(self, callback):
        """Start recording"""
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
        """Record audio with silence detection"""
        try:
            device_info = sd.query_devices(kind='input')
            sample_rate = int(device_info['default_samplerate'])
            channels = device_info['max_input_channels']
            
            if channels < MIN_CHANNELS:
                raise ValueError("Mikrofono klaida")
            
            silence_tracker = SilenceTracker(SILENCE_THRESHOLD, SILENCE_DURATION_LIMIT)
            
            with wave.open(AUDIO_FILE_PATH, 'wb') as wf:
                self._configure_wave_file(wf, channels, sample_rate)
                
                audio_callback = self._create_audio_callback(wf, silence_tracker)
                
                self._run_input_stream(sample_rate, channels, audio_callback)
            
            self._validate_recording()
            result = self._run_transcription()
            Clock.schedule_once(lambda dt: callback(result))
        
        except Exception as e:
            error_message = f"Klaida įrašymo metu: {e}"
            print(error_message)
            Clock.schedule_once(lambda dt: callback(error_message))
    
    def _configure_wave_file(self, wf, channels, sample_rate):
        """Configure wave file parameters"""
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
    
    def _create_audio_callback(self, wf, silence_tracker):
        """Create audio callback function"""
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"Įrašinėjimo statusas: {status}")
            
            amplified_data = self._amplify_audio(indata)
            wf.writeframes(amplified_data.tobytes())
            
            if silence_tracker.check_silence(amplified_data):
                print("🛑 Aptikta tyla – stabdome įrašymą.")
                self.is_recording = False
            
            if not self.is_recording:
                raise sd.CallbackStop()
        
        return audio_callback
    
    def _amplify_audio(self, indata):
        """Amplify audio data"""
        return np.clip(indata * GAIN_MULTIPLIER, MIN_INT16, MAX_INT16).astype(np.int16)
    
    def _run_input_stream(self, sample_rate, channels, audio_callback):
        """Run audio input stream"""
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            callback=audio_callback
        ):
            print("🔴 Įrašymas pradėtas (kalbėkite)...")
            start_time = time.time()
            
            while self.is_recording:
                sd.sleep(SLEEP_INTERVAL_MS)
                
                if time.time() - start_time > MAX_RECORDING_DURATION:
                    self.is_recording = False
                    raise ValueError(f"Įrašymas per ilgas (max {MAX_RECORDING_DURATION}s)")
    
    def _validate_recording(self):
        """Validate recorded audio file"""
        if self._is_audio_file_empty(AUDIO_FILE_PATH):
            raise ValueError("Audio failas tuščias. Įrašymo klaida!")
        
        recording_length = self._get_audio_length(AUDIO_FILE_PATH)
        
        if recording_length > MAX_RECORDING_DURATION:
            raise ValueError(
                f"Įrašymas per ilgas: ({recording_length:.2f} s). Max {MAX_RECORDING_DURATION}s."
            )
        
        if recording_length < MIN_RECORDING_DURATION:
            raise ValueError(
                f"Įrašymas per trumpas: ({recording_length:.2f} s). Min {MIN_RECORDING_DURATION}s."
            )
        
        too_large, file_size_bytes = self.check_file_size(AUDIO_FILE_PATH)
        
        if too_large:
            raise ValueError(
                f"Failo dydis per didelis: ({file_size_bytes / 1024:.2f} KB). "
                f"Max leidžiamas dydis – 6 MB."
            )
    
    def check_file_size(self, filename, max_file_size=6_000_000):
        """Check if file size exceeds limit"""
        try:
            file_size = os.path.getsize(filename)
            is_too_large = file_size > max_file_size
            return is_too_large, file_size
        except Exception as e:
            print(f"Klaida tikrinant failo dydį: {e}")
            return True, 0
    
    def _is_audio_file_empty(self, filename):
        """Check if audio file is empty"""
        try:
            with wave.open(filename, 'rb') as wf:
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
            return 0
    
    def _run_transcription(self):
        """Run Whisper transcription"""
        try:
            with open(AUDIO_FILE_PATH, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=(AUDIO_FILE_PATH, audio_file.read()),
                    model="whisper-large-v3-turbo",
                    language=self.language_code,
                    response_format="verbose_json",
                )
                
                if hasattr(transcription, 'text'):
                    return transcription.text
                elif isinstance(transcription, dict):
                    return transcription.get("text", "")
                else:
                    raise TypeError(f"Netikėta klaida: {type(transcription)}")
        
        except Exception as e:
            return f"Klaida transkribuojant: {e}"
    
    def set_language(self, language):
        """Set language"""
        language_map = {
            'English': 'en',
            'Lithuanian': 'lt'
        }
        self.language_code = language_map.get(language, 'en')


class SilenceTracker:
    """Tracks silence duration in audio stream"""
    
    def __init__(self, threshold, duration_limit):
        self.threshold = threshold
        self.duration_limit = duration_limit
        self.silence_start_time = None
    
    def check_silence(self, audio_data):
        """Check if silence duration exceeds limit"""
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        is_silent = rms < self.threshold
        
        if not is_silent:
            self.silence_start_time = None
            return False
        
        if self.silence_start_time is None:
            self.silence_start_time = time.time()
            print("🤫 Tyla aptikta...")
            return False
        
        elapsed = time.time() - self.silence_start_time
        return elapsed >= self.duration_limit