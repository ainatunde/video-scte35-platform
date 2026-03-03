import React, { useEffect, useRef } from 'react';
import Hls from 'hls.js';

export default function HLSPlayer({ src }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(video);
      return () => hls.destroy();
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = src;
    }
  }, [src]);

  return (
    <video
      ref={videoRef}
      controls
      style={{ width: '100%', maxHeight: 400, background: '#000', borderRadius: 4 }}
    />
  );
}
