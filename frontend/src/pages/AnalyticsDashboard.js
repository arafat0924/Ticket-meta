import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  LineChart, Line, PieChart, Pie, Cell, Area, AreaChart, ScatterChart, Scatter, ZAxis
} from 'recharts';
import {
  analyticsOverview, analyticsTopAirlines, analyticsDayOfWeek,
  analyticsBookingWindow, analyticsWeekendMidweek, analyticsEconomyGap
} from '../api';

const COLORS = ['#f5a623', '#22c55e', '#3b82f6', '#ef4444', '#a855f7', '#ec4899', '#14b8a6', '#f97316'];

const DarkTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: 10, padding: '12px 16px', fontSize: 13, color: '#c0c0c0', boxShadow: '0 0 20px rgba(0,0,0,0.5)' }}>
        <div style={{ fontWeight: 700, marginBottom: 6 }}>{label}</div>
        {payload.map((p, i) => (
          <div key={i} style={{ color: p.color, marginBottom: 2 }}>
            {p.name}: {typeof p.value === 'number' ? (p.name.toLowerCase().includes('fare') || p.name.toLowerCase().includes('price') ? `$${p.value.toFixed(2)}` : p.value.toLocaleString()) : p.value}
          </div>
        ))}
      </div>
    );
  }
  return null;
};

function StatCard({ label, value, sub, color = '#f5a623', icon }) {
  return (
    <div className="search-panel" style={{ textAlign: 'center', flex: 1, minWidth: 180, padding: '20px 16px' }}>
      {icon && <div style={{ fontSize: 28, marginBottom: 4 }}>{icon}</div>}
      <div style={{ fontSize: 12, color: '#555', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function SectionTitle({ children }) {
  return <div className="chart-title" style={{ marginTop: 32, marginBottom: 8 }}>{children}</div>;
}

function AnalyticsDashboard() {
  const [overview, setOverview] = useState(null);
  const [topAirlines, setTopAirlines] = useState([]);
  const [dayOfWeek, setDayOfWeek] = useState([]);
  const [bookingWindow, setBookingWindow] = useState([]);
  const [weekendMidweek, setWeekendMidweek] = useState([]);
  const [economyGap, setEconomyGap] = useState([]);

  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});
  const [queries, setQueries] = useState({});
  const [showQueries, setShowQueries] = useState(false);

  const loadSection = useCallback(async (key, apiFn, setter) => {
    setLoading(prev => ({ ...prev, [key]: true }));
    setErrors(prev => ({ ...prev, [key]: '' }));
    try {
      const res = await apiFn();
      const data = res.data;
      setter(data);
      if (data.query) setQueries(prev => ({ ...prev, [key]: data.query }));
    } catch (err) {
      setErrors(prev => ({ ...prev, [key]: err.response?.data?.error || err.message }));
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  }, []);

  const loadAll = useCallback(() => {
    loadSection('overview', analyticsOverview, (d) => setOverview(d.overview));
    loadSection('topAirlines', analyticsTopAirlines, (d) => setTopAirlines(d.airlines || []));
    loadSection('dayOfWeek', analyticsDayOfWeek, (d) => setDayOfWeek(d.days || []));
    loadSection('bookingWindow', analyticsBookingWindow, (d) => setBookingWindow(d.bookingWindow || []));
    loadSection('weekendMidweek', analyticsWeekendMidweek, (d) => setWeekendMidweek(d.comparison || []));
    loadSection('economyGap', analyticsEconomyGap, (d) => setEconomyGap(d.routes || []));
  }, [loadSection]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const g = (obj, key) => {
    if (!obj) return 0;
    return Number(obj[key] || obj[key.toLowerCase()] || 0);
  };

  const anyLoading = Object.values(loading).some(Boolean);

  // Prepare chart data
  const airlineChartData = topAirlines.map(a => ({
    name: (a.airline || 'Unknown').length > 18 ? (a.airline || 'Unknown').substring(0, 16) + '…' : (a.airline || 'Unknown'),
    avgFare: Number(a.avgFare || a.avgfare || 0),
    flightCount: Number(a.flightCount || a.flightcount || 0),
  }));

  const dowChartData = dayOfWeek.map(d => ({
    day: d.dayName || d.dayname || `Day ${d.dayNum || d.daynum}`,
    flights: Number(d.flightCount || d.flightcount || 0),
    avgFare: Number(d.avgFare || d.avgfare || 0),
  }));

  const bwChartData = bookingWindow
    .filter(b => Number(b.bookingWindow || b.bookingwindow) <= 120)
    .map(b => ({
      days: Number(b.bookingWindow || b.bookingwindow),
      avgFare: Number(b.avgFare || b.avgfare || 0),
      minFare: Number(b.minFare || b.minfare || 0),
    }));

  const ecoGapData = economyGap.slice(0, 15).map(r => ({
    route: `${r.startingAirport || r.startingairport}→${r.destinationAirport || r.destinationairport}`,
    basic: Number(r.avgBasic || r.avgbasic || 0),
    standard: Number(r.avgStandard || r.avgstandard || 0),
    gap: Number(r.priceGap || r.pricegap || 0),
  }));

  // Refundable pie data
  const refPieData = overview ? [
    { name: 'Refundable', value: g(overview, 'refundableCount'), color: '#22c55e' },
    { name: 'Non-Refundable', value: g(overview, 'nonRefundableCount'), color: '#ef4444' },
  ] : [];

  const ecoPieData = overview ? [
    { name: 'Basic Economy', value: g(overview, 'basicEconomyCount'), color: '#3b82f6' },
    { name: 'Standard Economy', value: g(overview, 'standardEconomyCount'), color: '#f5a623' },
  ] : [];

  return (
    <div className="page-container">
      <title>Analytics Dashboard — SkyQuery</title>

      <div className="page-hero">
        <h1>📊 Analytics Dashboard</h1>
        <p>Comprehensive data analysis across the entire flight dataset</p>
      </div>

      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <button className="btn-primary" onClick={loadAll} disabled={anyLoading} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <RefreshCw size={16} className={anyLoading ? 'spinning' : ''} />
          {anyLoading ? 'Loading analytics…' : 'Refresh All Data'}
        </button>
        {anyLoading && (
          <div style={{ marginTop: 8, fontSize: 13, color: '#888' }}>
            ⏱ Each query scans ~80M rows. This may take a few minutes.
          </div>
        )}
      </div>

      {/* ===== SECTION 1: Pricing Overview ===== */}
      <SectionTitle>I. Pricing Overview</SectionTitle>
      {loading.overview && <div className="loading-container"><div className="spinner" /><div className="loading-text">Loading pricing overview…</div></div>}
      {errors.overview && <div className="error-banner">⚠ {errors.overview}</div>}
      {overview && (
        <>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
            <StatCard label="Total Flights" value={g(overview, 'totalFlights').toLocaleString()} icon="✈️" color="#3b82f6" />
            <StatCard label="Avg Fare" value={`$${g(overview, 'avgFare').toFixed(2)}`} icon="💰" color="#f5a623" />
            <StatCard label="Min Fare" value={`$${g(overview, 'minFare').toFixed(2)}`} icon="🏷️" color="#22c55e" />
            <StatCard label="Max Fare" value={`$${g(overview, 'maxFare').toFixed(2)}`} icon="💎" color="#ef4444" />
          </div>

          {/* Flexibility Premium */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
            <StatCard
              label="Avg Refundable Fare"
              value={`$${g(overview, 'avgFareRefundable').toFixed(2)}`}
              sub={`${g(overview, 'refundableCount').toLocaleString()} tickets`}
              color="#22c55e" icon="🔄"
            />
            <StatCard
              label="Avg Non-Refundable Fare"
              value={`$${g(overview, 'avgFareNonRefundable').toFixed(2)}`}
              sub={`${g(overview, 'nonRefundableCount').toLocaleString()} tickets`}
              color="#ef4444" icon="🚫"
            />
            <StatCard
              label="Flexibility Premium"
              value={`$${(g(overview, 'avgFareRefundable') - g(overview, 'avgFareNonRefundable')).toFixed(2)}`}
              sub="refundable − non-refundable"
              color="#a855f7" icon="📈"
            />
          </div>

          {/* Pie Charts Row */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
            <div className="chart-container" style={{ flex: 1, minWidth: 300 }}>
              <div className="chart-title">Refundable vs Non-Refundable</div>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={refPieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`} labelLine={false} fontSize={11}>
                    {refPieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Tooltip content={<DarkTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-container" style={{ flex: 1, minWidth: 300 }}>
              <div className="chart-title">Basic Economy vs Standard</div>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={ecoPieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`} labelLine={false} fontSize={11}>
                    {ecoPieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Tooltip content={<DarkTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* ===== SECTION 2: Top 15 Airlines ===== */}
      <SectionTitle>II. Top 15 Airlines by Volume</SectionTitle>
      {loading.topAirlines && <div className="loading-container"><div className="spinner" /><div className="loading-text">Loading airline data…</div></div>}
      {errors.topAirlines && <div className="error-banner">⚠ {errors.topAirlines}</div>}
      {airlineChartData.length > 0 && (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={450}>
            <BarChart data={airlineChartData} margin={{ top: 10, right: 30, left: 10, bottom: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
              <XAxis dataKey="name" stroke="#333" fontSize={11} angle={-35} textAnchor="end" height={100} />
              <YAxis yAxisId="left" stroke="#f5a623" tickFormatter={(v) => `$${v}`} />
              <YAxis yAxisId="right" orientation="right" stroke="#3b82f6" tickFormatter={(v) => v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v} />
              <Tooltip content={<DarkTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#555' }} />
              <Bar yAxisId="left" dataKey="avgFare" name="Avg Fare ($)" fill="#f5a623" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="right" dataKey="flightCount" name="Flight Count" fill="#3b82f6" radius={[4, 4, 0, 0]} opacity={0.6} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ===== SECTION 3: Day of Week ===== */}
      <SectionTitle>III. Flights & Pricing by Day of Week</SectionTitle>
      {loading.dayOfWeek && <div className="loading-container"><div className="spinner" /><div className="loading-text">Loading day-of-week data…</div></div>}
      {errors.dayOfWeek && <div className="error-banner">⚠ {errors.dayOfWeek}</div>}
      {dowChartData.length > 0 && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <div className="chart-container" style={{ flex: 1, minWidth: 350 }}>
            <div className="chart-title">Flight Volume by Day</div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={dowChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="day" stroke="#333" fontSize={12} />
                <YAxis stroke="#333" tickFormatter={(v) => v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : `${(v / 1000).toFixed(0)}K`} />
                <Tooltip content={<DarkTooltip />} />
                <Bar dataKey="flights" name="Flights" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                  {dowChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-container" style={{ flex: 1, minWidth: 350 }}>
            <div className="chart-title">Average Fare by Day</div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={dowChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="day" stroke="#333" fontSize={12} />
                <YAxis stroke="#333" tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<DarkTooltip />} />
                <Bar dataKey="avgFare" name="Avg Fare" fill="#f5a623" radius={[4, 4, 0, 0]}>
                  {dowChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ===== SECTION 4: Weekend vs Midweek ===== */}
      {weekendMidweek.length > 0 && (
        <>
          <SectionTitle>IV. Weekend vs Mid-week Pricing</SectionTitle>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
            {weekendMidweek.map((w, i) => {
              const type = w.travelType || w.traveltype || 'Unknown';
              const isWeekend = type.toLowerCase().includes('weekend');
              return (
                <StatCard key={i}
                  label={type}
                  value={`$${Number(w.avgFare || w.avgfare || 0).toFixed(2)}`}
                  sub={`${Number(w.flightCount || w.flightcount || 0).toLocaleString()} flights | Min $${Number(w.minFare || w.minfare || 0).toFixed(0)} | Max $${Number(w.maxFare || w.maxfare || 0).toFixed(0)}`}
                  color={isWeekend ? '#ef4444' : '#22c55e'}
                  icon={isWeekend ? '🌅' : '💼'}
                />
              );
            })}
          </div>
        </>
      )}

      {/* ===== SECTION 5: Booking Window ===== */}
      <SectionTitle>V. Booking Window Analysis</SectionTitle>
      <p style={{ color: '#666', fontSize: 13, marginBottom: 12, textAlign: 'center' }}>
        How does ticket price change as the flight date approaches? (Days before departure vs. Average fare)
      </p>
      {loading.bookingWindow && <div className="loading-container"><div className="spinner" /><div className="loading-text">Loading booking window data…</div></div>}
      {errors.bookingWindow && <div className="error-banner">⚠ {errors.bookingWindow}</div>}
      {bwChartData.length > 0 && (
        <div className="chart-container">
          <div className="chart-title">Average Fare vs Days Before Departure</div>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={bwChartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="bwGradAvg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f5a623" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f5a623" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bwGradMin" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
              <XAxis dataKey="days" stroke="#333" fontSize={12} label={{ value: 'Days Before Departure', position: 'insideBottom', offset: -5, fill: '#555' }} />
              <YAxis stroke="#333" tickFormatter={(v) => `$${v}`} />
              <Tooltip content={<DarkTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="avgFare" name="Avg Fare" stroke="#f5a623" fill="url(#bwGradAvg)" strokeWidth={2} />
              <Area type="monotone" dataKey="minFare" name="Min Fare" stroke="#22c55e" fill="url(#bwGradMin)" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ===== SECTION 6: Economy Class Gap ===== */}
      <SectionTitle>VI. Basic vs Standard Economy Price Gap (Top Routes)</SectionTitle>
      {loading.economyGap && <div className="loading-container"><div className="spinner" /><div className="loading-text">Loading economy comparison…</div></div>}
      {errors.economyGap && <div className="error-banner">⚠ {errors.economyGap}</div>}
      {ecoGapData.length > 0 && (
        <>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={450}>
              <BarChart data={ecoGapData} margin={{ top: 10, right: 30, left: 10, bottom: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="route" stroke="#333" fontSize={10} angle={-40} textAnchor="end" height={100} />
                <YAxis stroke="#333" tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<DarkTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#555' }} />
                <Bar dataKey="basic" name="Basic Economy" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="standard" name="Standard Economy" fill="#f5a623" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="data-table-wrapper" style={{ marginTop: 16 }}>
            <table className="data-table">
              <thead>
                <tr><th>Route</th><th>Avg Basic</th><th>Avg Standard</th><th>Price Gap</th></tr>
              </thead>
              <tbody>
                {ecoGapData.map((r, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{r.route}</td>
                    <td style={{ color: '#3b82f6' }}>${r.basic.toFixed(2)}</td>
                    <td style={{ color: '#f5a623' }}>${r.standard.toFixed(2)}</td>
                    <td style={{ color: r.gap > 0 ? '#ef4444' : '#22c55e', fontWeight: 700 }}>
                      {r.gap > 0 ? '+' : ''}${r.gap.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ===== Debug Queries ===== */}
      {Object.keys(queries).length > 0 && (
        <div className="query-debug" style={{ marginTop: 32 }}>
          <button className="query-toggle" onClick={() => setShowQueries(!showQueries)}>
            {showQueries ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {showQueries ? 'Hide' : 'Show'} All HiveQL Queries ({Object.keys(queries).length})
          </button>
          {showQueries && Object.entries(queries).map(([key, sql]) => (
            <div key={key} style={{ marginTop: 12 }}>
              <div style={{ fontSize: 12, color: '#f5a623', fontWeight: 600, marginBottom: 4 }}>{key}</div>
              <pre className="query-code">{sql}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AnalyticsDashboard;
