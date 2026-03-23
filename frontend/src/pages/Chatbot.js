import React, { useState, useRef, useEffect, useTransition, useOptimistic, useCallback } from 'react';
import { Send, Bot, User } from 'lucide-react';
import { chatbot } from '../api';

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
  const messagesEnd = useRef(null);

  // React 19: useTransition for non-blocking async chat
  const [isPending, startTransition] = useTransition();

  // React 19: useOptimistic for instant user message display
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    messages,
    (currentMessages, newMessage) => [...currentMessages, newMessage]
  );

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [optimisticMessages]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isPending) return;
    const question = input.trim();
    setInput('');

    // React 19: Optimistically show user message immediately
    addOptimisticMessage({ role: 'user', text: question });

    startTransition(async () => {
      // Add user message to actual state
      setMessages(prev => [...prev, { role: 'user', text: question }]);

      try {
        const res = await chatbot(question);
        const data = res.data;
        setMessages(prev => [
          ...prev,
          {
            role: 'bot',
            text: data.answer || data.error || 'No response',
            sql: data.sql || null,
            results: data.results || null,
          },
        ]);
      } catch (err) {
        const errData = err.response?.data;
        setMessages(prev => [
          ...prev,
          {
            role: 'bot',
            text: errData?.error || errData?.answer || err.message || 'Something went wrong',
            sql: errData?.sql || null,
            results: null,
          },
        ]);
      }
    });
  }, [input, isPending, addOptimisticMessage]);

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
        {optimisticMessages.length <= 1 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
            {suggestions.map((s, i) => (
              <button key={i} className="btn-secondary" onClick={() => setInput(s)} style={{ fontSize: 12 }}>
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="chat-messages">
          {optimisticMessages.map((msg, i) => (
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
          {isPending && (
            <div className="chat-message bot">
              <div className="chat-avatar"><Bot size={18} /></div>
              <div className="chat-bubble">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                  <span>Thinking & querying Hive...</span>
                </div>
                <div style={{ fontSize: 12, color: '#f59e0b', marginTop: 8 }}>
                  ⏱ This may take a few minutes for large table scans
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
            disabled={isPending}
          />
          <button className="btn-primary" onClick={handleSend} disabled={!input.trim() || isPending}>
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;
