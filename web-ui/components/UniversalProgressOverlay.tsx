'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
    X,
    Minus,
    Maximize2,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Play,
    BookOpen,
    Search,
    FileText,
    Database,
    Activity,
    Terminal
} from 'lucide-react';
import { cn } from '../lib/utils';

interface ProgressStep {
    id: string;
    name: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    description?: string;
    progress?: number;
}

interface UniversalProgressOverlayProps {
    jobId: string | null;
    title: string;
    type?: 'thesis' | 'general' | 'analysis';
    onClose: () => void;
    backendUrl?: string;
}

export default function UniversalProgressOverlay({
    jobId,
    title,
    type = 'general',
    onClose,
    backendUrl = 'http://127.0.0.1:8000'
}: UniversalProgressOverlayProps) {
    const [isMinimized, setIsMinimized] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [currentStatus, setCurrentStatus] = useState('Connecting to AntiGravity engine...');
    const [currentAgent, setCurrentAgent] = useState('');
    const [overallProgress, setOverallProgress] = useState(0);
    const [expectedTotalSteps, setExpectedTotalSteps] = useState<number | null>(null);
    const [progressOverride, setProgressOverride] = useState<number | null>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [isComplete, setIsComplete] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [steps, setSteps] = useState<ProgressStep[]>([]);

    // Draggable State
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

    const eventSourceRef = useRef<EventSource | null>(null);
    const logsEndRef = useRef<HTMLDivElement>(null);
    const overlayRef = useRef<HTMLDivElement>(null);

    // Handle Dragging
    const handleMouseDown = (e: React.MouseEvent) => {
        // Only drag from header, ignore buttons
        if ((e.target as HTMLElement).closest('button')) return;

        setIsDragging(true);
        setDragStart({
            x: e.clientX - position.x,
            y: e.clientY - position.y
        });
    };

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging) return;

            setPosition({
                x: e.clientX - dragStart.x,
                y: e.clientY - dragStart.y
            });
        };

        const handleMouseUp = () => {
            setIsDragging(false);
        };

        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        }

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, dragStart]);

    // Initialize steps based on job type
    useEffect(() => {
        setOverallProgress(0);
        setExpectedTotalSteps(null);
        setProgressOverride(null);
        setIsComplete(false);
        setError(null);

        if (type === 'thesis') {
            setSteps([]);
        } else {
            setSteps([
                { id: 'understand', name: 'Understanding Objective', status: 'pending', description: 'Analyzing intent and planning actions' },
                { id: 'research', name: 'Gathering Information', status: 'pending', description: 'Searching web and academic databases' },
                { id: 'action', name: 'Executing Actions', status: 'pending', description: 'Generating content or performing analysis' },
                { id: 'verify', name: 'Verifying Results', status: 'pending', description: 'Reviewing quality and consistency' },
            ]);
        }
    }, [type, jobId]);

    const upsertStep = (incoming: ProgressStep) => {
        setSteps(prev => {
            const next = [...prev];
            const idx = next.findIndex(step => step.id === incoming.id);
            if (idx >= 0) {
                next[idx] = { ...next[idx], ...incoming };
            } else {
                next.push(incoming);
            }
            return next.sort((a, b) => {
                const aNum = parseInt(a.id.replace(/\D+/g, ''), 10);
                const bNum = parseInt(b.id.replace(/\D+/g, ''), 10);
                if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) return aNum - bNum;
                return a.id.localeCompare(b.id);
            });
        });
    };

    // Auto-scroll logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    useEffect(() => {
        const completedCount = steps.filter(s => s.status === 'completed').length;
        const denominator = expectedTotalSteps || Math.max(steps.length, 1);
        const computed = Math.round((completedCount / denominator) * 100);
        const nextProgress = progressOverride !== null
            ? Math.max(progressOverride, computed)
            : computed;
        setOverallProgress(Math.min(100, Math.max(0, nextProgress)));
    }, [steps, expectedTotalSteps, progressOverride]);

    useEffect(() => {
        if (!expectedTotalSteps) return;
        const completedCount = steps.filter(s => s.status === 'completed').length;
        if (completedCount >= expectedTotalSteps && !error) {
            setIsComplete(true);
            setCurrentStatus('🎉 All tasks completed successfully');
        }
    }, [steps, expectedTotalSteps, error]);

    // Connect to SSE
    useEffect(() => {
        if (!jobId) return;

        const streamUrl = `${backendUrl}/api/stream/agent-actions?job_id=${jobId}`;
        console.log('🔌 Progress overlay connecting to:', streamUrl);

        const eventSource = new EventSource(streamUrl);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
            setIsConnected(true);
            addLog('📡 Connection established with backend');
        };

        const updateStepStatus = (stepId: string, status: 'running' | 'completed' | 'error', description?: string, name?: string) => {
            upsertStep({
                id: stepId,
                name: name || description || 'Step',
                status,
                description
            });
        };

        const parseEventData = (payload: any): any => {
            if (payload == null) return {};
            if (typeof payload === 'object') return payload;
            if (typeof payload !== 'string') return { message: String(payload) };
            const trimmed = payload.trim();
            if (!trimmed) return {};
            try {
                return JSON.parse(trimmed);
            } catch {
                return { message: trimmed };
            }
        };

        // Event listeners
        eventSource.addEventListener('agent_activity', (e: any) => {
            const data = parseEventData(e.data);
            setCurrentAgent(data.agent_name || data.agent || '');
            if (data.message) {
                setCurrentStatus(data.message);
                addLog(`🤖 ${data.agent_type}: ${data.message}`);
            }

            // Auto-map agent activity to general steps
            if (type === 'general') {
                if (data.agent_type === 'understanding') updateStepStatus('understand', 'running');
                if (data.agent_type === 'research') {
                    updateStepStatus('understand', 'completed');
                    updateStepStatus('research', 'running');
                }
                if (data.agent_type === 'action') {
                    updateStepStatus('research', 'completed');
                    updateStepStatus('action', 'running');
                }
                if (data.agent_type === 'verification') {
                    updateStepStatus('action', 'completed');
                    updateStepStatus('verify', 'running');
                }
            }
        });

        eventSource.addEventListener('step_started', (e: any) => {
            const data = parseEventData(e.data);
            if (type === 'thesis' && data.step) {
                if (data.total_steps) {
                    setExpectedTotalSteps(data.total_steps);
                }
                updateStepStatus(data.step.toString(), 'running', data.name, data.name);
            }
            addLog(`🚀 Starting: ${data.name || 'Next phase'}`);
        });

        eventSource.addEventListener('step_completed', (e: any) => {
            const data = parseEventData(e.data);
            if (type === 'thesis' && data.step) {
                updateStepStatus(data.step.toString(), 'completed', data.name, data.name);
            }
            addLog(`✅ Completed: ${data.name || 'Phase'}`);
        });

        eventSource.addEventListener('progress', (e: any) => {
            const data = parseEventData(e.data);
            const percent = data.percentage ?? data.percent;
            if (typeof percent === 'number') {
                setProgressOverride(Math.round(percent));
            }
            if (data.message) setCurrentStatus(data.message);
        });

        eventSource.addEventListener('log', (e: any) => {
            const data = parseEventData(e.data);
            if (data.message) addLog(data.message);
        });

        eventSource.addEventListener('agent_stream', (e: any) => {
            try {
                const data = parseEventData(e.data);
                if (data.agent === 'planner' && Array.isArray(data.metadata?.steps)) {
                    const plannerSteps = data.metadata.steps.map((step: any) => ({
                        id: step.id || step.name || `${step.icon || 'step'}-${Math.random().toString(36).slice(2)}`,
                        name: step.name || step.title || 'Step',
                        status: step.status === 'done' ? 'completed' : step.status === 'running' ? 'running' : step.status === 'error' ? 'error' : 'pending',
                        description: step.description
                    }));
                    setExpectedTotalSteps(plannerSteps.length);
                    setSteps(plannerSteps);
                }
            } catch (err) {
                console.error('Error parsing agent_stream event:', err);
            }
        });

        eventSource.addEventListener('error', (e: any) => {
            const data = parseEventData(e.data);
            const message = data.message || 'Workflow failed';
            setError(message);
            setCurrentStatus('❌ Error');
            addLog(`❌ ERROR: ${message}`);
        });

        eventSource.addEventListener('stage_completed', (e: any) => {
            const data = parseEventData(e.data);
            if (data.stage === 'complete' && data.status === 'success') {
                setIsComplete(true);
                setOverallProgress(100);
                setCurrentStatus('🎉 All tasks completed successfully');
                setSteps(prev => prev.map(s => ({ ...s, status: 'completed' as const })));
            }
        });

        eventSource.onerror = () => {
            setIsConnected(false);
        };

        return () => {
            eventSource.close();
        };
    }, [jobId, type, backendUrl]);

    const addLog = (message: string) => {
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setLogs(prev => [...prev.slice(-49), `[${time}] ${message}`]);
    };

    if (!jobId) return null;

    const StatusIcon = ({ status }: { status: ProgressStep['status'] }) => {
        switch (status) {
            case 'completed': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
            case 'running': return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
            case 'error': return <AlertCircle className="w-4 h-4 text-red-500" />;
            default: return <div className="w-4 h-4 border-2 border-slate-700 rounded-full" />;
        }
    };

    if (isMinimized) {
        return (
            <div
                className="fixed bottom-4 right-4 z-[100] group cursor-pointer"
                style={{ transform: `translate(${position.x}px, ${position.y}px)` }}
                onClick={() => setIsMinimized(false)}
            >
                <div className="bg-slate-900 border border-slate-700 rounded-full pl-4 pr-2 py-2 flex items-center gap-3 shadow-2xl hover:border-slate-500 transition-all">
                    <div className="flex items-center gap-2">
                        {!isComplete && !error && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                        {isComplete && <CheckCircle2 className="w-4 h-4 text-green-400" />}
                        {error && <AlertCircle className="w-4 h-4 text-red-400" />}
                        <span className="text-xs font-semibold text-slate-200">
                            {isComplete ? 'Execution Complete' : error ? 'Error Occurred' : `Processing... ${overallProgress}%`}
                        </span>
                    </div>
                    <button
                        onClick={(e) => { e.stopPropagation(); onClose(); }}
                        className="p-1 hover:bg-slate-800 rounded-full text-slate-500 hover:text-white transition-colors"
                    >
                        <X className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div
            ref={overlayRef}
            className="fixed bottom-4 right-4 z-[100] w-[420px] bg-slate-950 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col animate-in slide-in-from-bottom-5 duration-300"
            style={{
                transform: `translate(${position.x}px, ${position.y}px)`,
                cursor: isDragging ? 'grabbing' : 'auto'
            }}
        >
            {/* Header - Grabbable Area */}
            <div
                onMouseDown={handleMouseDown}
                className="bg-slate-900/50 px-4 py-3 flex items-center justify-between border-b border-slate-800 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <div className={cn("w-2 h-2 rounded-full", isConnected ? "bg-green-500" : "bg-red-500 animate-pulse")} />
                    <h3 className="text-xs font-bold text-slate-200 tracking-tight flex items-center gap-2">
                        <Activity className="w-3.5 h-3.5 text-blue-400" />
                        ANTIGRAVITY WORKFLOW
                    </h3>
                </div>
                <div className="flex items-center gap-1">
                    <button onClick={() => setIsMinimized(true)} className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 hover:text-white transition-colors">
                        <Minus className="w-4 h-4" />
                    </button>
                    <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 hover:text-white transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Progress Bar Area */}
            <div className="px-5 py-4 space-y-3 bg-slate-900/30">
                <div className="flex items-end justify-between mb-1">
                    <div className="space-y-0.5">
                        <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">Global Progress</p>
                        <p className="text-lg font-black text-slate-100 italic tabular-nums">{overallProgress}%</p>
                    </div>
                    <div className="text-right">
                        <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest text-right">Job Type</p>
                        <p className="text-xs font-bold text-blue-400 uppercase">{type}</p>
                    </div>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                        className={cn(
                            "h-full transition-all duration-700 ease-out relative",
                            isComplete ? "bg-green-500" : error ? "bg-red-500" : "bg-gradient-to-r from-blue-600 to-indigo-500"
                        )}
                        style={{ width: `${overallProgress}%` }}
                    >
                        {!isComplete && !error && (
                            <div className="absolute inset-0 bg-white/20 animate-shimmer" style={{ backgroundSize: '200% 100%', backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)' }} />
                        )}
                    </div>
                </div>
            </div>

            {/* Current Task Detail */}
            <div className="px-5 py-3 border-y border-slate-800 bg-slate-900/10">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                        <Terminal className="w-4 h-4 text-blue-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Current Pipeline Activity</p>
                        <p className="text-sm font-medium text-slate-200 truncate">{currentStatus}</p>
                    </div>
                </div>
            </div>

            {/* Steps List */}
            <div className="px-5 py-4 max-h-[180px] overflow-y-auto scrollbar-thin">
                <div className="space-y-3">
                    {steps.map((step) => (
                        <div key={step.id} className="flex gap-4">
                            <div className="flex flex-col items-center">
                                <StatusIcon status={step.status} />
                                <div className="w-[1px] h-full bg-slate-800 my-1" />
                            </div>
                            <div className="flex-1 pb-2">
                                <p className={cn(
                                    "text-xs font-bold leading-none mb-1",
                                    step.status === 'running' ? "text-blue-400" :
                                        step.status === 'completed' ? "text-green-400" :
                                            step.status === 'error' ? "text-red-400" : "text-slate-500"
                                )}>
                                    {step.name}
                                </p>
                                {step.description && (
                                    <p className="text-[10px] text-slate-500 line-clamp-1">{step.description}</p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Logs View */}
            <div className="mt-auto border-t border-slate-800 bg-black/40">
                <div className="px-4 py-2 flex items-center justify-between border-b border-slate-800/50">
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                        <div className="w-1 h-1 bg-blue-500 rounded-full animate-ping" />
                        Live Execution Log
                    </span>
                    <span className="text-[9px] text-slate-600 font-mono">{jobId.slice(0, 8)}...</span>
                </div>
                <div className="h-28 overflow-y-auto p-3 font-mono text-[10px] space-y-1 scrollbar-thin">
                    {logs.map((log, i) => (
                        <div key={i} className="text-slate-400 border-l border-slate-800 pl-2 leading-relaxed">
                            {log}
                        </div>
                    ))}
                    <div ref={logsEndRef} />
                </div>
            </div>

            {/* Footer Status */}
            {isComplete && (
                <div className="bg-green-500 px-4 py-2 flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                    <span className="text-[11px] font-black text-white uppercase tracking-tighter">Workflow Completed Successfully</span>
                </div>
            )}
            {error && (
                <div className="bg-red-500 px-4 py-2 flex items-center justify-center gap-2">
                    <AlertCircle className="w-3.5 h-3.5 text-white" />
                    <span className="text-[11px] font-black text-white uppercase tracking-tighter">Process Interrupted: Error</span>
                </div>
            )}
        </div>
    );
}
