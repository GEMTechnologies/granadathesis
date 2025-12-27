import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { session_id: string } }
) {
  try {
    const { session_id } = params;

    try {
      const response = await fetch(`${BACKEND_URL}/api/session/${session_id}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch (fetchError: any) {
      // Backend not available, return default session info
      console.log('Backend session service unavailable');
    }

    // Return default session info if backend unavailable
    return NextResponse.json({
      session_id: session_id,
      user_id: 'user-1',
      session_url: `/session/${session_id}`,
      workspace: null,
    });

  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

