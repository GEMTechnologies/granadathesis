'use client';

import React, { useState, useEffect } from 'react';
import { CheckCircle2, Circle, Loader2, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ExecutionStep {
    id: string;
    title: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    progress?: number;
    description?: string;
    substeps?: ExecutionStep[];
    timestamp?: string;
    metadata?: Record<string, any>;
}

interface TaskExecution {
    taskName: string;
    mode: 'PLANNING' | 'EXECUTION' | 'VERIFICATION';
    status: 'running' | 'completed' | 'error';
    summary: string;
    steps: ExecutionStep[];
}

interface ModernExecutionPanelProps {
    execution: TaskExecution;
    onComplete?: () => void;
}

export function ModernExecutionPanel({ execution, onComplete }: ModernExecutionPanelProps) {
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

    const toggleStep = (stepId: string) => {
        const newExpanded = new Set(expandedSteps);
        if (newExpanded.has(stepId)) {
            newExpanded.delete(stepId);
        } else {
            newExpanded.add(stepId);
        }
        setExpandedSteps(newExpanded);
    };

    const getModeColor = (mode: string) => {
        switch (mode) {
            case 'PLANNING':
                return 'bg-blue-500';
            case 'EXECUTION':
                return 'bg-green-500';
            case 'VERIFICATION':
                return 'bg-purple-500';
            default:
                return 'bg-gray-500';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle2 className="w-5 h-5 text-green-500" />;
            case 'running':
                return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
            case 'error':
                return <AlertCircle className="w-5 h-5 text-red-500" />;
            default:
                return <Circle className="w-5 h-5 text-gray-300" />;
        }
    };

    const renderStep = (step: ExecutionStep, depth: number = 0) => {
        const isExpanded = expandedSteps.has(step.id);
        const hasSubsteps = step.substeps && step.substeps.length > 0;

        return (
            <div key={step.id} className="mb-2" style={{ marginLeft: `${depth * 24}px` }}>
                <div
                    className={cn(
                        "flex items-start gap-3 p-3 rounded-lg transition-all",
                        step.status === 'running' && "bg-blue-50 border border-blue-200",
                        step.status === 'completed' && "bg-green-50 border border-green-200",
                        step.status === 'error' && "bg-red-50 border border-red-200",
                        step.status === 'pending' && "bg-gray-50 border border-gray-200"
                    )}
                >
                    {/* Status Icon */}
                    <div className="flex-shrink-0 mt-0.5">
                        {getStatusIcon(step.status)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                {hasSubsteps && (
                                    <button
                                        onClick={() => toggleStep(step.id)}
                                        className="p-0.5 hover:bg-gray-200 rounded transition-colors"
                                    >
                                        {isExpanded ? (
                                            <ChevronDown className="w-4 h-4 text-gray-600" />
                                        ) : (
                                            <ChevronRight className="w-4 h-4 text-gray-600" />
                                        )}
                                    </button>
                                )}
                                <h4
                                    className={cn(
                                        "font-medium text-sm",
                                        step.status === 'running' && "text-blue-700",
                                        step.status === 'completed' && "text-green-700",
                                        step.status === 'error' && "text-red-700",
                                        step.status === 'pending' && "text-gray-600"
                                    )}
                                >
                                    {step.title}
                                </h4>
                            </div>

                            {step.timestamp && (
                                <span className="text-xs text-gray-400">
                                    {new Date(step.timestamp).toLocaleTimeString()}
                                </span>
                            )}
                        </div>

                        {step.description && (
                            <p className="text-xs text-gray-600 mt-1">{step.description}</p>
                        )}

                        {/* Progress Bar */}
                        {step.progress !== undefined && step.status === 'running' && (
                            <div className="mt-2">
                                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-500 transition-all duration-300 rounded-full"
                                        style={{ width: `${step.progress}%` }}
                                    />
                                </div>
                                <span className="text-xs text-gray-500 mt-1">{step.progress}%</span>
                            </div>
                        )}

                        {/* Metadata */}
                        {step.metadata && Object.keys(step.metadata).length > 0 && (
                            <div className="mt-2 text-xs text-gray-500 font-mono">
                                {Object.entries(step.metadata).map(([key, value]) => (
                                    <div key={key} className="truncate">
                                        <span className="text-gray-400">{key}:</span> {String(value)}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Substeps */}
                {hasSubsteps && isExpanded && (
                    <div className="mt-1">
                        {step.substeps!.map((substep) => renderStep(substep, depth + 1))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full bg-white">
            {/* Header - Task Information */}
            <div className="flex-shrink-0 border-b border-gray-200 p-4">
                <div className="flex items-center gap-3">
                    <div className={cn("w-2 h-12 rounded-full", getModeColor(execution.mode))} />
                    <div className="flex-1">
                        <h2 className="text-lg font-semibold text-gray-900">{execution.taskName}</h2>
                        <p className="text-sm text-gray-600 mt-0.5">{execution.summary}</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <span
                            className={cn(
                                "px-3 py-1 rounded-full text-xs font-medium uppercase",
                                execution.mode === 'PLANNING' && "bg-blue-100 text-blue-700",
                                execution.mode === 'EXECUTION' && "bg-green-100 text-green-700",
                                execution.mode === 'VERIFICATION' && "bg-purple-100 text-purple-700"
                            )}
                        >
                            {execution.mode}
                        </span>
                        {execution.status === 'running' && (
                            <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                        )}
                    </div>
                </div>
            </div>

            {/* Steps - Scrollable */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {execution.steps.map((step) => renderStep(step))}
            </div>

            {/* Footer - Completion Status */}
            {execution.status === 'completed' && (
                <div className="flex-shrink-0 border-t border-gray-200 p-4 bg-green-50">
                    <div className="flex items-center gap-2 text-green-700">
                        <CheckCircle2 className="w-5 h-5" />
                        <span className="font-medium">Task Completed Successfully</span>
                    </div>
                </div>
            )}

            {execution.status === 'error' && (
                <div className="flex-shrink-0 border-t border-gray-200 p-4 bg-red-50">
                    <div className="flex items-center gap-2 text-red-700">
                        <AlertCircle className="w-5 h-5" />
                        <span className="font-medium">Task Failed</span>
                    </div>
                </div>
            )}
        </div>
    );
}

// Hook for real-time execution updates via SSE
export function useExecutionStream(jobId: string) {
    const [execution, setExecution] = useState<TaskExecution | null>(null);

    useEffect(() => {
        if (!jobId) return;

        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const eventSource = new EventSource(
            `${backendUrl}/api/stream/agent-actions?session_id=default&job_id=${jobId}`
        );

        let currentTask: TaskExecution = {
            taskName: 'Processing...',
            mode: 'EXECUTION',
            status: 'running',
            summary: '',
            steps: []
        };

        eventSource.addEventListener('log', (e) => {
            try {
                const data = JSON.parse(e.data);
                const newStep: ExecutionStep = {
                    id: `step-${Date.now()}`,
                    title: data.message,
                    status: data.level === 'error' ? 'error' : 'completed',
                    timestamp: new Date().toISOString()
                };
                currentTask.steps.push(newStep);
                setExecution({ ...currentTask });
            } catch (err) {
                console.error('Error parsing log:', err);
            }
        });

        eventSource.addEventListener('progress', (e) => {
            try {
                const data = JSON.parse(e.data);
                if (currentTask.steps.length > 0) {
                    const lastStep = currentTask.steps[currentTask.steps.length - 1];
                    lastStep.progress = data.percent;
                    lastStep.description = data.stage;
                    setExecution({ ...currentTask });
                }
            } catch (err) {
                console.error('Error parsing progress:', err);
            }
        });

        eventSource.addEventListener('stage_completed', (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.stage === 'complete') {
                    currentTask.status = 'completed';
                    setExecution({ ...currentTask });
                }
            } catch (err) {
                console.error('Error parsing stage:', err);
            }
        });

        return () => {
            eventSource.close();
        };
    }, [jobId]);

    return execution;
}
