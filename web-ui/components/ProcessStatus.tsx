'use client';

import React, { useState } from 'react';
import { Loader2, CheckCircle2, AlertCircle, Clock, Zap, Brain, FileText, Search, Edit, CheckSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from './ui/card';
import { Badge } from './ui/badge';

interface StatusUpdate {
  timestamp: Date;
  agent: string;
  action: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  icon?: React.ReactNode;
}

interface ProcessStatusProps {
  currentAgent?: string;
  currentAction?: string;
  currentDescription?: string;
  isProcessing?: boolean;
  statusUpdates?: StatusUpdate[];
  progress?: number;
  estimatedTimeRemaining?: number;
}

const agentIcons: Record<string, React.ReactNode> = {
  'research': <Search className="w-5 h-5" />,
  'writer': <FileText className="w-5 h-5" />,
  'editor': <Edit className="w-5 h-5" />,
  'planner': <Brain className="w-5 h-5" />,
  'citation': <CheckSquare className="w-5 h-5" />,
  'search': <Search className="w-5 h-5" />,
};

const getAgentColor = (agent: string) => {
  const colors: Record<string, string> = {
    'research': 'from-blue-500 to-blue-600',
    'writer': 'from-purple-500 to-purple-600',
    'editor': 'from-green-500 to-green-600',
    'planner': 'from-indigo-500 to-indigo-600',
    'citation': 'from-amber-500 to-amber-600',
    'search': 'from-cyan-500 to-cyan-600',
  };
  return colors[agent.toLowerCase()] || 'from-gray-500 to-gray-600';
};

export function ProcessStatus({
  currentAgent,
  currentAction,
  currentDescription,
  isProcessing = false,
  statusUpdates = [],
  progress = 0,
  estimatedTimeRemaining
}: ProcessStatusProps) {
  const [expanded, setExpanded] = useState(true);

  const formatTime = (seconds?: number) => {
    if (!seconds) return null;
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-3">
      {/* Current Status Card */}
      {isProcessing && currentAgent && (
        <Card className="overflow-hidden border-0 shadow-lg bg-gradient-to-r" style={{
          backgroundImage: `linear-gradient(to right, var(--tw-gradient-stops))`,
          '--tw-gradient-from': 'rgba(15, 98, 254, 0.1)',
          '--tw-gradient-to': 'rgba(15, 98, 254, 0.05)',
        } as React.CSSProperties}>
          <div className="p-4 space-y-3">
            {/* Agent Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 flex-1">
                <div className="mt-1 p-2 rounded-lg" style={{
                  backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
                }}>
                  {agentIcons[currentAgent.toLowerCase()] || <Zap className="w-5 h-5" style={{ color: 'var(--color-primary, #0F62FE)' }} />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-bold" style={{ color: 'var(--color-text, #161616)' }}>
                      {currentAgent.charAt(0).toUpperCase() + currentAgent.slice(1)} Agent
                    </h3>
                    {isProcessing && (
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" style={{ animationDelay: '0.2s' }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" style={{ animationDelay: '0.4s' }} />
                      </div>
                    )}
                  </div>
                  <p className="text-xs font-semibold" style={{ color: 'var(--color-primary, #0F62FE)' }}>
                    {currentAction}
                  </p>
                </div>
              </div>
              <Badge className="bg-blue-100 text-blue-700 border-0">
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                Running
              </Badge>
            </div>

            {/* Description */}
            {currentDescription && (
              <p className="text-sm" style={{ color: 'var(--color-text-secondary, #525252)' }}>
                {currentDescription}
              </p>
            )}

            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                  Progress
                </span>
                <span className="text-xs font-bold" style={{ color: 'var(--color-primary, #0F62FE)' }}>
                  {Math.round(progress)}%
                </span>
              </div>
              <div className="w-full h-2 rounded-full" style={{
                backgroundColor: 'rgba(0, 0, 0, 0.1)',
              }}>
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${Math.min(progress, 100)}%`,
                    backgroundColor: 'var(--color-primary, #0F62FE)',
                  }}
                />
              </div>
            </div>

            {/* Estimated Time */}
            {estimatedTimeRemaining && (
              <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                <Clock className="w-3.5 h-3.5" />
                <span>Est. time remaining: {formatTime(estimatedTimeRemaining)}</span>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Status History */}
      {statusUpdates.length > 0 && (
        <Card className="bg-white dark:bg-gray-950">
          <div className="p-4">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center justify-between w-full mb-3 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-gray-900 p-2 rounded transition-colors"
              style={{ color: 'var(--color-text, #161616)' }}
            >
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--color-success, #24A148)' }} />
                Recent Activity ({statusUpdates.length})
              </span>
              <span>{expanded ? '−' : '+'}</span>
            </button>

            {expanded && (
              <div className="space-y-2">
                {statusUpdates.slice(-5).reverse().map((update, idx) => (
                  <div
                    key={idx}
                    className="flex gap-3 p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors"
                  >
                    {/* Status Icon */}
                    <div className="flex-shrink-0 mt-0.5">
                      {update.status === 'completed' && (
                        <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--color-success, #24A148)' }} />
                      )}
                      {update.status === 'running' && (
                        <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--color-primary, #0F62FE)' }} />
                      )}
                      {update.status === 'error' && (
                        <AlertCircle className="w-4 h-4" style={{ color: 'var(--color-danger, #DA1E28)' }} />
                      )}
                      {update.status === 'pending' && (
                        <Clock className="w-4 h-4" style={{ color: 'var(--color-text-muted, #8D8D8D)' }} />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{
                          backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
                          color: 'var(--color-primary, #0F62FE)',
                        }}>
                          {update.agent}
                        </span>
                        <span className="text-xs font-medium" style={{ color: 'var(--color-text, #161616)' }}>
                          {update.action}
                        </span>
                      </div>
                      {update.description && (
                        <p className="text-xs mt-1 truncate" style={{ color: 'var(--color-text-secondary, #525252)' }}>
                          {update.description}
                        </p>
                      )}
                      <span className="text-xs mt-1" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                        {update.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
