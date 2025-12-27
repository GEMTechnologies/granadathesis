import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { workspace_id: string } }
) {
  try {
    const { workspace_id } = params;

    // If backend is not available, return empty workspace structure
    let response;
    try {
      response = await fetch(`${BACKEND_URL}/api/workspace/${workspace_id}/structure`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        // Add timeout
        signal: AbortSignal.timeout(5000),
      });
    } catch (fetchError: any) {
      // Backend not available - return empty structure
      console.error('Backend not available, returning empty workspace:', fetchError.message);
      return NextResponse.json({
        items: [],
        workspace_id: workspace_id,
        error: 'Backend server not available. Please start the backend server.'
      });
    }

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error:', errorText);
      return NextResponse.json(
        {
          error: 'Failed to fetch workspace structure',
          details: errorText,
          items: [],
          workspace_id: workspace_id
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('API route error:', error);
    return NextResponse.json(
      {
        error: error.message || 'Internal server error',
        items: [],
        workspace_id: params?.workspace_id || 'unknown'
      },
      { status: 500 }
    );
  }
}

