import React, { useState, useTransition, useId, useCallback } from 'react';
import { Scissors, Search, ChevronDown, ChevronUp, ArrowRight, Clock, DollarSign, Percent } from 'lucide-react';
import { flightSplicing } from '../api';

function FlightSplicing() {
  const [origin, setOrigin] = useState('');
  const [dest, setDest] = useState('');
  const [maxLayover, setMaxLayover] = useState(4);
  const [minLayover, setMinLayover] = useState(1.5);
  const [limit, setLimit] = useState(20);
  const [direct, setDirect] = useState(null);
  const [itineraries, setItineraries] = useState([]);
  const [error, setError] = useState('');
  const [queries, setQueries] = useState({});
  const [showQuery, setShowQuery] = useState(false);
  const [searched, setSearched] = useState(false);

  const [isPending, startTransition] = useTransition();
  const originId = useId();
  const destId = useId();

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!origin || !dest) return;
    setError('');
    setItineraries([]);
    setDirect(null);
    setSearched(true);

    startTransition(async () => {
      try {
        const res = await flightSplicing({ origin, dest, maxLayover, minLayover, limit });
        setDirect(res.data.direct || {});
        setItineraries(res.data.itineraries || []);
        setQueries({
          direct: res.data.directQuery || '',
          splice: res.data.spliceQuery || '',
        });
      } catch (err) {
        setError(err.response?.data?.error || err.message);
      }
    });
  }, [origin, dest, maxLayover, minLayover, limit]);

  const g = (obj, key) => {
    if (!obj) return 0;
    return Number(obj[key] || obj[key.toLowerCase()] || 0);
  };

  const bestDirect = direct ? g(direct, 'bestDirect') : 0;
  const avgDirect = direct ? g(direct, 'avgDirect') : 0;
  const directCount = direct ? g(direct, 'directCount') : 0;

  return (
    <div className="page-container">
      <title>Flight Splicing — SkyQuery</title>

      <div className="page-hero">
        <h1>✂️ Intelligent Flight Splicing</h1>
        <p>Find hidden savings by combining disconnected flight segments into virtual itineraries</p>
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
              <input id={destId} type="text" placeholder="e.g. SFO" value={dest}
                onChange={(e) => setDest(e.target.value.toUpperCase())} maxLength={3} required />
            </div>
            <div className="input-group">
              <label>Min Layover (hrs)</label>
              <select value={minLayover} onChange={(e) => setMinLayover(Number(e.target.value))}>
                <option value={1}>1 hr</option>
                <option value={1.5}>1.5 hrs</option>
                <option value={2}>2 hrs</option>
              </select>
            </div>
            <div className="input-group">
              <label>Max Layover (hrs)</label>
              <select value={maxLayover} onChange={(e) => setMaxLayover(Number(e.target.value))}>
                <option value={3}>3 hrs</option>
                <option value={4}>4 hrs</option>
                <option value={6}>6 hrs</option>
                <option value={8}>8 hrs</option>
              </select>
            </div>
            <button className="btn-primary" type="submit" disabled={isPending || !origin || !dest}>
              <Scissors size={18} />
              {isPending ? 'Splicing...' : 'Find Savings'}
            </button>
          </div>
        </div>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {isPending && (
        <div className="loading-container">
          <div className="spinner" />
          <div className="loading-text">
            Scanning flight combinations via intermediate hubs...
            <span className="warning">⏱ This JOIN query may take 5–15 minutes on 80M rows</span>
          </div>
        </div>
      )}

      {!isPending && searched && direct && (
        <>
          {/* Direct Flight Baseline */}
          <div className="search-panel" style={{ textAlign: 'center', marginBottom: 20 }}>
            <div style={{ fontSize: 14, color: '#555', marginBottom: 8 }}>🎯 Direct Flight Baseline: {origin} → {dest}</div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 32, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: 12, color: '#666' }}>Best Direct Price</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#f5a623' }}>
                  {bestDirect > 0 ? `$${bestDirect.toFixed(2)}` : 'N/A'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#666' }}>Avg Direct Price</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#888' }}>
                  {avgDirect > 0 ? `$${avgDirect.toFixed(2)}` : 'N/A'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#666' }}>Direct Flights Found</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#3b82f6' }}>
                  {directCount.toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          {/* Spliced Itineraries */}
          {itineraries.length > 0 ? (
            <>
              <div className="chart-title" style={{ marginBottom: 16 }}>
                ✂️ Found {itineraries.length} Spliced Itineraries
                {bestDirect > 0 && itineraries[0] && (
                  <span style={{ fontSize: 14, color: '#22c55e', marginLeft: 12 }}>
                    Best saves up to ${g(itineraries[0], 'savings').toFixed(2)} ({g(itineraries[0], 'savingsPercent').toFixed(1)}%)
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {itineraries.map((it, i) => {
                  const hub = it.hub || it.hub;
                  const fare1 = g(it, 'fare1');
                  const fare2 = g(it, 'fare2');
                  const combined = g(it, 'combinedFare');
                  const savings = g(it, 'savings');
                  const savingsPct = g(it, 'savingsPercent');
                  const layover = g(it, 'layoverHours');
                  const airline1 = it.airline1 || 'Unknown';
                  const airline2 = it.airline2 || 'Unknown';
                  const date = it.flightDate || it.flightdate || '';
                  const isCrossAlliance = airline1 !== airline2;

                  return (
                    <div key={i} className="search-panel" style={{ padding: '16px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                        {/* Route visualization */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 2, minWidth: 280 }}>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 18, fontWeight: 800, color: '#fff' }}>{origin}</div>
                            <div style={{ fontSize: 10, color: '#666' }}>{airline1.length > 15 ? airline1.substring(0, 13) + '…' : airline1}</div>
                            <div style={{ fontSize: 11, color: '#f5a623' }}>${fare1.toFixed(0)}</div>
                          </div>
                          <ArrowRight size={16} style={{ color: '#555' }} />
                          <div style={{ textAlign: 'center', background: '#111', padding: '6px 12px', borderRadius: 8, border: '1px solid #222' }}>
                            <div style={{ fontSize: 16, fontWeight: 700, color: '#a855f7' }}>{hub}</div>
                            <div style={{ fontSize: 10, color: '#666', display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'center' }}>
                              <Clock size={10} /> {layover.toFixed(1)}h layover
                            </div>
                          </div>
                          <ArrowRight size={16} style={{ color: '#555' }} />
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 18, fontWeight: 800, color: '#fff' }}>{dest}</div>
                            <div style={{ fontSize: 10, color: '#666' }}>{airline2.length > 15 ? airline2.substring(0, 13) + '…' : airline2}</div>
                            <div style={{ fontSize: 11, color: '#f5a623' }}>${fare2.toFixed(0)}</div>
                          </div>
                        </div>

                        {/* Date */}
                        <div style={{ textAlign: 'center', minWidth: 80 }}>
                          <div style={{ fontSize: 10, color: '#666' }}>Date</div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: '#888' }}>{date}</div>
                          {isCrossAlliance && (
                            <div style={{ fontSize: 9, color: '#ec4899', marginTop: 4, background: 'rgba(236,72,153,0.1)', borderRadius: 4, padding: '2px 6px' }}>
                              🔀 Cross-Alliance
                            </div>
                          )}
                        </div>

                        {/* Combined Price */}
                        <div style={{ textAlign: 'center', minWidth: 100 }}>
                          <div style={{ fontSize: 10, color: '#666' }}>Combined Fare</div>
                          <div style={{ fontSize: 22, fontWeight: 800, color: '#22c55e' }}>${combined.toFixed(0)}</div>
                        </div>

                        {/* Savings */}
                        {savings > 0 && (
                          <div style={{ textAlign: 'center', minWidth: 100, background: 'rgba(34,197,94,0.1)', borderRadius: 8, padding: '8px 12px' }}>
                            <div style={{ fontSize: 10, color: '#22c55e' }}>Savings</div>
                            <div style={{ fontSize: 18, fontWeight: 800, color: '#22c55e' }}>${savings.toFixed(0)}</div>
                            <div style={{ fontSize: 11, color: '#22c55e' }}>({savingsPct.toFixed(1)}% off)</div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <div className="icon">✂️</div>
              <h3>No spliced itineraries found</h3>
              <p>No viable hub connections found for {origin} → {dest} within the layover window. Try adjusting layover times or different airports.</p>
            </div>
          )}
        </>
      )}

      {!searched && !isPending && (
        <div className="empty-state">
          <div className="icon"><Scissors size={48} /></div>
          <h3>Discover hidden savings</h3>
          <p>The Flight Splicing Engine scans millions of flights to find two-segment combinations<br />
          (A→Hub + Hub→B) that beat direct flight prices. It enforces realistic layover times<br />
          and highlights cross-airline "Frankenstein" routes for maximum savings.</p>
        </div>
      )}

      {(queries.direct || queries.splice) && (
        <div className="query-debug" style={{ marginTop: 24 }}>
          <button className="query-toggle" onClick={() => setShowQuery(!showQuery)}>
            {showQuery ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {showQuery ? 'Hide' : 'Show'} HiveQL Queries
          </button>
          {showQuery && (
            <>
              {queries.direct && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 12, color: '#f5a623', fontWeight: 600, marginBottom: 4 }}>Direct Flight Baseline</div>
                  <pre className="query-code">{queries.direct}</pre>
                </div>
              )}
              {queries.splice && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 12, color: '#a855f7', fontWeight: 600, marginBottom: 4 }}>Splice JOIN Query</div>
                  <pre className="query-code">{queries.splice}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default FlightSplicing;
