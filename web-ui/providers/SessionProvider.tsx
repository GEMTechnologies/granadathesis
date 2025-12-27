'use client';

import { SessionProvider as SessionProviderClient } from '../contexts/SessionContext';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  return <SessionProviderClient>{children}</SessionProviderClient>;
}

















