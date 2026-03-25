import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import FlightSearch from './pages/FlightSearch';
import WhereToFly from './pages/WhereToFly';
import WhenToFly from './pages/WhenToFly';
import AirlineComparison from './pages/AirlineComparison';
import Chatbot from './pages/Chatbot';
import AirportExplorer from './pages/AirportExplorer';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import FlightSplicing from './pages/FlightSplicing';
import BudgetExplorer from './pages/BudgetExplorer';
import './App.css';

function AppContent() {
  const location = useLocation();
  const isLanding = location.pathname === '/';

  return (
    <div className="app">
      {!isLanding && <Navbar />}
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/flights" element={<FlightSearch />} />
        <Route path="/where-to-fly" element={<WhereToFly />} />
        <Route path="/when-to-fly" element={<WhenToFly />} />
        <Route path="/airline-comparison" element={<AirlineComparison />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        <Route path="/budget-explorer" element={<BudgetExplorer />} />
        <Route path="/flight-splicing" element={<FlightSplicing />} />
        <Route path="/chatbot" element={<Chatbot />} />
        <Route path="/airports" element={<AirportExplorer />} />
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
