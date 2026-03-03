import React from 'react';

const STATUS_CLASS = {
  running: 'badge-running',
  stopped: 'badge-stopped',
  starting: 'badge-starting',
  stopping: 'badge-starting',
  restarting: 'badge-starting',
  error: 'badge-error',
};

export default function StatusBadge({ status }) {
  return (
    <span className={`badge ${STATUS_CLASS[status] || 'badge-stopped'}`}>
      {status}
    </span>
  );
}
