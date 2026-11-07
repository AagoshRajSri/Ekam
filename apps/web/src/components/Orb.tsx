'use client';

import React from 'react';

interface OrbProps {
  state: 'disconnected' | 'connecting' | 'listening' | 'thinking' | 'speaking';
  audioLevel?: number; // 0.0 to 1.0
}

export function Orb({ state, audioLevel = 0 }: OrbProps) {
  // Compute dynamic scale and shadow from audio level
  const scale = state === 'speaking' ? 1 + audioLevel * 0.25 : 1;
  const shadowIntensity = state === 'speaking' ? Math.min(60 + audioLevel * 80, 100) : 40;

  const stateStyles = {
    disconnected: {
      gradient: 'from-gray-700 via-gray-800 to-gray-900',
      glow: 'rgba(75, 85, 99, 0.2)',
      label: 'Offline',
      pulseClass: '',
    },
    connecting: {
      gradient: 'from-amber-500 via-orange-600 to-yellow-600',
      glow: 'rgba(245, 158, 11, 0.5)',
      label: 'Connecting…',
      pulseClass: 'animate-pulse',
    },
    listening: {
      gradient: 'from-cyan-400 via-blue-500 to-indigo-600',
      glow: 'rgba(56, 189, 248, 0.6)',
      label: 'Listening',
      pulseClass: 'animate-pulse-glow',
    },
    thinking: {
      gradient: 'from-purple-500 via-pink-600 to-indigo-600',
      glow: 'rgba(168, 85, 247, 0.7)',
      label: 'Thinking…',
      pulseClass: 'animate-spin-slow',
    },
    speaking: {
      gradient: 'from-blue-400 via-indigo-500 to-violet-500',
      glow: 'rgba(99, 131, 246, 0.8)',
      label: 'Speaking',
      pulseClass: 'animate-speaking-wave',
    },
  }[state];

  return (
    <div className="relative flex flex-col items-center justify-center my-8">
      {/* Outer ambient blur aura */}
      <div
        className="absolute w-56 h-56 rounded-full transition-all duration-300 ease-out pointer-events-none"
        style={{
          background: `radial-gradient(circle, ${stateStyles.glow} 0%, transparent 70%)`,
          transform: `scale(${scale * 1.3})`,
          filter: 'blur(30px)',
        }}
      />

      {/* Main core orb */}
      <div
        className={`relative w-44 h-44 rounded-full bg-gradient-to-tr ${stateStyles.gradient} shadow-2xl transition-transform duration-150 ease-out flex items-center justify-center ${stateStyles.pulseClass}`}
        style={{
          transform: `scale(${scale})`,
          boxShadow: `0 0 ${shadowIntensity}px ${stateStyles.glow}`,
        }}
      >
        {/* Core highlight reflection */}
        <div className="absolute top-4 left-6 w-14 h-8 bg-white/20 rounded-full rotate-[-30deg] blur-[2px]" />

        {/* Center state text / icon */}
        <div className="text-center select-none">
          <span className="text-xs uppercase tracking-widest font-semibold text-white/90 drop-shadow">
            {stateStyles.label}
          </span>
        </div>
      </div>
    </div>
  );
}

