import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import {
  fetchChannels, createChannel, startChannel, stopChannel, deleteChannel,
} from '../store/channelsSlice';
import StatusBadge from '../components/StatusBadge';
import CreateChannelModal from '../components/CreateChannelModal';

export default function ChannelListPage() {
  const dispatch = useDispatch();
  const { items, status } = useSelector((s) => s.channels);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    dispatch(fetchChannels());
  }, [dispatch]);

  const handleCreate = (data) => dispatch(createChannel(data));

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h1 style={{ margin: 0 }}>Channels</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>+ New Channel</button>
      </div>

      {status === 'loading' && <p>Loading…</p>}

      {items.map((ch) => (
        <div className="card" key={ch.id} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ flex: 1 }}>
            <Link to={`/channels/${ch.id}`} style={{ fontSize: '1rem', fontWeight: 600 }}>{ch.name}</Link>
            <div style={{ fontSize: '0.78rem', color: '#888', marginTop: 2 }}>
              {ch.input_protocol.toUpperCase()} — {ch.input_url}
            </div>
          </div>
          <StatusBadge status={ch.status} />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {ch.status !== 'running' && ch.status !== 'starting' && (
              <button className="btn-primary" onClick={() => dispatch(startChannel(ch.id))}>Start</button>
            )}
            {(ch.status === 'running' || ch.status === 'starting') && (
              <button className="btn-danger" onClick={() => dispatch(stopChannel(ch.id))}>Stop</button>
            )}
            <button className="btn-secondary" onClick={() => dispatch(deleteChannel(ch.id))}>Delete</button>
          </div>
        </div>
      ))}

      {items.length === 0 && status !== 'loading' && (
        <p style={{ color: '#666' }}>No channels yet. Create one to get started.</p>
      )}

      {showModal && (
        <CreateChannelModal onClose={() => setShowModal(false)} onCreate={handleCreate} />
      )}
    </div>
  );
}
