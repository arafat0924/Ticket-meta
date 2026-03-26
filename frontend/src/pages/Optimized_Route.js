import React, { useState } from 'react';
import { Search, Map } from 'lucide-react';

function OptimizedRoute() {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [error, setError] = useState('');

  const handleSearch = (e) => {
    e.preventDefault();
    if (!origin || !destination || !date) {
      setError('Please fill in all three fields (Origin, Destination, and Date) before searching.');
      return;
    }
    
    setError('');
    console.log({ origin, destination, date });
  };

  return (
    <div className="page-container">
      <title>Optimized Route — SkyQuery</title>

      <div className="page-hero">
        <h1><Map size={30} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} /> Optimized Route</h1>
        <p>Find the best multi-segment flights for maximum savings</p>
      </div>

      <form onSubmit={handleSearch}>
        <div className="search-panel">
          <div className="search-row">
            <div className="input-group">
              <label>Origin</label>
              <input 
                type="text" 
                placeholder="From: LAX" 
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())} 
              />
            </div>
            
            <div className="input-group">
              <label>Destination</label>
              <input 
                type="text" 
                placeholder="To: JFK" 
                value={destination}
                onChange={(e) => setDestination(e.target.value.toUpperCase())} 
              />
            </div>

            <div className="input-group">
              <label>Departure Date</label>
              <input 
                type="date" 
                placeholder="Departure Date"
                value={date} 
                onChange={(e) => setDate(e.target.value)} 
              />
            </div>

            <button className="btn-primary" type="submit">
              <Search size={18} />
              Search
            </button>
          </div>
        </div>
      </form>

      {error && <div className="error-banner" style={{ marginTop: '16px' }}>⚠ {error}</div>}

      <div id="results-container"></div>
    </div>
  );
}

export default OptimizedRoute;
