import { loadEnvConfig } from '@next/env';
import { AccessToken } from 'livekit-server-sdk';
import { NextRequest, NextResponse } from 'next/server';
import path from 'path';

// Load root .env file from repository root (2 levels above apps/web)
const repoRoot = path.resolve(process.cwd(), '../..');
loadEnvConfig(repoRoot);

export async function GET(req: NextRequest) {
  try {
    const apiKey = process.env.LIVEKIT_API_KEY;
    const apiSecret = process.env.LIVEKIT_API_SECRET;
    const livekitUrl = process.env.LIVEKIT_URL;

    if (!apiKey || !apiSecret || !livekitUrl) {
      return NextResponse.json(
        {
          error:
            'Missing LiveKit configuration: LIVEKIT_API_KEY, LIVEKIT_API_SECRET, or LIVEKIT_URL is not set.',
        },
        { status: 500 }
      );
    }

    const { searchParams } = new URL(req.url);
    const room = searchParams.get('room') || `daimon_${crypto.randomUUID().slice(0, 8)}`;
    const identity = `user_${crypto.randomUUID()}`;

    // Token TTL: 10 minutes (600s)
    const at = new AccessToken(apiKey, apiSecret, {
      identity,
      name: identity,
      ttl: '10m',
    });

    // Minimal participant grants: roomJoin, canPublish, canSubscribe, canPublishData
    at.addGrant({
      room,
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
    });

    const token = await at.toJwt();

    return NextResponse.json({
      token,
      url: livekitUrl,
      room,
      identity,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Internal Server Error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

