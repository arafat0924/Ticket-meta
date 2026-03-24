import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, MapPin, Calendar, Users, ArrowRight, ArrowUpRight, Plane, Globe, Shield, Headphones, ChevronLeft, ChevronRight } from 'lucide-react';

const destinations = [
  { city: 'Tokyo', country: 'Japan', tag: 'Cultural Heritage', price: '14,200', img: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=600&q=80' },
  { city: 'Maldives', country: 'Malé', tag: 'Tropical Seclusion', price: '18,900', img: 'https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=600&q=80' },
  { city: 'Reykjavik', country: 'Iceland', tag: 'Arctic Luxury', price: '12,400', img: 'https://images.unsplash.com/photo-1504829857797-ddff29c27927?w=600&q=80' },
];

const stats = [
  { value: '80M+', label: 'Flight Records', icon: <Plane size={20} /> },
  { value: '15k', label: 'Airport Database', icon: <Globe size={20} /> },
  { value: '48', label: 'Airlines Tracked', icon: <Shield size={20} /> },
  { value: '24/7', label: 'AI Concierge', icon: <Headphones size={20} /> },
];

function Landing() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      {/* HERO */}
      <section className="landing-hero">
        <div className="hero-bg" />
        <div className="hero-content">
          <h1 className="hero-title">WHERE TO NEXT?</h1>
          <p className="hero-subtitle">CHARTING THE COURSE FOR THE DISCERNING WANDERER</p>

          {/* Search Bar */}
          <div className="hero-search">
            <div className="hero-search-field">
              <span className="hsf-label">DEPARTURE</span>
              <div className="hsf-value"><MapPin size={16} className="hsf-icon" /> Atlanta, US</div>
            </div>
            <div className="hero-search-divider" />
            <div className="hero-search-field">
              <span className="hsf-label">DESTINATION</span>
              <div className="hsf-value"><MapPin size={16} className="hsf-icon" /> Los Angeles, US</div>
            </div>
            <div className="hero-search-divider" />
            <div className="hero-search-field">
              <span className="hsf-label">DATES</span>
              <div className="hsf-value"><Calendar size={16} className="hsf-icon" /> Dec 12 - Dec 24</div>
            </div>
            <div className="hero-search-divider" />
            <div className="hero-search-field">
              <span className="hsf-label">TRAVELERS</span>
              <div className="hsf-value"><Users size={16} className="hsf-icon" /> 2 Adults, First</div>
            </div>
            <button className="hero-search-btn" onClick={() => navigate('/flights')}>
              SEARCH FLIGHTS <ArrowRight size={16} />
            </button>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="hero-scroll">
          <span className="hero-scroll-text">EXPLORE DESTINATIONS</span>
          <div className="hero-scroll-line" />
        </div>
      </section>

      {/* STATS */}
      <section className="landing-stats">
        {stats.map((s, i) => (
          <div key={i} className="landing-stat">
            <div className="ls-value">{s.value}</div>
            <div className="ls-label">{s.label}</div>
          </div>
        ))}
      </section>

      {/* DESTINATIONS */}
      <section className="landing-destinations">
        <div className="ld-header">
          <div>
            <span className="ld-tag">THE COLLECTION</span>
            <h2 className="ld-title">Exclusive Destinations</h2>
          </div>
          <div className="ld-arrows">
            <button className="ld-arrow"><ChevronLeft size={20} /></button>
            <button className="ld-arrow"><ChevronRight size={20} /></button>
          </div>
        </div>
        <div className="ld-grid">
          {destinations.map((d, i) => (
            <div key={i} className="dest-hero-card" onClick={() => navigate('/flights')}>
              <div className="dhc-img" style={{ backgroundImage: `url(${d.img})` }} />
              <div className="dhc-overlay" />
              <div className="dhc-content">
                <div className="dhc-info">
                  <h3 className="dhc-city">{d.city}</h3>
                  <p className="dhc-country">{d.country} • {d.tag}</p>
                </div>
                <div className="dhc-bottom">
                  <span className="dhc-price">FROM ${d.price}</span>
                  <span className="dhc-arrow"><ArrowUpRight size={18} /></span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section className="landing-features">
        <div className="lf-header">
          <span className="ld-tag">POWERED BY BIG DATA</span>
          <h2 className="ld-title">Why SkyQuery?</h2>
        </div>
        <div className="lf-grid">
          <div className="lf-card" onClick={() => navigate('/flights')}>
            <div className="lf-icon"><Search size={24} /></div>
            <h3>Flight Search</h3>
            <p>Search 80M+ flight itineraries with Hive-powered big data analytics</p>
          </div>
          <div className="lf-card" onClick={() => navigate('/flights')}>
            <div className="lf-icon"><Globe size={24} /></div>
            <h3>Route Discovery</h3>
            <p>Explore route options using the current flight search experience</p>
          </div>
          <div className="lf-card" onClick={() => navigate('/when-to-fly')}>
            <div className="lf-icon"><Calendar size={24} /></div>
            <h3>When to Fly</h3>
            <p>Find the best month to book with historical price trend analysis</p>
          </div>
          <div className="lf-card" onClick={() => navigate('/chatbot')}>
            <div className="lf-icon"><Headphones size={24} /></div>
            <h3>AI Concierge</h3>
            <p>Ask natural questions — our AI generates SQL and queries the database</p>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="landing-footer">
        <div className="lfoot-left">
          <div className="lfoot-brand">SKYQUERY</div>
          <div className="lfoot-copy">Royal Edition © 2024</div>
        </div>
        <div className="lfoot-links">
          <a href="#privacy">PRIVACY POLICY</a>
          <a href="#terms">TERMS OF SERVICE</a>
          <a href="#contact">CONTACT US</a>
          <a href="#concierge">GLOBAL CONCIERGE</a>
        </div>
      </footer>
    </div>
  );
}

export default Landing;
