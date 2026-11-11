'use client';

import React from 'react';
import { Activity, Clock, Zap, ShieldCheck } from 'lucide-react';

export interface TelemetryPoint {
  turnId: number;
  firstAudioMs: number;
  timestamp: string;
  sttRequests?: number;
  llmRequests?: number;
  ttsRequests?: number;
  ttsRequestsHourly?: number;
}

interface TelemetryBarProps {
  points: TelemetryPoint[];
  currentTurnMs: number | null;
  agentState: string;
}

export function TelemetryBar({ points, currentTurnMs, agentState }: TelemetryBarProps) {
  const latestMs = currentTurnMs ?? (points.length > 0 ? points[points.length - 1].firstAudioMs : null);
  const avgMs =
    points.length > 0
      ? Math.round(points.reduce((acc, p) => acc + p.firstAudioMs, 0) / points.length)
      : null;

  // Latency rating
  const getRating = (ms: number | null) => {
    if (ms === null) return { text: 'Idle', color: 'text-gray-400', bg: 'bg-gray-800' };
    if (ms <= 800) return { text: 'Ultra Fast', color: 'text-emerald-400', bg: 'bg-emerald-950/60' };
    if (ms <= 1200) return { text: 'Target (≤1.2s)', color: 'text-blue-400', bg: 'bg-blue-950/60' };
    return { text: 'Elevated (>1.2s)', color: 'text-amber-400', bg: 'bg-amber-950/60' };
  };

  const rating = getRating(latestMs);

  return (
    <div className="w-full max-w-2xl bg-neutral-900/80 border border-neutral-800 rounded-xl p-4 backdrop-blur-md shadow-lg my-4">
      <div className="flex items-center justify-between border-b border-neutral-800 pb-2 mb-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-400">
          <Activity className="w-4 h-4 text-brand-400" />
          <span>Client Latency & Telemetry (LiveKit Data Channel)</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${rating.bg} ${rating.color}`}>
          {rating.text}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 text-center">
        <div className="bg-neutral-950/60 rounded-lg p-2.5 border border-neutral-800/60">
          <div className="flex items-center justify-center gap-1 text-[11px] text-neutral-400 mb-1">
            <Zap className="w-3.5 h-3.5 text-yellow-400" />
            <span>Latest First Audio</span>
          </div>
          <div className="text-lg font-bold text-white font-mono">
            {latestMs !== null ? `${latestMs} ms` : '—'}
          </div>
        </div>

        <div className="bg-neutral-950/60 rounded-lg p-2.5 border border-neutral-800/60">
          <div className="flex items-center justify-center gap-1 text-[11px] text-neutral-400 mb-1">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            <span>Session Average</span>
          </div>
          <div className="text-lg font-bold text-neutral-200 font-mono">
            {avgMs !== null ? `${avgMs} ms` : '—'}
          </div>
        </div>

        <div className="bg-neutral-950/60 rounded-lg p-2.5 border border-neutral-800/60">
          <div className="flex items-center justify-center gap-1 text-[11px] text-neutral-400 mb-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Completed Turns</span>
          </div>
          <div className="text-lg font-bold text-neutral-200 font-mono">{points.length}</div>
        </div>
      </div>

      {points.length > 0 && points[points.length - 1].sttRequests !== undefined && (
        <div className="mt-3 pt-2.5 border-t border-neutral-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] text-neutral-400">
          <div className="flex items-center gap-2">
            <span>Per-Turn Requests:</span>
            <span className="font-mono bg-neutral-950 px-1.5 py-0.5 rounded border border-neutral-800 text-neutral-200">
              STT: {points[points.length - 1].sttRequests}
            </span>
            <span className="font-mono bg-neutral-950 px-1.5 py-0.5 rounded border border-neutral-800 text-neutral-200">
              LLM: {points[points.length - 1].llmRequests}
            </span>
            <span className="font-mono bg-neutral-950 px-1.5 py-0.5 rounded border border-neutral-800 text-neutral-200">
              TTS: {points[points.length - 1].ttsRequests}
            </span>
          </div>
          {points[points.length - 1].ttsRequestsHourly !== undefined && (
            <div className="flex items-center gap-1.5 font-mono text-neutral-300">
              <span className="text-neutral-400">TTS Hourly:</span>
              <span className={points[points.length - 1].ttsRequestsHourly! >= 90 ? "text-red-400 font-semibold" : "text-emerald-400"}>
                {points[points.length - 1].ttsRequestsHourly} / 100 req/hr
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

