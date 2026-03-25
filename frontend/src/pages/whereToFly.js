import React, { useState, useTransition, useId, useCallback } from 'react';
import { MapPin, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { whereToFly } from '../api';

const COLORS = ['#f5a623', '#e8930c', '#d4800a', '#c06d08', '#ab5a06', '#964804', '#f7b84e', '#f9ca78', '#e09520', '#cc8218'];

function WhereToFly() {
  const [origin, setOrigin] = useState('');
  const [limit, setLimit] = useState(10);
  const [nonstop, setNonstop] = useState(false);
  const [destinations, setDestinations] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [showQuery, setShowQuery] = useState(false);
  const [searched, setSearched] = useState(false);

  // React 19: useTransition for non-blocking search
  const [isPending, startTransition] = useTransition();

  // React 19: useId for accessible form labels
  const originId = useId();
  const limitId = useId();
  const nonstopId = useId();

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!origin) return;
    setError('');
    setDestinations([]);
    setSearched(true);

    startTransition(async () => {
      try {
        const res = await whereToFly({ origin, limit, nonstop });
        setDestinations(res.data.destinations || []);
        setQuery(res.data.query || '');
      } catch (err) {
        setError(err.response?.data?.error || err.message);
        setQuery(err.response?.data?.query || '');
      }
    });
  }, [origin, limit, nonstop]);

  const chartData = destinations.map(d => ({
    name: d.destinationairport || d.destinationAirport,
    minFare: Number(d.minfare || d.minFare || 0),
    avgFare: Number(d.avgfare || d.avgFare || 0),
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload?.length) {
      return (
        <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: 10, padding: '12px 16px', fontSize: 13, color: '#c0c0c0', boxShadow: '0 0 20px rgba(0,0,0,0.5)' }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>{label}</div>
          {payload.map((p, i) => (
            <div key={i} style={{ color: p.color }}>{p.name}: ${Number(p.value).toFixed(2)}</div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="page-container">
      <title>Where to Fly ÔÇö SkyQuery</title>

      <div className="page-hero">
        <h1>­ƒù║ Where to Fly</h1>
        <p>Discover the cheapest destinations from any airport</p>
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
              <label htmlFor={limitId}>Show Top</label>
              <select id={limitId} value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={15}>15</option>
                <option value={20}>20</option>
              </select>
            </div>
            <button className="btn-primary" type="submit" disabled={isPending || !origin}>
              <Search size={18} />
              {isPending ? 'Searching...' : 'Explore'}
            </button>
          </div>
          <div className="checkbox-group">
            <input type="checkbox" id={nonstopId} checked={nonstop} onChange={(e) => setNonstop(e.target.checked)} />
            <label htmlFor={nonstopId}>Nonstop flights only</label>
          </div>
        </div>
      </form>

      {error && <div className="error-banner">ÔÜá {error}</div>}

      {isPending && (
        <div className="loading-container">
          <div className="spinner" />
          <div className="loading-text">
            Finding cheapest destinations...
            <span className="warning">ÔÅ▒ Hive queries may take 2ÔÇô8 minutes on 80M rows</span>
          </div>
        </div>
      )}

      {!isPending && destinations.length > 0 && (
        <>
          <div className="chart-container">
            <div className="chart-title">Cheapest Destinations from {origin}</div>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis type="number" stroke="#333" tickFormatter={(v) => `$${v}`} />
                <YAxis type="category" dataKey="name" stroke="#555" width={50} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="minFare" name="Min Fare" radius={[0, 6, 6, 0]}>
                  {chartData.map((_, i) => (<Cell key={i} fill={COLORS[i % COLORS.length]} />))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="dest-grid">
            {destinations.map((d, i) => (
              <div className="dest-card" key={i}>
                <div className="rank-badge">{i + 1}</div>
                <div className="dest-airport">{d.destinationairport || d.destinationAirport}</div>
                <div className="dest-price">${Number(d.minfare || d.minFare || 0).toFixed(0)}<span> min</span></div>
                <div className="dest-avg">Avg: ${Number(d.avgfare || d.avgFare || 0).toFixed(0)}</div>
                <div className="dest-count">{Number(d.flightcount || d.flightCount || 0).toLocaleString()} flights</div>
              </div>
            ))}
          </div>
        </>
      )}

      {!isPending && searched && destinations.length === 0 && !error && (
        <div className="empty-state"><div className="icon">­ƒöì</div><h3>No destinations found</h3><p>Try a different origin airport</p></div>
      )}

      {!searched && !isPending && (
        <div className="empty-state"><div className="icon"><MapPin size={48} /></div><h3>Explore destinations</h3><p>Enter your departure airport to discover cheapest places to fly</p></div>
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

export default WhereToFly;
