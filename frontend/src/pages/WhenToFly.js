import React, { useState, useTransition, useId, useCallback } from 'react';
import { Calendar, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { whenToFly } from '../api';

function WhenToFly() {
  const [origin, setOrigin] = useState('');
  const [dest, setDest] = useState('');
  const [months, setMonths] = useState([]);
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
    setMonths([]);
    setSearched(true);

    startTransition(async () => {
      try {
        const res = await whenToFly({ origin, dest });
        setMonths(res.data.months || []);
        setQuery(res.data.query || '');
      } catch (err) {
        setError(err.response?.data?.error || err.message);
        setQuery(err.response?.data?.query || '');
      }
    });
  }, [origin, dest]);

  const chartData = months.map(m => ({
    month: m.month,
    minFare: Number(m.minfare || m.minFare || 0),
    avgFare: Number(m.avgfare || m.avgFare || 0),
    maxFare: Number(m.maxfare || m.maxFare || 0),
  }));

  const cheapestMonth = chartData.length > 0
    ? chartData.reduce((a, b) => a.minFare < b.minFare ? a : b)
    : null;

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload?.length) {
      return (
        <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: 10, padding: '12px 16px', fontSize: 13, color: '#c0c0c0', boxShadow: '0 0 20px rgba(0,0,0,0.5)' }}>
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
      <title>When to Fly — SkyQuery</title>

      <div className="page-hero">
        <h1>📅 When to Fly</h1>
        <p>Find the cheapest month to fly on any route</p>
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
              {isPending ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
        </div>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {isPending && (
        <div className="loading-container">
          <div className="spinner" />
          <div className="loading-text">
            Analyzing price trends by month...
            <span className="warning">⏱ Hive queries may take 2–8 minutes on 80M rows</span>
          </div>
        </div>
      )}

      {!isPending && months.length > 0 && (
        <>
          {cheapestMonth && (
            <div className="search-panel" style={{ textAlign: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: 14, color: '#555', marginBottom: 4 }}>💡 Best time to fly</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: '#22c55e' }}>{cheapestMonth.month}</div>
              <div style={{ fontSize: 16, color: '#666' }}>
                from <strong style={{ color: '#f5a623' }}>${cheapestMonth.minFare.toFixed(0)}</strong>
              </div>
            </div>
          )}

          <div className="chart-container">
            <div className="chart-title">Price Trends: {origin} → {dest}</div>
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorMin" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorAvg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f5a623" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f5a623" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorMax" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="month" stroke="#333" fontSize={12} />
                <YAxis stroke="#333" tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="maxFare" name="Max Fare" stroke="#f59e0b" fill="url(#colorMax)" strokeWidth={1.5} />
                <Area type="monotone" dataKey="avgFare" name="Avg Fare" stroke="#f5a623" fill="url(#colorAvg)" strokeWidth={2} />
                <Area type="monotone" dataKey="minFare" name="Min Fare" stroke="#22c55e" fill="url(#colorMin)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr><th>Month</th><th>Min Fare</th><th>Avg Fare</th><th>Max Fare</th><th>Flights</th></tr>
              </thead>
              <tbody>
                {months.map((m, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{m.month}</td>
                    <td className="fare-cell" style={{ color: '#22c55e' }}>${Number(m.minfare || m.minFare || 0).toFixed(2)}</td>
                    <td className="fare-cell">${Number(m.avgfare || m.avgFare || 0).toFixed(2)}</td>
                    <td className="fare-cell" style={{ color: '#f59e0b' }}>${Number(m.maxfare || m.maxFare || 0).toFixed(2)}</td>
                    <td>{Number(m.flightcount || m.flightCount || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!isPending && searched && months.length === 0 && !error && (
        <div className="empty-state"><div className="icon">🔍</div><h3>No data found</h3><p>Try different airport codes</p></div>
      )}

      {!searched && !isPending && (
        <div className="empty-state"><div className="icon"><Calendar size={48} /></div><h3>Analyze price trends</h3><p>Enter origin and destination to see prices by month</p></div>
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

export default WhenToFly;
