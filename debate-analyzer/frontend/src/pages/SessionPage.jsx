import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../utils/api';
import { SpeakerCard } from '../components/SpeakerCard';
import { MindMap } from '../components/MindMap';
import { TopicTimeline } from '../components/TopicTimeline';
import { TranscriptView } from '../components/TranscriptView';
import ReactMarkdown from 'react-markdown';

export function SessionPage() {
  const { sessionId } = useParams();
  const [status, setStatus] = useState({ status: 'pending', progress_percent: 0 });
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('speakers');

  useEffect(() => {
    let interval;
    const checkStatus = async () => {
      try {
        const data = await api.getStatus(sessionId);
        setStatus(data);
        if (data.status === 'complete' || data.status === 'failed') {
          clearInterval(interval);
          if (data.status === 'complete') {
            const resData = await api.getResult(sessionId);
            setResult(resData);
          }
        }
      } catch (err) {
        console.error("Status check failed", err);
      }
    };

    checkStatus();
    interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleRename = async (label, newName) => {
    try {
      await api.renameSpeaker(sessionId, label, newName);
      setResult(prev => ({
        ...prev,
        speakers: prev.speakers.map(s => s.speaker_label === label ? { ...s, display_name: newName } : s)
      }));
    } catch (err) {
      console.error("Rename failed", err);
    }
  };

  if (status.status === 'failed') {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 p-8 flex flex-col items-center justify-center">
        <h1 className="text-3xl font-bold mb-4 text-red-500">Processing Failed</h1>
        <p className="text-slate-400 text-center max-w-md">There was an error analyzing this session. Please try recording again.</p>
      </div>
    );
  }

  if (!result || status.status !== 'complete') {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 p-8 flex flex-col items-center justify-center">
        <h1 className="text-3xl font-bold mb-8 bg-gradient-to-r from-teal-400 to-emerald-300 bg-clip-text text-transparent">
          Analyzing Session...
        </h1>
        <div className="w-full max-w-md bg-slate-800 rounded-full h-4 mb-4 overflow-hidden shadow-inner">
          <div 
            className="bg-gradient-to-r from-teal-500 to-emerald-400 h-4 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${status.progress_percent}%` }}
          />
        </div>
        <p className="text-slate-400 text-sm font-medium tracking-wide">
          {status.status.toUpperCase()} — {status.progress_percent}%
        </p>
      </div>
    );
  }

  const tabs = [
    { id: 'speakers', label: 'Speakers & Arguments' },
    { id: 'mindmap', label: 'Knowledge Graph' },
    { id: 'timeline', label: 'Topic Timeline' },
    { id: 'transcript', label: 'Transcript' }
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-4 md:p-8 selection:bg-teal-500/30">
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-col md:flex-row md:items-center justify-between mb-8 pb-6 border-b border-slate-700/50">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Session Analysis</h1>
            <p className="text-slate-400 text-sm mt-1">
              Duration: {Math.floor(result.session.duration_seconds / 60)}m {Math.floor(result.session.duration_seconds % 60)}s 
              • {result.session.speaker_count} Speakers
            </p>
          </div>
          <button 
            onClick={() => api.downloadPdf(sessionId)}
            className="mt-4 md:mt-0 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center gap-2"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Download PDF Report
          </button>
        </header>

        <div className="flex space-x-1 mb-8 overflow-x-auto pb-2 custom-scrollbar">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap
                ${activeTab === tab.id 
                  ? 'bg-teal-500/10 text-teal-400 border border-teal-500/30 shadow-[0_0_15px_rgba(20,184,166,0.15)]' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-transparent'
                }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <main className="min-h-[500px]">
          {activeTab === 'speakers' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {result.speakers.map(speaker => (
                <SpeakerCard key={speaker.id} speaker={speaker} onRename={handleRename} />
              ))}
            </div>
          )}

          {activeTab === 'mindmap' && (
            <div className="space-y-8">
              <MindMap graphData={result.graph} />
              
              {result.graph.explanation && (
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4 text-teal-400">Detailed Analysis</h3>
                  <div className="text-slate-300 prose prose-invert max-w-none">
                    <ReactMarkdown>{result.graph.explanation}</ReactMarkdown>
                  </div>
                </div>
              )}

              {result.graph.conclusion && (
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4 text-emerald-400">Conclusion</h3>
                  <div className="text-slate-300 prose prose-invert max-w-none">
                    <ReactMarkdown>{result.graph.conclusion}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'timeline' && (
            <TopicTimeline 
              segments={result.segments} 
              shifts={result.topic_shifts} 
              duration={result.session.duration_seconds} 
              speakers={result.speakers} 
            />
          )}

          {activeTab === 'transcript' && (
            <TranscriptView segments={result.segments} speakers={result.speakers} />
          )}
        </main>
      </div>
    </div>
  );
}
