import React, { useState, useTransition, useId, useCallback } from 'react';
import { BarChart3, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { airlineComparison } from '../api';

function AirlineComparison() {
  const [origin, setOrigin] = useState('');
  const [dest, setDest] = useState('');
  const [airlines, setAirlines] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [showQuery, setShowQuery] = useState(false);
  const [searched, setSearched] = useState(false);

  const [isPending, startTransition] = useTransition();
  const originId = useId();
  const destId = useId();

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!origin || !dest) return;
    setError('');
    setAirlines([]);
    setSearched(true);

    startTransition(async () => {
      try {
        const res = await airlineComparison({ origin, dest });
        setAirlines(res.data.airlines || []);
        setQuery(res.data.query || '');
      } catch (err) {
        setError(err.response?.data?.error || err.message);
        setQuery(err.response?.data?.query || '');
      }
    });
  }, [origin, dest]);

  const chartData = airlines.map(a => ({
    name: (a.airline || 'Unknown').length > 20 ? (a.airline || 'Unknown').substring(0, 18) + '...' : (a.airline || 'Unknown'),
    minFare: Number(a.minfare || a.minFare || 0),
    avgFare: Number(a.avgfare || a.avgFare || 0),
    maxFare: Number(a.maxfare || a.maxFare || 0),
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload?.length) {
      return (
        <div style={{ background: '#1e1b4b', border: '1px solid #6366f1', borderRadius: 10, padding: '12px 16px', fontSize: 13, color: '#e2e8f0' }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>{label}</div>
          {payload.map((p, i) => (
            <div key={i} style={{ color: p.color, marginBottom: 2 }}>{p.name}: ${Number(p.value).toFixed(2)}</div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="page-container">
      <title>Airline Comparison — SkyQuery</title>

      <div className="page-hero">
        <h1>📊 Airline Comparison</h1>
        <p>Compare airline prices on any route</p>
      </div>

      <form onSubmit={handleSearch}>
        <div className="search-panel">
          <div className="search-row">
            <div className="input-group">
              <label htmlFor={originId}>From</label>
              <input id={originId} type="text" placeholder="e.g. ATL" value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())} maxLength={3} required />
            </div>
            <div className="input-group">
              <label htmlFor={destId}>To</label>
              <input id={destId} type="text" placeholder="e.g. LAX" value={dest}
                onChange={(e) => setDest(e.target.value.toUpperCase())} maxLength={3} required />
            </div>
            <button className="btn-primary" type="submit" disabled={isPending || !origin || !dest}>
              <Search size={18} />
              {isPending ? 'Comparing...' : 'Compare'}
            </button>
          </div>
        </div>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {isPending && (
        <div className="loading-container">
          <div className="spinner" />
          <div className="loading-text">
            Comparing airline prices...
            <span className="warning">⏱ Hive queries may take 2–8 minutes on 80M rows</span>
          </div>
        </div>
      )}

      {!isPending && airlines.length > 0 && (
        <>
          <div className="chart-container">
            <div className="chart-title">Airline Price Comparison: {origin} → {dest}</div>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} angle={-35} textAnchor="end" height={80} />
                <YAxis stroke="#64748b" tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                <Bar dataKey="minFare" name="Min Fare" fill="#22c55e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="avgFare" name="Avg Fare" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="maxFare" name="Max Fare" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="airline-grid">
            {airlines.map((a, i) => (
              <div className="airline-card" key={i}>
                <div className="airline-card-name">{a.airline || 'Unknown Airline'}</div>
                <div className="price-range">
                  <div className="price-item">
                    <span className="price-label">Min</span>
                    <span className="price-value min">${Number(a.minfare || a.minFare || 0).toFixed(0)}</span>
                  </div>
                  <div className="price-item">
                    <span className="price-label">Avg</span>
                    <span className="price-value avg">${Number(a.avgfare || a.avgFare || 0).toFixed(0)}</span>
                  </div>
                  <div className="price-item">
                    <span className="price-label">Max</span>
                    <span className="price-value max">${Number(a.maxfare || a.maxFare || 0).toFixed(0)}</span>
                  </div>
                </div>
                <div className="flight-count-bar">{Number(a.flightcount || a.flightCount || 0).toLocaleString()} flights available</div>
              </div>
            ))}
          </div>
        </>
      )}

      {!isPending && searched && airlines.length === 0 && !error && (
        <div className="empty-state"><div className="icon">🔍</div><h3>No airline data found</h3><p>Try different airport codes</p></div>
      )}

      {!searched && !isPending && (
        <div className="empty-state"><div className="icon"><BarChart3 size={48} /></div><h3>Compare airlines</h3><p>Enter origin and destination to compare airline prices</p></div>
      )}

      {query && (
        <div className="query-debug">
          <button className="query-toggle" onClick={() => setShowQuery(!showQuery)}>
            {showQuery ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {showQuery ? 'Hide' : 'Show'} HiveQL Query
          </button>
          {showQuery && <pre className="query-code">{query}</pre>}
        </div>
      )}
    </div>
  );
}

export default AirlineComparison;
