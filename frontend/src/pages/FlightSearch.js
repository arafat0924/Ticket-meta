import React, { useState, useTransition, useId, useCallback } from 'react';
import { Search, Plane, ChevronDown, ChevronUp } from 'lucide-react';
import { searchFlights } from '../api';

function FlightSearch() {
  const [origin, setOrigin] = useState('');
  const [dest, setDest] = useState('');
  const [date, setDate] = useState('');
  const [nonstop, setNonstop] = useState(false);
  const [sort, setSort] = useState('cheapest');
  const [limit, setLimit] = useState(20);
  const [flights, setFlights] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [showQuery, setShowQuery] = useState(false);
  const [searched, setSearched] = useState(false);

  // React 19: useTransition for non-blocking search
  const [isPending, startTransition] = useTransition();

  // React 19: useId for accessible form labels
  const originId = useId();
  const destId = useId();
  const dateId = useId();
  const limitId = useId();
  const nonstopId = useId();

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!origin || !dest) return;
    setError('');
    setFlights([]);
    setSearched(true);

    startTransition(async () => {
      try {
        const res = await searchFlights({ origin, dest, nonstop, sort, limit, date });
        setFlights(res.data.flights || []);
        setQuery(res.data.query || '');
      } catch (err) {
        setError(err.response?.data?.error || err.message);
        setQuery(err.response?.data?.query || '');
      }
    });
  }, [origin, dest, nonstop, sort, limit, date]);

  const formatTime = (raw) => {
    if (!raw) return '--:--';
    const parts = raw.split('||');
    const match = parts[0]?.match(/T(\d{2}:\d{2})/);
    return match ? match[1] : '--:--';
  };

  const getArrivalTime = (raw) => {
    if (!raw) return '--:--';
    const parts = raw.split('||');
    const last = parts[parts.length - 1];
    const match = last?.match(/T(\d{2}:\d{2})/);
    return match ? match[1] : '--:--';
  };

  const formatDuration = (dur) => {
    if (!dur) return '';
    const match = dur.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
    if (match) return `${match[1] || '0'}h ${match[2] || '0'}m`;
    return dur;
  };

  return (
    <div className="page-container">
      {/* React 19: Document metadata */}
      <title>Search Flights — SkyQuery</title>

      <div className="page-hero">
        <h1>✈ Search Flights</h1>
        <p>Search through 80M+ flight itineraries powered by Hive</p>
      </div>

      <form onSubmit={handleSearch}>
        <div className="search-panel">
          <div className="search-row">
            <div className="input-group">
              <label htmlFor={originId}>From</label>
              <input
                id={originId}
                type="text"
                placeholder="e.g. ATL"
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())}
                maxLength={3}
                required
              />
            </div>
            <div className="input-group">
              <label htmlFor={destId}>To</label>
              <input
                id={destId}
                type="text"
                placeholder="e.g. LAX"
                value={dest}
                onChange={(e) => setDest(e.target.value.toUpperCase())}
                maxLength={3}
                required
              />
            </div>
            <div className="input-group">
              <label htmlFor={dateId}>Date (optional)</label>
              <input
                id={dateId}
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="input-group">
              <label htmlFor={limitId}>Limit</label>
              <select id={limitId} value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
            <button className="btn-primary" type="submit" disabled={isPending || !origin || !dest}>
              <Search size={18} />
              {isPending ? 'Searching...' : 'Search'}
            </button>
          </div>
          <div className="checkbox-group">
            <input
              type="checkbox"
              id={nonstopId}
              checked={nonstop}
              onChange={(e) => setNonstop(e.target.checked)}
            />
            <label htmlFor={nonstopId}>Nonstop flights only</label>
          </div>
        </div>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {isPending && (
        <div className="loading-container">
          <div className="spinner" />
          <div className="loading-text">
            Scanning flight database...
            <span className="warning">⏱ Hive queries may take 2–8 minutes on 80M rows</span>
          </div>
        </div>
      )}

      {!isPending && searched && flights.length > 0 && (
        <>
          <div className="sort-buttons">
            {['cheapest', 'fastest', 'best'].map(s => (
              <button
                key={s}
                className={`sort-btn ${sort === s ? 'active' : ''}`}
                onClick={() => setSort(s)}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
          <div className="result-count">
            Found <strong>{flights.length}</strong> flights from <strong>{origin}</strong> to <strong>{dest}</strong>
          </div>
          <div className="flight-cards">
            {flights.map((f, i) => {
              const isNonstop = (f.isnonstop || f.isNonStop) === 'True';
              const isRefundable = (f.isrefundable || f.isRefundable) === 'True';
              const isBasic = (f.isbasiceconomy || f.isBasicEconomy) === 'True';
              const seats = Number(f.seatsremaining || f.seatsRemaining || 99);

              return (
                <div className="flight-card" key={`${i}-${f.legid || f.legId}`}>
                  <div className="flight-airline">
                    <div className="airline-name">{f.segmentsairlinename || f.segmentsAirlineName || 'Unknown'}</div>
                    <div className="airline-code">{f.segmentsairlinecode || f.segmentsAirlineCode || ''}</div>
                    <div className="flight-tags">
                      {isNonstop && <span className="tag tag-nonstop">Nonstop</span>}
                      {isRefundable && <span className="tag tag-refundable">Refundable</span>}
                      {isBasic && <span className="tag tag-basic">Basic Economy</span>}
                      {seats <= 3 && <span className="tag tag-seats">{seats} left</span>}
                    </div>
                  </div>
                  <div className="flight-route">
                    <div className="flight-time">
                      <div className="time">{formatTime(f.segmentsdeparturetimeraw || f.segmentsDepartureTimeRaw)}</div>
                      <div className="airport">{f.startingairport || f.startingAirport}</div>
                    </div>
                    <div className="flight-path">
                      <div className="duration">{formatDuration(f.travelduration || f.travelDuration)}</div>
                      <div className="line" />
                      <div className={`stops ${isNonstop ? '' : 'has-stops'}`}>
                        {isNonstop ? 'Nonstop' : 'Connecting'}
                      </div>
                    </div>
                    <div className="flight-time">
                      <div className="time">{getArrivalTime(f.segmentsarrivaltimeraw || f.segmentsArrivalTimeRaw)}</div>
                      <div className="airport">{f.destinationairport || f.destinationAirport}</div>
                    </div>
                  </div>
                  <div className="flight-price">
                    <div className="price">${Number(f.totalfare || f.totalFare || 0).toFixed(0)}</div>
                    <div className="price-label">total fare</div>
                    {(f.flightdate || f.flightDate) && (
                      <div className="price-label" style={{ marginTop: 4 }}>{f.flightdate || f.flightDate}</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {!isPending && searched && flights.length === 0 && !error && (
        <div className="empty-state">
          <div className="icon">🔍</div>
          <h3>No flights found</h3>
          <p>Try different airports or remove the nonstop filter</p>
        </div>
      )}

      {!searched && !isPending && (
        <div className="empty-state">
          <div className="icon"><Plane size={48} /></div>
          <h3>Search for flights</h3>
          <p>Enter origin and destination airport codes (e.g., ATL → LAX)</p>
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

export default FlightSearch;
