"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Globe, Play, Square, RefreshCw, MousePointer, Keyboard, Eye } from 'lucide-react';

interface BrowserViewerProps {
    workspaceId: string;
}

export default function BrowserViewer({ workspaceId }: BrowserViewerProps) {
    const [browserStarted, setBrowserStarted] = useState(false);
    const [loading, setLoading] = useState(false);
    const [currentUrl, setCurrentUrl] = useState('');
    const [screenshot, setScreenshot] = useState<string | null>(null);
    const [actions, setActions] = useState<any[]>([]);

    // Input states
    const [urlInput, setUrlInput] = useState('');
    const [selectorInput, setSelectorInput] = useState('');
    const [textInput, setTextInput] = useState('');

    useEffect(() => {
        // Connect to live stream if browser started
        if (browserStarted) {
            connectToStream();
        }
    }, [browserStarted]);

    const connectToStream = async () => {
        try {
            const response = await fetch(`/api/browser/stream/${workspaceId}`);
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            while (reader) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value);
                const lines = text.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'browser_action') {
                            // Update screenshot
                            if (data.screenshot) {
                                setScreenshot(data.screenshot);
                            }

                            // Add to action log
                            setActions(prev => [...prev, data]);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stream error:', error);
        }
    };

    const startBrowser = async () => {
        setLoading(true);
        try {
            await fetch(`/api/browser/start?workspace_id=${workspaceId}&headless=false`, {
                method: 'POST'
            });
            setBrowserStarted(true);
        } catch (error) {
            console.error('Failed to start browser:', error);
        } finally {
            setLoading(false);
        }
    };

    const navigate = async () => {
        if (!urlInput.trim()) return;

        setLoading(true);
        try {
            const response = await fetch('/api/browser/navigate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: urlInput,
                    workspace_id: workspaceId
                })
            });

            const data = await response.json();
            setCurrentUrl(data.url);
            setScreenshot(data.screenshot);
        } catch (error) {
            console.error('Navigate failed:', error);
        } finally {
            setLoading(false);
        }
    };

    const clickElement = async () => {
        if (!selectorInput.trim()) return;

        setLoading(true);
        try {
            const response = await fetch('/api/browser/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selector: selectorInput,
                    workspace_id: workspaceId
                })
            });

            const data = await response.json();
            setScreenshot(data.screenshot);
        } catch (error) {
            console.error('Click failed:', error);
        } finally {
            setLoading(false);
        }
    };

    const typeText = async () => {
        if (!selectorInput.trim() || !textInput.trim()) return;

        setLoading(true);
        try {
            const response = await fetch('/api/browser/type', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selector: selectorInput,
                    text: textInput,
                    workspace_id: workspaceId
                })
            });

            const data = await response.json();
            setScreenshot(data.screenshot);
        } catch (error) {
            console.error('Type failed:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-full flex flex-col bg-gray-900">
            {/* Header */}
            <div className="px-4 py-3 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                    <Globe className="h-5 w-5 text-blue-400" />
                    <span className="text-white font-semibold">Live Browser</span>
                    {browserStarted && (
                        <span className="px-2 py-0.5 bg-green-500 text-white text-xs rounded">● LIVE</span>
                    )}
                </div>

                {!browserStarted ? (
                    <button
                        onClick={startBrowser}
                        disabled={loading}
                        className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition disabled:opacity-50"
                    >
                        <Play className="h-4 w-4" />
                        <span>Start Browser</span>
                    </button>
                ) : (
                    <div className="flex items-center space-x-2 text-xs text-gray-400">
                        <Eye className="h-4 w-4" />
                        <span>Watching agent browse...</span>
                    </div>
                )}
            </div>

            {browserStarted && (
                <>
                    {/* Controls */}
                    <div className="px-4 py-3 bg-gray-800 border-b border-gray-700 space-y-2">
                        {/* Navigate */}
                        <div className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={urlInput}
                                onChange={(e) => setUrlInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && navigate()}
                                placeholder="https://example.com"
                                className="flex-1 px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded focus:ring-2 focus:ring-blue-500"
                            />
                            <button
                                onClick={navigate}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition flex items-center space-x-1"
                            >
                                <Globe className="h-4 w-4" />
                                <span>Go</span>
                            </button>
                        </div>

                        {/* Click/Type */}
                        <div className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={selectorInput}
                                onChange={(e) => setSelectorInput(e.target.value)}
                                placeholder="CSS Selector (e.g., button.submit)"
                                className="flex-1 px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded text-sm"
                            />
                            <button
                                onClick={clickElement}
                                className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition flex items-center space-x-1"
                            >
                                <MousePointer className="h-4 w-4" />
                                <span>Click</span>
                            </button>
                        </div>

                        <div className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={textInput}
                                onChange={(e) => setTextInput(e.target.value)}
                                placeholder="Text to type"
                                className="flex-1 px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded text-sm"
                            />
                            <button
                                onClick={typeText}
                                className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded transition flex items-center space-x-1"
                            >
                                <Keyboard className="h-4 w-4" />
                                <span>Type</span>
                            </button>
                        </div>
                    </div>

                    {/* Browser Screen */}
                    <div className="flex-1 flex overflow-hidden">
                        {/* Main View */}
                        <div className="flex-1 flex items-center justify-center bg-black p-4">
                            {screenshot ? (
                                <img
                                    src={`data:image/png;base64,${screenshot}`}
                                    alt="Browser screenshot"
                                    className="max-w-full max-h-full object-contain border border-gray-600 rounded shadow-2xl"
                                />
                            ) : (
                                <div className="text-center text-gray-500">
                                    <Globe className="h-16 w-16 mx-auto mb-4 opacity-30" />
                                    <p>No screenshot yet</p>
                                    <p className="text-sm mt-1">Navigate to a URL to see browser</p>
                                </div>
                            )}
                        </div>

                        {/* Action Log */}
                        <div className="w-80 bg-gray-800 border-l border-gray-700 overflow-y-auto p-4">
                            <h3 className="text-white font-semibold mb-3 flex items-center space-x-2">
                                <RefreshCw className="h-4 w-4" />
                                <span>Action Log</span>
                            </h3>
                            <div className="space-y-2">
                                {actions.map((action, idx) => (
                                    <div
                                        key={idx}
                                        className="p-2 bg-gray-700 rounded text-sm"
                                    >
                                        <div className="flex items-center space-x-2 mb-1">
                                            {action.action === 'navigate' && <Globe className="h-3 w-3 text-blue-400" />}
                                            {action.action === 'click' && <MousePointer className="h-3 w-3 text-green-400" />}
                                            {action.action === 'type' && <Keyboard className="h-3 w-3 text-purple-400" />}
                                            <span className="text-gray-300 font-medium">{action.action}</span>
                                        </div>
                                        <p className="text-gray-400 text-xs truncate">
                                            {action.url || action.selector || action.text}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Status Bar */}
                    <div className="px-4 py-2 bg-gray-800 border-t border-gray-700 flex items-center justify-between text-xs text-gray-400">
                        <span>{currentUrl || 'No page loaded'}</span>
                        <span>{actions.length} actions</span>
                    </div>
                </>
            )}

            {!browserStarted && (
                <div className="flex-1 flex items-center justify-center bg-black text-center">
                    <div>
                        <Globe className="h-24 w-24 mx-auto mb-6 text-gray-700" />
                        <p className="text-gray-500 text-lg mb-2">Browser Automation</p>
                        <p className="text-gray-600 text-sm mb-6">
                            Agent can browse the web and you'll see everything live!
                        </p>
                        <button
                            onClick={startBrowser}
                            disabled={loading}
                            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center space-x-2 mx-auto disabled:opacity-50"
                        >
                            {loading ? (
                                <>
                                    <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                                    <span>Starting...</span>
                                </>
                            ) : (
                                <>
                                    <Play className="h-5 w-5" />
                                    <span>Start Browser</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
