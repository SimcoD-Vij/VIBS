import { useMemo } from 'react';

export function TopicTimeline({ segments, shifts, duration, speakers }) {
  const speakerColors = useMemo(() => {
    return speakers.reduce((acc, s) => ({ ...acc, [s.speaker_label]: s.color }), {});
  }, [speakers]);

  const speakerRows = useMemo(() => {
    const rows = {};
    speakers.forEach(s => rows[s.speaker_label] = []);
    segments.forEach(seg => {
      if(rows[seg.speaker_label]) {
        rows[seg.speaker_label].push(seg);
      }
    });
    return rows;
  }, [segments, speakers]);

  return (
    <div className="bg-slate-800/80 backdrop-blur-md rounded-2xl p-6 shadow-xl border border-slate-700">
      <h3 className="text-lg font-semibold text-slate-200 mb-6">Conversation Timeline & Topic Shifts</h3>
      
      <div className="relative">
        {/* Timeline Axis */}
        <div className="flex justify-between text-xs text-slate-500 mb-2 px-[100px]">
          <span>0:00</span>
          <span>{Math.floor(duration/60)}:{(Math.round(duration%60)).toString().padStart(2,'0')}</span>
        </div>

        {/* Rows */}
        <div className="relative pl-[100px] border-l border-slate-700 py-2">
          {speakers.map(spk => (
            <div key={spk.speaker_label} className="h-8 mb-4 relative group">
              <div className="absolute -left-[90px] top-1/2 -translate-y-1/2 text-sm text-slate-400 font-medium truncate w-20 text-right">
                {spk.display_name}
              </div>
              <div className="absolute inset-0 bg-slate-900/50 rounded overflow-hidden">
                {speakerRows[spk.speaker_label].map(seg => {
                  const left = (seg.start_time / duration) * 100;
                  const width = ((seg.end_time - seg.start_time) / duration) * 100;
                  return (
                    <div 
                      key={seg.id}
                      className="absolute top-0 h-full cursor-pointer hover:brightness-125 transition-all"
                      style={{ 
                        left: `${left}%`, 
                        width: `${Math.max(width, 0.5)}%`, 
                        backgroundColor: speakerColors[spk.speaker_label] 
                      }}
                      title={seg.text}
                    />
                  );
                })}
              </div>
            </div>
          ))}

          {/* Topic Shift Markers */}
          {shifts.map((shift, idx) => {
            const left = (shift.time_seconds / duration) * 100;
            return (
              <div 
                key={idx} 
                className="absolute top-0 bottom-0 border-l border-dashed border-amber-500/50 z-10"
                style={{ left: `${left}%` }}
              >
                <div className="bg-slate-800 text-amber-400 text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap absolute -translate-x-1/2 -top-4 border border-amber-500/30">
                  {shift.to_topic}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
