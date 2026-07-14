import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

// Word-timed karaoke captions on a TRANSPARENT background. `words` comes
// straight from a tts .timing.json sidecar (audio_gen.py) — times are relative
// to the VO start, so composite this overlay at the VO's `at` offset.

export type Word = {word: string; start: number; end: number};

export type KaraokeProps = {
  width: number;
  height: number;
  fps: number;
  durationS: number;
  words: Word[];
  /** words per caption page (a gap > gapS also breaks the page) */
  wordsPerPage?: number;
  gapS?: number;
  textColor?: string;
  highlightColor?: string;
  /** vertical center of the caption block, as a fraction of height */
  y?: number;
  /** font size as a fraction of height */
  fontScale?: number;
};

export const karaokeDefaults: KaraokeProps = {
  width: 1080,
  height: 1920,
  fps: 30,
  durationS: 5,
  words: [
    {word: 'okay', start: 0.0, end: 0.3},
    {word: 'so', start: 0.3, end: 0.5},
    {word: 'this', start: 0.5, end: 0.8},
    {word: 'happened', start: 0.8, end: 1.4},
  ],
  wordsPerPage: 4,
  gapS: 0.6,
  textColor: '#ffffff',
  highlightColor: '#ffd400',
  y: 0.76,
  fontScale: 0.038,
};

type Page = {words: Word[]; start: number; end: number};

const paginate = (words: Word[], perPage: number, gapS: number): Page[] => {
  const pages: Page[] = [];
  let cur: Word[] = [];
  for (const w of words) {
    const prev = cur[cur.length - 1];
    if (cur.length >= perPage || (prev && w.start - prev.end > gapS)) {
      pages.push({words: cur, start: cur[0].start, end: prev!.end});
      cur = [];
    }
    cur.push(w);
  }
  if (cur.length) {
    pages.push({words: cur, start: cur[0].start, end: cur[cur.length - 1].end});
  }
  // Hold each page until the next one starts (or slightly past the last word).
  return pages.map((p, i) => ({
    ...p,
    end: i + 1 < pages.length ? pages[i + 1].start : p.end + 0.4,
  }));
};

export const KaraokeCaptions: React.FC<KaraokeProps> = (props) => {
  const {fps} = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const {
    words,
    wordsPerPage = 4,
    gapS = 0.6,
    textColor = '#ffffff',
    highlightColor = '#ffd400',
    y = 0.76,
    fontScale = 0.038,
    height,
  } = props;

  const pages = paginate(words, wordsPerPage, gapS);
  const page = pages.find((p) => t >= p.start && t < p.end);
  if (!page) {
    return <AbsoluteFill />;
  }

  const fontSize = Math.round(height * fontScale);
  const stroke = Math.max(2, Math.round(fontSize / 14));

  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          top: `${y * 100}%`,
          left: '7%',
          right: '7%',
          transform: 'translateY(-50%)',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          columnGap: fontSize * 0.35,
          rowGap: fontSize * 0.2,
          fontFamily:
            "'Helvetica Neue', 'Arial Black', Arial, sans-serif",
          fontWeight: 900,
          fontSize,
          textTransform: 'uppercase',
          letterSpacing: '0.01em',
        }}
      >
        {page.words.map((w, i) => {
          const active = t >= w.start && t < w.end;
          const spoken = t >= w.end;
          return (
            <span
              key={i}
              style={{
                color: active ? highlightColor : textColor,
                opacity: spoken || active ? 1 : 0.85,
                transform: active ? 'scale(1.12)' : 'scale(1)',
                WebkitTextStroke: `${stroke}px rgba(0,0,0,0.9)`,
                paintOrder: 'stroke fill',
                textShadow: '0 2px 12px rgba(0,0,0,0.55)',
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
