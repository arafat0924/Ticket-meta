import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import FlightSearch from './pages/FlightSearch';
import WhereToFly from './pages/WhereToFly';
import WhenToFly from './pages/WhenToFly';
import AirlineComparison from './pages/AirlineComparison';
import Chatbot from './pages/Chatbot';
import AirportExplorer from './pages/AirportExplorer';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <Routes>
          <Route path="/" element={<FlightSearch />} />
          <Route path="/where-to-fly" element={<WhereToFly />} />
          <Route path="/when-to-fly" element={<WhenToFly />} />
          <Route path="/airline-comparison" element={<AirlineComparison />} />
          <Route path="/chatbot" element={<Chatbot />} />
          <Route path="/airports" element={<AirportExplorer />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
