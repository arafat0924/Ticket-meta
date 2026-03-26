import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import FlightSearch from './pages/FlightSearch';
import Chatbot from './pages/Chatbot';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import FlightSplicing from './pages/FlightSplicing';
import DataEnrichment from './pages/DataEnrichment';
import './App.css';

function AppContent() {
  const location = useLocation();
  const isLanding = location.pathname === '/';

  return (
    <div className={`app${isLanding ? ' landing-active' : ''}`}>
      {!isLanding && <Navbar />}
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/flights" element={<FlightSearch />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        <Route path="/flight-splicing" element={<FlightSplicing />} />
        <Route path="/chatbot" element={<Chatbot />} />
        <Route path="/enrichment" element={<DataEnrichment />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
