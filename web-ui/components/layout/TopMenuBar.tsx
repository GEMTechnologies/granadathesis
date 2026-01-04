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
    Minus,
    MessageCircle,
    Trash2
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { ThemeToggle } from '../ui/ThemeToggle';

interface Conversation {
    conversation_id: string;
    title: string;
    updated_at: string;
    summary?: string;
    total_messages: number;
}

interface TopMenuBarProps {
    workspaceId: string;
    onNewChat: () => void;
    onSelectHistoryItem: (id: string, type: 'job' | 'conversation') => void;
    currentHistoryId?: string | null;
    chatTitle?: string;
}

export function TopMenuBar({
    workspaceId,
    onNewChat,
    onSelectHistoryItem,
    currentHistoryId,
    chatTitle
}: TopMenuBarProps) {
    const [showHistory, setShowHistory] = useState(false);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [loading, setLoading] = useState(false);
    const [activeJobs, setActiveJobs] = useState<any[]>([]);
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

    // Fetch conversations on mount and when dropdown opens
    useEffect(() => {
        if (showHistory) {
            fetchConversations();
        }
    }, [showHistory, workspaceId]);

    // Check for active jobs on mount
    useEffect(() => {
        checkActiveJobs();
        const interval = setInterval(checkActiveJobs, 10000); // Check every 10s
        return () => clearInterval(interval);
    }, [workspaceId]);

    const fetchConversations = async () => {
        setLoading(true);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
            const response = await fetch(`${backendUrl}/api/sessions/list`);
            if (response.ok) {
                const data = await response.json();
                setConversations(data.conversations || []);
            }
        } catch (error) {
            console.error('Failed to fetch conversations:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        if (!confirm('Are you sure you want to delete this chat and all its files?')) return;

        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
            const response = await fetch(`${backendUrl}/api/session/${id}`, { method: 'DELETE' });
            if (response.ok) {
                if (currentHistoryId === id) {
                    onNewChat();
                }
                fetchConversations();
            }
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    };

    const handleClearAll = async () => {
        if (!confirm('Are you sure you want to delete ALL chat history and ALL associated files? This cannot be undone.')) return;

        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
            const response = await fetch(`${backendUrl}/api/sessions/clear`, { method: 'DELETE' });
            if (response.ok) {
                onNewChat();
                fetchConversations();
            }
        } catch (error) {
            console.error('Failed to clear sessions:', error);
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

    const formatTime = (dateString: string) => {
        if (!dateString) return '';
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

            {/* Right side - History & Theme */}
            <div className="flex items-center gap-2">
                <ThemeToggle />
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
                                    onClick={fetchConversations}
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
                            ) : conversations.length === 0 ? (
                                <div className="p-8 text-center text-muted-foreground">
                                    <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    No chat history yet
                                </div>
                            ) : (
                                <div className="divide-y">
                                    {conversations.map(conv => (
                                        <div key={conv.conversation_id} className="group relative">
                                            <button
                                                onClick={() => {
                                                    onSelectHistoryItem(conv.conversation_id, 'conversation');
                                                    setShowHistory(false);
                                                }}
                                                className={cn(
                                                    "w-full p-3 pr-12 text-left hover:bg-accent transition-colors",
                                                    currentHistoryId === conv.conversation_id && "bg-accent"
                                                )}
                                            >
                                                <div className="flex items-start gap-3">
                                                    <div className="mt-1">
                                                        <MessageCircle className="w-4 h-4 text-primary opacity-70" />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-sm font-medium truncate">
                                                            {conv.title}
                                                        </p>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <span className="text-xs text-muted-foreground">
                                                                {formatTime(conv.updated_at)}
                                                            </span>
                                                            <span className="text-xs text-muted-foreground">
                                                                • {conv.total_messages} messages
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={(e) => handleDeleteConversation(e, conv.conversation_id)}
                                                className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive p-2 h-auto"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    ))}
                                    <div className="p-2 bg-accent/30 border-t">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleClearAll}
                                            className="w-full text-destructive hover:bg-destructive/10 gap-2"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                            Clear All History
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
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
