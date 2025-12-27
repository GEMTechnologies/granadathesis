'use client';

import React from 'react';
import { Loader2, CheckCircle, XCircle, Terminal } from 'lucide-react';

interface AgentStep {
    message: string;
    status: 'running' | 'completed' | 'error';
    timestamp?: string;
}

interface AgentExecutionPanelProps {
    steps: AgentStep[];
    taskName?: string;
}

export function AgentExecutionPanel({ steps, taskName }: AgentExecutionPanelProps) {
    const getIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-4 h-4 text-green-400" />;
            case 'running':
                return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
            case 'error':
                return <XCircle className="w-4 h-4 text-red-400" />;
        }
    };

    return (
        <div className="h-full bg-gray-900 text-gray-100 font-mono text-sm">
            {/* Terminal Header */}
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-800 border-b border-gray-700">
                <Terminal className="w-4 h-4 text-gray-400" />
                <span className="text-gray-400 text-xs">
                    {taskName || 'Agent Execution'}
                </span>
            </div>

            {/* Terminal Content */}
            <div className="p-4 space-y-1 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 200px)' }}>
                {steps.map((step, index) => (
                    <div
                        key={index}
                        className="flex items-start gap-3 py-1 hover:bg-gray-800/50 px-2 -mx-2 rounded transition-colors"
                    >
                        <span className="text-gray-500 text-xs mt-0.5 w-12 flex-shrink-0">
                            {step.timestamp || `${String(index + 1).padStart(2, '0')}:`}
                        </span>
                        <div className="flex-shrink-0 mt-0.5">
                            {getIcon(step.status)}
                        </div>
                        <span
                            className={
                                step.status === 'error'
                                    ? 'text-red-400'
                                    : step.status === 'running'
                                        ? 'text-blue-400'
                                        : 'text-gray-300'
                            }
                        >
                            {step.message}
                        </span>
                    </div>
                ))}

                {/* Cursor */}
                {steps.some(s => s.status === 'running') && (
                    <div className="flex items-center gap-3 py-1">
                        <span className="text-gray-500 text-xs w-12"></span>
                        <span className="text-blue-400 animate-pulse">▊</span>
                    </div>
                )}
            </div>
        </div>
    );
}
