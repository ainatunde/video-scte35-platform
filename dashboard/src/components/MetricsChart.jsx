import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function MetricsChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
        <XAxis dataKey="t" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 10 }} />
        <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333' }} />
        <Legend />
        <Line type="monotone" dataKey="bitrate" stroke="#61dafb" dot={false} name="Bitrate (kbps)" />
        <Line type="monotone" dataKey="fps" stroke="#ffab40" dot={false} name="FPS" />
      </LineChart>
    </ResponsiveContainer>
  );
}
