
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowUpRight, Plus, Mic, Volume2, ArrowUp, Star,
  X, Facebook, Twitter, Instagram, Linkedin, Plane,
  Search, MapPin, Calendar, BarChart3, MessageSquare, Building2
} from 'lucide-react';

// Scroll-triggered animation hook
function useScrollAnim() {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('anim-visible');
          observer.unobserve(el);
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return ref;
}

function AnimDiv({ className = '', children, ...props }) {
  const ref = useScrollAnim();
  return <div ref={ref} className={`anim-hidden ${className}`} {...props}>{children}</div>;
}

const testimonials = [
  {
    name: 'Sophia & Liam',
    role: 'Honeymoon Travelers',
    text: 'AI Travel Planner made my honeymoon trip flawless! It even adjusted our schedule when it started raining.',
    avatar: 'https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=100&q=80',
    hasMultipleAvatars: true,
  },
  {
    name: 'Dianne Russell',
    role: 'Family Traveler',
    text: 'Planning a family trip can be stressful, but the AI made it effortless. It created a balanced plan with kid-friendly...',
    avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&q=80',
  },
  {
    name: 'Annette Black',
    role: 'Backpacker',
    text: 'As a solo traveler, I was truly amazed by how the AI uncovered hidden coffee shops, charming local spots, and unique experiences I would have never found on my own, turning my trip into a personalized adventure filled with authentic discoveries.',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&q=80',
  },
];

const faqs = [
  { q: 'What is an AI Travel Planner?', a: 'An AI Travel Planner uses artificial intelligence to create personalized travel itineraries based on your preferences, budget, and interests. It analyzes millions of data points to recommend the best destinations, activities, and accommodations for your trip.' },
  { q: "Can I edit the itinerary after it's created?", a: 'Yes! You can easily adjust destinations, activities, and timings. The AI will automatically reoptimize your trip plan to fit your new preferences.' },
  { q: 'How does it work?', a: 'Simply tell us your travel preferences — dates, budget, interests — and our AI will generate a complete itinerary with flights, hotels, activities, and dining recommendations tailored just for you.' },
  { q: 'Does it include hotel or flight bookings?', a: 'Yes, our platform integrates with major booking services to provide real-time pricing and availability for flights and hotels directly within your itinerary.' },
  { q: 'Can I use it for group trips?', a: 'Absolutely! Our AI can plan for groups of any size, balancing different preferences and interests to create an itinerary everyone will enjoy.' },
];

const footerLinks = {
  releases: ['Integrations', 'Smart Routes', 'AI Itineraries', 'Vision Maps', '100M Destinations'],
  resources: ['Travel Stories', 'Our Apps', 'Travel Library', 'Tutorials'],
  company: ['About', 'Careers', 'Blog', 'Contact'],
};

function Landing() {
  const navigate = useNavigate();
  const [openFaq, setOpenFaq] = useState(1);
  const [testimonialPage, setTestimonialPage] = useState(0);
  const [typedText, setTypedText] = useState('');
  const line1 = 'Turning Volatility';
  const line2 = 'Into Visibility';
  const fullText = line1 + ' ' + line2;

  useEffect(() => {
    let i = 0;
    const timer = setInterval(() => {
      setTypedText(fullText.slice(0, i + 1));
      i++;
      if (i >= fullText.length) clearInterval(timer);
    }, 60);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="tl-landing">
      {/* ===== HERO SECTION ===== */}
      <section className="tl-hero" id="hero">
        <div className="tl-hero-bg" />
        <video
          className="tl-hero-video"
          autoPlay
          loop
          muted
          playsInline
        >
          <source src="/herovideo.mp4" type="video/mp4" />
        </video>
        <div className="tl-hero-video-overlay" />
        {/* Slogan - centered on the plane */}
        <div className="tl-hero-slogan-area">
          <h1 className="tl-hero-title">
            {typedText.length <= 18 ? typedText : line1}
            {typedText.length > 19 && <><br />{typedText.slice(19)}</>}
            <span className="tl-typing-cursor">.</span>
          </h1>
        </div>

        {/* Buttons - below the airplane */}
        <div className="tl-hero-btn-area">
          <button className="tl-hero-btn-primary" onClick={() => navigate('/flights')}>
            Explore Flights <ArrowUpRight size={16} />
          </button>
          <button className="tl-hero-btn-ghost" onClick={() => navigate('/chatbot')}>
            Ask AI Assistant
          </button>
        </div>

        {/* Floating Stats */}
        <div className="tl-hero-stats">
          <div className="tl-hero-stat">
            <span className="tl-hero-stat-value">150+</span>
            <span className="tl-hero-stat-label">Destinations</span>
          </div>
          <div className="tl-hero-stat-divider" />
          <div className="tl-hero-stat">
            <span className="tl-hero-stat-value">50+</span>
            <span className="tl-hero-stat-label">Airlines</span>
          </div>
          <div className="tl-hero-stat-divider" />
          <div className="tl-hero-stat">
            <span className="tl-hero-stat-value">1M+</span>
            <span className="tl-hero-stat-label">Flights Analyzed</span>
          </div>
          <div className="tl-hero-stat-divider" />
          <div className="tl-hero-stat">
            <span className="tl-hero-stat-value">24/7</span>
            <span className="tl-hero-stat-label">AI Monitoring</span>
          </div>
        </div>

        {/* Scroll Indicator */}
        <div className="tl-scroll-indicator">
          <div className="tl-scroll-line" />
        </div>

      </section>

      {/* ===== AI DESCRIPTION SECTION ===== */}
      <section className="tl-ai-section" id="about">
        <AnimDiv className="tl-ai-section-inner">
          <div className="tl-ai-avatars-left">
            <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=60&q=80" alt="" className="tl-ai-avatar tl-av-1" />
            <img src="https://images.unsplash.com/photo-1580489944761-15a19d654956?w=60&q=80" alt="" className="tl-ai-avatar tl-av-2" />
          </div>
          <div className="tl-ai-text-center">
            <h2>Our AI simplifies every step of<br />travel planning allowing you.</h2>
            <p>Our AI-driven platform analyzes millions of data points to craft personalized itineraries that fit your time budget and interests making travel planning effortless and accurate.</p>
            <div className="tl-ai-buttons">
              <button className="tl-btn-outline" onClick={() => navigate('/where-to-fly')}>View All <ArrowUpRight size={14} /></button>
              <button className="tl-btn-dark" onClick={() => navigate('/chatbot')}>● Learn More</button>
            </div>
          </div>
          <div className="tl-ai-avatars-right">
            <img src="https://images.unsplash.com/photo-1527980965255-d3b416303d12?w=60&q=80" alt="" className="tl-ai-avatar tl-av-3" />
            <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=60&q=80" alt="" className="tl-ai-avatar tl-av-4" />
          </div>
        </AnimDiv>
      </section>

      {/* ===== IMAGE GALLERY ===== */}
      <section className="tl-gallery" id="destinations">
        <div className="tl-gallery-grid">
          <div className="tl-gallery-card">
            <img src="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&q=80" alt="Mountain" />
            <div className="tl-gallery-badge"><Star size={12} /></div>
          </div>
          <div className="tl-gallery-card tl-gallery-featured">
            <img src="https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=400&q=80" alt="Explorer" />
            <div className="tl-gallery-live">
              <span className="tl-live-dot"></span> LIVE
            </div>
          </div>
          <div className="tl-gallery-card">
            <img src="https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400&q=80" alt="Nature" />
          </div>
          <div className="tl-gallery-card">
            <img src="https://images.unsplash.com/photo-1454391304352-2bf4678b1a7a?w=400&q=80" alt="Mountain peak" />
            <div className="tl-gallery-counter">+3</div>
          </div>
        </div>
      </section>

      {/* ===== TESTIMONIALS ===== */}
      <section className="tl-testimonials" id="how">
        <div className="tl-testimonials-inner">
          <AnimDiv className="tl-testimonials-header">
            <div>
              <span className="tl-section-badge">Testimonials</span>
              <h2>Loved by Explorers<br />Worldwide</h2>
            </div>
            <p className="tl-testimonials-desc">
              Discover how our AI-powered planner has transformed the way travelers explore the world — from seamless itineraries to stress-free adventures.
            </p>
          </AnimDiv>

          <AnimDiv className="tl-testimonials-grid">
            {/* Traveler count badge */}
            <div className="tl-traveler-count">
              <div className="tl-traveler-avatars">
                <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=40&q=80" alt="" />
                <img src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=40&q=80" alt="" />
                <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=40&q=80" alt="" />
              </div>
              <span>12M+ travelers</span>
            </div>

            {testimonials.map((t, i) => (
              <div key={i} className={`tl-testimonial-card ${i === 0 ? 'tl-tc-featured' : ''}`}>
                <div className="tl-tc-header">
                  <img src={t.avatar} alt={t.name} className="tl-tc-avatar" />
                  <div>
                    <div className="tl-tc-name">{t.name}</div>
                    <div className="tl-tc-role">{t.role}</div>
                  </div>
                </div>
                <p className="tl-tc-text">{t.text}</p>
                {i === 1 && (
                  <button className="tl-btn-outline tl-btn-sm" onClick={() => navigate('/chatbot')}>★ View All <ArrowUpRight size={12} /></button>
                )}
              </div>
            ))}
          </AnimDiv>

          <div className="tl-testimonials-dots">
            <span className={`tl-dot ${testimonialPage === 0 ? 'active' : ''}`} onClick={() => setTestimonialPage(0)}></span>
            <span className={`tl-dot ${testimonialPage === 1 ? 'active' : ''}`} onClick={() => setTestimonialPage(1)}></span>
            <span className={`tl-dot ${testimonialPage === 2 ? 'active' : ''}`} onClick={() => setTestimonialPage(2)}></span>
          </div>
        </div>
      </section>

      {/* ===== FAQ SECTION ===== */}
      <section className="tl-faq">
        <div className="tl-faq-inner">
          <AnimDiv className="tl-faq-header">
            <h2>Common Questions from<br />Smart Travelers</h2>
            <p>Discover how our AI Travel Planner helps you create personalized trips, adjust plans instantly, and explore with confidence.</p>
          </AnimDiv>
          <div className="tl-faq-list">
            {faqs.map((faq, i) => (
              <div key={i} className={`tl-faq-item ${openFaq === i ? 'open' : ''}`} onClick={() => setOpenFaq(openFaq === i ? -1 : i)}>
                <div className="tl-faq-question">
                  <span>{faq.q}</span>
                  <button className="tl-faq-toggle">
                    {openFaq === i ? <X size={16} /> : <Plus size={16} />}
                  </button>
                </div>
                {openFaq === i && (
                  <div className="tl-faq-answer">{faq.a}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== CTA SECTION ===== */}
      <section className="tl-cta">
        <AnimDiv className="tl-cta-inner">
          <h2>Plan Your Dream Trip<br />with AI in Seconds</h2>
          <p>Get personalized itineraries, smart recommendations, and seamless travel planning, all powered by AI.</p>
          <button className="tl-btn-outline tl-btn-cta" onClick={() => navigate('/flights')}>
            Join The Trip <ArrowUpRight size={14} />
          </button>
        </AnimDiv>
        <div className="tl-cta-mountains"></div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer className="tl-footer" id="contact">
        <div className="tl-footer-inner">
          <div className="tl-footer-brand">
            <div className="tl-nav-logo">
              <div className="tl-logo-icon"><Plane size={16} /></div>
              <span className="tl-logo-text">Data Turbulence</span>
            </div>
            <p>Explore the world effortlessly with intelligent, personalized travel planning powered by AI.</p>
            <button className="tl-btn-outline tl-btn-sm">Try it now <ArrowUpRight size={12} /></button>
          </div>

          <div className="tl-footer-columns">
            <div className="tl-footer-col">
              <h4>Releases</h4>
              {footerLinks.releases.map((l, i) => <a key={i} href="#">{l}</a>)}
            </div>
            <div className="tl-footer-col">
              <h4>Resources</h4>
              {footerLinks.resources.map((l, i) => <a key={i} href="#">{l}</a>)}
            </div>
            <div className="tl-footer-col">
              <h4>Company</h4>
              {footerLinks.company.map((l, i) => <a key={i} href="#">{l}</a>)}
            </div>
          </div>

          <div className="tl-footer-right">
            <div className="tl-footer-legal">
              <a href="#">Terms</a>
              <a href="#">Privacy</a>
            </div>
            <div className="tl-footer-social">
              <a href="#"><Facebook size={16} /></a>
              <a href="#"><Twitter size={16} /></a>
              <a href="#"><Instagram size={16} /></a>
              <a href="#"><Linkedin size={16} /></a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Landing;
