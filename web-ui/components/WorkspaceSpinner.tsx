"use client";

import React, { useState } from 'react';
import { Loader2, Box, CheckCircle2 } from 'lucide-react';

interface WorkspaceSpinnerProps {
    topic?: string;
    onWorkspaceCreated?: (workspaceId: string) => void;
}

export default function WorkspaceSpinner({ topic = "New Project", onWorkspaceCreated }: WorkspaceSpinnerProps) {
    const [status, setStatus] = useState<'creating' | 'success' | 'error'>('creating');
    const [workspaceId, setWorkspaceId] = useState<string>('');
    const [errorMessage, setErrorMessage] = useState<string>('');

    React.useEffect(() => {
        createWorkspaceWithSandbox();
    }, []);

    const createWorkspaceWithSandbox = async () => {
        try {
            setStatus('creating');

            const response = await fetch('/api/workspace/create-with-sandbox', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic,
                    template: 'python',
                    enable_network: false
                })
            });

            if (!response.ok) {
                throw new Error('Failed to create workspace');
            }

            const data = await response.json();

            setWorkspaceId(data.workspace_id);
            setStatus('success');

            // Notify parent component
            if (onWorkspaceCreated) {
                onWorkspaceCreated(data.workspace_id);
            }

            // Auto-redirect after 1 second
            setTimeout(() => {
                window.location.href = data.url;
            }, 1000);

        } catch (error) {
            setStatus('error');
            setErrorMessage(error instanceof Error ? error.message : 'Unknown error');
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="bg-white rounded-2xl shadow-2xl p-12 max-w-md w-full text-center">
                {/* Icon */}
                <div className="mb-6">
                    {status === 'creating' && (
                        <div className="relative">
                            <Box className="h-16 w-16 mx-auto text-blue-500 animate-pulse" />
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Loader2 className="h-12 w-12 text-blue-600 animate-spin" />
                            </div>
                        </div>
                    )}
                    {status === 'success' && (
                        <CheckCircle2 className="h-16 w-16 mx-auto text-green-500" />
                    )}
                    {status === 'error' && (
                        <div className="h-16 w-16 mx-auto rounded-full bg-red-100 flex items-center justify-center">
                            <span className="text-3xl">❌</span>
                        </div>
                    )}
                </div>

                {/* Status Text */}
                <div className="space-y-3">
                    {status === 'creating' && (
                        <>
                            <h2 className="text-2xl font-bold text-gray-900">
                                Creating Your Workspace
                            </h2>
                            <div className="space-y-2 text-sm text-gray-600">
                                <p className="flex items-center justify-center space-x-2">
                                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                                    <span>Initializing workspace...</span>
                                </p>
                                <p className="flex items-center justify-center space-x-2">
                                    <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse delay-100"></span>
                                    <span>Spinning up secure sandbox...</span>
                                </p>
                                <p className="flex items-center justify-center space-x-2">
                                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse delay-200"></span>
                                    <span>Configuring environment...</span>
                                </p>
                            </div>
                        </>
                    )}

                    {status === 'success' && (
                        <>
                            <h2 className="text-2xl font-bold text-green-600">
                                Workspace Ready!
                            </h2>
                            <p className="text-gray-600">
                                Your isolated sandbox is configured and ready to use.
                            </p>
                            <p className="text-xs text-gray-500 font-mono">
                                {workspaceId}
                            </p>
                            <p className="text-sm text-gray-500 mt-4">
                                Redirecting...
                            </p>
                        </>
                    )}

                    {status === 'error' && (
                        <>
                            <h2 className="text-2xl font-bold text-red-600">
                                Creation Failed
                            </h2>
                            <p className="text-gray-600">
                                {errorMessage}
                            </p>
                            <button
                                onClick={createWorkspaceWithSandbox}
                                className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                            >
                                Try Again
                            </button>
                        </>
                    )}
                </div>

                {/* Progress Bar */}
                {status === 'creating' && (
                    <div className="mt-8">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full animate-progress"></div>
                        </div>
                    </div>
                )}

                {/* Security Badge */}
                <div className="mt-8 pt-6 border-t border-gray-200">
                    <p className="text-xs text-gray-500 flex items-center justify-center space-x-2">
                        <span className="text-green-600">🔒</span>
                        <span>Secure Docker-isolated environment</span>
                    </p>
                </div>
            </div>

            <style jsx>{`
        @keyframes progress {
          0% { width: 0%; }
          100% { width: 100%; }
        }
        .animate-progress {
          animation: progress 3s ease-in-out infinite;
        }
        .delay-100 {
          animation-delay: 0.1s;
        }
        .delay-200 {
          animation-delay: 0.2s;
        }
      `}</style>
        </div>
    );
}
