import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

// Branded closing card — an OPAQUE standalone clip (append it to the timeline
// as a normal clip; it is not an overlay). Headline springs in, CTA pops.

export type EndCardProps = {
  width: number;
  height: number;
  fps: number;
  durationS: number;
  headline: string;
  subhead?: string;
  cta: string;
  brand?: string;
  /** absolute path or data: URI; rendered above the headline if given */
  logo?: string;
  bgColor?: string;
  accentColor?: string;
  textColor?: string;
};

export const endCardDefaults: EndCardProps = {
  width: 1080,
  height: 1920,
  fps: 30,
  durationS: 3,
  headline: 'Your headline here',
  subhead: '',
  cta: 'Shop now',
  brand: '',
  bgColor: '#101014',
  accentColor: '#ffd400',
  textColor: '#ffffff',
};

export const EndCard: React.FC<EndCardProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {
    height,
    headline,
    subhead,
    cta,
    brand,
    logo,
    bgColor = '#101014',
    accentColor = '#ffd400',
    textColor = '#ffffff',
  } = props;

  const headIn = spring({frame, fps, config: {damping: 14, mass: 0.8}});
  const ctaIn = spring({frame: frame - Math.round(fps * 0.35), fps,
                        config: {damping: 11, mass: 0.7}});
  const fadeIn = interpolate(frame, [0, Math.round(fps * 0.25)], [0, 1],
                             {extrapolateRight: 'clamp'});

  const headSize = Math.round(height * 0.045);
  const ctaSize = Math.round(height * 0.026);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: bgColor,
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: "'Helvetica Neue', Arial, sans-serif",
        textAlign: 'center',
        padding: '0 8%',
      }}
    >
      {logo ? (
        <Img
          src={logo}
          style={{
            width: height * 0.09,
            height: height * 0.09,
            objectFit: 'contain',
            marginBottom: height * 0.03,
            opacity: fadeIn,
          }}
        />
      ) : null}
      <div
        style={{
          color: textColor,
          fontSize: headSize,
          fontWeight: 800,
          lineHeight: 1.15,
          opacity: headIn,
          transform: `translateY(${(1 - headIn) * height * 0.02}px)`,
        }}
      >
        {headline}
      </div>
      {subhead ? (
        <div
          style={{
            color: textColor,
            opacity: 0.75 * fadeIn,
            fontSize: Math.round(headSize * 0.5),
            fontWeight: 400,
            marginTop: height * 0.015,
          }}
        >
          {subhead}
        </div>
      ) : null}
      <div
        style={{
          marginTop: height * 0.04,
          backgroundColor: accentColor,
          color: '#101014',
          fontSize: ctaSize,
          fontWeight: 800,
          padding: `${ctaSize * 0.7}px ${ctaSize * 1.8}px`,
          borderRadius: ctaSize * 1.6,
          transform: `scale(${ctaIn})`,
        }}
      >
        {cta}
      </div>
      {brand ? (
        <div
          style={{
            position: 'absolute',
            bottom: height * 0.05,
            color: textColor,
            opacity: 0.55 * fadeIn,
            fontSize: Math.round(headSize * 0.38),
            fontWeight: 600,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}
        >
          {brand}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
