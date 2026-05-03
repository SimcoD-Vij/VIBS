import whisperx
import torch
import os
from pyannote.audio import Pipeline

def pre_download():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Pre-downloading models for device: {device}")

    # 1. Whisper models
    print("Downloading Whisper 'base' model...")
    whisperx.load_model("base", device, compute_type="int8")
    
    # 2. VAD model (Silero)
    # This is handled by whisperx internally, but we can trigger it
    print("VAD model usually handled by WhisperX alignment.")

    # 3. Diarization models (Official + Fallback)
    hf_token = os.getenv("HF_TOKEN")
    
    models = [
        "pyannote/speaker-diarization-3.1",
        "fatymatariq/speaker-diarization-3.1",
        "pyannote/segmentation-3.0"
    ]

    for model_name in models:
        print(f"Downloading {model_name}...")
        try:
            Pipeline.from_pretrained(model_name, use_auth_token=hf_token)
            print(f"Successfully downloaded {model_name}")
        except Exception as e:
            print(f"Failed to download {model_name}: {e}")

    print("Pre-download complete.")

if __name__ == "__main__":
    pre_download()
