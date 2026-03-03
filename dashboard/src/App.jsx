import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import ChannelListPage from './pages/ChannelListPage';
import ChannelDetailPage from './pages/ChannelDetailPage';

export default function App() {
  return (
    <>
      <nav>
        <span className="brand">⚡ SCTE-35 Platform</span>
        <Link to="/">Channels</Link>
      </nav>
      <div className="container" style={{ paddingTop: '1.5rem' }}>
        <Routes>
          <Route path="/" element={<ChannelListPage />} />
          <Route path="/channels/:id" element={<ChannelDetailPage />} />
        </Routes>
      </div>
    </>
  );
}
