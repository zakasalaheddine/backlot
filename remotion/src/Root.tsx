import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {KaraokeCaptions, KaraokeProps, karaokeDefaults} from './KaraokeCaptions';
import {EndCard, EndCardProps, endCardDefaults} from './EndCard';
import {HookCard, HookCardProps, hookCardDefaults} from './HookCard';
import {ProgressBar, ProgressBarProps, progressBarDefaults} from './ProgressBar';

// Every template is fully props-driven: render_overlay.py injects width /
// height / fps / durationS into the props, and this derives the composition
// metadata from them — one composition covers every size and length.
type Sized = {width: number; height: number; fps: number; durationS: number};

const fromProps: CalculateMetadataFunction<Sized> = ({props}) => ({
  durationInFrames: Math.max(1, Math.ceil(props.durationS * props.fps)),
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const Root: React.FC = () => (
  <>
    <Composition
      id="KaraokeCaptions"
      component={KaraokeCaptions}
      calculateMetadata={fromProps as CalculateMetadataFunction<KaraokeProps>}
      durationInFrames={150}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={karaokeDefaults}
    />
    <Composition
      id="EndCard"
      component={EndCard}
      calculateMetadata={fromProps as CalculateMetadataFunction<EndCardProps>}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={endCardDefaults}
    />
    <Composition
      id="HookCard"
      component={HookCard}
      calculateMetadata={fromProps as CalculateMetadataFunction<HookCardProps>}
      durationInFrames={60}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={hookCardDefaults}
    />
    <Composition
      id="ProgressBar"
      component={ProgressBar}
      calculateMetadata={fromProps as CalculateMetadataFunction<ProgressBarProps>}
      durationInFrames={150}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={progressBarDefaults}
    />
  </>
);
