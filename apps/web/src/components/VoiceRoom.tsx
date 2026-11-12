'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  useDataChannel,
  useRoomContext,
  useTrackToggle,
  useLocalParticipant,
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
  const { localParticipant } = useLocalParticipant();
  const { state: agentState, audioTrack, agentTranscriptions } = useVoiceAssistant();
  const [telemetryPoints, setTelemetryPoints] = useState<TelemetryPoint[]>([]);
  const [currentTurnMs, setCurrentTurnMs] = useState<number | null>(null);
  const [dataChannelTranscripts, setDataChannelTranscripts] = useState<TranscriptEntry[]>([]);
  const [quotaAlert, setQuotaAlert] = useState<boolean>(false);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [bargeInTrials, setBargeInTrials] = useState<number[]>([]);
  const [latestBargeInMs, setLatestBargeInMs] = useState<number | null>(null);

  // Turn timing & barge-in probe tracking
  const userSpeechEndRef = useRef<number | null>(null);
  const currentTurnIdRef = useRef<number>(1);
  const isAgentSpeakingRef = useRef<boolean>(false);
  const lastAudioLevelUpdateRef = useRef<number>(0);
  const onDisconnectRef = useRef(onDisconnect);
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);

  const probeStateRef = useRef<{
    trialActive: boolean;
    speechStartTime: number | null;
    trialCount: number;
  }>({
    trialActive: false,
    speechStartTime: null,
    trialCount: 1,
  });

  // Stable data channel message handler with zero fluctuating dependencies
  const onDataChannelMessage = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const decoded = new TextDecoder().decode(msg.payload);
      const data = JSON.parse(decoded);

      if (data.type === 'transcript') {
        setDataChannelTranscripts((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === (data.role || 'assistant') && last.text === data.text) {
            return prev;
          }
          return [
            ...prev,
            {
              id: `server-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
              role: data.role || 'assistant',
              text: data.text,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            },
          ];
        });
      } else if (data.type === 'quota_exceeded' || data.type === 'fallback_429') {
        setQuotaAlert(true);
      } else if (data.type === 'session_closed') {
        setDataChannelTranscripts((prev) => [
          ...prev,
          {
            id: `server-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
            role: 'system',
            text: data.reason || 'Session closed due to inactivity.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          },
        ]);
        setTimeout(() => onDisconnectRef.current?.(), 1500);
      } else if (data.type === 'telemetry_update') {
        setTelemetryPoints((prev) => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          const lastIndex = updated.length - 1;
          updated[lastIndex] = {
            ...updated[lastIndex],
            sttRequests: data.stt_requests,
            llmRequests: data.llm_requests,
            ttsRequests: data.tts_requests,
            ttsRequestsHourly: data.tts_requests_hourly,
          };
          return updated;
        });
      }
    } catch {
      // ignore non-json messages
    }
  }, []);

  // Data channel for custom messages (telemetry, on-screen text fallbacks)
  const { send } = useDataChannel('telemetry', onDataChannelMessage);
  const sendRef = useRef(send);
  useEffect(() => {
    sendRef.current = send;
  }, [send]);

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

        // Publish asynchronously over LiveKit data channel via stable ref
        if (sendRef.current) {
          const payload = JSON.stringify({
            type: 'client_telemetry',
            turn_id: point.turnId,
            first_audio_ms: elapsed,
            timestamp: point.timestamp,
          });
          sendRef.current(new TextEncoder().encode(payload), { reliable: true }).catch(() => {});
        }
        userSpeechEndRef.current = null;
      }
    } else if (!isSpeaking) {
      isAgentSpeakingRef.current = false;
    }
  }, [agentState]);

  // Audio level monitoring and Client-Side Barge-In Probe
  const remoteTrack = audioTrack?.publication?.track?.mediaStreamTrack;
  const micPub = localParticipant?.getTrackPublication(Track.Source.Microphone);
  const micTrack = micPub?.track?.mediaStreamTrack;

  useEffect(() => {
    if (!remoteTrack) return;

    let animId: number;
    let audioCtx: AudioContext | null = null;
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      audioCtx = new AudioCtx();

      // Remote agent audio stream & analyser
      const remoteSrc = audioCtx.createMediaStreamSource(new MediaStream([remoteTrack]));
      const remoteAnalyser = audioCtx.createAnalyser();
      remoteAnalyser.fftSize = 64;
      remoteSrc.connect(remoteAnalyser);
      const remoteData = new Uint8Array(new ArrayBuffer(remoteAnalyser.frequencyBinCount));

      // Local microphone stream & analyser (for barge-in speech onset detection)
      let micAnalyser: AnalyserNode | null = null;
      let micData: Uint8Array<ArrayBuffer> | null = null;
      if (micTrack) {
        try {
          const micSrc = audioCtx.createMediaStreamSource(new MediaStream([micTrack]));
          micAnalyser = audioCtx.createAnalyser();
          micAnalyser.fftSize = 64;
          micSrc.connect(micAnalyser);
          micData = new Uint8Array(new ArrayBuffer(micAnalyser.frequencyBinCount));
        } catch {
          // Mic track media stream creation error
        }
      }

      const update = () => {
        remoteAnalyser.getByteFrequencyData(remoteData);
        const remoteAvg = remoteData.reduce((acc, v) => acc + v, 0) / remoteData.length;
        
        // Throttle audioLevel updates to max once per 100ms and quantize to 0.1 steps
        const now = performance.now();
        if (now - lastAudioLevelUpdateRef.current > 100) {
          lastAudioLevelUpdateRef.current = now;
          const quantized = Math.round((remoteAvg / 255) * 10) / 10;
          setAudioLevel((prev) => (prev !== quantized ? quantized : prev));
        }

        if (micAnalyser && micData) {
          micAnalyser.getByteFrequencyData(micData);
          const micAvg = micData.reduce((acc, v) => acc + v, 0) / micData.length;

          // Agent is actively speaking when remote audio energy is non-trivial (> 8)
          const agentIsProducingAudio = remoteAvg > 8;

          // Detect user speech onset during agent playout (mic energy > 16)
          if (agentIsProducingAudio && micAvg > 16 && !probeStateRef.current.trialActive) {
            probeStateRef.current.trialActive = true;
            probeStateRef.current.speechStartTime = performance.now();
          }

          // If trial is active, wait for remote agent audio to cease (<= 3)
          if (probeStateRef.current.trialActive && probeStateRef.current.speechStartTime) {
            if (remoteAvg <= 3) {
              const deltaMs = Math.round(performance.now() - probeStateRef.current.speechStartTime);
              if (deltaMs >= 25 && deltaMs <= 3000) {
                setLatestBargeInMs(deltaMs);
                setBargeInTrials((prev) => [...prev, deltaMs]);

                if (sendRef.current) {
                  const payload = JSON.stringify({
                    type: 'client_barge_in_telemetry',
                    barge_in_ms: deltaMs,
                    trial_id: probeStateRef.current.trialCount++,
                    timestamp: new Date().toISOString(),
                  });
                  sendRef.current(new TextEncoder().encode(payload), { reliable: true }).catch(() => {});
                }
              }
              probeStateRef.current.trialActive = false;
              probeStateRef.current.speechStartTime = null;
            }
          }
        }

        animId = requestAnimationFrame(update);
      };
      animId = requestAnimationFrame(update);
    } catch {
      // AudioContext fallback
    }

    return () => {
      if (animId) cancelAnimationFrame(animId);
      if (audioCtx) audioCtx.close().catch(() => {});
    };
  }, [remoteTrack, micTrack]);

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
        latestBargeInMs={latestBargeInMs}
        bargeInTrials={bargeInTrials}
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
      audio={{
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      }}
      video={false}
      onDisconnected={onDisconnect}
      className="flex flex-col items-center justify-center w-full"
    >
      <ActiveVoiceRoom onDisconnect={onDisconnect} />
    </LiveKitRoom>
  );
}
