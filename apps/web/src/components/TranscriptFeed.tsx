'use client';

import React, { useEffect, useRef } from 'react';
import { User, Bot, AlertTriangle } from 'lucide-react';

export interface TranscriptEntry {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  timestamp: string;
  isPartial?: boolean;
}

interface TranscriptFeedProps {
  entries: TranscriptEntry[];
  quotaAlert?: boolean;
}

export function TranscriptFeed({ entries, quotaAlert }: TranscriptFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div className="w-full max-w-2xl flex-1 bg-neutral-900/60 border border-neutral-800 rounded-xl p-4 backdrop-blur-md overflow-hidden flex flex-col">
      <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-3 pb-2 border-b border-neutral-800 flex items-center justify-between">
        <span>Live Transcript</span>
        <span className="text-[11px] text-neutral-400 font-normal">Spoken utterances & responses</span>
      </div>

      {quotaAlert && (
        <div className="mb-3 p-3 bg-amber-950/40 border border-amber-600/50 rounded-lg flex items-start gap-2.5 text-amber-200 text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-amber-300">Voice Limit Fallback Active:</span> The hourly voice synthesis limit was reached. Replies will continue to appear on screen in real time.
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-sm max-h-[360px]">
        {entries.length === 0 ? (
          <div className="h-full flex items-center justify-center text-neutral-400 text-xs italic py-8">
            Connect and speak to begin…
          </div>
        ) : (
          entries.map((entry) => {
            const isUser = entry.role === 'user';
            const isSystem = entry.role === 'system';

            if (isSystem) {
              return (
                <div key={entry.id} className="text-center my-2 text-xs text-neutral-400 italic">
                  {entry.text}
                </div>
              );
            }

            return (
              <div
                key={entry.id}
                className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                    isUser
                      ? 'bg-blue-600 text-white'
                      : 'bg-gradient-to-tr from-violet-600 to-indigo-600 text-white'
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div
                  className={`max-w-[80%] rounded-2xl px-3.5 py-2 ${
                    isUser
                      ? 'bg-blue-600/20 border border-blue-500/30 text-blue-100'
                      : 'bg-neutral-800/80 border border-neutral-700/50 text-neutral-100'
                  } ${entry.isPartial ? 'opacity-70 italic' : ''}`}
                >
                  <div className="flex items-center justify-between gap-3 text-[10px] text-neutral-400 mb-0.5">
                    <span className="font-semibold text-neutral-300">{isUser ? 'You' : (process.env.NEXT_PUBLIC_APP_NAME || 'Daimon')}</span>
                    <span>{entry.timestamp}</span>
                  </div>
                  <div className="leading-relaxed">{entry.text}</div>
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

