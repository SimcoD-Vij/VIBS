import { useMemo, useState } from 'react';

export function TranscriptView({ segments, speakers }) {
  const [filter, setFilter] = useState('');
  
  const speakerMap = useMemo(() => {
    return speakers.reduce((acc, s) => ({
      ...acc,
      [s.speaker_label]: s
    }), {});
  }, [speakers]);

  const filteredSegments = segments.filter(seg => 
    seg.text.toLowerCase().includes(filter.toLowerCase()) ||
    (speakerMap[seg.speaker_label]?.display_name || '').toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="bg-slate-800/80 backdrop-blur-md rounded-2xl p-6 shadow-xl border border-slate-700 h-[600px] flex flex-col">
      <div className="mb-4">
        <input 
          type="text" 
          placeholder="Search transcript..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-teal-500 transition-colors"
        />
      </div>
      
      <div className="flex-1 overflow-y-auto pr-4 space-y-4 custom-scrollbar">
        {filteredSegments.map(seg => {
          const spk = speakerMap[seg.speaker_label] || { display_name: seg.speaker_label, color: '#888' };
          const time = `${Math.floor(seg.start_time/60)}:${Math.floor(seg.start_time%60).toString().padStart(2,'0')}`;
          
          return (
            <div key={seg.id} className={`p-4 rounded-xl border border-slate-700/50 bg-slate-900/30 hover:bg-slate-700/30 transition-colors ${seg.is_overlap ? 'bg-[url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDUpIiBzdHJva2Utd2lkdGg9IjIiPjxwb2x5Z29uIHBvaW50cz0iMCAwIDEwIDAgMCAxMCIvPjwvc3ZnPg==")]' : ''}`}>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full shadow-sm" style={{ backgroundColor: spk.color }} />
                <span className="font-semibold text-slate-300" style={{ color: spk.color }}>{spk.display_name}</span>
                <span className="text-xs text-slate-500 font-mono ml-2">{time}</span>
                {seg.is_overlap && <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded ml-auto">OVERLAP</span>}
              </div>
              <p className="text-slate-300 leading-relaxed text-sm">
                {seg.text}
              </p>
            </div>
          );
        })}
        {filteredSegments.length === 0 && (
          <div className="text-center text-slate-500 py-10">No matching segments found.</div>
        )}
      </div>
    </div>
  );
}
