import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { fetchChannels, startChannel, stopChannel } from '../store/channelsSlice';
import { upsertChannel } from '../store/channelsSlice';
import { useChannelWebSocket } from '../hooks/useChannelWebSocket';
import HLSPlayer from '../components/HLSPlayer';
import EventLog from '../components/EventLog';
import MetricsChart from '../components/MetricsChart';
import StatusBadge from '../components/StatusBadge';

const MAX_EVENTS = 200;
const MAX_METRICS = 60;

export default function ChannelDetailPage() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const channel = useSelector((s) => s.channels.items.find((c) => c.id === id));
  const [events, setEvents] = useState([]);
  const [metrics, setMetrics] = useState([]);

  useEffect(() => {
    if (!channel) dispatch(fetchChannels());
  }, [channel, dispatch]);

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'status' && msg.status) {
      dispatch(upsertChannel({ id, status: msg.status }));
    }
    if (['detection', 'marker', 'status'].includes(msg.type)) {
      setEvents((prev) => [...prev.slice(-MAX_EVENTS + 1), msg]);
    }
    if (msg.type === 'metrics') {
      setMetrics((prev) => [
        ...prev.slice(-MAX_METRICS + 1),
        { t: new Date(msg.timestamp).toLocaleTimeString(), bitrate: msg.bitrate, fps: msg.fps },
      ]);
    }
  }, [dispatch, id]);

  useChannelWebSocket(id, handleWsMessage);

  if (!channel) return <p>Loading channel…</p>;

  const hlsSrc = `/hls/${id}/master.m3u8`;

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/">← Channels</Link>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <h1 style={{ margin: 0 }}>{channel.name}</h1>
        <StatusBadge status={channel.status} />
        {channel.status !== 'running' && channel.status !== 'starting' && (
          <button className="btn-primary" onClick={() => dispatch(startChannel(channel.id))}>Start</button>
        )}
        {(channel.status === 'running' || channel.status === 'starting') && (
          <button className="btn-danger" onClick={() => dispatch(stopChannel(channel.id))}>Stop</button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Live Preview</h3>
            <HLSPlayer src={channel.status === 'running' ? hlsSrc : null} />
            {channel.status !== 'running' && (
              <p style={{ color: '#666', fontSize: '0.85rem', textAlign: 'center' }}>
                Start the channel to see the live preview.
              </p>
            )}
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Metrics (placeholder)</h3>
            <MetricsChart data={metrics} />
            {metrics.length === 0 && (
              <p style={{ color: '#666', fontSize: '0.85rem' }}>Waiting for metrics data…</p>
            )}
          </div>
        </div>
        <div>
          <div className="card" style={{ height: '100%' }}>
            <h3 style={{ marginTop: 0 }}>Real-time Event Log</h3>
            <EventLog events={events} />
            {events.length === 0 && (
              <p style={{ color: '#666', fontSize: '0.85rem' }}>Waiting for events…</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
