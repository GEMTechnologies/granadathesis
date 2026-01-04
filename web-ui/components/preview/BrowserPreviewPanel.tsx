'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Loader2, Globe, RefreshCw, ExternalLink, X, Monitor, Eye } from 'lucide-react';
import { cn } from '../../lib/utils';

interface BrowserPreviewPanelProps {
    sessionId?: string;
    workspaceId?: string;
    onClose?: () => void;
    className?: string;
}

/**
 * BrowserPreviewPanel - Shows live browser automation in the preview panel
 * 
 * Connects to backend SSE stream to receive:
 * - Screenshots from Playwright
 * - Current URL being visited
 * - Actions being performed
 */
export function BrowserPreviewPanel({
    sessionId = 'default',
    workspaceId = 'default',
    onClose,
    className = ''
}: BrowserPreviewPanelProps) {
    const [currentUrl, setCurrentUrl] = useState<string>('');
    const [screenshot, setScreenshot] = useState<string>(''); // Base64 image
    const [isLoading, setIsLoading] = useState(true);
    const [currentAction, setCurrentAction] = useState<string>('');
    const [isConnected, setIsConnected] = useState(false);
    const eventSourceRef = useRef<EventSource | null>(null);

    useEffect(() => {
        // Connect to browser events stream
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const workspaceId = `ws_${sessionId.substring(0, 12)}`;
        const eventSource = new EventSource(`${backendUrl}/api/browser/stream/${workspaceId}`);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
            setIsConnected(true);
            setIsLoading(false);
        };

        // Handle generic message events
        eventSource.onmessage = (event) => {
            handleBrowserEvent(event.data);
        };

        // Handle browser_update events specifically
        eventSource.addEventListener('browser_update', (event) => {
            handleBrowserEvent(event.data);
        });

        // Handle connected events
        eventSource.addEventListener('connected', () => {
            setIsConnected(true);
            setIsLoading(false);
        });

        function handleBrowserEvent(eventData: string) {
            try {
                const data = JSON.parse(eventData);
                setIsLoading(false);

                if (data.type === 'screenshot') {
                    setScreenshot(data.image); // Base64 image
                    setCurrentUrl(data.url || '');
                    setCurrentAction('');
                } else if (data.type === 'action') {
                    setCurrentAction(data.action || '');
                } else if (data.type === 'url') {
                    setCurrentUrl(data.url || '');
                } else if (data.type === 'loading') {
                    setIsLoading(data.loading);
                }
            } catch (e) {
                console.error('Error parsing browser event:', e);
            }
        }

        eventSource.onerror = () => {
            setIsConnected(false);
            setIsLoading(false);
        };

        return () => {
            eventSource.close();
        };
    }, [sessionId]);

    return (
        <div className={cn("flex flex-col h-full bg-background", className)}>
            {/* Header */}
            <div className="flex items-center justify-between p-3 border-b bg-muted/30">
                <div className="flex items-center gap-2">
                    <Monitor className="w-4 h-4 text-primary" />
                    <span className="font-medium text-sm">Live Browser</span>
                    {isConnected && (
                        <span className="flex items-center gap-1 text-xs text-green-600">
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            Connected
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setIsLoading(true)}
                        className="p-1.5 hover:bg-muted rounded-md transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                    </button>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="p-1.5 hover:bg-muted rounded-md transition-colors"
                            title="Close"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* URL Bar */}
            {currentUrl && (
                <div className="flex items-center gap-2 px-3 py-2 border-b bg-muted/20">
                    <Globe className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 truncate text-xs text-muted-foreground font-mono">
                        {currentUrl}
                    </div>
                    <a
                        href={currentUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1 hover:bg-muted rounded transition-colors"
                        title="Open in new tab"
                    >
                        <ExternalLink className="w-3 h-3" />
                    </a>
                </div>
            )}

            {/* Current Action */}
            {currentAction && (
                <div className="px-3 py-2 border-b bg-blue-50 dark:bg-blue-950/30">
                    <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400">
                        <Eye className="w-3 h-3 animate-pulse" />
                        <span>{currentAction}</span>
                    </div>
                </div>
            )}

            {/* Browser View */}
            <div className="flex-1 relative overflow-hidden bg-gray-100 dark:bg-gray-900">
                {isLoading && !screenshot ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center space-y-3">
                            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
                            <p className="text-sm text-muted-foreground">Waiting for browser...</p>
                        </div>
                    </div>
                ) : screenshot ? (
                    <img
                        src={`data:image/png;base64,${screenshot}`}
                        alt="Browser screenshot"
                        className="w-full h-full object-contain"
                    />
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center space-y-3 max-w-xs">
                            <Monitor className="w-12 h-12 text-muted-foreground/30 mx-auto" />
                            <div className="space-y-1">
                                <p className="text-sm font-medium">No browser activity</p>
                                <p className="text-xs text-muted-foreground">
                                    When the AI browses the web, you'll see it here in real-time.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Loading overlay when updating */}
                {isLoading && screenshot && (
                    <div className="absolute inset-0 bg-background/50 flex items-center justify-center">
                        <Loader2 className="w-6 h-6 animate-spin text-primary" />
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="px-3 py-2 border-t bg-muted/20 text-xs text-muted-foreground text-center">
                🎭 Playwright Browser Automation
            </div>
        </div>
    );
}

export default BrowserPreviewPanel;
