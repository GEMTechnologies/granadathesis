'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, Circle, Loader2, AlertCircle, Zap, Code, FileText, Search, Image as ImageIcon, Clock } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ExecutionStep {
    id: string;
    title: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    progress?: number;
    description?: string;
    details?: string[];
    timestamp?: Date;
    duration?: number;
    metadata?: Record<string, any>;
}

interface EnhancedExecutionViewProps {
    steps: ExecutionStep[];
    mode?: 'PLANNING' | 'EXECUTION' | 'VERIFICATION';
    taskName?: string;
}

export function EnhancedExecutionView({ steps, mode = 'EXECUTION', taskName }: EnhancedExecutionViewProps) {
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
    const [hoveredStep, setHoveredStep] = useState<string | null>(null);

    const toggleStep = (stepId: string) => {
        const newExpanded = new Set(expandedSteps);
        if (newExpanded.has(stepId)) {
            newExpanded.delete(stepId);
        } else {
            newExpanded.add(stepId);
        }
        setExpandedSteps(newExpanded);
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

    const getModeGradient = (mode: string) => {
        switch (mode) {
            case 'PLANNING':
                return 'from-blue-500 to-blue-600';
            case 'EXECUTION':
                return 'from-green-500 to-green-600';
            case 'VERIFICATION':
                return 'from-purple-500 to-purple-600';
            default:
                return 'from-gray-500 to-gray-600';
        }
    };

    return (
        <div className="flex flex-col h-full bg-gradient-to-br from-gray-50 to-gray-100">
            {/* Beautiful Header */}
            {taskName && (
                <div className={cn("p-6 bg-gradient-to-r text-white", getModeGradient(mode))}>
                    <div className="flex items-center gap-3">
                        <Zap className="w-6 h-6" />
                        <div>
                            <h2 className="text-xl font-bold">{taskName}</h2>
                            <p className="text-sm opacity-90 mt-1">{mode} Mode</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Steps Container */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {steps.map((step, index) => {
                    const isExpanded = expandedSteps.has(step.id);
                    const hasDetails = step.details && step.details.length > 0;
                    const isHovered = hoveredStep === step.id;

                    return (
                        <div
                            key={step.id}
                            className={cn(
                                "group relative rounded-xl transition-all duration-300 transform",
                                isHovered && "scale-[1.02]",
                                step.status === 'running' && "shadow-lg shadow-blue-500/20",
                                step.status === 'completed' && "shadow-md shadow-green-500/10",
                                step.status === 'error' && "shadow-md shadow-red-500/20"
                            )}
                            onMouseEnter={() => setHoveredStep(step.id)}
                            onMouseLeave={() => setHoveredStep(null)}
                        >
                            {/* Timeline Connector */}
                            {index < steps.length - 1 && (
                                <div className="absolute left-[22px] top-[60px] w-0.5 h-8 bg-gradient-to-b from-gray-300 to-transparent" />
                            )}

                            {/* Main Step Card */}
                            <div
                                className={cn(
                                    "relative rounded-xl border-2 p-4 backdrop-blur-sm transition-all duration-300",
                                    step.status === 'completed' && "bg-white/90 border-green-200 hover:border-green-300",
                                    step.status === 'running' && "bg-blue-50/90 border-blue-300 hover:border-blue-400",
                                    step.status === 'error' && "bg-red-50/90 border-red-300 hover:border-red-400",
                                    step.status === 'pending' && "bg-white/70 border-gray-200 hover:border-gray-300"
                                )}
                                onClick={() => hasDetails && toggleStep(step.id)}
                                style={{ cursor: hasDetails ? 'pointer' : 'default' }}
                            >
                                {/* Status Indicator Pulse */}
                                {step.status === 'running' && (
                                    <div className="absolute -left-1 -top-1 w-3 h-3">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                                    </div>
                                )}

                                <div className="flex items-start gap-4">
                                    {/* Icon */}
                                    <div className="flex-shrink-0 mt-0.5">
                                        {getStatusIcon(step.status)}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                {hasDetails && (
                                                    <button className="p-1 hover:bg-gray-200/50 rounded transition-colors">
                                                        {isExpanded ? (
                                                            <ChevronDown className="w-4 h-4 text-gray-600" />
                                                        ) : (
                                                            <ChevronRight className="w-4 h-4 text-gray-600" />
                                                        )}
                                                    </button>
                                                )}
                                                <h4 className={cn(
                                                    "font-semibold text-sm",
                                                    step.status === 'running' && "text-blue-700",
                                                    step.status === 'completed' && "text-green-700",
                                                    step.status === 'error' && "text-red-700",
                                                    step.status === 'pending' && "text-gray-600"
                                                )}>
                                                    {step.title}
                                                </h4>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                {step.duration && (
                                                    <div className="flex items-center gap-1 text-xs text-gray-500">
                                                        <Clock className="w-3 h-3" />
                                                        {step.duration}ms
                                                    </div>
                                                )}
                                                {step.timestamp && (
                                                    <span className="text-xs text-gray-400">
                                                        {step.timestamp.toLocaleTimeString()}
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        {step.description && (
                                            <p className="text-xs text-gray-600 mb-2">{step.description}</p>
                                        )}

                                        {/* Beautiful Progress Bar */}
                                        {step.progress !== undefined && step.status === 'running' && (
                                            <div className="mt-3">
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="text-xs font-medium text-blue-600">Processing...</span>
                                                    <span className="text-xs font-bold text-blue-700">{step.progress}%</span>
                                                </div>
                                                <div className="relative h-2 bg-blue-100 rounded-full overflow-hidden">
                                                    <div
                                                        className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500 ease-out"
                                                        style={{ width: `${step.progress}%` }}
                                                    >
                                                        <div className="absolute inset-0 bg-white/30 animate-pulse"></div>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Metadata Badges */}
                                        {step.metadata && Object.keys(step.metadata).length > 0 && (
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                {Object.entries(step.metadata).map(([key, value]) => (
                                                    <span
                                                        key={key}
                                                        className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
                                                    >
                                                        {key}: {String(value)}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Expandable Details */}
                                {hasDetails && isExpanded && (
                                    <div className="mt-4 pt-4 border-t border-gray-200/60 animate-in slide-in-from-top-2 duration-300">
                                        <div className="space-y-2">
                                            {step.details!.map((detail, idx) => (
                                                <div
                                                    key={idx}
                                                    className="flex items-start gap-2 text-xs text-gray-600 bg-gray-50/50 rounded-lg p-2"
                                                >
                                                    <Code className="w-3 h-3 mt-0.5 flex-shrink-0 text-gray-400" />
                                                    <span className="font-mono">{detail}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Beautiful Footer Summary */}
            <div className="flex-shrink-0 border-t border-gray-200 bg-white/80 backdrop-blur-sm p-4">
                <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-green-500" />
                            <span className="text-gray-600">
                                {steps.filter(s => s.status === 'completed').length} completed
                            </span>
                        </div>
                        {steps.some(s => s.status === 'running') && (
                            <div className="flex items-center gap-2">
                                <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                                <span className="text-blue-600 font-medium">
                                    {steps.filter(s => s.status === 'running').length} in progress
                                </span>
                            </div>
                        )}
                        {steps.some(s => s.status === 'error') && (
                            <div className="flex items-center gap-2">
                                <AlertCircle className="w-4 h-4 text-red-500" />
                                <span className="text-red-600">
                                    {steps.filter(s => s.status === 'error').length} failed
                                </span>
                            </div>
                        )}
                    </div>
                    <span className="text-xs text-gray-400">
                        Total: {steps.length} steps
                    </span>
                </div>
            </div>
        </div>
    );
}
