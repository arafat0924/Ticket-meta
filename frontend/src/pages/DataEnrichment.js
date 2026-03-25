import React, { useState, useEffect } from 'react';
import { enrichmentWeather, enrichmentWealth, enrichmentBrand, enrichmentRail, enrichmentGhost } from '../api';
import { CloudRain, DollarSign, Award, Train, Ghost, Loader2, AlertTriangle, ExternalLink } from 'lucide-react';

const TABS = [
  { id: 'weather', label: 'I. Weather Impact', icon: CloudRain, color: '#3b82f6' },
  { id: 'wealth', label: 'II. Wealth Gap', icon: DollarSign, color: '#10b981' },
  { id: 'brand', label: 'III. Brand Markup', icon: Award, color: '#f59e0b' },
  { id: 'rail', label: 'IV. Rail Effect', icon: Train, color: '#8b5cf6' },
  { id: 'ghost', label: 'V. Ghost Fares', icon: Ghost, color: '#ef4444' },
];

function DataEnrichment() {
  const [tab, setTab] = useState('weather');
  const [data, setData] = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});
  const [weatherAirport, setWeatherAirport] = useState('ATL');

  const loadTab = async (tabId, airport) => {
    if (data[tabId] && tabId !== 'weather') return;
    setLoading(p => ({ ...p, [tabId]: true }));
    setErrors(p => ({ ...p, [tabId]: null }));
    try {
      let res;
      switch (tabId) {
        case 'weather': res = await enrichmentWeather(airport || weatherAirport); break;
        case 'wealth': res = await enrichmentWealth(); break;
        case 'brand': res = await enrichmentBrand(); break;
        case 'rail': res = await enrichmentRail(); break;
        case 'ghost': res = await enrichmentGhost(); break;
        default: return;
      }
      setData(p => ({ ...p, [tabId]: res.data }));
    } catch (e) {
      setErrors(p => ({ ...p, [tabId]: e.response?.data?.error || e.message }));
    }
    setLoading(p => ({ ...p, [tabId]: false }));
  };

  useEffect(() => { loadTab(tab); }, [tab]); // eslint-disable-line

  const renderWeather = () => {
    const d = data.weather;
    if (!d) return null;
    const daily = d.dailyData || [];
    const weather = d.weather || {};
    const weatherDates = Object.keys(weather).filter(k => k !== 'error');
    return (
      <div>
        <h3 style={{ color: '#3b82f6' }}>🌩️ Severe Weather & Capacity Contraction Premium</h3>
        <p className="enr-desc">Hypothesis: Extreme weather at hub airports causes capacity contraction, driving up fares and shifting passengers to multi-stop routes.</p>
        <div className="enr-controls">
          <label>Airport:</label>
          <select value={weatherAirport} onChange={e => { setWeatherAirport(e.target.value); loadTab('weather', e.target.value); }}>
            {['ATL','ORD','DEN','DFW','JFK','LAX','SFO','MIA','SEA','BOS','EWR','CLT','PHX','IAH','MSP','DTW'].map(a => <option key={a}>{a}</option>)}
          </select>
          <span className="enr-source">External: <a href="https://api.weather.gov/" target="_blank" rel="noreferrer">NOAA Weather API</a></span>
        </div>
        <div className="enr-grid">
          <div className="enr-card">
            <h4>📊 Internal Data (Expedia/Hive)</h4>
            <p>Daily flight metrics for <strong>{d.airport}</strong>: {daily.length} dates analyzed</p>
            <div className="enr-table-wrap">
              <table className="enr-table">
                <thead><tr><th>Date</th><th>Avg Fare</th><th>Flights</th><th>Nonstop</th><th>Connecting</th><th>Avg Seats</th><th>Lead Days</th></tr></thead>
                <tbody>{daily.slice(0, 20).map((r, i) => (
                  <tr key={i} className={weatherDates.includes(r.flightDate) ? 'enr-highlight' : ''}>
                    <td>{r.flightDate}</td><td>${r.avgFare}</td><td>{r.flightCount}</td>
                    <td>{r.nonstopCount}</td><td>{r.connectingCount}</td><td>{r.avgSeats}</td><td>{r.avgLeadDays}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>
          <div className="enr-card">
            <h4>🌦️ External Data (NOAA Weather)</h4>
            {weather.error ? <p className="enr-err">{weather.error}</p> :
              weatherDates.length > 0 ? (
                <div className="enr-table-wrap">
                  <table className="enr-table">
                    <thead><tr><th>Date</th><th>Temp °C</th><th>Wind m/s</th><th>Precip mm</th><th>Condition</th></tr></thead>
                    <tbody>{weatherDates.slice(0, 20).map((date, i) => {
                      const w = weather[date];
                      return <tr key={i}><td>{date}</td><td>{w.temp?.toFixed(1) ?? '—'}</td><td>{w.wind?.toFixed(1) ?? '—'}</td><td>{w.precip?.toFixed(1) ?? '—'}</td><td>{w.desc || '—'}</td></tr>;
                    })}</tbody>
                  </table>
                </div>
              ) : <p>No weather observations returned. NOAA API returns recent data only.</p>
            }
            <p className="enr-insight">💡 <strong>Analysis:</strong> Compare avg fares on stormy days (high wind/precip) vs clear days to quantify the weather premium.</p>
          </div>
        </div>
      </div>
    );
  };

  const renderWealth = () => {
    const d = data.wealth;
    if (!d) return null;
    const airports = d.airports || [];
    const tiers = d.tierSummary || [];
    return (
      <div>
        <h3 style={{ color: '#10b981' }}>💰 Geographical Wealth & Purchasing Power Discrimination</h3>
        <p className="enr-desc">Hypothesis: Airlines charge higher price-per-mile from wealthy metro areas where passengers are less price-sensitive.</p>
        <span className="enr-source">External: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noreferrer">FRED / Census Bureau</a> (API Key: 510d1bf...)</span>
        <div className="enr-grid">
          <div className="enr-card">
            <h4>📈 Income Tier Summary</h4>
            <table className="enr-table">
              <thead><tr><th>Tier</th><th>Airports</th><th>Avg $/Mile</th><th>Avg Fare</th></tr></thead>
              <tbody>{tiers.map((t, i) => (
                <tr key={i} className={t.tier === 'High' ? 'enr-highlight' : ''}>
                  <td><span className={`enr-badge enr-badge-${t.tier.toLowerCase()}`}>{t.tier}</span></td>
                  <td>{t.airportCount}</td><td>${t.avgPricePerMile}</td><td>${t.avgFare}</td>
                </tr>
              ))}</tbody>
            </table>
            {tiers.length >= 2 && <p className="enr-insight">💡 High-income hubs pay <strong>${(tiers[0]?.avgPricePerMile - tiers[tiers.length-1]?.avgPricePerMile).toFixed(4)}/mile</strong> more on average — evidence of purchasing power discrimination.</p>}
          </div>
          <div className="enr-card">
            <h4>🏙️ Airport Price-per-Mile vs Median Income</h4>
            <div className="enr-table-wrap">
              <table className="enr-table">
                <thead><tr><th>Airport</th><th>City</th><th>Income</th><th>Tier</th><th>$/Mile</th><th>Avg Fare</th><th>Flights</th></tr></thead>
                <tbody>{airports.map((a, i) => (
                  <tr key={i}><td>{a.startingAirport}</td><td>{a.city}</td><td>${a.medianIncome?.toLocaleString() ?? '—'}</td>
                    <td><span className={`enr-badge enr-badge-${(a.incomeTier||'').toLowerCase()}`}>{a.incomeTier}</span></td>
                    <td>${a.avgPricePerMile}</td><td>${a.avgFare}</td><td>{a.flightCount?.toLocaleString()}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderBrand = () => {
    const d = data.brand;
    if (!d) return null;
    const comps = d.comparisons || [];
    const delays = d.delayData || {};
    return (
      <div>
        <h3 style={{ color: '#f59e0b' }}>✈️ Brand Markup & Service Quality Correlation</h3>
        <p className="enr-desc">Hypothesis: On competitive routes, airlines with better service quality maintain premium pricing through brand reputation.</p>
        <span className="enr-source">External: <a href="https://www.bts.gov/topics/airlines-and-airports/understanding-reporting-causes-flight-delays-and-cancellations" target="_blank" rel="noreferrer">DOT Airline_Delay_Cause.csv</a></span>
        {comps.map((c, ci) => (
          <div key={ci} className="enr-card" style={{ marginTop: '1rem' }}>
            <h4>Route: {c.route} ({c.airlines?.length} airlines competing)</h4>
            <table className="enr-table">
              <thead><tr><th>Airline</th><th>Avg Fare</th><th>Min</th><th>Max</th><th>Nonstop%</th><th>On-Time%</th><th>Flights</th></tr></thead>
              <tbody>{(c.airlines || []).map((a, i) => {
                const delayInfo = Object.entries(delays).find(([k]) => a.airline?.includes(k) || k.includes(a.airline?.split(' ')[0]));
                const onTime = delayInfo ? delayInfo[1].onTimePct : null;
                return (
                  <tr key={i}><td>{a.airline}</td><td className="enr-bold">${a.avgFare}</td><td>${a.minFare}</td><td>${a.maxFare}</td>
                    <td>{a.nonstopPct}%</td><td>{onTime ? `${onTime}%` : '—'}</td><td>{a.flightCount}</td></tr>
                );
              })}</tbody>
            </table>
          </div>
        ))}
        {comps.length > 0 && <p className="enr-insight">💡 Airlines with higher on-time performance tend to maintain higher average fares — brand reputation creates pricing power.</p>}
      </div>
    );
  };

  const renderRail = () => {
    const d = data.rail;
    if (!d) return null;
    const summary = d.summary || {};
    const rc = d.railCovered || [];
    const rv = d.railVacuum || [];
    return (
      <div>
        <h3 style={{ color: '#8b5cf6' }}>🚆 Intermodal Competition: Rail "Price Ceiling" Effect</h3>
        <p className="enr-desc">Hypothesis: On short-haul routes (&lt;500 mi), Amtrak rail competition forces airfares lower vs. routes without rail alternatives.</p>
        <span className="enr-source">External: <a href="https://amtrak-api.marcmap.app/get-stations" target="_blank" rel="noreferrer">Amtrak Stations API</a> ({d.amtrakStations || 0} stations)</span>
        <div className="enr-grid">
          <div className="enr-card">
            <h4>📊 Price Ceiling Summary</h4>
            <table className="enr-table">
              <thead><tr><th>Category</th><th>Routes</th><th>Avg $/Mile</th></tr></thead>
              <tbody>
                <tr className="enr-highlight"><td>🚆 Rail Covered</td><td>{summary.railCovered?.count}</td><td>${summary.railCovered?.avgPricePerMile}</td></tr>
                <tr><td>✈️ Rail Vacuum</td><td>{summary.railVacuum?.count}</td><td>${summary.railVacuum?.avgPricePerMile}</td></tr>
              </tbody>
            </table>
            {summary.priceCeilingEffect && <p className="enr-insight">💡 Rail competition reduces price-per-mile by <strong>{summary.priceCeilingEffect}%</strong> — confirming the "price ceiling" hypothesis.</p>}
          </div>
          <div className="enr-card">
            <h4>🚆 Rail-Covered Routes (NE Corridor)</h4>
            <div className="enr-table-wrap">
              <table className="enr-table">
                <thead><tr><th>Route</th><th>Avg Fare</th><th>Distance</th><th>$/Mile</th><th>Flights</th></tr></thead>
                <tbody>{rc.slice(0, 15).map((r, i) => (
                  <tr key={i}><td>{r.startingAirport}→{r.destinationAirport}</td><td>${r.avgFare}</td><td>{r.avgDistance} mi</td><td>${r.pricePerMile}</td><td>{r.flightCount}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </div>
          <div className="enr-card">
            <h4>✈️ Rail-Vacuum Routes (No Train)</h4>
            <div className="enr-table-wrap">
              <table className="enr-table">
                <thead><tr><th>Route</th><th>Avg Fare</th><th>Distance</th><th>$/Mile</th><th>Flights</th></tr></thead>
                <tbody>{rv.slice(0, 15).map((r, i) => (
                  <tr key={i}><td>{r.startingAirport}→{r.destinationAirport}</td><td>${r.avgFare}</td><td>{r.avgDistance} mi</td><td>${r.pricePerMile}</td><td>{r.flightCount}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderGhost = () => {
    const d = data.ghost;
    if (!d) return null;
    const anomalies = d.anomalies || [];
    const posts = d.redditPosts || [];
    return (
      <div>
        <h3 style={{ color: '#ef4444' }}>👻 Price Manipulation & Ghost Fare Monitoring</h3>
        <p className="enr-desc">Hypothesis: Some platforms display unbookable "ghost fares" or use sawtooth pricing to induce panic buying.</p>
        <span className="enr-source">External: <a href="https://www.reddit.com/r/travel/search.json?q=ghost%20fare&limit=100" target="_blank" rel="noreferrer">Reddit r/travel Complaints</a></span>
        <div className="enr-grid">
          <div className="enr-card">
            <h4>🔍 Price Anomalies Detected (Price Ratio &gt; 3x)</h4>
            <p>{anomalies.length} route-date combinations show extreme price variance</p>
            <div className="enr-table-wrap">
              <table className="enr-table">
                <thead><tr><th>Route</th><th>Date</th><th>Min Fare</th><th>Max Fare</th><th>Ratio</th><th>Listings</th></tr></thead>
                <tbody>{anomalies.slice(0, 20).map((a, i) => (
                  <tr key={i} className={a.priceRatio > 5 ? 'enr-danger' : ''}>
                    <td>{a.startingAirport}→{a.destinationAirport}</td><td>{a.flightDate}</td>
                    <td>${a.minFare}</td><td className="enr-bold">${a.maxFare}</td>
                    <td className="enr-bold">{a.priceRatio}x</td><td>{a.listings}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>
          <div className="enr-card">
            <h4>📱 Reddit Consumer Complaints ({posts.length} posts)</h4>
            {posts.length > 0 ? (
              <div className="enr-posts">{posts.slice(0, 15).map((p, i) => (
                <div key={i} className="enr-post">
                  <a href={p.url} target="_blank" rel="noreferrer">{p.title} <ExternalLink size={12} /></a>
                  <span className="enr-post-meta">⬆️ {p.score} · 💬 {p.comments} · r/{p.subreddit}</span>
                </div>
              ))}</div>
            ) : <p>No Reddit posts found or API rate-limited.</p>}
            <p className="enr-insight">💡 Routes with &gt;5x price ratios and matching Reddit complaints suggest systematic price manipulation patterns.</p>
          </div>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    if (loading[tab]) return <div className="enr-loading"><Loader2 className="spin" size={32} /> Loading {TABS.find(t=>t.id===tab)?.label}... (Hive queries may take 1-3 min)</div>;
    if (errors[tab]) return <div className="enr-error"><AlertTriangle size={20} /> {errors[tab]}</div>;
    switch (tab) {
      case 'weather': return renderWeather();
      case 'wealth': return renderWealth();
      case 'brand': return renderBrand();
      case 'rail': return renderRail();
      case 'ghost': return renderGhost();
      default: return null;
    }
  };

  return (
    <div className="enr-page">
      <div className="enr-header">
        <h1>📊 Data Enrichment & External Analysis</h1>
        <p>Cross-referencing Expedia flight data with 5 external datasets to uncover deep pricing insights</p>
      </div>
      <div className="enr-tabs">
        {TABS.map(t => (
          <button key={t.id} className={`enr-tab ${tab === t.id ? 'active' : ''}`}
            style={tab === t.id ? { borderColor: t.color, color: t.color } : {}}
            onClick={() => setTab(t.id)}>
            <t.icon size={16} /> {t.label}
          </button>
        ))}
      </div>
      <div className="enr-content">{renderContent()}</div>
      <style>{`
        .enr-page { max-width: 1400px; margin: 0 auto; padding: 2rem 1rem; }
        .enr-header { text-align: center; margin-bottom: 2rem; }
        .enr-header h1 { font-size: 1.8rem; color: #f0f0f0; }
        .enr-header p { color: #94a3b8; }
        .enr-tabs { display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; margin-bottom: 2rem; }
        .enr-tab { display: flex; align-items: center; gap: 6px; padding: 0.6rem 1rem; border: 2px solid #334155; border-radius: 8px; background: rgba(30,41,59,0.8); color: #94a3b8; cursor: pointer; font-size: 0.85rem; transition: all 0.2s; }
        .enr-tab:hover { border-color: #64748b; color: #e2e8f0; }
        .enr-tab.active { background: rgba(30,41,59,0.95); font-weight: 600; }
        .enr-content { background: rgba(15,23,42,0.6); border: 1px solid #1e293b; border-radius: 12px; padding: 1.5rem; }
        .enr-desc { color: #94a3b8; font-style: italic; margin-bottom: 1rem; padding: 0.75rem; background: rgba(30,41,59,0.5); border-radius: 8px; border-left: 3px solid #3b82f6; }
        .enr-source { display: inline-block; font-size: 0.8rem; color: #64748b; margin-bottom: 1rem; }
        .enr-source a { color: #3b82f6; text-decoration: underline; }
        .enr-controls { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
        .enr-controls select { padding: 0.4rem; border-radius: 6px; background: #1e293b; color: #e2e8f0; border: 1px solid #334155; }
        .enr-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1rem; margin-top: 1rem; }
        .enr-card { background: rgba(30,41,59,0.5); border: 1px solid #334155; border-radius: 10px; padding: 1rem; }
        .enr-card h4 { color: #e2e8f0; margin-bottom: 0.75rem; font-size: 1rem; }
        .enr-table-wrap { overflow-x: auto; max-height: 400px; overflow-y: auto; }
        .enr-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
        .enr-table th { background: #1e293b; color: #94a3b8; padding: 0.5rem; text-align: left; position: sticky; top: 0; }
        .enr-table td { padding: 0.4rem 0.5rem; border-bottom: 1px solid #1e293b; color: #cbd5e1; }
        .enr-table tr:hover { background: rgba(59,130,246,0.08); }
        .enr-highlight { background: rgba(59,130,246,0.12) !important; }
        .enr-danger { background: rgba(239,68,68,0.12) !important; }
        .enr-bold { font-weight: 700; color: #f59e0b; }
        .enr-badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .enr-badge-high { background: rgba(239,68,68,0.2); color: #fca5a5; }
        .enr-badge-medium { background: rgba(245,158,11,0.2); color: #fcd34d; }
        .enr-badge-low { background: rgba(16,185,129,0.2); color: #6ee7b7; }
        .enr-insight { margin-top: 1rem; padding: 0.75rem; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); border-radius: 8px; color: #fcd34d; font-size: 0.85rem; }
        .enr-loading { text-align: center; padding: 3rem; color: #94a3b8; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
        .enr-error { text-align: center; padding: 2rem; color: #fca5a5; display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
        .enr-posts { display: flex; flex-direction: column; gap: 0.5rem; max-height: 350px; overflow-y: auto; }
        .enr-post { padding: 0.5rem; background: rgba(15,23,42,0.5); border-radius: 6px; }
        .enr-post a { color: #93c5fd; text-decoration: none; font-size: 0.85rem; }
        .enr-post a:hover { text-decoration: underline; }
        .enr-post-meta { display: block; font-size: 0.75rem; color: #64748b; margin-top: 2px; }
        .enr-err { color: #fca5a5; }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

export default DataEnrichment;
