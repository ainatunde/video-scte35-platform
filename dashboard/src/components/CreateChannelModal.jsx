import React, { useState } from 'react';

export default function CreateChannelModal({ onClose, onCreate }) {
  const [form, setForm] = useState({
    name: '',
    input_protocol: 'file',
    input_url: '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreate(form);
    onClose();
  };

  return (
    <div style={overlay}>
      <div style={modal}>
        <h2 style={{ marginTop: 0 }}>New Channel</h2>
        <form onSubmit={handleSubmit}>
          <div style={field}>
            <label>Name</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              style={input}
            />
          </div>
          <div style={field}>
            <label>Input Protocol</label>
            <select
              value={form.input_protocol}
              onChange={(e) => setForm({ ...form, input_protocol: e.target.value })}
              style={input}
            >
              <option value="file">File</option>
              <option value="rtmp">RTMP</option>
              <option value="srt">SRT</option>
            </select>
          </div>
          <div style={field}>
            <label>Input URL</label>
            <input
              required
              value={form.input_url}
              onChange={(e) => setForm({ ...form, input_url: e.target.value })}
              style={input}
              placeholder="e.g. /data/input.mp4 or rtmp://..."
            />
          </div>
          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
  );
}

const overlay = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
};
const modal = {
  background: '#1a1a1a', border: '1px solid #333', borderRadius: 8,
  padding: '1.5rem', width: 400, maxWidth: '90vw',
};
const field = { marginBottom: '0.75rem', display: 'flex', flexDirection: 'column', gap: 4 };
const input = {
  background: '#0d0d0d', border: '1px solid #333', borderRadius: 4,
  color: '#e0e0e0', padding: '6px 10px', fontSize: '0.9rem',
};
