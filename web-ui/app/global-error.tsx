'use client';

import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: '#F4F4F4' }}>
          <div className="max-w-md w-full text-center space-y-4">
            <div className="p-4 rounded-full mx-auto w-fit" style={{ backgroundColor: 'rgba(218, 30, 40, 0.1)' }}>
              <AlertCircle className="w-12 h-12 text-red-600" />
            </div>
            <h1 className="text-2xl font-bold" style={{ color: '#161616' }}>
              Something went wrong!
            </h1>
            <p className="text-sm" style={{ color: '#525252' }}>
              {error.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={reset}
              className="px-4 py-2 rounded-lg font-semibold"
              style={{
                backgroundColor: '#0F62FE',
                color: 'white',
              }}
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
















