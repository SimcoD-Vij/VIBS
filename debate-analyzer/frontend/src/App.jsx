import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { RecordPage } from './pages/RecordPage';
import { SessionPage } from './pages/SessionPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RecordPage />} />
        <Route path="/session/:sessionId" element={<SessionPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
