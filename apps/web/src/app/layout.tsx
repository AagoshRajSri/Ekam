import type { Metadata } from 'next';
import '@livekit/components-styles';
import './globals.css';

export const metadata: Metadata = {
  title: 'Ekam — Voice-First AI Assistant',
  description: 'Ultra-low-latency, real-time voice-first personal AI assistant.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090a0f] text-[#f0f2f5] antialiased min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
