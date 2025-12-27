"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Brain, Loader2, CheckCircle2, XCircle, Lightbulb, Code, Wrench } from 'lucide-react';

interface AgentThought {
    type: 'thought' | 'start' | 'complete' | 'error';
    content?: string;
    query?: string;
    result?: any;
    error?: string;
}

interface AgentStreamProps {
    workspaceId: string;
    query: string;
    onComplete?: (result: any) => void;
}

export default function AgentStream({ workspaceId, query, onComplete }: AgentStreamProps) {
    const [thoughts, setThoughts] = useState<AgentThought[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const [result, setResult] = useState<any>(null);
    const thoughtsEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        startAgent();
    }, []);

    useEffect(() => {
        // Auto-scroll to latest thought
        thoughtsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [thoughts]);

    const startAgent = async () => {
        setIsRunning(true);

        try {
            const response = await fetch('/api/agent/solve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    workspace_id: workspaceId
                })
            });

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
                        setThoughts(prev => [...prev, data]);

                        if (data.type === 'complete') {
                            setResult(data.result);
                            setIsRunning(false);
                            if (onComplete) onComplete(data.result);
                        } else if (data.type === 'error') {
                            setIsRunning(false);
                        }
                    }
                }
            }
        } catch (error) {
            setThoughts(prev => [...prev, {
                type: 'error',
                error: error instanceof Error ? error.message : 'Unknown error'
            }]);
            setIsRunning(false);
        }
    };

    const getIcon = (type: string, content?: string) => {
        if (type === 'start') return <Brain className="h-5 w-5 text-purple-500 animate-pulse" />;
        if (type === 'complete') return <CheckCircle2 className="h-5 w-5 text-green-500" />;
        if (type === 'error') return <XCircle className="h-5 w-5 text-red-500" />;

        // Content-based icons
        if (content?.includes('🧠')) return <Brain className="h-5 w-5 text-blue-500" />;
        if (content?.includes('💭')) return <Lightbulb className="h-5 w-5 text-yellow-500" />;
        if (content?.includes('🔨')) return <Wrench className="h-5 w-5 text-orange-500" />;
        if (content?.includes('⚡') || content?.includes('▶️')) return <Code className="h-5 w-5 text-purple-500" />;

        return <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />;
    };

    const getColor = (content?: string) => {
        if (!content) return 'text-gray-600';
        if (content.includes('✅')) return 'text-green-600';
        if (content.includes('❌')) return 'text-red-600';
        if (content.includes('🧠') || content.includes('💭')) return 'text-blue-600';
        if (content.includes('🔨')) return 'text-orange-600';
        if (content.includes('⚡')) return 'text-purple-600';
        return 'text-gray-700';
    };

    return (
        <div className="h-full flex flex-col bg-gradient-to-br from-gray-50 to-blue-50 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <Brain className="h-6 w-6" />
                        <div>
                            <h2 className="font-bold">Autonomous Agent</h2>
                            <p className="text-sm text-blue-100 truncate max-w-md">{query}</p>
                        </div>
                    </div>
                    {isRunning && (
                        <div className="flex items-center space-x-2 bg-white/20 px-3 py-1 rounded-full">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Thinking...</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Thought Stream */}
            <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {thoughts.map((thought, idx) => (
                    <div
                        key={idx}
                        className="flex items-start space-x-3 bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition animate-fadeIn"
                    >
                        <div className="flex-shrink-0 mt-0.5">
                            {getIcon(thought.type, thought.content)}
                        </div>
                        <div className="flex-1 min-w-0">
                            {thought.type === 'start' && (
                                <p className="text-gray-700">
                                    <span className="font-semibold">Starting:</span> {thought.query}
                                </p>
                            )}
                            {thought.type === 'thought' && (
                                <p className={`${getColor(thought.content)} leading-relaxed`}>
                                    {thought.content}
                                </p>
                            )}
                            {thought.type === 'complete' && (
                                <div>
                                    <p className="text-green-600 font-semibold mb-2">✅ Task Complete!</p>
                                    {thought.result && (
                                        <div className="bg-gray-50 p-3 rounded border border-gray-200">
                                            <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                                                {JSON.stringify(thought.result, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )}
                            {thought.type === 'error' && (
                                <p className="text-red-600">
                                    <span className="font-semibold">Error:</span> {thought.error}
                                </p>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={thoughtsEndRef} />
            </div>

            {/* Footer Stats */}
            {result && !isRunning && (
                <div className="px-6 py-3 bg-white border-t border-gray-200">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">
                            {thoughts.length} thoughts • {result.tools_created?.length || 0} tools created
                        </span>
                        <span className="text-green-600 font-medium">Complete</span>
                    </div>
                </div>
            )}

            <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
        </div>
    );
}
