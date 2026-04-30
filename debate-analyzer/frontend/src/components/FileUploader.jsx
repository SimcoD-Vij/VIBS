import { useState, useRef } from 'react';
import axios from 'axios';

export function FileUploader({ onUploadStart, onUploadSuccess, onUploadError }) {
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Optional: check file size (e.g., 100MB limit)
    if (file.size > 100 * 1024 * 1024) {
      if (onUploadError) onUploadError('File is too large (max 100MB)');
      return;
    }

    setIsUploading(true);
    if (onUploadStart) onUploadStart();

    const formData = new FormData();
    formData.append('file', file);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    try {
      const response = await axios.post(`${apiUrl}/api/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      if (onUploadSuccess) onUploadSuccess(response.data);
    } catch (err) {
      console.error('Upload error:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to upload file';
      if (onUploadError) onUploadError(errorMessage);
    } finally {
      setIsUploading(false);
      // Reset input so the same file can be selected again if needed
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
        accept=".wav,.mp3,.m4a,.flac,.ogg"
      />
      <button
        onClick={() => fileInputRef.current.click()}
        disabled={isUploading}
        className="group relative flex items-center gap-3 px-8 py-4 rounded-2xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-teal-500/50 text-slate-300 transition-all duration-300 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isUploading ? (
          <>
            <svg className="animate-spin h-5 w-5 text-teal-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="font-medium">Uploading...</span>
          </>
        ) : (
          <>
            <svg 
              width="20" 
              height="20" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round"
              className="text-teal-400 group-hover:translate-y-[-2px] transition-transform"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="font-medium tracking-wide">Upload Audio File</span>
          </>
        )}
      </button>
      <div className="flex flex-col items-center gap-1">
        <p className="text-slate-500 text-[10px] uppercase tracking-[0.2em] font-bold">
          Supported: WAV, MP3, M4A, FLAC
        </p>
      </div>
    </div>
  );
}
