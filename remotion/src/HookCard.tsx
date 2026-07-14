import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';

// Big hook text popping over the opening shot — TRANSPARENT overlay for the
// first beat ("POV: you forgot Valentine's again").

export type HookCardProps = {
  width: number;
  height: number;
  fps: number;
  durationS: number;
  text: string;
  textColor?: string;
  /** vertical center of the text block, fraction of height */
  y?: number;
  fontScale?: number;
};

export const hookCardDefaults: HookCardProps = {
  width: 1080,
  height: 1920,
  fps: 30,
  durationS: 2,
  text: 'POV: your hook here',
  textColor: '#ffffff',
  y: 0.22,
  fontScale: 0.045,
};

export const HookCard: React.FC<HookCardProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const {height, text, textColor = '#ffffff', y = 0.22, fontScale = 0.045} = props;

  const pop = spring({frame, fps, config: {damping: 12, mass: 0.6}});
  const outStart = durationInFrames - Math.round(fps * 0.2);
  const fadeOut = frame >= outStart
    ? Math.max(0, 1 - (frame - outStart) / (durationInFrames - outStart))
    : 1;

  const fontSize = Math.round(height * fontScale);
  const stroke = Math.max(2, Math.round(fontSize / 12));

  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          top: `${y * 100}%`,
          left: '6%',
          right: '6%',
          transform: `translateY(-50%) scale(${pop})`,
          opacity: fadeOut,
          textAlign: 'center',
          fontFamily: "'Helvetica Neue', 'Arial Black', Arial, sans-serif",
          fontWeight: 900,
          fontSize,
          lineHeight: 1.2,
          color: textColor,
          WebkitTextStroke: `${stroke}px rgba(0,0,0,0.9)`,
          paintOrder: 'stroke fill',
          textShadow: '0 3px 16px rgba(0,0,0,0.5)',
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
