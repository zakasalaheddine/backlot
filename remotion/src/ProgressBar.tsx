import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

// Thin progress bar filling over the video's duration — TRANSPARENT overlay,
// the retention-nudge strip UGC ads use. durationS should equal the reel's
// total length so the bar completes exactly at the end.

export type ProgressBarProps = {
  width: number;
  height: number;
  fps: number;
  durationS: number;
  color?: string;
  trackColor?: string;
  /** bar thickness as a fraction of height */
  thickness?: number;
  position?: 'top' | 'bottom';
};

export const progressBarDefaults: ProgressBarProps = {
  width: 1080,
  height: 1920,
  fps: 30,
  durationS: 5,
  color: '#ffd400',
  trackColor: 'rgba(255,255,255,0.25)',
  thickness: 0.006,
  position: 'top',
};

export const ProgressBar: React.FC<ProgressBarProps> = (props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const {
    height,
    color = '#ffd400',
    trackColor = 'rgba(255,255,255,0.25)',
    thickness = 0.006,
    position = 'top',
  } = props;

  const pct = Math.min(1, frame / Math.max(1, durationInFrames - 1));
  const barH = Math.max(4, Math.round(height * thickness));

  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          [position]: 0,
          left: 0,
          right: 0,
          height: barH,
          backgroundColor: trackColor,
        }}
      >
        <div
          style={{
            width: `${pct * 100}%`,
            height: '100%',
            backgroundColor: color,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
