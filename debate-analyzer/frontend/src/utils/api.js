const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const api = {
  getStatus:  (id) => fetch(`${BASE}/api/session/${id}/status`).then(r => r.json()),
  getResult:  (id) => fetch(`${BASE}/api/session/${id}/result`).then(r => {
    if(r.status === 202) return null;
    if(!r.ok) throw new Error('Result fetch failed');
    return r.json();
  }),
  renameSpeaker: (id, label, name) =>
    fetch(`${BASE}/api/session/${id}/speaker/${label}`, {
      method: 'PATCH',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({display_name: name})
    }),
  downloadPdf: (id) => window.open(`${BASE}/api/session/${id}/export/pdf`)
};
