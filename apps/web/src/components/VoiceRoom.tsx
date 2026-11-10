'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  useDataChannel,
  useRoomContext,
  useTrackToggle,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import { Mic, MicOff, PhoneOff, Radio, RefreshCw } from 'lucide-react';
import { Orb } from './Orb';
import { TelemetryBar, TelemetryPoint } from './TelemetryBar';
import { TranscriptFeed, TranscriptEntry } from './TranscriptFeed';

interface VoiceSessionProps {
  token: string;
  url: string;
  roomName: string;
  onDisconnect: () => void;
}

function ActiveVoiceRoom({ onDisconnect }: { onDisconnect: () => void }) {
  const room = useRoomContext();
  const { state: agentState, audioTrack, agentTranscriptions } = useVoiceAssistant();
  const [telemetryPoints, setTelemetryPoints] = useState<TelemetryPoint[]>([]);
  const [currentTurnMs, setCurrentTurnMs] = useState<number | null>(null);
  const [dataChannelTranscripts, setDataChannelTranscripts] = useState<TranscriptEntry[]>([]);
  const [quotaAlert, setQuotaAlert] = useState<boolean>(false);
  const [audioLevel, setAudioLevel] = useState<number>(0);

  // Turn timing tracking
  const userSpeechEndRef = useRef<number | null>(null);
  const currentTurnIdRef = useRef<number>(1);
  const isAgentSpeakingRef = useRef<boolean>(false);

  // Data channel for custom messages (telemetry, on-screen text fallbacks)
  const { send } = useDataChannel('telemetry', (msg) => {
    try {
      const decoded = new TextDecoder().decode(msg.payload);
      const data = JSON.parse(decoded);

      if (data.type === 'transcript') {
        setDataChannelTranscripts((prev) => [
          ...prev,
          {
            id: `server-${Date.now()}`,
            role: data.role || 'assistant',
            text: data.text,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          },
        ]);
      } else if (data.type === 'quota_exceeded' || data.type === 'fallback_429') {
        setQuotaAlert(true);
      }
    } catch {
      // ignore non-json messages
    }
  });

  // Derived transcript feed combining data channel messages and agent transcriptions
  const transcripts = React.useMemo<TranscriptEntry[]>(() => {
    const list = [...dataChannelTranscripts];
    if (agentTranscriptions && agentTranscriptions.length > 0) {
      for (const t of agentTranscriptions) {
        if (t.text && !list.some((existing) => existing.text === t.text)) {
          list.push({
            id: `transcription-${t.id || t.text}`,
            role: 'assistant',
            text: t.text,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          });
        }
      }
    }
    return list;
  }, [dataChannelTranscripts, agentTranscriptions]);

  // Track microphone toggle
  const { enabled: isMicEnabled, toggle: toggleMic } = useTrackToggle({
    source: Track.Source.Microphone,
  });

  // Client-side first audio measurement
  // When agent transitions to 'speaking', compute delta from user speech end
  useEffect(() => {
    const isSpeaking = agentState === 'speaking';
    if (isSpeaking && !isAgentSpeakingRef.current) {
      isAgentSpeakingRef.current = true;
      if (userSpeechEndRef.current) {
        const elapsed = Math.round(performance.now() - userSpeechEndRef.current);
        setCurrentTurnMs(elapsed);
        const point: TelemetryPoint = {
          turnId: currentTurnIdRef.current++,
          firstAudioMs: elapsed,
          timestamp: new Date().toISOString(),
        };
        setTelemetryPoints((prev) => [...prev, point]);

        // Publish asynchronously over LiveKit data channel
        if (send) {
          const payload = JSON.stringify({
            type: 'client_telemetry',
            turn_id: point.turnId,
            first_audio_ms: elapsed,
            timestamp: point.timestamp,
          });
          send(new TextEncoder().encode(payload), { reliable: true }).catch(() => {});
        }
        userSpeechEndRef.current = null;
      }
    } else if (!isSpeaking) {
      isAgentSpeakingRef.current = false;
    }
  }, [agentState, send]);


  // Audio level monitoring when agent is speaking
  useEffect(() => {
    if (!audioTrack?.publication?.track) return;
    const track = audioTrack.publication.track;
    const mediaStreamTrack = track.mediaStreamTrack;
    if (!mediaStreamTrack) return;

    let animId: number;
    let audioCtx: AudioContext | null = null;
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      audioCtx = new AudioCtx();
      const src = audioCtx.createMediaStreamSource(new MediaStream([mediaStreamTrack]));
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      src.connect(analyser);
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const update = () => {
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((acc, v) => acc + v, 0) / dataArray.length;
        setAudioLevel(avg / 255);
        animId = requestAnimationFrame(update);
      };
      update();
    } catch {
      // AudioContext not allowed without user interaction fallback
    }

    return () => {
      if (animId) cancelAnimationFrame(animId);
      if (audioCtx) audioCtx.close().catch(() => {});
    };
  }, [audioTrack]);

  // Record user speech end when state moves from listening/user speaking to thinking
  useEffect(() => {
    if (agentState === 'thinking') {
      userSpeechEndRef.current = performance.now();
    }
  }, [agentState]);

  return (
    <div className="flex flex-col items-center w-full max-w-4xl px-4 py-2">
      {/* Visualizer Orb */}
      <Orb
        state={
          agentState === 'speaking'
            ? 'speaking'
            : agentState === 'thinking'
            ? 'thinking'
            : agentState === 'listening'
            ? 'listening'
            : 'connecting'
        }
        audioLevel={audioLevel}
      />

      {/* Control Action Bar */}
      <div className="flex items-center gap-4 mb-4">
        <button
          onClick={() => toggleMic()}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium text-sm transition-all shadow-md ${
            isMicEnabled
              ? 'bg-neutral-800 hover:bg-neutral-700 text-white border border-neutral-700'
              : 'bg-red-600/90 hover:bg-red-600 text-white shadow-red-900/30'
          }`}
        >
          {isMicEnabled ? (
            <>
              <Mic className="w-4 h-4 text-emerald-400" />
              <span>Mute Mic</span>
            </>
          ) : (
            <>
              <MicOff className="w-4 h-4 text-white" />
              <span>Unmute Mic</span>
            </>
          )}
        </button>

        <button
          onClick={onDisconnect}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full font-medium text-sm bg-red-950/80 hover:bg-red-900 text-red-200 border border-red-800/80 transition-all shadow-md"
        >
          <PhoneOff className="w-4 h-4 text-red-400" />
          <span>End Session</span>
        </button>
      </div>

      {/* Telemetry Bar */}
      <TelemetryBar
        points={telemetryPoints}
        currentTurnMs={currentTurnMs}
        agentState={agentState}
      />

      {/* Live Transcript Feed */}
      <TranscriptFeed entries={transcripts} quotaAlert={quotaAlert} />

      {/* Audio Renderer for LiveKit playback */}
      <RoomAudioRenderer />
    </div>
  );
}

export function VoiceRoom({ token, url, roomName, onDisconnect }: VoiceSessionProps) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={url}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={onDisconnect}
      className="flex flex-col items-center justify-center w-full"
    >
      <ActiveVoiceRoom onDisconnect={onDisconnect} />
    </LiveKitRoom>
  );
}
