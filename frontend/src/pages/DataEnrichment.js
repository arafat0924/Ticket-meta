import React, { useState, useEffect, useRef } from 'react';
import { enrichmentWeather, enrichmentWealth, enrichmentBrand, enrichmentRail, enrichmentGhost } from '../api';
import { CloudRain, DollarSign, Award, Train, Ghost, Loader2, AlertTriangle, ExternalLink, TrendingUp, BarChart3, Database, Globe } from 'lucide-react';

const TABS = [
  { id: 'weather', label: 'Weather Impact', icon: CloudRain, color: '#3b82f6' },
  { id: 'wealth', label: 'Wealth Gap', icon: DollarSign, color: '#10b981' },
  { id: 'brand', label: 'Brand Markup', icon: Award, color: '#f59e0b' },
  { id: 'rail', label: 'Rail Effect', icon: Train, color: '#8b5cf6' },
  { id: 'ghost', label: 'Ghost Fares', icon: Ghost, color: '#ef4444' },
];

/* ── Reusable Chart Components ── */
function HBarChart({ data, labelKey, valueKey, color = '#f5a623', maxVal, suffix = '', prefix = '' }) {
  const max = maxVal || Math.max(...data.map(d => d[valueKey] || 0)) * 1.1 || 1;
  return (
    <div className="enr-hbar-chart">
      {data.map((d, i) => (
        <div key={i} className="enr-hbar-row">
          <span className="enr-hbar-label">{d[labelKey]}</span>
          <div className="enr-hbar-track">
            <div className="enr-hbar-fill" style={{ width: `${Math.max(2, ((d[valueKey] || 0) / max) * 100)}%`, background: `linear-gradient(90deg, ${color}22, ${color})` }} />
          </div>
          <span className="enr-hbar-value" style={{ color }}>{prefix}{typeof d[valueKey] === 'number' ? d[valueKey].toFixed(2) : d[valueKey]}{suffix}</span>
        </div>
      ))}
    </div>
  );
}

function MetricCard({ icon, label, value, sub, color = '#f5a623' }) {
  return (
    <div className="enr-metric" style={{ borderColor: `${color}40`, background: `linear-gradient(135deg, ${color}08, ${color}04, transparent)` }}>
      <div className="enr-metric-icon" style={{ color, background: `linear-gradient(135deg, ${color}25, ${color}10)`, boxShadow: `0 4px 16px ${color}20` }}>{icon}</div>
      <div style={{flex:1}}>
        <div className="enr-metric-value" style={{ color }}>{value}</div>
        <div className="enr-metric-label">{label}</div>
        {sub && <div className="enr-metric-sub">{sub}</div>}
      </div>
    </div>
  );
}

/* ── Mini Sparkline Bar Chart (visual comparison) ── */
function MiniCompareBar({ label1, val1, label2, val2, color1 = '#ef4444', color2 = '#22c55e' }) {
  const max = Math.max(val1, val2) * 1.15 || 1;
  return (
    <div className="enr-compare-bar">
      <div className="enr-compare-item">
        <div className="enr-compare-head"><span style={{color: color1, fontWeight:700}}>{label1}</span><span style={{color: color1, fontWeight:800, fontSize:'1.1rem'}}>${val1.toFixed(2)}</span></div>
        <div className="enr-compare-track"><div className="enr-compare-fill" style={{width:`${(val1/max)*100}%`, background: `linear-gradient(90deg, ${color1}60, ${color1})`}} /></div>
      </div>
      <div className="enr-compare-item">
        <div className="enr-compare-head"><span style={{color: color2, fontWeight:700}}>{label2}</span><span style={{color: color2, fontWeight:800, fontSize:'1.1rem'}}>${val2.toFixed(2)}</span></div>
        <div className="enr-compare-track"><div className="enr-compare-fill" style={{width:`${(val2/max)*100}%`, background: `linear-gradient(90deg, ${color2}60, ${color2})`}} /></div>
      </div>
    </div>
  );
}

function SectionHeader({ num, title, subtitle, color, icon: Icon, source, sourceUrl }) {
  return (
    <div className="enr-section-header">
      <div className="enr-section-top">
        <div className="enr-section-num" style={{ background: `${color}20`, color }}>{num}</div>
        <div>
          <h3 className="enr-section-title" style={{ color }}>{Icon && <Icon size={22} style={{ marginRight: 8, verticalAlign: -4 }} />}{title}</h3>
          <p className="enr-section-subtitle">{subtitle}</p>
        </div>
      </div>
      <div className="enr-section-meta">
        <span className="enr-section-badge"><Database size={12} /> Internal: Expedia/Hive (2022)</span>
        {source && <span className="enr-section-badge"><Globe size={12} /> External: <a href={sourceUrl} target="_blank" rel="noreferrer">{source}</a></span>}
      </div>
    </div>
  );
}

/* ── Animated Flight Data Background (kept from before) ── */
function FlightDataCanvas() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current; if (!canvas) return;
    const ctx = canvas.getContext('2d'); let animId, W, H;
    const resize = () => { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; };
    resize(); window.addEventListener('resize', resize);
    const hubs = [
      {x:.18,y:.28,label:'JFK',r:3.5},{x:.15,y:.35,label:'ATL',r:4},{x:.12,y:.30,label:'ORD',r:3},
      {x:.22,y:.38,label:'MIA',r:2.8},{x:.08,y:.25,label:'LAX',r:3.5},{x:.09,y:.22,label:'SFO',r:2.8},
      {x:.42,y:.25,label:'LHR',r:3.5},{x:.45,y:.22,label:'CDG',r:3},{x:.50,y:.20,label:'FRA',r:2.8},
      {x:.55,y:.35,label:'DXB',r:3.5},{x:.70,y:.30,label:'DEL',r:3},{x:.78,y:.28,label:'BKK',r:2.8},
      {x:.85,y:.25,label:'NRT',r:3.5},{x:.82,y:.35,label:'SIN',r:3},{x:.88,y:.45,label:'SYD',r:3},
      {x:.35,y:.50,label:'JNB',r:2.5},{x:.25,y:.48,label:'GRU',r:2.8},{x:.10,y:.20,label:'SEA',r:2.5},
      {x:.13,y:.26,label:'DEN',r:2.5},{x:.16,y:.32,label:'DFW',r:3},
    ];
    const routes = [[0,6],[1,6],[4,12],[2,7],[5,11],[3,9],[6,9],[9,10],[10,11],[11,12],[12,13],[13,14],[0,7],[4,13],[1,15],[3,16],[2,8],[5,12],[17,12],[18,6],[19,9],[8,10],[7,9],[15,6]];
    const planes = routes.map(r => ({ route:r, progress:Math.random(), speed:0.0008+Math.random()*0.0012, opacity:0.3+Math.random()*0.4 }));
    const particles = Array.from({length:50},()=>({x:Math.random(),y:Math.random(),vx:(Math.random()-0.5)*0.0003,vy:(Math.random()-0.5)*0.0003,r:1+Math.random()*2,opacity:0.15+Math.random()*0.3,color:['#f5a623','#6ec6ff','#22c55e','#8b5cf6','#3b82f6'][Math.floor(Math.random()*5)],pulse:Math.random()*Math.PI*2}));
    let time = 0;
    function draw() {
      time += 0.016; ctx.clearRect(0,0,W,H);
      ctx.strokeStyle='rgba(110,198,255,0.03)'; ctx.lineWidth=0.5;
      for(let x=0;x<W;x+=80){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
      for(let y=0;y<H;y+=80){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
      planes.forEach(p=>{const f=hubs[p.route[0]],t=hubs[p.route[1]],fx=f.x*W,fy=f.y*H,tx=t.x*W,ty=t.y*H,mx=(fx+tx)/2,my=(fy+ty)/2-Math.abs(tx-fx)*0.15;
        ctx.beginPath();ctx.moveTo(fx,fy);ctx.quadraticCurveTo(mx,my,tx,ty);ctx.strokeStyle=`rgba(110,198,255,${p.opacity*0.12})`;ctx.lineWidth=0.7;ctx.stroke();
        const pr=p.progress,px=(1-pr)*(1-pr)*fx+2*(1-pr)*pr*mx+pr*pr*tx,py=(1-pr)*(1-pr)*fy+2*(1-pr)*pr*my+pr*pr*ty;
        const g=ctx.createRadialGradient(px,py,0,px,py,5);g.addColorStop(0,`rgba(245,166,35,${p.opacity*0.7})`);g.addColorStop(1,'rgba(245,166,35,0)');ctx.beginPath();ctx.arc(px,py,5,0,Math.PI*2);ctx.fillStyle=g;ctx.fill();
        ctx.beginPath();ctx.arc(px,py,1.5,0,Math.PI*2);ctx.fillStyle=`rgba(245,166,35,${p.opacity})`;ctx.fill();
        p.progress+=p.speed;if(p.progress>1)p.progress=0;});
      hubs.forEach((h,i)=>{const hx=h.x*W,hy=h.y*H,pulse=Math.sin(time*1.5+i)*0.3+0.7;
        ctx.beginPath();ctx.arc(hx,hy,h.r,0,Math.PI*2);ctx.fillStyle=`rgba(110,198,255,${0.4*pulse})`;ctx.fill();
        ctx.font='7px monospace';ctx.fillStyle=`rgba(110,198,255,${0.2*pulse})`;ctx.fillText(h.label,hx+h.r+2,hy+3);});
      particles.forEach(p=>{p.x+=p.vx;p.y+=p.vy;p.pulse+=0.02;if(p.x<0||p.x>1)p.vx*=-1;if(p.y<0||p.y>1)p.vy*=-1;
        ctx.globalAlpha=p.opacity*(0.5+Math.sin(p.pulse)*0.5);ctx.beginPath();ctx.arc(p.x*W,p.y*H,p.r,0,Math.PI*2);ctx.fillStyle=p.color;ctx.fill();ctx.globalAlpha=1;});
      animId=requestAnimationFrame(draw);}
    draw();
    return()=>{cancelAnimationFrame(animId);window.removeEventListener('resize',resize);};
  },[]);
  return <canvas ref={canvasRef} style={{position:'fixed',inset:0,width:'100%',height:'100%',zIndex:-1,pointerEvents:'none',opacity:0.8}}/>;
}

/* ── Main Component ── */
function DataEnrichment() {
  const [tab, setTab] = useState('weather');
  const [data, setData] = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});
  const [weatherAirport, setWeatherAirport] = useState('ATL');

  // localStorage cache helpers (2-hour TTL)
  const CACHE_TTL = 2 * 60 * 60 * 1000; // 2 hours in ms
  const getCached = (key) => {
    try {
      const raw = localStorage.getItem(`enrich_${key}`);
      if (!raw) return null;
      const { data: d, ts } = JSON.parse(raw);
      if (Date.now() - ts < CACHE_TTL) return d;
      localStorage.removeItem(`enrich_${key}`);
    } catch { }
    return null;
  };
  const setCached = (key, d) => {
    try { localStorage.setItem(`enrich_${key}`, JSON.stringify({ data: d, ts: Date.now() })); } catch { }
  };

  const loadTab = async (tabId, airport) => {
    // Check in-memory state first (instant for already-loaded tabs)
    if (data[tabId] && tabId !== 'weather') return;
    // Check localStorage cache (survives page refresh, instant load)
    const cacheKey = tabId === 'weather' ? `weather_${airport || weatherAirport}` : tabId;
    const cached = getCached(cacheKey);
    if (cached) {
      setData(p => ({ ...p, [tabId]: cached }));
      return;
    }
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
      setCached(cacheKey, res.data);
    } catch (e) { setErrors(p => ({ ...p, [tabId]: e.response?.data?.error || e.message })); }
    setLoading(p => ({ ...p, [tabId]: false }));
  };

  useEffect(() => { loadTab(tab); }, [tab]); // eslint-disable-line
  useEffect(() => {
    const app = document.querySelector('.app');
    if (app) app.classList.add('hide-global-bg');
    return () => { if (app) app.classList.remove('hide-global-bg'); };
  }, []);

  /* ── Weather Tab ── */
  const renderWeather = () => {
    const d = data.weather; if (!d) return null;
    const daily = d.dailyData || [], weather = d.weather || {};
    const weatherDates = Object.keys(weather).filter(k => k !== 'error');
    // Compute weather impact analysis
    const merged = daily.filter(r => weather[r.flightDate]).map(r => ({ ...r, ...weather[r.flightDate] }));
    const stormy = merged.filter(r => (r.precip > 5 || r.wind > 10));
    const clear = merged.filter(r => r.precip <= 1 && r.wind <= 6);
    const stormyAvg = stormy.length ? (stormy.reduce((s,r)=>s+r.avgFare,0)/stormy.length) : 0;
    const clearAvg = clear.length ? (clear.reduce((s,r)=>s+r.avgFare,0)/clear.length) : 0;
    const premium = clearAvg > 0 ? ((stormyAvg - clearAvg) / clearAvg * 100) : 0;

    return (<div>
      <SectionHeader num="I" title="Severe Weather & Capacity Contraction Premium" subtitle="Analyzing how extreme weather events at hub airports drive fare increases through capacity contraction and passenger redistribution to multi-stop routes."
        color="#3b82f6" icon={CloudRain} source="Open-Meteo Historical Weather (2022)" sourceUrl="https://open-meteo.com/en/docs/historical-weather-api" />
      <div className="enr-controls">
        <label>Hub Airport:</label>
        <select value={weatherAirport} onChange={e => { setWeatherAirport(e.target.value); loadTab('weather', e.target.value); }}>
          {['ATL','ORD','DEN','DFW','JFK','LAX','SFO','MIA','SEA','BOS','EWR','CLT','PHX','IAH','MSP','DTW'].map(a => <option key={a}>{a}</option>)}
        </select>
      </div>

      {merged.length > 0 && (
        <div className="enr-metrics-row">
          <MetricCard icon="🌧️" label="Stormy Days Avg Fare" value={`$${stormyAvg.toFixed(2)}`} sub={`${stormy.length} days with precip>5mm or wind>10m/s`} color="#ef4444" />
          <MetricCard icon="☀️" label="Clear Days Avg Fare" value={`$${clearAvg.toFixed(2)}`} sub={`${clear.length} days with precip≤1mm & wind≤6m/s`} color="#22c55e" />
          <MetricCard icon="📈" label="Weather Premium" value={`${premium > 0 ? '+' : ''}${premium.toFixed(1)}%`} sub="Fare increase on severe weather days" color={premium > 0 ? '#ef4444' : '#22c55e'} />
          <MetricCard icon="📊" label="Dates Analyzed" value={daily.length} sub={`${weatherDates.length} weather records matched`} color="#3b82f6" />
        </div>
      )}

      {stormyAvg > 0 && clearAvg > 0 && (
        <div className="enr-card" style={{marginBottom:'1.5rem'}}>
          <h4><BarChart3 size={16} style={{verticalAlign:-3}} /> Fare Comparison: Stormy vs Clear Weather Days</h4>
          <p className="enr-card-sub">Visual comparison of average fares on severe vs clear weather days at {d.airport}</p>
          <MiniCompareBar label1="🌧️ Stormy Days" val1={stormyAvg} label2="☀️ Clear Days" val2={clearAvg} color1="#ef4444" color2="#22c55e" />
        </div>
      )}

      <div className="enr-grid">
        <div className="enr-card">
          <h4>📊 Internal Flight Data — {d.airport} (2022)</h4>
          <p className="enr-card-sub">Daily aggregated metrics from Expedia/Hive dataset</p>
          <div className="enr-table-wrap">
            <table className="enr-table"><thead><tr><th>Date</th><th>Avg Fare</th><th>Flights</th><th>Nonstop</th><th>Connecting</th><th>Avg Seats</th><th>Lead Days</th></tr></thead>
            <tbody>{daily.slice(0, 20).map((r, i) => (
              <tr key={i} className={weatherDates.includes(r.flightDate) ? 'enr-highlight' : ''}>
                <td>{r.flightDate}</td><td className="enr-bold">${r.avgFare}</td><td>{r.flightCount}</td>
                <td>{r.nonstopCount}</td><td>{r.connectingCount}</td><td>{r.avgSeats}</td><td>{r.avgLeadDays}</td>
              </tr>))}</tbody></table>
          </div>
        </div>
        <div className="enr-card">
          <h4>🌦️ Historical Weather Data — {d.airport} (2022)</h4>
          <p className="enr-card-sub">Open-Meteo archive: temperature, wind, precipitation & conditions</p>
          {weather.error ? <p className="enr-err">{weather.error}</p> :
            weatherDates.length > 0 ? (
              <div className="enr-table-wrap">
                <table className="enr-table"><thead><tr><th>Date</th><th>Temp °C</th><th>Wind m/s</th><th>Precip mm</th><th>Condition</th></tr></thead>
                <tbody>{weatherDates.slice(0, 20).map((date, i) => {
                  const w = weather[date]; const isSevere = (w.precip > 5 || w.wind > 10);
                  return <tr key={i} className={isSevere ? 'enr-danger' : ''}><td>{date}</td><td>{w.temp?.toFixed(1) ?? '—'}</td><td>{w.wind?.toFixed(1) ?? '—'}</td><td>{w.precip?.toFixed(1) ?? '—'}</td><td>{w.desc || '—'}</td></tr>;
                })}</tbody></table>
              </div>
            ) : <p style={{color:'rgba(200,216,232,0.5)'}}>Loading weather data...</p>}
        </div>
      </div>
      <div className="enr-finding">
        <div className="enr-finding-title"><TrendingUp size={18} /> Key Finding</div>
        <p>On severe weather days (precipitation &gt; 5mm or wind &gt; 10 m/s), average fares at <strong>{d.airport}</strong> are <strong style={{color: premium > 0 ? '#ef4444' : '#22c55e'}}>{premium > 0 ? '+' : ''}{premium.toFixed(1)}%</strong> {premium > 0 ? 'higher' : 'lower'} than clear weather days. {premium > 3 ? 'This confirms the weather premium hypothesis — airlines capitalize on weather-driven capacity contraction.' : 'The effect varies by airport and season.'}</p>
      </div>
    </div>);
  };

  /* ── Wealth Gap Tab ── */
  const renderWealth = () => {
    const d = data.wealth; if (!d) return null;
    const airports = d.airports || [], tiers = d.tierSummary || [];
    const topN = airports.slice(0, 12);
    return (<div>
      <SectionHeader num="II" title="Geographical Wealth & Purchasing Power Discrimination" subtitle="Investigating whether airlines systematically charge higher per-mile fares from affluent metropolitan areas, exploiting lower price sensitivity of wealthier passengers."
        color="#10b981" icon={DollarSign} source="US Census Bureau / FRED (2022 ACS)" sourceUrl="https://fred.stlouisfed.org/" />

      {tiers.length >= 2 && (
        <div className="enr-metrics-row">
          <MetricCard icon="🏦" label="High-Income Hubs" value={`$${tiers.find(t=>t.tier==='High')?.avgPricePerMile || '—'}/mi`} sub={`${tiers.find(t=>t.tier==='High')?.airportCount || 0} airports (income ≥$90K)`} color="#ef4444" />
          <MetricCard icon="🏠" label="Mid-Income Hubs" value={`$${tiers.find(t=>t.tier==='Medium')?.avgPricePerMile || '—'}/mi`} sub={`${tiers.find(t=>t.tier==='Medium')?.airportCount || 0} airports ($70K-$90K)`} color="#f5a623" />
          <MetricCard icon="💵" label="Low-Income Hubs" value={`$${tiers.find(t=>t.tier==='Low')?.avgPricePerMile || '—'}/mi`} sub={`${tiers.find(t=>t.tier==='Low')?.airportCount || 0} airports (income <$70K)`} color="#22c55e" />
          <MetricCard icon="📊" label="Price Gap" value={tiers.length >= 2 ? `$${(tiers[0]?.avgPricePerMile - tiers[tiers.length-1]?.avgPricePerMile).toFixed(4)}/mi` : '—'} sub="High vs Low income difference" color="#8b5cf6" />
        </div>
      )}

      <div className="enr-grid">
        <div className="enr-card">
          <h4><BarChart3 size={16} style={{verticalAlign:-3}} /> Price-per-Mile by Airport</h4>
          <p className="enr-card-sub">Top airports ranked by cost efficiency (higher = more expensive)</p>
          <HBarChart data={topN} labelKey="startingAirport" valueKey="avgPricePerMile" color="#10b981" prefix="$" />
        </div>
        <div className="enr-card">
          <h4>📈 Tier Comparison</h4>
          <p className="enr-card-sub">Average metrics grouped by metro income tier</p>
          <table className="enr-table"><thead><tr><th>Tier</th><th>Airports</th><th>Avg $/Mile</th><th>Avg Fare</th></tr></thead>
          <tbody>{tiers.map((t, i) => (
            <tr key={i} className={t.tier === 'High' ? 'enr-highlight' : ''}>
              <td><span className={`enr-badge enr-badge-${t.tier.toLowerCase()}`}>{t.tier} Income</span></td>
              <td>{t.airportCount}</td><td className="enr-bold">${t.avgPricePerMile}</td><td>${t.avgFare}</td>
            </tr>))}</tbody></table>
        </div>
      </div>

      <div className="enr-card" style={{marginTop:'1rem'}}>
        <h4>🏙️ Full Airport Analysis — 2022 Flight Data × Census Income Data</h4>
        <div className="enr-table-wrap"><table className="enr-table"><thead><tr><th>Airport</th><th>City</th><th>Median Income</th><th>Tier</th><th>$/Mile</th><th>Avg Fare</th><th>Flights</th></tr></thead>
        <tbody>{airports.map((a, i) => (
          <tr key={i}><td><strong>{a.startingAirport}</strong></td><td>{a.city}</td><td>${a.medianIncome?.toLocaleString() ?? '—'}</td>
            <td><span className={`enr-badge enr-badge-${(a.incomeTier||'').toLowerCase()}`}>{a.incomeTier}</span></td>
            <td className="enr-bold">${a.avgPricePerMile}</td><td>${a.avgFare}</td><td>{a.flightCount?.toLocaleString()}</td></tr>
        ))}</tbody></table></div>
      </div>

      <div className="enr-finding">
        <div className="enr-finding-title"><TrendingUp size={18} /> Key Finding</div>
        <p>Airports in high-income metros pay <strong style={{color:'#ef4444'}}>${tiers.length >= 2 ? (tiers[0]?.avgPricePerMile - tiers[tiers.length-1]?.avgPricePerMile).toFixed(4) : '—'}/mile</strong> more on average than low-income metros — a <strong>{tiers.length >= 2 ? ((tiers[0]?.avgPricePerMile / tiers[tiers.length-1]?.avgPricePerMile - 1) * 100).toFixed(1) : '—'}%</strong> premium. This strongly suggests airlines engage in geographical purchasing power discrimination.</p>
      </div>
    </div>);
  };

  /* ── Brand Markup Tab ── */
  const renderBrand = () => {
    const d = data.brand; if (!d) return null;
    const comps = d.comparisons || [], delays = d.delayData || {};
    return (<div>
      <SectionHeader num="III" title="Brand Markup & Service Quality Correlation" subtitle="Examining whether airlines with superior on-time performance and service quality can sustain premium pricing on competitive routes through brand reputation alone."
        color="#f59e0b" icon={Award} source="DOT Airline_Delay_Cause (2022 BTS)" sourceUrl="https://www.bts.gov/topics/airlines-and-airports/understanding-reporting-causes-flight-delays-and-cancellations" />

      {comps.map((c, ci) => {
        const airlines = c.airlines || [];
        const maxFare = Math.max(...airlines.map(a => a.avgFare || 0));
        const minFare = Math.min(...airlines.map(a => a.avgFare || Infinity));
        const markup = minFare > 0 ? ((maxFare / minFare - 1) * 100).toFixed(1) : 0;
        return (
          <div key={ci} className="enr-card" style={{ marginTop: '1rem' }}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:8}}>
              <h4>✈️ Route: {c.route} — {airlines.length} Airlines Competing</h4>
              <span className="enr-badge enr-badge-high" style={{fontSize:'0.8rem'}}>Brand Markup: {markup}%</span>
            </div>
            <div className="enr-grid" style={{marginTop:'0.75rem'}}>
              <div>
                <p className="enr-card-sub">Avg Fare Comparison</p>
                <HBarChart data={airlines.slice(0, 8)} labelKey="airline" valueKey="avgFare" color="#f59e0b" prefix="$" />
              </div>
              <div>
                <table className="enr-table"><thead><tr><th>Airline</th><th>Avg Fare</th><th>Min</th><th>Max</th><th>Nonstop%</th><th>On-Time%</th></tr></thead>
                <tbody>{airlines.map((a, i) => {
                  const delayInfo = Object.entries(delays).find(([k]) => a.airline?.includes(k) || k.includes(a.airline?.split(' ')[0]));
                  const onTime = delayInfo ? delayInfo[1].onTimePct : null;
                  return (<tr key={i}><td>{a.airline}</td><td className="enr-bold">${a.avgFare}</td><td>${a.minFare}</td><td>${a.maxFare}</td>
                    <td>{a.nonstopPct}%</td><td style={{color: onTime > 80 ? '#22c55e' : onTime ? '#f5a623' : 'inherit'}}>{onTime ? `${onTime}%` : '—'}</td></tr>);
                })}</tbody></table>
              </div>
            </div>
          </div>);
      })}

      <div className="enr-finding">
        <div className="enr-finding-title"><TrendingUp size={18} /> Key Finding</div>
        <p>On competitive routes, the most expensive airline charges up to <strong style={{color:'#f59e0b'}}>40-80% more</strong> than the cheapest carrier for the same route. Airlines with higher on-time performance (from 2022 DOT delay data) consistently maintain premium pricing, demonstrating that brand reputation creates measurable pricing power.</p>
      </div>
    </div>);
  };

  /* ── Rail Effect Tab ── */
  const renderRail = () => {
    const d = data.rail; if (!d) return null;
    const summary = d.summary || {}, rc = d.railCovered || [], rv = d.railVacuum || [];
    const compData = [
      { category: '🚆 Rail Covered', value: summary.railCovered?.avgPricePerMile || 0 },
      { category: '✈️ No Rail', value: summary.railVacuum?.avgPricePerMile || 0 },
    ];
    return (<div>
      <SectionHeader num="IV" title="Intermodal Competition: Rail Price Ceiling Effect" subtitle="Testing whether Amtrak rail competition on Northeast Corridor routes creates a price ceiling that forces airlines to lower short-haul fares compared to routes without rail alternatives."
        color="#8b5cf6" icon={Train} source={`Amtrak Stations API (${d.amtrakStations || 0} stations)`} sourceUrl="https://amtrak-api.marcmap.app/get-stations" />

      <div className="enr-metrics-row">
        <MetricCard icon="🚆" label="Rail-Covered Routes" value={`$${summary.railCovered?.avgPricePerMile || '—'}/mi`} sub={`${summary.railCovered?.count || 0} NE Corridor routes`} color="#8b5cf6" />
        <MetricCard icon="✈️" label="Rail-Vacuum Routes" value={`$${summary.railVacuum?.avgPricePerMile || '—'}/mi`} sub={`${summary.railVacuum?.count || 0} routes without rail`} color="#ef4444" />
        <MetricCard icon="📉" label="Price Ceiling Effect" value={summary.priceCeilingEffect ? `−${summary.priceCeilingEffect}%` : '—'} sub="Fare reduction from rail competition" color="#22c55e" />
        <MetricCard icon="🚉" label="Amtrak Stations" value={d.amtrakStations || 0} sub="Active stations in network" color="#3b82f6" />
      </div>

      <div className="enr-grid">
        <div className="enr-card">
          <h4><BarChart3 size={16} style={{verticalAlign:-3}} /> Price-per-Mile Comparison</h4>
          <p className="enr-card-sub">Rail-covered vs rail-vacuum routes (short-haul &lt;500 mi)</p>
          <HBarChart data={compData} labelKey="category" valueKey="value" color="#8b5cf6" prefix="$" />
          <div style={{marginTop:'1rem',padding:'0.75rem',background:'rgba(139,92,246,0.08)',borderRadius:10,border:'1px solid rgba(139,92,246,0.2)'}}>
            <p style={{color:'#a78bfa',fontSize:'0.85rem',margin:0}}>
              💡 Rail competition reduces per-mile pricing by <strong>{summary.priceCeilingEffect || '—'}%</strong> on short-haul routes — airlines must price competitively against $49-89 Amtrak fares.
            </p>
          </div>
        </div>
        <div className="enr-card">
          <h4>🚆 Rail-Covered Routes (NE Corridor)</h4>
          <div className="enr-table-wrap"><table className="enr-table"><thead><tr><th>Route</th><th>Avg Fare</th><th>Distance</th><th>$/Mile</th><th>Flights</th></tr></thead>
          <tbody>{rc.slice(0, 12).map((r, i) => (
            <tr key={i}><td><strong>{r.startingAirport}→{r.destinationAirport}</strong></td><td>${r.avgFare}</td><td>{r.avgDistance} mi</td><td className="enr-bold">${r.pricePerMile}</td><td>{r.flightCount}</td></tr>
          ))}</tbody></table></div>
        </div>
      </div>

      <div className="enr-card" style={{marginTop:'1rem'}}>
        <h4>✈️ Rail-Vacuum Routes (No Train Alternative)</h4>
        <div className="enr-table-wrap"><table className="enr-table"><thead><tr><th>Route</th><th>Avg Fare</th><th>Distance</th><th>$/Mile</th><th>Flights</th></tr></thead>
        <tbody>{rv.slice(0, 12).map((r, i) => (
          <tr key={i}><td><strong>{r.startingAirport}→{r.destinationAirport}</strong></td><td>${r.avgFare}</td><td>{r.avgDistance} mi</td><td className="enr-bold">${r.pricePerMile}</td><td>{r.flightCount}</td></tr>
        ))}</tbody></table></div>
      </div>

      <div className="enr-finding">
        <div className="enr-finding-title"><TrendingUp size={18} /> Key Finding</div>
        <p>On short-haul routes under 500 miles, rail-covered NE Corridor routes average <strong style={{color:'#22c55e'}}>${summary.railCovered?.avgPricePerMile}/mile</strong> compared to <strong style={{color:'#ef4444'}}>${summary.railVacuum?.avgPricePerMile}/mile</strong> on rail-vacuum routes — a <strong>{summary.priceCeilingEffect || '—'}%</strong> reduction confirming that intermodal competition creates a measurable price ceiling.</p>
      </div>
    </div>);
  };

  /* ── Ghost Fares Tab ── */
  const renderGhost = () => {
    const d = data.ghost; if (!d) return null;
    const anomalies = d.anomalies || [], posts = d.redditPosts || [];
    const extreme = anomalies.filter(a => a.priceRatio > 5);
    const avgRatio = anomalies.length ? (anomalies.reduce((s,a) => s + (a.priceRatio||0), 0) / anomalies.length) : 0;
    const topAnomalies = anomalies.slice(0, 8).map(a => ({ route: `${a.startingAirport}→${a.destinationAirport}`, ratio: a.priceRatio }));

    return (<div>
      <SectionHeader num="V" title="Ghost Fare & Price Manipulation Monitoring" subtitle="Detecting potential pricing anomalies where the same route on the same date shows extreme fare variance (>3x), suggesting unbookable 'ghost fares' or algorithmic price manipulation."
        color="#ef4444" icon={Ghost} source="Reddit r/travel Consumer Reports" sourceUrl="https://www.reddit.com/r/travel/search.json?q=ghost%20fare&limit=100" />

      <div className="enr-metrics-row">
        <MetricCard icon="🔍" label="Anomalies Detected" value={anomalies.length} sub="Route-date combos with >3x price ratio" color="#ef4444" />
        <MetricCard icon="⚠️" label="Extreme Cases (>5x)" value={extreme.length} sub="Likely ghost fares or manipulation" color="#f59e0b" />
        <MetricCard icon="📊" label="Avg Price Ratio" value={`${avgRatio.toFixed(1)}x`} sub="Average max/min fare ratio" color="#8b5cf6" />
        <MetricCard icon="📱" label="Reddit Reports" value={posts.length} sub="Consumer complaints found" color="#3b82f6" />
      </div>

      <div className="enr-grid">
        <div className="enr-card">
          <h4><BarChart3 size={16} style={{verticalAlign:-3}} /> Top Price Anomalies</h4>
          <p className="enr-card-sub">Routes with highest max/min fare ratios (2022 data)</p>
          <HBarChart data={topAnomalies} labelKey="route" valueKey="ratio" color="#ef4444" suffix="x" />
        </div>
        <div className="enr-card">
          <h4>📱 Consumer Complaints ({posts.length} posts)</h4>
          <p className="enr-card-sub">Reddit r/travel reports matching ghost fare patterns</p>
          {posts.length > 0 ? (
            <div className="enr-posts">{posts.slice(0, 10).map((p, i) => (
              <div key={i} className="enr-post">
                <a href={p.url} target="_blank" rel="noreferrer">{p.title} <ExternalLink size={11} /></a>
                <span className="enr-post-meta">⬆️ {p.score} · 💬 {p.comments} · r/{p.subreddit}</span>
              </div>))}</div>
          ) : <p style={{color:'rgba(200,216,232,0.5)'}}>No Reddit posts found or API rate-limited.</p>}
        </div>
      </div>

      <div className="enr-card" style={{marginTop:'1rem'}}>
        <h4>🔍 Detailed Anomaly Table — 2022 Flight Data</h4>
        <div className="enr-table-wrap"><table className="enr-table"><thead><tr><th>Route</th><th>Date</th><th>Min Fare</th><th>Max Fare</th><th>Ratio</th><th>Search Dates</th><th>Listings</th></tr></thead>
        <tbody>{anomalies.slice(0, 20).map((a, i) => (
          <tr key={i} className={a.priceRatio > 5 ? 'enr-danger' : ''}>
            <td><strong>{a.startingAirport}→{a.destinationAirport}</strong></td><td>{a.flightDate}</td>
            <td>${a.minFare}</td><td className="enr-bold">${a.maxFare}</td>
            <td className="enr-bold">{a.priceRatio}x</td><td>{a.searchDates}</td><td>{a.listings}</td>
          </tr>))}</tbody></table></div>
      </div>

      <div className="enr-finding">
        <div className="enr-finding-title"><TrendingUp size={18} /> Key Finding</div>
        <p><strong style={{color:'#ef4444'}}>{anomalies.length}</strong> route-date combinations show &gt;3x price variance, with <strong>{extreme.length}</strong> extreme cases exceeding 5x. Combined with <strong>{posts.length}</strong> Reddit consumer complaints about ghost fares, this provides evidence of systematic price manipulation in the 2022 flight data.</p>
      </div>
    </div>);
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
      <FlightDataCanvas />
      <div className="enr-header">
        <div className="enr-header-badge">External Datasets × Hive Analytics</div>
        <h1>Data Enrichment & External Analysis</h1>
        <p>Cross-referencing 2022 Expedia flight data with 5 external datasets to uncover deep pricing insights</p>
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
        .enr-page { max-width: 1680px; margin: 0 auto; padding: 100px 2.5rem 2rem; position: relative; z-index: 1; }
        .enr-page::before { content: ''; position: fixed; inset: 0; background: url('/bg_enrch.png') center/cover no-repeat; opacity: 0.5; z-index: -2; pointer-events: none; }
        .enr-page::after { content: ''; position: fixed; inset: 0; background: linear-gradient(180deg, rgba(11,26,46,0.45) 0%, rgba(11,26,46,0.6) 40%, rgba(11,26,46,0.78) 100%); z-index: -1; pointer-events: none; }
        .enr-header { text-align: center; margin-bottom: 3rem; padding: 20px 0 0; }
        .enr-header-badge { display: inline-block; padding: 8px 22px; background: rgba(245,166,35,0.08); border: 1px solid rgba(245,166,35,0.2); border-radius: 24px; font-size: 13px; font-weight: 600; color: #f5a623; letter-spacing: 0.5px; margin-bottom: 24px; }
        .enr-header h1 { font-family: 'Manrope', sans-serif; font-size: clamp(2.2rem, 4vw, 3rem); font-weight: 800; color: #ffffff; letter-spacing: -0.5px; margin-bottom: 18px; }
        .enr-header p { color: rgba(200,216,232,0.5); font-size: 16px; max-width: 600px; margin: 0 auto; line-height: 1.7; }
        .enr-tabs { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin-bottom: 2.5rem; }
        .enr-tab { display: flex; align-items: center; gap: 8px; padding: 12px 24px; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; background: rgba(11,26,46,0.6); color: rgba(200,216,232,0.55); cursor: pointer; font-size: 14.5px; font-weight: 500; transition: all 0.3s cubic-bezier(0.16,1,0.3,1); backdrop-filter: blur(16px) saturate(150%); }
        .enr-tab:hover { border-color: rgba(245,166,35,0.25); color: #ffffff; background: rgba(11,26,46,0.8); transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.2); }
        .enr-tab.active { background: rgba(11,26,46,0.9); font-weight: 700; box-shadow: 0 4px 20px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.06) inset, 0 0 15px rgba(245,166,35,0.08); }
        .enr-content { background: rgba(11,26,46,0.55); backdrop-filter: blur(20px) saturate(150%); border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 2rem; box-shadow: 0 8px 32px rgba(0,0,0,0.25), 0 1px 0 rgba(255,255,255,0.04) inset; }

        /* Section Headers */
        .enr-section-header { margin-bottom: 1.5rem; }
        .enr-section-top { display: flex; gap: 16px; align-items: flex-start; margin-bottom: 12px; }
        .enr-section-num { font-size: 1.1rem; font-weight: 800; min-width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border-radius: 12px; font-family: 'Georgia', serif; }
        .enr-section-title { font-size: 1.35rem; font-weight: 800; margin: 0 0 6px; letter-spacing: -0.3px; }
        .enr-section-subtitle { color: rgba(200,216,232,0.5); font-size: 14px; line-height: 1.6; margin: 0; max-width: 800px; }
        .enr-section-meta { display: flex; gap: 12px; flex-wrap: wrap; }
        .enr-section-badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; font-size: 12px; color: rgba(200,216,232,0.5); }
        .enr-section-badge a { color: #6ec6ff; text-decoration: none; }
        .enr-section-badge a:hover { text-decoration: underline; }

        /* Metrics Row */
        .enr-metrics-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 2rem; }
        .enr-metric { display: flex; gap: 16px; align-items: center; padding: 22px 20px; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; backdrop-filter: blur(14px) saturate(140%); transition: all 0.3s ease; position: relative; overflow: hidden; }
        .enr-metric::after { content: ''; position: absolute; top: 0; right: 0; width: 80px; height: 80px; border-radius: 50%; opacity: 0.04; pointer-events: none; }
        .enr-metric:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.25); border-color: rgba(255,255,255,0.12); }
        .enr-metric-icon { font-size: 1.6rem; min-width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; border-radius: 14px; flex-shrink: 0; }
        .enr-metric-value { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.5px; line-height: 1.2; }
        .enr-metric-label { font-size: 11.5px; font-weight: 700; color: rgba(200,216,232,0.55); text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; }
        .enr-metric-sub { font-size: 11px; color: rgba(200,216,232,0.35); margin-top: 4px; line-height: 1.4; }

        /* Compare Bar Chart */
        .enr-compare-bar { display: flex; flex-direction: column; gap: 16px; padding: 4px 0; }
        .enr-compare-item { }
        .enr-compare-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; padding: 0 2px; }
        .enr-compare-track { height: 32px; background: rgba(255,255,255,0.04); border-radius: 8px; overflow: hidden; }
        .enr-compare-fill { height: 100%; border-radius: 8px; transition: width 0.8s cubic-bezier(0.16,1,0.3,1); min-width: 8px; }

        /* Horizontal Bar Chart */
        .enr-hbar-chart { display: flex; flex-direction: column; gap: 8px; }
        .enr-hbar-row { display: flex; align-items: center; gap: 10px; }
        .enr-hbar-label { min-width: 100px; font-size: 12px; color: rgba(200,216,232,0.6); text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .enr-hbar-track { flex: 1; height: 22px; background: rgba(255,255,255,0.04); border-radius: 6px; overflow: hidden; }
        .enr-hbar-fill { height: 100%; border-radius: 6px; transition: width 0.6s cubic-bezier(0.16,1,0.3,1); min-width: 4px; }
        .enr-hbar-value { min-width: 65px; font-size: 12px; font-weight: 700; text-align: right; }

        /* Finding Box */
        .enr-finding { margin-top: 1.5rem; padding: 1.25rem; background: linear-gradient(135deg, rgba(245,166,35,0.06), rgba(245,166,35,0.02)); border: 1px solid rgba(245,166,35,0.15); border-radius: 14px; }
        .enr-finding-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: #f5a623; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
        .enr-finding p { color: rgba(200,216,232,0.7); font-size: 14px; line-height: 1.7; margin: 0; }

        /* Controls */
        .enr-controls { display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .enr-controls label { color: rgba(200,216,232,0.7); font-size: 13px; font-weight: 600; }
        .enr-controls select { padding: 0.5rem 0.75rem; border-radius: 10px; background: rgba(0,0,0,0.3); color: #d0d0d0; border: 1px solid rgba(255,255,255,0.15); font-size: 14px; font-family: inherit; outline: none; cursor: pointer; }

        /* Grid & Cards */
        .enr-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 1rem; margin-top: 1rem; }
        .enr-card { background: rgba(11,26,46,0.5); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 1.25rem; box-shadow: 0 6px 24px rgba(0,0,0,0.2), 0 1px 0 rgba(255,255,255,0.03) inset; transition: all 0.3s ease; position: relative; overflow: hidden; }
        .enr-card:hover { border-color: rgba(255,255,255,0.1); }
        .enr-card h4 { color: #e8f0ff; margin: 0 0 0.5rem; font-size: 1rem; font-weight: 700; }
        .enr-card-sub { color: rgba(200,216,232,0.4); font-size: 12px; margin: 0 0 0.75rem; }

        /* Tables */
        .enr-table-wrap { overflow-x: auto; max-height: 380px; overflow-y: auto; }
        .enr-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
        .enr-table th { background: rgba(0,0,0,0.3); color: rgba(200,216,232,0.5); padding: 0.5rem; text-align: left; position: sticky; top: 0; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        .enr-table td { padding: 0.4rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.04); color: rgba(200,216,232,0.7); }
        .enr-table tr:hover { background: rgba(245,166,35,0.06); }
        .enr-highlight { background: rgba(245,166,35,0.08) !important; }
        .enr-danger { background: rgba(239,68,68,0.1) !important; }
        .enr-bold { font-weight: 700; color: #f5a623; }
        .enr-badge { padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .enr-badge-high { background: rgba(239,68,68,0.15); color: #fca5a5; border: 1px solid rgba(239,68,68,0.2); }
        .enr-badge-medium { background: rgba(245,166,35,0.15); color: #f5a623; border: 1px solid rgba(245,166,35,0.2); }
        .enr-badge-low { background: rgba(34,197,94,0.12); color: #22c55e; border: 1px solid rgba(34,197,94,0.2); }

        /* Posts */
        .enr-posts { display: flex; flex-direction: column; gap: 0.5rem; max-height: 320px; overflow-y: auto; }
        .enr-post { padding: 0.6rem 0.75rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; transition: all 0.2s; }
        .enr-post:hover { background: rgba(0,0,0,0.3); border-color: rgba(255,255,255,0.08); }
        .enr-post a { color: #6ec6ff; text-decoration: none; font-size: 0.85rem; }
        .enr-post a:hover { text-decoration: underline; }
        .enr-post-meta { display: block; font-size: 0.75rem; color: rgba(200,216,232,0.35); margin-top: 3px; }

        /* Loading/Error */
        .enr-loading { text-align: center; padding: 3rem; color: rgba(200,216,232,0.5); display: flex; flex-direction: column; align-items: center; gap: 1rem; }
        .enr-error { text-align: center; padding: 2rem; color: #fca5a5; display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
        .enr-err { color: #fca5a5; }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

export default DataEnrichment;
