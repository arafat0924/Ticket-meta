import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User } from 'lucide-react';
import { chatbotStream } from '../api';

function Chatbot() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: 'Hi! I\'m your AI flight assistant. Ask me anything about flights, prices, or airports. I\'ll generate SQL queries and run them on the Hive database.\n\nTry: "cheapest nonstop flights from ATL to LAX" or "which airlines fly from JFK to SFO?"',
      sql: null,
      results: null,
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [streamSql, setStreamSql] = useState(null); // SQL shown while query runs
  const abortRef = useRef(null);
  const messagesEnd = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, statusMsg, streamSql]);

  const handleSend = useCallback(() => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput('');

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', text: question }]);
    setLoading(true);
    setStatusMsg('Asking AI...');
    setStreamSql(null);

    // Build conversation history (last 10 messages) for context
    const history = [...messages, { role: 'user', text: question }]
      .slice(-10)
      .map(m => ({
        role: m.role === 'bot' ? 'assistant' : 'user',
        content: m.text + (m.sql ? `\n[SQL: ${m.sql}]` : '')
      }));

    // Use streaming endpoint — each event updates UI progressively
    abortRef.current = chatbotStream(question, history, (event) => {
      switch (event.type) {
        case 'status':
          setStatusMsg(event.message || 'Processing...');
          break;

        case 'sql':
          // Show SQL immediately while query is running
          setStreamSql(event.sql);
          setStatusMsg('Running query on Hive...');
          break;

        case 'answer':
          // Final answer — add bot message with results
          setMessages(prev => [
            ...prev,
            {
              role: 'bot',
              text: event.answer || 'Done.',
              sql: event.sql || null,
              results: event.results || null,
            },
          ]);
          setStreamSql(null);
          setStatusMsg('');
          break;

        case 'error':
          setMessages(prev => [
            ...prev,
            {
              role: 'bot',
              text: `⚠️ ${event.message || 'Something went wrong'}`,
              sql: null,
              results: null,
            },
          ]);
          setStreamSql(null);
          setStatusMsg('');
          break;

        case 'done':
          setLoading(false);
          setStatusMsg('');
          setStreamSql(null);
          break;

        default:
          break;
      }
    });
  }, [input, loading, messages]);

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const renderResults = (results) => {
    if (!results || results.length === 0) return null;
    const cols = Object.keys(results[0]);
    return (
      <div className="data-table-wrapper" style={{ marginTop: 12 }}>
        <table className="data-table">
          <thead>
            <tr>{cols.map((col, i) => <th key={i}>{col}</th>)}</tr>
          </thead>
          <tbody>
            {results.slice(0, 20).map((row, ri) => (
              <tr key={ri}>
                {cols.map((col, ci) => (
                  <td key={ci} className={
                    typeof row[col] === 'number' || (typeof row[col] === 'string' && !isNaN(row[col]) && row[col] !== '')
                      ? 'fare-cell' : ''
                  }>
                    {row[col] != null ? String(row[col]) : '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {results.length > 20 && (
          <div style={{ padding: '8px 16px', fontSize: 12, color: '#64748b' }}>
            Showing 20 of {results.length} results
          </div>
        )}
      </div>
    );
  };

  const suggestions = [
    "Cheapest flights from ATL to LAX",
    "Average fare by airline from JFK to SFO",
    "Top 5 cheapest destinations from MIA",
    "How many nonstop flights from ORD?",
    "List airports in California",
  ];

  return (
    <div className="page-container">
      <title>AI Flight Assistant — SkyQuery</title>

      <div className="page-hero">
        <h1><Bot size={32} style={{ display: 'inline', verticalAlign: 'middle' }} /> AI Flight Assistant</h1>
        <p>Ask questions in natural language — powered by DeepSeek AI + Hive</p>
      </div>

      <div className="chat-container">
        {messages.length <= 1 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
            {suggestions.map((s, i) => (
              <button key={i} className="btn-secondary" onClick={() => setInput(s)} style={{ fontSize: 12 }}>
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-message ${msg.role}`}>
              <div className="chat-avatar">{msg.role === 'bot' ? <Bot size={18} /> : <User size={18} />}</div>
              <div>
                <div className="chat-bubble">
                  {msg.text}
                  {msg.sql && <div className="chat-sql">{msg.sql}</div>}
                </div>
                {msg.results && renderResults(msg.results)}
              </div>
            </div>
          ))}

          {/* Live streaming status indicator */}
          {loading && (
            <div className="chat-message bot">
              <div className="chat-avatar"><Bot size={18} /></div>
              <div>
                <div className="chat-bubble">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                    <span>{statusMsg || 'Thinking...'}</span>
                  </div>
                  {streamSql && (
                    <div className="chat-sql" style={{ marginTop: 8 }}>{streamSql}</div>
                  )}
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEnd} />
        </div>

        <div className="chat-input-row">
          <input
            type="text"
            placeholder="Ask about flights, prices, airports..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button className="btn-primary" onClick={handleSend} disabled={!input.trim() || loading}>
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;
