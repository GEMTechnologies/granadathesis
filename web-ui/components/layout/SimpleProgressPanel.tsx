import React, { useEffect, useRef } from 'react';
import { X, CheckCircle, Circle, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ProgressStep {
    id: string;
    label: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    timestamp?: Date;
}

import { AgentAction } from '../workspace/StreamingWorkspace';

interface SimpleProgressPanelProps {
    isOpen: boolean;
    onClose: () => void;
    isProcessing: boolean;
    onProcessingComplete: () => void;
    progressSteps: ProgressStep[];
    liveResponse: string;
    agentActions?: AgentAction[];
    variant?: 'overlay' | 'column';
    reasoning?: string;
}

export function SimpleProgressPanel({
    isOpen,
    onClose,
    isProcessing,
    onProcessingComplete,
    progressSteps,
    liveResponse,
    agentActions = [],
    variant = 'overlay',
    reasoning
}: SimpleProgressPanelProps) {
    const panelRef = useRef<HTMLDivElement>(null);

    // Close on click outside - ONLY for overlay mode
    useEffect(() => {
        if (variant !== 'overlay') return;

        const handleClickOutside = (event: MouseEvent) => {
            if (panelRef.current && !panelRef.current.contains(event.target as Node) && isOpen) {
                onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen, onClose, variant]);

    // Filter relevant actions for the progress panel (e.g., tool calls, thoughts)
    const relevantActions = agentActions.filter(a =>
        ['tool_call', 'code_execution', 'file_write', 'research_result'].includes(a.type)
    ).reverse(); // Show newest first

    return (
        <div
            className={cn(
                variant === 'overlay'
                    ? "fixed inset-y-0 right-0 w-96 bg-white shadow-2xl transform transition-transform duration-300 ease-in-out z-50 flex flex-col"
                    : "flex flex-col h-full bg-white border-l",
                variant === 'overlay' && (isOpen ? "translate-x-0" : "translate-x-full")
            )}
            ref={panelRef}
            style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderLeft: '1px solid var(--color-border, #E0E0E0)'
            }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
                <h2 className="text-lg font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
                    Agent Operations
                </h2>
                <button
                    onClick={onClose}
                    className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                    style={{ color: 'var(--color-text-secondary, #525252)' }}
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
                {/* Reasoning Section */}
                {reasoning && (
                    <div className="space-y-2">
                        <h3 className="text-sm font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                            Reasoning
                        </h3>
                        <div
                            className="p-3 rounded-lg text-sm italic border-l-4"
                            style={{
                                backgroundColor: 'var(--color-bg-secondary, #F4F4F4)',
                                color: 'var(--color-text-secondary, #525252)',
                                borderColor: 'var(--color-primary, #0F62FE)'
                            }}
                        >
                            {reasoning}
                        </div>
                    </div>
                )}

                {/* Live Agent Actions */}
                {relevantActions.length > 0 && (
                    <div className="space-y-4">
                        <h3 className="text-sm font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                            Live Activity
                        </h3>
                        <div className="space-y-3">
                            {relevantActions.map((action) => (
                                <div key={action.id} className="p-3 rounded-lg border text-sm" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium" style={{ color: 'var(--color-text, #161616)' }}>
                                            {action.title}
                                        </span>
                                        <span className="text-xs text-gray-400">
                                            {action.timestamp.toLocaleTimeString()}
                                        </span>
                                    </div>
                                    <p className="text-xs text-gray-500 truncate">
                                        {action.type.replace('_', ' ')}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Progress Steps */}
                <div className="space-y-6">
                    <h3 className="text-sm font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                        Status
                    </h3>
                    <div className="space-y-4">
                        {progressSteps.map((step, index) => (
                            <div key={step.id} className="flex items-start gap-3">
                                <div className="mt-0.5">
                                    {step.status === 'completed' && <CheckCircle className="w-5 h-5 text-green-500" />}
                                    {step.status === 'running' && <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />}
                                    {step.status === 'error' && <AlertCircle className="w-5 h-5 text-red-500" />}
                                    {step.status === 'pending' && <Circle className="w-5 h-5 text-gray-300" />}
                                </div>
                                <div className="flex-1">
                                    <p className={cn(
                                        "text-sm font-medium",
                                        step.status === 'completed' ? "text-gray-900" :
                                            step.status === 'running' ? "text-blue-600" :
                                                step.status === 'error' ? "text-red-600" :
                                                    "text-gray-500"
                                    )}>
                                        {step.label}
                                    </p>
                                    {step.timestamp && (
                                        <p className="text-xs text-gray-400 mt-1">
                                            {step.timestamp.toLocaleTimeString()}
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}
                        {progressSteps.length === 0 && !isProcessing && relevantActions.length === 0 && (
                            <p className="text-sm text-gray-500 italic">No active tasks</p>
                        )}
                    </div>
                </div>

                {/* Live Response / Output */}
                {(liveResponse || isProcessing) && (
                    <div className="space-y-4 pt-6 border-t" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
                        <h3 className="text-sm font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                            Output
                        </h3>
                        <div
                            className="p-4 rounded-lg text-sm font-mono whitespace-pre-wrap"
                            style={{
                                backgroundColor: 'var(--color-bg-secondary, #F4F4F4)',
                                color: 'var(--color-text, #161616)'
                            }}
                        >
                            {liveResponse || (isProcessing ? "Waiting for response..." : "")}
                        </div>
                    </div>
                )}
            </div>

            {/* Footer */}
            {isProcessing && (
                <div className="p-4 border-t bg-gray-50" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
                    <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Processing...
                    </div>
                </div>
            )}
        </div>
    );
}
