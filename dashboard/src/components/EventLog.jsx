import React, { useEffect, useRef } from 'react';

function classForType(type) {
  if (type === 'detection') return 'log-detection';
  if (type === 'marker') return 'log-marker';
  if (type === 'status') return 'log-status';
  return 'log-error';
}

export default function EventLog({ events }) {
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  return (
    <div className="event-log">
      {events.map((evt, i) => (
        <div key={i} className={`log-entry ${classForType(evt.type)}`}>
          <span style={{ opacity: 0.5 }}>{new Date(evt.timestamp).toLocaleTimeString()} </span>
          <strong>[{evt.type}]</strong>{' '}
          {evt.type === 'detection' && `${evt.event_type} conf=${evt.confidence?.toFixed(2)} pts=${evt.pts?.toFixed(2)}`}
          {evt.type === 'marker' && `SCTE-35 ${evt.splice_type} pts=${evt.pts?.toFixed(2)} dur=${evt.duration_secs}s`}
          {evt.type === 'status' && `status → ${evt.status}`}
          {!['detection', 'marker', 'status'].includes(evt.type) && JSON.stringify(evt)}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
