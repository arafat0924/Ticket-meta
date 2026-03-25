import React, { useState, useTransition, useId, useCallback } from 'react';
import { Building2, Search, ChevronDown, ChevronUp, ExternalLink, Globe, MapPin } from 'lucide-react';
import { searchAirports } from '../api';

function AirportExplorer() {
  const [searchQuery, setSearchQuery] = useState('');
  const [airports, setAirports] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [showQuery, setShowQuery] = useState(false);
  const [searched, setSearched] = useState(false);

  const [isPending, startTransition] = useTransition();
  const searchId = useId();

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!searchQuery) return;
    setError('');
    setAirports([]);
    setSearched(true);

    startTransition(async () => {
      try {
        const res = await searchAirports({ q: searchQuery, limit: 20 });
        setAirports(res.data.airports || []);
        setQuery(res.data.query || '');
      } catch (err) {
        setError(err.response?.data?.error || err.message);
        setQuery(err.response?.data?.query || '');
      }
    });
  }, [searchQuery]);

  const getTypeColor = (type) => {
    switch (type) {
      case 'large_airport': return '#6366f1';
      case 'medium_airport': return '#8b5cf6';
      case 'small_airport': return '#a78bfa';
      case 'heliport': return '#f59e0b';
      case 'seaplane_base': return '#22d3ee';
      case 'closed': return '#ef4444';
      default: return '#64748b';
    }
  };

  const formatType = (type) => {
    if (!type) return 'Unknown';
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const quickSearches = ['New York', 'Tokyo', 'London', 'ATL', 'LAX', 'Dubai', 'Singapore'];

  return (
    <div className="page-container">
      <title>Airport Explorer — SkyQuery</title>

      <div className="page-hero">
        <h1>🏢 Airport Explorer</h1>
        <p>Search airports worldwide by name, city, or IATA code</p>
      </div>

      <form onSubmit={handleSearch}>
        <div className="search-panel">
          <div className="search-row">
            <div className="input-group" style={{ flex: 3 }}>
              <label htmlFor={searchId}>Search</label>
              <input
                id={searchId}
                type="text"
                placeholder="Search by city, airport name, or IATA code..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                required
              />
            </div>
            <button className="btn-primary" type="submit" disabled={isPending || !searchQuery}>
              <Search size={18} />
              {isPending ? 'Searching...' : 'Search'}
            </button>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
            {quickSearches.map((qs, i) => (
              <button key={i} type="button" className="btn-secondary" onClick={() => setSearchQuery(qs)}
                style={{ fontSize: 12, padding: '6px 12px' }}>{qs}</button>
            ))}
          </div>
        </div>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {isPending && (
        <div className="loading-container">
          <div className="spinner" />
          <div className="loading-text">Searching airports...</div>
        </div>
      )}

      {!isPending && airports.length > 0 && (
        <>
          <div className="result-count">
            Found <strong>{airports.length}</strong> airports matching "<strong>{searchQuery}</strong>"
          </div>
          <div className="airport-grid">
            {airports.map((a, i) => {
              const color = getTypeColor(a.type);
              return (
                <div className="airport-card" key={a.id || i}>
                  <div className="airport-header">
                    <div className="iata-badge" style={{ background: `linear-gradient(135deg, ${color} 0%, ${color}cc 100%)` }}>
                      {a.iata_code || a.ident || '—'}
                    </div>
                    <div>
                      <div className="airport-name">{a.name || 'Unknown Airport'}</div>
                      <div className="airport-location">{[a.municipality, a.iso_country, a.continent].filter(Boolean).join(' · ')}</div>
                    </div>
                  </div>
                  <div style={{ display: 'inline-block', fontSize: 11, padding: '3px 10px', borderRadius: 6, background: `${color}22`, color, fontWeight: 600, marginBottom: 8 }}>
                    {formatType(a.type)}
                  </div>
                  <div className="airport-details">
                    <div className="detail-item"><span className="detail-label">IATA Code</span><span className="detail-value">{a.iata_code || '—'}</span></div>
                    <div className="detail-item"><span className="detail-label">ICAO / Ident</span><span className="detail-value">{a.ident || '—'}</span></div>
                    <div className="detail-item"><span className="detail-label">Latitude</span><span className="detail-value">{a.latitude_deg != null ? `${Number(a.latitude_deg).toFixed(4)}°` : '—'}</span></div>
                    <div className="detail-item"><span className="detail-label">Longitude</span><span className="detail-value">{a.longitude_deg != null ? `${Number(a.longitude_deg).toFixed(4)}°` : '—'}</span></div>
                    <div className="detail-item"><span className="detail-label">Elevation</span><span className="detail-value">{a.elevation_ft != null ? `${Number(a.elevation_ft).toLocaleString()} ft` : '—'}</span></div>
                    <div className="detail-item"><span className="detail-label">Scheduled Service</span><span className="detail-value" style={{ color: a.scheduled_service === 'yes' ? '#22c55e' : '#64748b' }}>{a.scheduled_service === 'yes' ? '✓ Yes' : '✗ No'}</span></div>
                  </div>
                  <div className="airport-links">
                    {a.home_link && <a href={a.home_link} target="_blank" rel="noopener noreferrer"><Globe size={12} style={{ display: 'inline', marginRight: 4 }} />Website</a>}
                    {a.wikipedia_link && <a href={a.wikipedia_link} target="_blank" rel="noopener noreferrer"><ExternalLink size={12} style={{ display: 'inline', marginRight: 4 }} />Wikipedia</a>}
                    {a.latitude_deg && a.longitude_deg && <a href={`https://www.google.com/maps?q=${a.latitude_deg},${a.longitude_deg}`} target="_blank" rel="noopener noreferrer"><MapPin size={12} style={{ display: 'inline', marginRight: 4 }} />Map</a>}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {!isPending && searched && airports.length === 0 && !error && (
        <div className="empty-state"><div className="icon">🔍</div><h3>No airports found</h3><p>Try a different search term</p></div>
      )}

      {!searched && !isPending && (
        <div className="empty-state"><div className="icon"><Building2 size={48} /></div><h3>Search airports</h3><p>Search by city name, airport name, or IATA code</p></div>
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

export default AirportExplorer;
