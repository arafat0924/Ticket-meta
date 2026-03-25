import React, { useState, useTransition, useId, useCallback } from 'react';
import { DollarSign, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, Cell } from 'recharts';
import { whereToFlyBudget } from '../api';

const COLORS = ['#22c55e', '#3b82f6', '#f5a623', '#ef4444', '#a855f7', '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16'];

function BudgetExplorer() {
  const [origin, setOrigin] = useState('');
  const [budget, setBudget] = useState('');
  const [nonstop, setNonstop] = useState(false);
  const [destinations, setDestinations] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [showQuery, setShowQuery] = useState(false);
  const [searched, setSearched] = useState(false);

  const [isPending, startTransition] = useTransition();
  const originId = useId();
  const budgetId = useId();
  const nonstopId = useId();

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!origin) return;
    setError('');
    setDestinations([]);
    setSearched(true);

    startTransition(async () => {
      try {
        const res = await whereToFlyBudget({ origin, budget: budget || undefined, nonstop, limit: 50 });
        setDestinations(res.data.destinations || []);
        setQuery(res.data.query || '');
      } catch (err) {
        setError(err.response?.data?.error || err.message);
        setQuery(err.response?.data?.query || '');
      }
    });
  }, [origin, budget, nonstop]);

  const g = (obj, key) => Number(obj[key] || obj[key.toLowerCase()] || 0);

  const scatterData = destinations.map(d => ({
    airport: d.destinationAirport || d.destinationairport,
    distance: g(d, 'avgDistance'),
    fare: g(d, 'minFare'),
    avgFare: g(d, 'avgFare'),
    flights: g(d, 'flightCount'),
  }));

  // Find best value (furthest distance per dollar)
  const bestValue = scatterData.length > 0
    ? scatterData.reduce((best, d) => (d.distance / d.fare) > (best.distance / best.fare) ? d : best)
    : null;

  // Find cheapest
  const cheapest = scatterData.length > 0
    ? scatterData.reduce((c, d) => d.fare < c.fare ? d : c)
    : null;

  // Find furthest
  const furthest = scatterData.length > 0
    ? scatterData.reduce((f, d) => d.distance > f.distance ? d : f)
    : null;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload?.length) {
      const d = payload[0].payload;
      return (
        <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: 10, padding: '12px 16px', fontSize: 13, color: '#c0c0c0', boxShadow: '0 0 20px rgba(0,0,0,0.5)' }}>
          <div style={{ fontWeight: 700, marginBottom: 6, fontSize: 16 }}>✈️ {d.airport}</div>
          <div style={{ color: '#22c55e', marginBottom: 2 }}>Min Fare: ${d.fare.toFixed(2)}</div>
          <div style={{ color: '#f5a623', marginBottom: 2 }}>Avg Fare: ${d.avgFare.toFixed(2)}</div>
          <div style={{ color: '#3b82f6', marginBottom: 2 }}>Distance: {d.distance.toLocaleString()} mi</div>
          <div style={{ color: '#888' }}>Flights: {d.flights.toLocaleString()}</div>
          <div style={{ color: '#a855f7', marginTop: 4, fontSize: 11 }}>
            Value: {(d.distance / d.fare).toFixed(1)} mi/$
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="page-container">
      <title>Budget Explorer — SkyQuery</title>

      <div className="page-hero">
        <h1>💰 Where Can I Afford to Go?</h1>
        <p>Discover destinations within your budget — see fare vs. distance for the best value</p>
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
              <label htmlFor={budgetId}>Budget ($)</label>
              <input id={budgetId} type="number" placeholder="e.g. 500 (optional)" value={budget}
                onChange={(e) => setBudget(e.target.value)} min={0} step={50} />
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

      {error && <div className="error-banner">⚠ {error}</div>}

      {isPending && (
        <div className="loading-container">
          <div className="spinner" />
          <div className="loading-text">
            Finding affordable destinations...
            <span className="warning">⏱ Hive queries may take 2–8 minutes on 80M rows</span>
          </div>
        </div>
      )}

      {!isPending && scatterData.length > 0 && (
        <>
          {/* Highlight cards */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
            {cheapest && (
              <div className="search-panel" style={{ flex: 1, minWidth: 200, textAlign: 'center', padding: '16px' }}>
                <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>🏷️ CHEAPEST</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: '#22c55e' }}>{cheapest.airport}</div>
                <div style={{ fontSize: 14, color: '#f5a623' }}>${cheapest.fare.toFixed(0)}</div>
                <div style={{ fontSize: 11, color: '#666' }}>{cheapest.distance.toLocaleString()} mi</div>
              </div>
            )}
            {furthest && (
              <div className="search-panel" style={{ flex: 1, minWidth: 200, textAlign: 'center', padding: '16px' }}>
                <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>🌍 FURTHEST</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: '#3b82f6' }}>{furthest.airport}</div>
                <div style={{ fontSize: 14, color: '#f5a623' }}>${furthest.fare.toFixed(0)}</div>
                <div style={{ fontSize: 11, color: '#666' }}>{furthest.distance.toLocaleString()} mi</div>
              </div>
            )}
            {bestValue && (
              <div className="search-panel" style={{ flex: 1, minWidth: 200, textAlign: 'center', padding: '16px' }}>
                <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>⭐ BEST VALUE</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: '#a855f7' }}>{bestValue.airport}</div>
                <div style={{ fontSize: 14, color: '#f5a623' }}>${bestValue.fare.toFixed(0)}</div>
                <div style={{ fontSize: 11, color: '#666' }}>{(bestValue.distance / bestValue.fare).toFixed(1)} mi per $</div>
              </div>
            )}
          </div>

          {/* Scatter / Bubble Chart */}
          <div className="chart-container">
            <div className="chart-title">
              Fare vs. Distance from {origin}
              {budget && <span style={{ color: '#ef4444', fontSize: 14, marginLeft: 8 }}>Budget: ${budget}</span>}
            </div>
            <ResponsiveContainer width="100%" height={500}>
              <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis
                  type="number" dataKey="distance" name="Distance"
                  stroke="#333" fontSize={12}
                  label={{ value: 'Distance (miles)', position: 'insideBottom', offset: -10, fill: '#555' }}
                  tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v}
                />
                <YAxis
                  type="number" dataKey="fare" name="Min Fare"
                  stroke="#333" fontSize={12}
                  label={{ value: 'Min Fare ($)', angle: -90, position: 'insideLeft', fill: '#555' }}
                  tickFormatter={(v) => `$${v}`}
                />
                <ZAxis type="number" dataKey="flights" range={[60, 400]} name="Flights" />
                <Tooltip content={<CustomTooltip />} />
                <Scatter name="Destinations" data={scatterData} fillOpacity={0.8}>
                  {scatterData.map((entry, i) => (
                    <Cell key={i} fill={
                      entry.airport === bestValue?.airport ? '#a855f7' :
                      entry.airport === cheapest?.airport ? '#22c55e' :
                      entry.airport === furthest?.airport ? '#3b82f6' :
                      COLORS[i % COLORS.length]
                    } />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          {/* Data table */}
          <div className="data-table-wrapper" style={{ marginTop: 16 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Destination</th>
                  <th>Min Fare</th>
                  <th>Avg Fare</th>
                  <th>Distance (mi)</th>
                  <th>Value (mi/$)</th>
                  <th>Flights</th>
                </tr>
              </thead>
              <tbody>
                {scatterData.map((d, i) => (
                  <tr key={i}>
                    <td style={{ color: '#555' }}>{i + 1}</td>
                    <td style={{ fontWeight: 700 }}>
                      {d.airport}
                      {d.airport === bestValue?.airport && <span style={{ color: '#a855f7', marginLeft: 6, fontSize: 11 }}>⭐ Best Value</span>}
                    </td>
                    <td style={{ color: '#22c55e', fontWeight: 600 }}>${d.fare.toFixed(2)}</td>
                    <td>${d.avgFare.toFixed(2)}</td>
                    <td>{d.distance.toLocaleString()}</td>
                    <td style={{ color: '#a855f7' }}>{(d.distance / d.fare).toFixed(1)}</td>
                    <td>{d.flights.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!isPending && searched && scatterData.length === 0 && !error && (
        <div className="empty-state"><div className="icon">🔍</div><h3>No destinations found</h3><p>Try a different airport or increase your budget</p></div>
      )}

      {!searched && !isPending && (
        <div className="empty-state">
          <div className="icon"><DollarSign size={48} /></div>
          <h3>Explore destinations by budget</h3>
          <p>Enter your departure airport and optional budget to see a scatter chart<br />
          of fare vs. distance — highlighting the cheapest, furthest, and best-value destinations.</p>
        </div>
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

export default BudgetExplorer;
