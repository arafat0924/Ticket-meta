import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Search, MapPin, Calendar, BarChart3, MessageSquare, Building2, Plane } from 'lucide-react';
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
    <nav className="tl-nav tl-nav-pages">
      <div className="tl-nav-inner">
        <NavLink to="/" className="tl-nav-logo">
          <div className="tl-logo-icon"><Plane size={16} /></div>
          <span className="tl-logo-text">Data Turbulence</span>
        </NavLink>
        <div className="tl-nav-links">
          <NavLink to="/flights" className={({ isActive }) => `tl-nav-link ${isActive ? 'active' : ''}`}>
            <Search size={14} /> Flights
          </NavLink>
          <NavLink to="/where-to-fly" className={({ isActive }) => `tl-nav-link ${isActive ? 'active' : ''}`}>
            <MapPin size={14} /> Where to Fly
          </NavLink>
          <NavLink to="/when-to-fly" className={({ isActive }) => `tl-nav-link ${isActive ? 'active' : ''}`}>
            <Calendar size={14} /> When to Fly
          </NavLink>
          <NavLink to="/airline-comparison" className={({ isActive }) => `tl-nav-link ${isActive ? 'active' : ''}`}>
            <BarChart3 size={14} /> Airlines
          </NavLink>
          <NavLink to="/chatbot" className={({ isActive }) => `tl-nav-link ${isActive ? 'active' : ''}`}>
            <MessageSquare size={14} /> AI Chat
          </NavLink>
          <NavLink to="/airports" className={({ isActive }) => `tl-nav-link ${isActive ? 'active' : ''}`}>
            <Building2 size={14} /> Airports
          </NavLink>
        </div>
        <div className={`health-dot ${health}`} title={`Backend: ${health}`} />
      </div>
    </nav>
  );
}

export default Navbar;
