'use client';

import React, { useState, useEffect } from 'react';
import {
    Plus,
    History,
    ChevronDown,
    Search,
    Play,
    Pause,
    Square,
    Clock,
    CheckCircle2,
    XCircle,
    AlertCircle,
    RefreshCw,
    Type,
    Minus
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';

interface Job {
    job_id: string;
    message: string;
    status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
    progress: number;
    current_step: string;
    created_at: string;
    updated_at: string;
}

interface TopMenuBarProps {
    workspaceId: string;
    onNewChat: () => void;
    onSelectJob: (jobId: string) => void;
    currentJobId?: string | null;
    chatTitle?: string;  // Add chat title prop
}

export function TopMenuBar({
    workspaceId,
    onNewChat,
    onSelectJob,
    currentJobId,
    chatTitle
}: TopMenuBarProps) {
    const [showHistory, setShowHistory] = useState(false);
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(false);
    const [activeJobs, setActiveJobs] = useState<Job[]>([]);
    const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>('medium');

    // Load font size preference from localStorage
    useEffect(() => {
        const saved = localStorage.getItem('ui-font-size');
        if (saved && ['small', 'medium', 'large'].includes(saved)) {
            setFontSize(saved as 'small' | 'medium' | 'large');
            applyFontSize(saved as 'small' | 'medium' | 'large');
        }
    }, []);

    const applyFontSize = (size: 'small' | 'medium' | 'large') => {
        const root = document.documentElement;
        const sizes = {
            small: { base: '14px', content: '13px', sm: '11px' },
            medium: { base: '16px', content: '15px', sm: '13px' },
            large: { base: '18px', content: '17px', sm: '15px' }
        };
        root.style.setProperty('--font-size-base', sizes[size].base);
        root.style.setProperty('--font-size-content', sizes[size].content);
        root.style.setProperty('--font-size-sm', sizes[size].sm);
        document.body.style.fontSize = sizes[size].base;
    };

    const cycleFontSize = () => {
        const order: Array<'small' | 'medium' | 'large'> = ['small', 'medium', 'large'];
        const currentIndex = order.indexOf(fontSize);
        const nextSize = order[(currentIndex + 1) % order.length];
        setFontSize(nextSize);
        applyFontSize(nextSize);
        localStorage.setItem('ui-font-size', nextSize);
    };

    const decreaseFontSize = () => {
        const order: Array<'small' | 'medium' | 'large'> = ['small', 'medium', 'large'];
        const currentIndex = order.indexOf(fontSize);
        if (currentIndex > 0) {
            const newSize = order[currentIndex - 1];
            setFontSize(newSize);
            applyFontSize(newSize);
            localStorage.setItem('ui-font-size', newSize);
        }
    };

    const increaseFontSize = () => {
        const order: Array<'small' | 'medium' | 'large'> = ['small', 'medium', 'large'];
        const currentIndex = order.indexOf(fontSize);
        if (currentIndex < order.length - 1) {
            const newSize = order[currentIndex + 1];
            setFontSize(newSize);
            applyFontSize(newSize);
            localStorage.setItem('ui-font-size', newSize);
        }
    };

    // Fetch jobs on mount and when dropdown opens
    useEffect(() => {
        if (showHistory) {
            fetchJobs();
        }
    }, [showHistory, workspaceId]);

    // Check for active jobs on mount
    useEffect(() => {
        checkActiveJobs();
        const interval = setInterval(checkActiveJobs, 10000); // Check every 10s
        return () => clearInterval(interval);
    }, [workspaceId]);

    const fetchJobs = async () => {
        setLoading(true);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/jobs?limit=20`);
            if (response.ok) {
                const data = await response.json();
                setJobs(data.jobs || []);
            }
        } catch (error) {
            console.error('Failed to fetch jobs:', error);
        } finally {
            setLoading(false);
        }
    };

    const checkActiveJobs = async () => {
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/jobs/active`);
            if (response.ok) {
                const data = await response.json();
                setActiveJobs(data.jobs || []);
            }
        } catch (error) {
            console.error('Failed to check active jobs:', error);
        }
    };

    const getStatusIcon = (status: Job['status']) => {
        switch (status) {
            case 'running':
                return <Play className="w-3 h-3 text-green-500 animate-pulse" />;
            case 'paused':
                return <Pause className="w-3 h-3 text-yellow-500" />;
            case 'completed':
                return <CheckCircle2 className="w-3 h-3 text-green-500" />;
            case 'failed':
                return <XCircle className="w-3 h-3 text-red-500" />;
            case 'cancelled':
                return <Square className="w-3 h-3 text-gray-500" />;
            case 'pending':
                return <Clock className="w-3 h-3 text-blue-500" />;
            default:
                return <AlertCircle className="w-3 h-3 text-gray-400" />;
        }
    };

    const formatTime = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    // Get display title - use chatTitle, first message, or workspace name
    const displayTitle = chatTitle || 'Thesis Workspace';

    return (
        <div className="h-12 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between px-4 z-50">
            {/* Left side - New Chat */}
            <div className="flex items-center gap-2">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onNewChat}
                    className="gap-2 text-sm font-medium"
                >
                    <Plus className="w-4 h-4" />
                    New Chat
                </Button>

                {/* Active Job Indicator */}
                {activeJobs.length > 0 && (
                    <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 rounded-full border border-green-500/20">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs text-green-600 dark:text-green-400">
                            {activeJobs.length} active
                        </span>
                    </div>
                )}
            </div>

            {/* Center - Chat Title (not workspace ID) */}
            <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground max-w-[300px] truncate">
                    {displayTitle}
                </span>
            </div>

            {/* Right side - History */}
            <div className="relative">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowHistory(!showHistory)}
                    className="gap-2 text-sm"
                >
                    <History className="w-4 h-4" />
                    Chat History
                    <ChevronDown className={cn(
                        "w-4 h-4 transition-transform",
                        showHistory && "rotate-180"
                    )} />
                </Button>

                {/* History Dropdown */}
                {showHistory && (
                    <div className="absolute right-0 top-full mt-2 w-96 max-h-[70vh] overflow-y-auto bg-background border rounded-lg shadow-lg z-[100]">
                        <div className="p-3 border-b flex items-center justify-between">
                            <span className="text-sm font-medium">Recent Chats</span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={fetchJobs}
                                disabled={loading}
                            >
                                <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                            </Button>
                        </div>

                        {loading ? (
                            <div className="p-8 text-center text-muted-foreground">
                                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                                Loading...
                            </div>
                        ) : jobs.length === 0 ? (
                            <div className="p-8 text-center text-muted-foreground">
                                <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                No chat history yet
                            </div>
                        ) : (
                            <div className="divide-y">
                                {jobs.map(job => (
                                    <button
                                        key={job.job_id}
                                        onClick={() => {
                                            onSelectJob(job.job_id);
                                            setShowHistory(false);
                                        }}
                                        className={cn(
                                            "w-full p-3 text-left hover:bg-accent transition-colors",
                                            currentJobId === job.job_id && "bg-accent"
                                        )}
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="mt-1">
                                                {getStatusIcon(job.status)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium truncate">
                                                    {job.message.slice(0, 60)}
                                                    {job.message.length > 60 && '...'}
                                                </p>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <span className="text-xs text-muted-foreground">
                                                        {formatTime(job.created_at)}
                                                    </span>
                                                    {job.status === 'running' && (
                                                        <span className="text-xs text-green-500">
                                                            {Math.round(job.progress * 100)}%
                                                        </span>
                                                    )}
                                                    {job.current_step && job.status === 'running' && (
                                                        <span className="text-xs text-muted-foreground truncate max-w-[150px]">
                                                            • {job.current_step}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Click outside to close */}
            {showHistory && (
                <div
                    className="fixed inset-0 z-[99]"
                    onClick={() => setShowHistory(false)}
                />
            )}
        </div>
    );
}
