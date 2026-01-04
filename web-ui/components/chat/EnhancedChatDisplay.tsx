'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { ProgressBar } from '../ui/ProgressBar';
import { ProcessPlanner } from '../ProcessPlanner';
import { Loader2, CheckCircle2, AlertCircle, MessageCircle, Zap, Eye, Sparkles, ChevronRight } from 'lucide-react';
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

  // Auto-scroll to bottom when new messages arrive or processing state changes
  useEffect(() => {
    if (autoScroll && messagesEndRef.current) {
      const timer = setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({
          behavior: messages.length > 5 ? 'smooth' : 'auto',
          block: 'end'
        });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [messages, autoScroll, isProcessing]);

  // Handle manual scroll to detect if user scrolled up
  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
      // If we are at the bottom (within 50px), enable auto-scroll
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

      // If user scrolls up significantly, disable auto-scroll
      if (!isAtBottom) {
        setAutoScroll(false);
      } else {
        setAutoScroll(true);
      }
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
        className="flex-1 overflow-y-auto px-4 md:px-8 py-10 space-y-10 scroll-smooth"
        style={{
          background: 'linear-gradient(to bottom, transparent, rgba(15, 98, 254, 0.02))',
        }}
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-8 max-w-md animate-in fade-in zoom-in duration-700">
              <div className="relative">
                <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full scale-150 animate-pulse" />
                <div className="relative w-24 h-24 mx-auto rounded-[2rem] bg-gradient-to-tr from-primary to-primary-foreground flex items-center justify-center shadow-2xl shadow-primary/20">
                  <Sparkles className="w-12 h-12 text-white animate-pulse" />
                </div>
              </div>
              <div className="space-y-3">
                <h3 className="text-3xl font-extrabold tracking-tight text-foreground">Premium Research Assistant</h3>
                <p className="text-muted-foreground text-lg leading-relaxed max-w-sm mx-auto">
                  Ready to assist with your PhD thesis, academic research, and complex data analysis.
                </p>
                <div className="flex flex-wrap justify-center gap-2 mt-6">
                  {['/uoj_phd', '@research', '/validate'].map(cmd => (
                    <Badge key={cmd} variant="secondary" className="px-3 py-1 bg-muted/50 text-muted-foreground font-mono">
                      {cmd}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'group flex gap-4 md:gap-8 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out',
                  message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
                )}
              >
                {/* Avatar with Shadow and Glow */}
                <div className={cn(
                  "flex-shrink-0 w-10 h-10 md:w-12 md:h-12 rounded-2xl flex items-center justify-center text-lg font-bold shadow-xl transition-all duration-300 group-hover:scale-110 group-hover:rotate-3",
                  message.type === 'user'
                    ? "bg-gradient-to-br from-primary to-blue-700 text-primary-foreground shadow-primary/20 ring-4 ring-primary/5"
                    : "bg-white dark:bg-zinc-900 border border-border/50 text-foreground ring-4 ring-black/5"
                )}>
                  {message.type === 'user' ? 'U' : (
                    message.agent ? getAgentIcon(message.agent) : <Zap className="w-5 h-5 text-primary" />
                  )}
                </div>

                {/* Message Body */}
                <div className={cn(
                  'flex flex-col gap-3 min-w-[200px] max-w-[85%] md:max-w-[80%]',
                  message.type === 'user' ? 'items-end' : 'items-start'
                )}>
                  {message.agent && message.type === 'assistant' && (
                    <div className="flex items-center gap-2 px-1 mb-1">
                      <Badge variant="outline" className="text-[10px] font-bold uppercase tracking-widest bg-primary/5 border-primary/20 text-primary py-0 px-2 rounded-full">
                        {message.agent} agent
                      </Badge>
                      {message.isStreaming && (
                        <div className="flex items-center gap-1.5 text-[10px] text-primary/80 font-semibold animate-pulse">
                          <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                          generating content...
                        </div>
                      )}
                    </div>
                  )}

                  <div className={cn(
                    'relative px-5 py-4 md:px-7 md:py-5 rounded-[1.75rem] transition-all duration-300',
                    message.type === 'user'
                      ? 'bg-gradient-to-br from-[#F8F9FA] to-[#F1F3F5] dark:from-[#2A2A2A] dark:to-[#222222] text-foreground rounded-tr-none shadow-sm hover:shadow-md'
                      : 'bg-[#FFFFFF] dark:bg-[#1C1C1E] border border-border/40 shadow-xl shadow-black/[0.03] rounded-tl-none hover:border-primary/20 hover:shadow-primary/5 backdrop-blur-sm'
                  )}>
                    <div className={cn(
                      'prose prose-sm md:prose-base dark:prose-invert max-w-none leading-[1.6] font-medium tracking-tight',
                      'prose-p:my-2 prose-headings:my-4 prose-pre:my-3 prose-pre:rounded-xl prose-pre:bg-zinc-950 prose-pre:border prose-pre:border-zinc-800'
                    )}>
                      {message.type === 'assistant' ? (
                        <MarkdownRenderer content={message.content} />
                      ) : (
                        <p className="whitespace-pre-wrap break-words">{message.content}</p>
                      )}
                    </div>

                    {/* Quick Reactions / Actions (Only for assistant) */}
                    {message.type === 'assistant' && !message.isStreaming && (
                      <div className="absolute -bottom-9 left-0 opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center gap-2 p-1 bg-background/80 backdrop-blur-md rounded-lg border border-border/40 shadow-sm translate-y-2 group-hover:translate-y-0">
                        <button className="p-1.5 hover:bg-muted rounded-md transition-colors" title="Copy">
                          <svg className="w-4 h-4 text-muted-foreground hover:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" /></svg>
                        </button>
                        <button className="p-1.5 hover:bg-muted rounded-md transition-colors" title="Regenerate">
                          <svg className="w-4 h-4 text-muted-foreground hover:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Metadata Display */}
                  {message.metadata && (
                    <div className="w-full mt-3 space-y-4 px-1 animate-in slide-in-from-top-2 duration-500">
                      {/* Progress - only show when actually progressing (> 0 and < 100) */}
                      {message.metadata.progress !== undefined && message.metadata.progress > 0 && message.metadata.progress < 100 && (
                        <div className="space-y-2 p-4 rounded-2xl bg-gradient-to-br from-primary/[0.03] to-primary/[0.08] border border-primary/10 shadow-inner">
                          <div className="flex items-center justify-between text-[11px] mb-1">
                            <span className="font-bold text-primary uppercase tracking-widest">Execution Progress</span>
                            <span className="font-mono bg-primary/10 px-1.5 py-0.5 rounded text-primary font-bold">{message.metadata.progress}%</span>
                          </div>
                          <ProgressBar percentage={message.metadata.progress} size="sm" variant="default" />
                        </div>
                      )}

                      {/* Reasoning */}
                      {message.metadata.reasoning && (
                        <details className="group overflow-hidden rounded-2xl border border-border/50 bg-muted/20">
                          <summary className="cursor-pointer list-none flex items-center justify-between px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground/60 hover:text-foreground hover:bg-muted/30 transition-all">
                            <div className="flex items-center gap-2">
                              <Eye className="w-3.5 h-3.5" />
                              Internal Reasoning Trace
                            </div>
                            <ChevronRight className="w-3.5 h-3.5 transition-transform group-open:rotate-90" />
                          </summary>
                          <div className="px-4 pb-4 pt-1 text-[13px] leading-relaxed italic text-muted-foreground border-t border-border/30 mt-1 animate-in fade-in duration-300">
                            {message.metadata.reasoning}
                          </div>
                        </details>
                      )}
                    </div>
                  )}

                  <div className="text-[10px] text-muted-foreground/40 font-bold uppercase tracking-widest px-2 mt-1">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}

            {/* Streaming Indicator - EXECUTING STATE */}
            {isProcessing && (
              <div className="flex gap-4 md:gap-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="flex-shrink-0 w-10 h-10 md:w-12 md:h-12 rounded-2xl flex items-center justify-center bg-white dark:bg-zinc-900 border border-primary/20 shadow-xl ring-4 ring-primary/5">
                  {currentAgent ? getAgentIcon(currentAgent) : <div className="w-2 h-2 rounded-full bg-primary animate-ping" />}
                </div>

                <div className="flex-1 max-w-[85%] md:max-w-[80%] space-y-6">
                  {currentAgent && (
                    <div className="space-y-4 animate-in fade-in duration-500">
                      <div className="flex items-center gap-3 px-1">
                        <Badge className="bg-primary/10 hover:bg-primary/20 text-primary border-none text-[10px] py-0.5 tracking-widest uppercase">
                          {currentAgent} Agent Active
                        </Badge>
                        <div className="flex gap-1">
                          <span className="w-1 h-1 rounded-full bg-primary/40 animate-bounce duration-700" />
                          <span className="w-1 h-1 rounded-full bg-primary/60 animate-bounce duration-700 delay-150" />
                          <span className="w-1 h-1 rounded-full bg-primary animate-bounce duration-700 delay-300" />
                        </div>
                      </div>

                      {currentAction && (
                        <div className="p-5 md:p-6 rounded-[2rem] bg-white dark:bg-[#1C1C1E] border border-primary/20 shadow-2xl shadow-primary/5 transition-all backdrop-blur-sm ring-1 ring-primary/10">
                          <div className="space-y-4">
                            <div className="font-bold text-sm md:text-base flex items-center gap-3 text-foreground tracking-tight">
                              <div className="relative flex h-3.5 w-3.5">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-30"></span>
                                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-primary"></span>
                              </div>
                              {currentAction}
                            </div>
                            {currentDescription && (
                              <p className="text-xs md:text-sm text-muted-foreground leading-relaxed pl-6.5 border-l-2 border-primary/10 ml-1.5 font-medium italic">
                                "{currentDescription}"
                              </p>
                            )}

                            {/* Progress Bar for active execution */}
                            {currentProgress > 0 && (
                              <div className="space-y-2 pt-4 mt-2 border-t border-border/30">
                                <div className="flex items-center justify-between text-[10px] font-extrabold uppercase tracking-widest text-primary/70">
                                  <span>Task completion</span>
                                  <span>{currentProgress}%</span>
                                </div>
                                <ProgressBar percentage={currentProgress} size="sm" variant="default" />
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Process Steps with enhanced layout */}
                  {processSteps.length > 0 && (
                    <div className="p-1 animate-in zoom-in-95 duration-500 delay-200">
                      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 mb-4 px-2">Execution Roadmap</div>
                      <ProcessPlanner steps={processSteps} />
                    </div>
                  )}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} className="h-10" />
          </>
        )}
      </div>

      {/* Scroll to bottom floating button - Premium Rounded */}
      {!autoScroll && messages.length > 0 && (
        <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <button
            onClick={() => {
              setAutoScroll(true);
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="flex items-center gap-3 px-6 py-3 rounded-full border border-primary/20 shadow-[0_20px_50px_rgba(15,98,254,0.3)] bg-white dark:bg-zinc-900 hover:bg-primary hover:text-white transition-all duration-300 active:scale-95 group overflow-hidden relative"
          >
            <div className="absolute inset-0 bg-primary/10 group-hover:bg-primary transition-colors duration-300" />
            <div className="relative flex items-center gap-2">
              <svg className="w-4 h-4 transition-transform duration-300 group-hover:translate-y-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
              <span className="text-sm font-bold tracking-tight">New Activity</span>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
