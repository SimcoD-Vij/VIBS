import subprocess

def get_audio_duration(wav_path: str) -> float:
    """
    Get duration of audio file using ffprobe.
    Supports WAV, MP3, M4A, FLAC, etc.
    """
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            wav_path
        ]
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        return float(output)
    except Exception as e:
        print(f"Error getting duration via ffprobe: {e}")
        # Fallback to librosa if ffprobe fails
        try:
            import librosa
            return float(librosa.get_duration(path=wav_path))
        except:
            return 0.0

def detect_overlaps(segments: list):
    """
    Marks is_overlap=True on segments that overlap in time.
    """
    if not segments:
        return
    
    # Sort segments by start time
    segments.sort(key=lambda x: x.get('start', 0.0))
    
    for i in range(len(segments) - 1):
        current_seg = segments[i]
        next_seg = segments[i+1]
        
        # If current segment ends after next segment starts
        if current_seg.get('end', 0.0) > next_seg.get('start', 0.0):
            current_seg['is_overlap'] = True
            next_seg['is_overlap'] = True

def assign_speaker_colors(speaker_labels: list) -> dict:
    """
    Assign colors from a fixed accessible palette to speakers.
    """
    palette = ["#1D9E75","#534AB7","#D85A30","#BA7517","#D4537E","#639922","#378ADD","#888780"]
    unique_labels = sorted(list(set(speaker_labels)))
    return {label: palette[i % len(palette)] for i, label in enumerate(unique_labels)}
