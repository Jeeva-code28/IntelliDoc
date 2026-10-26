import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import WorkspacePage from './pages/WorkspacePage';
import LearnMore from './pages/LearnMore';

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/workspace" element={<WorkspacePage />} />
      <Route path="/chat" element={<Navigate to="/workspace" replace />} />
      <Route path="/learn-more" element={<LearnMore />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
