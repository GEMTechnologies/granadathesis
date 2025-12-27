'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { ProgressBar } from '../ui/ProgressBar';
import { ProcessPlanner } from '../ProcessPlanner';
import { Loader2, CheckCircle2, AlertCircle, MessageCircle, Zap, Eye, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';
import MarkdownRenderer from '../MarkdownRenderer';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  agent?: string;
  metadata?: {
    reasoning?: string;
    plan?: any[];
    progress?: number;
    status?: string;
  };
}

interface EnhancedChatDisplayProps {
  messages: ChatMessage[];
  isProcessing?: boolean;
  currentAgent?: string;
  currentAction?: string;
  currentDescription?: string;
  currentProgress?: number;
  processSteps?: any[];
  className?: string;
}

export function EnhancedChatDisplay({
  messages,
  isProcessing = false,
  currentAgent = '',
  currentAction = '',
  currentDescription = '',
  currentProgress = 0,
  processSteps = [],
  className = ''
}: EnhancedChatDisplayProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && messagesEndRef.current) {
      // Use a small timeout to ensure DOM has updated
      const timer = setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [messages, autoScroll, isProcessing]);

  // Handle manual scroll to detect if user scrolled up
  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setAutoScroll(isNearBottom);
    }
  };

  const getAgentIcon = (agent: string) => {
    const icons: { [key: string]: string } = {
      research: '🔬',
      writer: '📝',
      editor: '✏️',
      planner: '🧠',
      citation: '✓',
      search: '🔍'
    };
    return icons[agent.toLowerCase()] || '🤖';
  };

  return (
    <div
      className={cn(
        'flex flex-col h-full bg-[#FFFFFF] dark:bg-[#0B0B0B]',
        className
      )}
    >
      {/* Messages Container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 md:px-6 py-8 space-y-8 scroll-smooth"
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-6 max-w-sm">
              <div className="w-20 h-20 mx-auto rounded-3xl bg-gradient-to-tr from-primary/20 to-primary/5 flex items-center justify-center shadow-inner">
                <Sparkles className="w-10 h-10 text-primary animate-pulse" />
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold tracking-tight">How can I help you?</h3>
                <p className="text-muted-foreground leading-relaxed">
                  I can help you with your thesis, research papers, or any academic writing tasks.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'group flex gap-4 md:gap-6 animate-in fade-in slide-in-from-bottom-2 duration-500',
                  message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
                )}
              >
                {/* Avatar */}
                <div className={cn(
                  "flex-shrink-0 w-8 h-8 md:w-9 md:h-9 rounded-xl flex items-center justify-center text-sm font-medium shadow-sm transition-transform group-hover:scale-105",
                  message.type === 'user'
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted border border-border/40"
                )}>
                  {message.type === 'user' ? 'U' : (
                    message.agent ? getAgentIcon(message.agent) : <Zap className="w-4 h-4 text-primary" />
                  )}
                </div>

                {/* Message Body */}
                <div className={cn(
                  'flex flex-col gap-2 max-w-[85%] md:max-w-[75%]',
                  message.type === 'user' ? 'items-end' : 'items-start'
                )}>
                  {message.agent && message.type === 'assistant' && (
                    <div className="flex items-center gap-2 px-1">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/70">
                        {message.agent} agent
                      </span>
                      {message.isStreaming && (
                        <div className="flex items-center gap-1 text-[10px] text-primary/60">
                          <span className="w-1 h-1 rounded-full bg-primary animate-ping" />
                          writing...
                        </div>
                      )}
                    </div>
                  )}

                  <div className={cn(
                    'relative px-4 py-3 md:px-5 md:py-3.5 rounded-2xl transition-all',
                    message.type === 'user'
                      ? 'bg-[#F4F4F4] dark:bg-[#2F2F2F] text-foreground rounded-tr-none'
                      : 'bg-[#FFFFFF] dark:bg-[#1A1A1A] border border-border/50 shadow-sm rounded-tl-none hover:border-border/80'
                  )}>
                    <div className={cn(
                      'prose prose-sm md:prose-base dark:prose-invert max-w-none leading-relaxed',
                      'prose-p:my-1 prose-headings:my-2 prose-pre:my-2'
                    )}>
                      {message.type === 'assistant' ? (
                        <MarkdownRenderer content={message.content} />
                      ) : (
                        <p className="whitespace-pre-wrap break-words">{message.content}</p>
                      )}
                    </div>

                    {/* Quick Reactions / Actions (Only for assistant) */}
                    {message.type === 'assistant' && !message.isStreaming && (
                      <div className="absolute -bottom-7 left-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
                        <button className="p-1 hover:bg-muted rounded transition-colors" title="Copy">
                          <svg className="w-3.5 h-3.5 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" /></svg>
                        </button>
                        <button className="p-1 hover:bg-muted rounded transition-colors" title="Regenerate">
                          <svg className="w-3.5 h-3.5 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Metadata Display */}
                  {message.metadata && (
                    <div className="w-full mt-2 space-y-3 px-1">
                      {/* Progress - only show when actually progressing (> 0 and < 100) */}
                      {message.metadata.progress !== undefined && message.metadata.progress > 0 && message.metadata.progress < 100 && (
                        <div className="space-y-1.5 p-3 rounded-xl bg-primary/5 border border-primary/10">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-semibold text-primary">Progress</span>
                            <span className="font-mono">{message.metadata.progress}%</span>
                          </div>
                          <ProgressBar percentage={message.metadata.progress} size="xs" variant="default" />
                        </div>
                      )}

                      {/* Reasoning */}
                      {message.metadata.reasoning && (
                        <details className="group">
                          <summary className="cursor-pointer list-none flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground/60 hover:text-foreground transition-colors">
                            <Eye className="w-3 h-3 transition-transform group-open:rotate-180" />
                            Reasoning Process
                          </summary>
                          <div className="mt-2 p-4 rounded-xl bg-muted/30 border border-border/30 text-[13px] leading-relaxed italic text-muted-foreground">
                            {message.metadata.reasoning}
                          </div>
                        </details>
                      )}
                    </div>
                  )}

                  <div className="text-[10px] text-muted-foreground/50 font-medium px-1">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}

            {/* Streaming Indicator */}
            {isProcessing && (
              <div className="flex gap-4 md:gap-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
                <div className="flex-shrink-0 w-8 h-8 md:w-9 md:h-9 rounded-xl flex items-center justify-center bg-muted border border-border/40 text-lg shadow-sm">
                  {currentAgent ? getAgentIcon(currentAgent) : <Zap className="w-4 h-4 text-primary animate-pulse" />}
                </div>

                <div className="flex-1 max-w-[85%] md:max-w-[75%] space-y-4">
                  {currentAgent && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 px-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/70">
                          {currentAgent} agent is active
                        </span>
                        <div className="w-1 h-1 rounded-full bg-green-500 animate-pulse" />
                      </div>

                      {currentAction && (
                        <div className="p-4 rounded-2xl bg-[#FFFFFF] dark:bg-[#1A1A1A] border border-primary/20 shadow-sm transition-all hover:bg-primary/[0.02]">
                          <div className="space-y-3">
                            <div className="font-semibold text-sm flex items-center gap-2.5">
                              <div className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-20"></span>
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-primary/40"></span>
                              </div>
                              {currentAction}
                            </div>
                            {currentDescription && (
                              <p className="text-xs text-muted-foreground leading-relaxed pl-5.5">{currentDescription}</p>
                            )}

                            {/* Progress Bar */}
                            {currentProgress > 0 && (
                              <div className="space-y-1.5 pt-3 mt-1 border-t border-border/30">
                                <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
                                  <span>Task completion</span>
                                  <span>{currentProgress}%</span>
                                </div>
                                <ProgressBar percentage={currentProgress} size="xs" variant="default" />
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Process Steps */}
                  {processSteps.length > 0 && (
                    <div className="p-1">
                      <ProcessPlanner steps={processSteps} />
                    </div>
                  )}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Scroll to bottom floating button */}
      {!autoScroll && messages.length > 0 && (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-50 animate-in fade-in zoom-in duration-300">
          <button
            onClick={() => {
              setAutoScroll(true);
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-full border border-border shadow-2xl bg-background hover:bg-muted transition-all active:scale-95 group"
          >
            <svg className="w-4 h-4 text-primary transition-transform group-hover:translate-y-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <span className="text-sm font-medium">New messages</span>
          </button>
        </div>
      )}
    </div>
  );
}
