'use client';

import React, { useState } from 'react';
import { Sparkles, Mic, Radio, Shield, AlertCircle } from 'lucide-react';
import { VoiceRoom } from '@/components/VoiceRoom';

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [livekitUrl, setLivekitUrl] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string>('');
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const startSession = async () => {
    setIsConnecting(true);
    setErrorMsg(null);
    try {
      const query = roomName.trim() ? `?room=${encodeURIComponent(roomName.trim())}` : '';
      const res = await fetch(`/api/token${query}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Failed to obtain LiveKit token');
      }
      const data = await res.json();
      setToken(data.token);
      setLivekitUrl(data.url);
      setRoomName(data.room);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setIsConnecting(false);
    }
  };

  const endSession = () => {
    setToken(null);
    setLivekitUrl(null);
  };

  return (
    <main className="flex-1 flex flex-col items-center justify-between p-6 max-w-5xl mx-auto w-full">
      {/* Header Bar */}
      <header className="w-full flex items-center justify-between pb-4 border-b border-neutral-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Ekam</span>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">
                Phase 1 Voice Client
              </span>
            </h1>
            <p className="text-xs text-neutral-400">Ultra-low latency voice-first personal AI</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-neutral-400 bg-neutral-900 border border-neutral-800 px-3 py-1.5 rounded-full">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span>Profile A (Free Tier)</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="w-full flex-1 flex flex-col items-center justify-center my-6">
        {token && livekitUrl ? (
          <VoiceRoom
            token={token}
            url={livekitUrl}
            roomName={roomName}
            onDisconnect={endSession}
          />
        ) : (
          <div className="w-full max-w-md bg-neutral-900/70 border border-neutral-800/80 rounded-2xl p-8 backdrop-blur-xl shadow-2xl flex flex-col items-center text-center">
            {/* Visual Header */}
            <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-brand-500/20 via-indigo-500/10 to-transparent border border-brand-500/30 flex items-center justify-center mb-6 shadow-inner">
              <Radio className="w-10 h-10 text-brand-400 animate-pulse" />
            </div>

            <h2 className="text-2xl font-bold text-white mb-2">Talk to Ekam</h2>
            <p className="text-sm text-neutral-400 mb-6 leading-relaxed">
              Start an interactive, hands-free voice session with Ekam. Answers are concise, conversational, and real-time.
            </p>

            {/* Room Name Input (optional) */}
            <div className="w-full mb-4 text-left">
              <label className="block text-xs font-medium text-neutral-400 mb-1.5">
                Room Name (Optional)
              </label>
              <input
                type="text"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                placeholder="Leave blank for auto-generated room"
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3.5 py-2.5 text-sm text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-brand-500 transition-colors"
              />
            </div>

            {errorMsg && (
              <div className="w-full mb-4 p-3 bg-red-950/60 border border-red-800/60 rounded-lg flex items-center gap-2 text-xs text-red-300 text-left">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Connect Button */}
            <button
              onClick={startSession}
              disabled={isConnecting}
              className="w-full py-3.5 px-6 rounded-xl font-semibold text-sm bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 active:scale-[0.99] text-white shadow-lg shadow-brand-600/30 transition-all flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
            >
              <Mic className="w-4 h-4" />
              <span>{isConnecting ? 'Connecting to Ekam…' : 'Start Voice Session with Ekam'}</span>
            </button>

            {/* Pipeline Info */}
            <div className="mt-6 pt-6 border-t border-neutral-800/80 w-full text-left">
              <div className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-2">
                Active Pipeline (ADR-003):
              </div>
              <ul className="text-xs text-neutral-400 space-y-1">
                <li className="flex items-center justify-between">
                  <span>VAD:</span>
                  <span className="font-mono text-neutral-300">Silero (Local ONNX)</span>
                </li>
                <li className="flex items-center justify-between">
                  <span>STT:</span>
                  <span className="font-mono text-neutral-300">Groq Whisper large-v3-turbo</span>
                </li>
                <li className="flex items-center justify-between">
                  <span>LLM:</span>
                  <span className="font-mono text-neutral-300">Groq Qwen 3.8 27B</span>
                </li>
                <li className="flex items-center justify-between">
                  <span>TTS:</span>
                  <span className="font-mono text-neutral-300">Groq Orpheus / Local Guarded</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="w-full text-center py-3 text-xs text-neutral-400 border-t border-neutral-800">
        Ekam Voice Agent &copy; {new Date().getFullYear()} — Built on LiveKit Agents & Next.js 16
      </footer>
    </main>
  );
}

