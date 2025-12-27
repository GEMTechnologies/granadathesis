'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface SessionData {
  sessionId: string;
  userId: string;
  sessionUrl: string;
  workspaceId: string | null;
  workspaceUrl: string | null;
  shareableUrl: string | null;
  hasWorkspace: boolean;
}

interface SessionContextType {
  session: SessionData | null;
  loading: boolean;
  initSession: (userId?: string) => Promise<void>;
  setWorkspace: (workspaceId: string) => Promise<void>;
  refreshSession: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);

  const initSession = async (userId: string = 'user-1'): Promise<void> => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/session/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });

      if (response.ok) {
        const data = await response.json();
        setSession({
          sessionId: data.session_id,
          userId: data.user_id,
          sessionUrl: data.session_url,
          workspaceId: data.workspace?.workspace_id || null,
          workspaceUrl: data.workspace?.url || null,
          shareableUrl: data.workspace?.shareable_url || null,
          hasWorkspace: data.has_workspace || false,
        });

        // Store session ID in localStorage
        if (typeof window !== 'undefined') {
          localStorage.setItem('session_id', data.session_id);
          localStorage.setItem('user_id', data.user_id);
        }
        setLoading(false);
      } else {
        throw new Error('Failed to initialize session');
      }
    } catch (error) {
      console.error('Failed to initialize session:', error);
      // Don't set loading to false here, let caller handle fallback
      throw error;
    }
  };

  const setWorkspace = async (workspaceId: string) => {
    if (!session) return;

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/session/${session.sessionId}/workspace`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_id: workspaceId }),
      });

      if (response.ok) {
        const data = await response.json();
        setSession(prev => prev ? {
          ...prev,
          workspaceId: data.workspace_id,
          workspaceUrl: data.workspace_url,
          shareableUrl: data.shareable_url,
          hasWorkspace: true,
        } : null);
      }
    } catch (error) {
      console.error('Failed to set workspace:', error);
    }
  };

  const refreshSession = async () => {
    if (!session) return;
    await initSession(session.userId);
  };

  // Initialize session on mount
  useEffect(() => {
    const storedSessionId = typeof window !== 'undefined' ? localStorage.getItem('session_id') : null;
    const storedUserId = typeof window !== 'undefined' ? localStorage.getItem('user_id') : 'user-1';

    if (storedSessionId) {
      // Try to get existing session
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      fetch(`${backendUrl}/api/session/${storedSessionId}`)
        .then(res => {
          if (res.ok) {
            return res.json();
          }
          throw new Error('Session not found');
        })
        .then(data => {
          if (data.session_id) {
            setSession({
              sessionId: data.session_id,
              userId: data.user_id || storedUserId,
              sessionUrl: data.session_url,
              workspaceId: data.workspace?.workspace_id || null,
              workspaceUrl: data.workspace?.url || null,
              shareableUrl: data.workspace?.shareable_url || null,
              hasWorkspace: data.workspace !== null,
            });
            setLoading(false);
          } else {
            // Session expired, create new one
            initSession(storedUserId).catch(() => setLoading(false));
          }
        })
        .catch((err) => {
          console.log('Session check failed (expected for new/expired sessions):', err.message);
          // Failed to get session, create new one or use default
          initSession(storedUserId).catch(() => {
            // If backend is unavailable, use default session
            console.warn('Backend unavailable, using default session');
            const defaultSession: SessionData = {
              sessionId: storedSessionId || 'default-session',
              userId: storedUserId,
              sessionUrl: `/session/${storedSessionId || 'default-session'}`,
              workspaceId: 'default',
              workspaceUrl: '/workspace/default',
              shareableUrl: null,
              hasWorkspace: true,
            };
            setSession(defaultSession);
            setLoading(false);
          });
        });
    } else {
      // No session, create new one
      initSession(storedUserId).catch(() => {
        // If backend is unavailable, use default session
        const defaultSession: SessionData = {
          sessionId: 'default-session',
          userId: storedUserId,
          sessionUrl: '/session/default-session',
          workspaceId: 'default',
          workspaceUrl: '/workspace/default',
          shareableUrl: null,
          hasWorkspace: true,
        };
        setSession(defaultSession);
        setLoading(false);
      });
    }
  }, []);

  return (
    <SessionContext.Provider value={{ session, loading, initSession, setWorkspace, refreshSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}

