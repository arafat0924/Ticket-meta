import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User, Plus, Search, Paperclip, Mic, Settings, MessageSquare, Sparkles, Copy, Check, Maximize2, Minimize2 } from 'lucide-react';
import { chatbotStream } from '../api';

/* ──────── Mac-Window AI Chat ──────── */
function Chatbot() {
  const [input, setInput] = useState('');
  const [conversations, setConversations] = useState([
    { id: 1, title: 'New Conversation', messages: [] }
  ]);
  const [activeConv, setActiveConv] = useState(1);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [streamSql, setStreamSql] = useState(null);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const [zoomed, setZoomed] = useState(false);
  const abortRef = useRef(null);
  const messagesEnd = useRef(null);
  const inputRef = useRef(null);

  const activeMessages = conversations.find(c => c.id === activeConv)?.messages || [];

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeMessages, statusMsg, streamSql]);

  const updateConvMessages = useCallback((convId, updater) => {
    setConversations(prev =>
      prev.map(c => c.id === convId ? { ...c, messages: updater(c.messages) } : c)
    );
  }, []);

  const updateConvTitle = useCallback((convId, title) => {
    setConversations(prev =>
      prev.map(c => c.id === convId ? { ...c, title } : c)
    );
  }, []);

  const handleNewConversation = () => {
    const newId = Date.now();
    setConversations(prev => [{ id: newId, title: 'New Conversation', messages: [] }, ...prev]);
    setActiveConv(newId);
    setInput('');
  };

  const handleSend = useCallback(() => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput('');

    // Add user message
    updateConvMessages(activeConv, msgs => [...msgs, { role: 'user', text: question }]);

    // Update conversation title from first question
    const conv = conversations.find(c => c.id === activeConv);
    if (conv && (conv.title === 'New Conversation' || conv.messages.length === 0)) {
      updateConvTitle(activeConv, question.slice(0, 40) + (question.length > 40 ? '...' : ''));
    }

    setLoading(true);
    setStatusMsg('Thinking...');
    setStreamSql(null);

    const history = [...(conv?.messages || []), { role: 'user', text: question }]
      .slice(-10)
      .map(m => ({
        role: m.role === 'bot' ? 'assistant' : 'user',
        content: m.text + (m.sql ? `\n[SQL: ${m.sql}]` : '')
      }));

    abortRef.current = chatbotStream(question, history, (event) => {
      switch (event.type) {
        case 'status':
          setStatusMsg(event.message || 'Processing...');
          break;
        case 'sql':
          setStreamSql(event.sql);
          setStatusMsg('Running query on Hive...');
          break;
        case 'answer':
          updateConvMessages(activeConv, msgs => [...msgs, {
            role: 'bot',
            text: event.answer || 'Done.',
            sql: event.sql || null,
            results: event.results || null,
          }]);
          setStreamSql(null);
          setStatusMsg('');
          break;
        case 'error':
          updateConvMessages(activeConv, msgs => [...msgs, {
            role: 'bot',
            text: `⚠️ ${event.message || 'Something went wrong'}`,
            sql: null, results: null,
          }]);
          setStreamSql(null);
          setStatusMsg('');
          break;
        case 'done':
          setLoading(false);
          setStatusMsg('');
          setStreamSql(null);
          break;
        default: break;
      }
    });
  }, [input, loading, activeConv, conversations, updateConvMessages, updateConvTitle]);

  useEffect(() => () => { if (abortRef.current) abortRef.current.abort(); }, []);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }, [handleSend]);

  const copyToClipboard = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  /* ── Render SQL code block with line numbers ── */
  const renderCodeBlock = (sql, idx) => {
    if (!sql) return null;
    const lines = sql.trim().split('\n');
    return (
      <div className="mac-code-block">
        <div className="mac-code-header">
          <span className="mac-code-lang">&lt;&gt; sql</span>
          <button className="mac-copy-btn" onClick={() => copyToClipboard(sql, idx)}>
            {copiedIdx === idx ? <><Check size={12} /> Copied!</> : <><Copy size={12} /> Copy Code</>}
          </button>
        </div>
        <div className="mac-code-body">
          {lines.map((line, i) => (
            <div key={i} className="mac-code-line">
              <span className="mac-line-num">{i + 1}</span>
              <span className="mac-line-text">{highlightSQL(line)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  /* ── Simple SQL syntax highlighting ── */
  const highlightSQL = (line) => {
    const keywords = /\b(SELECT|FROM|WHERE|AND|OR|GROUP BY|ORDER BY|LIMIT|AS|JOIN|ON|LEFT|RIGHT|INNER|HAVING|COUNT|AVG|MIN|MAX|ROUND|CAST|LIKE|IN|NOT|NULL|IS|BETWEEN|DESC|ASC|DISTINCT|UNION|CASE|WHEN|THEN|END|ELSE|INSERT|INTO|VALUES|CREATE|TABLE|DROP|ALTER|UPDATE|DELETE|SET|WITH|OVER|PARTITION BY|SUBSTR|DOUBLE|INT|STRING|FLOAT)\b/gi;
    const strings = /('[^']*')/g;
    const numbers = /\b(\d+\.?\d*)\b/g;

    let result = line
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(strings, '<span class="sql-string">$1</span>')
      .replace(keywords, '<span class="sql-keyword">$1</span>')
      .replace(numbers, '<span class="sql-number">$1</span>');

    return <span dangerouslySetInnerHTML={{ __html: result }} />;
  };

  /* ── Render data table ── */
  const renderResults = (results) => {
    if (!results || results.length === 0) return null;
    const cols = Object.keys(results[0]);
    return (
      <div className="mac-data-table-wrap">
        <table className="mac-data-table">
          <thead>
            <tr>{cols.map((col, i) => <th key={i}>{col}</th>)}</tr>
          </thead>
          <tbody>
            {results.slice(0, 20).map((row, ri) => (
              <tr key={ri}>
                {cols.map((col, ci) => (
                  <td key={ci}>{row[col] != null ? String(row[col]) : '-'}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {results.length > 20 && (
          <div className="mac-table-footer">Showing 20 of {results.length} results</div>
        )}
      </div>
    );
  };

  const suggestions = [
    "Cheapest flights from ATL to LAX",
    "Average fare by airline from JFK",
    "Top 5 cheapest destinations from MIA",
    "How many nonstop flights from ORD?",
  ];

  return (
    <div className={`mac-window-wrapper ${zoomed ? 'mac-zoomed' : ''}`}>
      {/* ═══ Mac Chrome ═══ */}
      <div className="mac-chrome">
        <div className="mac-chrome-left">
          <div className="mac-dots">
            <span className="mac-dot red" />
            <span className="mac-dot yellow" />
            <span className="mac-dot green" />
          </div>
          <button className="mac-zoom-btn" onClick={() => setZoomed(z => !z)} title={zoomed ? 'Exit fullscreen' : 'Fullscreen'}>
            {zoomed ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
        <div className="mac-url-bar">
          <span className="mac-lock">🔒</span> dataturbulence.ai/chat
        </div>
      </div>

      <div className="mac-body">
        {/* ═══ Sidebar ═══ */}
        <aside className="mac-sidebar">
          <div className="mac-sidebar-top">
            <div className="mac-brand">
              <Sparkles size={18} className="mac-brand-icon" />
              <span className="mac-brand-text">DataTurbulence</span>
            </div>

            <button className="mac-new-conv" onClick={handleNewConversation}>
              <Plus size={16} /> New Conversation
            </button>

            <div className="mac-search-box">
              <Search size={14} />
              <input type="text" placeholder="Search chats..." />
            </div>

            <div className="mac-recent-label">RECENT ACTIVITY</div>
            <div className="mac-conv-list">
              {conversations.map(c => (
                <div
                  key={c.id}
                  className={`mac-conv-item ${c.id === activeConv ? 'active' : ''}`}
                  onClick={() => { setActiveConv(c.id); setInput(''); }}
                >
                  <MessageSquare size={14} />
                  <span className="mac-conv-title">{c.title}</span>
                  {c.id === activeConv && <span className="mac-conv-dot" />}
                </div>
              ))}
            </div>
          </div>

          <div className="mac-sidebar-bottom">
            <div className="mac-hive-status">
              <span className="mac-hive-dot" />
              <span className="mac-hive-label">HIVE CONNECTED</span>
            </div>
          </div>
        </aside>

        {/* ═══ Chat Area ═══ */}
        <main className="mac-chat-main">
          {/* Messages */}
          <div className="mac-messages">
            {activeMessages.length === 0 && !loading && (
              <div className="mac-welcome">
                <div className="mac-welcome-icon"><Bot size={48} /></div>
                <h2>Ask me anything about flights</h2>
                <p>I'll generate SQL queries and run them on the Hive database for you.</p>
                <div className="mac-suggestions">
                  {suggestions.map((s, i) => (
                    <button key={i} className="mac-suggestion-btn" onClick={() => setInput(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {activeMessages.map((msg, i) => (
              <div key={i} className={`mac-msg ${msg.role}`}>
                <div className="mac-msg-avatar">
                  {msg.role === 'bot' ? <Bot size={18} /> : <User size={18} />}
                </div>
                <div className="mac-msg-content">
                  <div className="mac-msg-text">{msg.text}</div>
                  {msg.sql && renderCodeBlock(msg.sql, i)}
                  {msg.results && renderResults(msg.results)}
                </div>
              </div>
            ))}

            {/* Loading state */}
            {loading && (
              <div className="mac-msg bot">
                <div className="mac-msg-avatar"><Bot size={18} /></div>
                <div className="mac-msg-content">
                  <div className="mac-msg-text mac-loading">
                    <div className="mac-typing-dots">
                      <span /><span /><span />
                    </div>
                    <span>{statusMsg || 'Thinking...'}</span>
                  </div>
                  {streamSql && renderCodeBlock(streamSql, 'stream')}
                </div>
              </div>
            )}

            <div ref={messagesEnd} />
          </div>

          {/* Input area */}
          <div className="mac-input-area">
            <div className="mac-input-box">
              <Paperclip size={18} className="mac-input-icon" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Ask about flights, prices, airports..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
              />
              {input.trim() ? (
                <button className="mac-send-btn" onClick={handleSend} disabled={loading}>
                  <Send size={18} />
                </button>
              ) : (
                <Mic size={18} className="mac-input-icon" />
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="mac-powered">
            POWERED BY <span className="mac-powered-highlight">DATATURBULENCE</span> • AI CAN MAKE MISTAKES
          </div>
        </main>
      </div>
    </div>
  );
}

export default Chatbot;
