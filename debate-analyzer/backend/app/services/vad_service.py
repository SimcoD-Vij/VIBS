import torch
import numpy as np
from app.config import settings

# Load model once at startup (cached by torch.hub after first download)
vad_model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad',
    force_reload=False,
    trust_repo=True
)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

def score_chunk(chunk_bytes: bytes, sample_rate=16000) -> float:
    """
    Input: raw audio bytes (PCM float32 or int16)
    Output: VAD probability for this chunk (0.0 to 1.0)
    If chunk is too short for VAD, return 1.0 (assume speech, do nothing)
    """
    audio_np = np.frombuffer(chunk_bytes, dtype=np.float32)
    if len(audio_np) < 512:  # minimum frame size
        return 1.0
    tensor = torch.FloatTensor(audio_np)
    with torch.no_grad():
        score = vad_model(tensor, sample_rate).item()
    return score

class SilenceTracker:
    def __init__(self, threshold_seconds=settings.SILENCE_THRESHOLD_SECONDS):
        self.threshold_seconds = threshold_seconds
        self.silence_seconds = 0.0
        
    def update(self, score: float, chunk_duration: float):
        if score < 0.5:
            self.silence_seconds += chunk_duration
        else:
            self.silence_seconds = 0.0
            
    @property
    def is_silent(self) -> bool:
        return self.silence_seconds >= self.threshold_seconds
