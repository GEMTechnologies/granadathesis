'use client';

import React from 'react';
import { cn } from '../../lib/utils';

interface AgentActivity {
    agent: string;
    agent_name: string;
    status: 'running' | 'completed' | 'idle';
    action: string;
    icon: string;
}

interface AgentActivityBadgeProps {
    activity: AgentActivity;
    onClick?: () => void;
    isActive?: boolean;
}

const agentColors: Record<string, { bg: string; text: string; border: string }> = {
    planner: { bg: 'rgba(168, 85, 247, 0.15)', text: '#a855f7', border: '#a855f7' },
    internet_search: { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', border: '#3b82f6' },
    writer: { bg: 'rgba(34, 197, 94, 0.15)', text: '#22c55e', border: '#22c55e' },
    editor: { bg: 'rgba(249, 115, 22, 0.15)', text: '#f97316', border: '#f97316' },
    researcher: { bg: 'rgba(236, 72, 153, 0.15)', text: '#ec4899', border: '#ec4899' },
    search: { bg: 'rgba(14, 165, 233, 0.15)', text: '#0ea5e9', border: '#0ea5e9' },
};

export function AgentActivityBadge({ activity, onClick, isActive = false }: AgentActivityBadgeProps) {
    const colors = agentColors[activity.agent] || { bg: 'rgba(107, 114, 128, 0.15)', text: '#6b7280', border: '#6b7280' };
    const isRunning = activity.status === 'running';

    return (
        <button
            onClick={onClick}
            className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all",
                "hover:scale-105 cursor-pointer border",
                isRunning && "animate-pulse"
            )}
            style={{
                backgroundColor: colors.bg,
                color: colors.text,
                borderColor: isActive ? colors.border : 'transparent',
            }}
            title={`${activity.agent_name}: ${activity.action}`}
        >
            <span className="text-sm">{activity.icon}</span>
            <span>{activity.agent_name}</span>
            {isRunning && (
                <span className="relative flex h-2 w-2">
                    <span
                        className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                        style={{ backgroundColor: colors.text }}
                    />
                    <span
                        className="relative inline-flex rounded-full h-2 w-2"
                        style={{ backgroundColor: colors.text }}
                    />
                </span>
            )}
            {activity.status === 'completed' && (
                <span className="text-green-500">✓</span>
            )}
        </button>
    );
}

interface AgentActivityTrackerProps {
    activities: AgentActivity[];
    activeAgentId?: string | null;
    onAgentClick?: (agentId: string) => void;
}

export function AgentActivityTracker({ activities, activeAgentId, onAgentClick }: AgentActivityTrackerProps) {
    if (activities.length === 0) return null;

    return (
        <div className="flex flex-wrap items-center gap-2 px-4 py-2 border-b"
            style={{ borderColor: 'var(--color-border, #E0E0E0)', backgroundColor: 'rgba(0,0,0,0.02)' }}>
            <span className="text-xs text-gray-500 mr-2">Agents:</span>
            {activities.map((activity) => (
                <AgentActivityBadge
                    key={activity.agent}
                    activity={activity}
                    isActive={activeAgentId === activity.agent}
                    onClick={() => onAgentClick?.(activity.agent)}
                />
            ))}
        </div>
    );
}

export default AgentActivityBadge;
