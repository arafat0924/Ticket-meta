import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Search, MapPin, Calendar, BarChart3, MessageSquare, Building2 } from 'lucide-react';
import { healthCheck } from '../api';

function Navbar() {
  const [health, setHealth] = useState('checking');

  useEffect(() => {
    healthCheck()
      .then(res => setHealth(res.data.status === 'connected' ? 'connected' : 'error'))
      .catch(() => setHealth('error'));
    
    const interval = setInterval(() => {
      healthCheck()
        .then(res => setHealth(res.data.status === 'connected' ? 'connected' : 'error'))
        .catch(() => setHealth('error'));
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-logo">
          <div className="logo-icon">✈</div>
          SkyQuery
        </NavLink>
        <div className="nav-links">
          <NavLink to="/flights" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Search size={16} /> Flights
          </NavLink>
          <NavLink to="/where-to-fly" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <MapPin size={16} /> Where to Fly
          </NavLink>
          <NavLink to="/when-to-fly" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Calendar size={16} /> When to Fly
          </NavLink>
          <NavLink to="/airline-comparison" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <BarChart3 size={16} /> Airlines
          </NavLink>
          <NavLink to="/chatbot" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <MessageSquare size={16} /> AI Chat
          </NavLink>
          <NavLink to="/airports" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Building2 size={16} /> Airports
          </NavLink>
        </div>
        <div className={`health-dot ${health}`} title={`Backend: ${health}`} />
      </div>
    </nav>
  );
}

export default Navbar;
