import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const userId = body.user_id || 'user-1';

    try {
      const response = await fetch(`${BACKEND_URL}/api/session/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }

      // If backend returns error, fall through to default session
    } catch (fetchError: any) {
      // Backend not available or connection failed
      console.log('Backend session service unavailable, using default session');
    }

    // Return default session if backend is unavailable
    const defaultSession = {
      session_id: `default-${Date.now()}`,
      user_id: userId,
      session_url: `/session/default-${Date.now()}`,
      workspace: null,
      has_workspace: false,
    };
    return NextResponse.json(defaultSession);

  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

