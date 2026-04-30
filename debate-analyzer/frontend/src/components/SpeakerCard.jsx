import { useState, useRef } from 'react';

export function SpeakerCard({ speaker, onRename }) {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(speaker.display_name);

  const handleBlur = () => {
    setIsEditing(false);
    if(name !== speaker.display_name) {
      onRename(speaker.speaker_label, name);
    }
  };

  const percent = Math.round((speaker.talk_share || 0) * 100);
  const mins = Math.floor((speaker.total_seconds || 0) / 60);
  const secs = Math.round((speaker.total_seconds || 0) % 60);

  return (
    <div className="bg-slate-800/80 backdrop-blur-md rounded-2xl p-6 shadow-xl border border-slate-700 hover:border-slate-600 transition-all duration-300 relative overflow-hidden group">
      <div 
        className="absolute top-0 left-0 w-1.5 h-full"
        style={{ backgroundColor: speaker.color }}
      />
      <div className="flex items-center justify-between mb-4 pl-4">
        <div className="flex items-center gap-3">
          <div 
            className="w-4 h-4 rounded-full shadow-[0_0_10px_rgba(255,255,255,0.3)]"
            style={{ backgroundColor: speaker.color }}
          />
          {isEditing ? (
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={handleBlur}
              onKeyDown={(e) => e.key === 'Enter' && handleBlur()}
              className="bg-slate-900 border-b border-teal-500 text-slate-100 focus:outline-none px-1 text-xl font-semibold"
            />
          ) : (
            <h3 
              onDoubleClick={() => setIsEditing(true)}
              className="text-xl font-semibold text-slate-100 cursor-pointer group-hover:text-teal-300 transition-colors duration-200"
              title="Double click to edit"
            >
              {name}
            </h3>
          )}
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-slate-200">{percent}%</span>
          <span className="text-xs text-slate-500 block">of session</span>
        </div>
      </div>
      
      <div className="mb-4 bg-slate-700/50 rounded-full h-2 overflow-hidden">
        <div 
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${percent}%`, backgroundColor: speaker.color }}
        />
      </div>

      <p className="text-slate-400 text-sm mb-4 pl-4">
        Spoke for <strong className="text-slate-300">{mins}m {secs}s</strong>
      </p>

      <div className="bg-slate-900/50 rounded-xl p-4 pl-5 border border-slate-700/50">
        <h4 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Key Arguments</h4>
        <ul className="text-sm text-slate-300 space-y-2 list-disc list-inside">
          {speaker.summary ? speaker.summary.split('\n').map((point, i) => (
            <li key={i} className="leading-relaxed">{point.replace(/^- /, '')}</li>
          )) : <li>No arguments extracted.</li>}
        </ul>
      </div>
    </div>
  );
}
