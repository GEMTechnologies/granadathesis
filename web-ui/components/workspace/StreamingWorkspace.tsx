'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ProcessPlanner, ProcessStep } from '../ProcessPlanner';
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Terminal,
  FileCode,
  Brain,
  MessageSquare,
  Play,
  Edit2,
  X,
  Save,
  FileText,
  Code2,
  Image as ImageIcon,
  Globe,
  File,
  Sparkles,
  Copy,
  Download,
  ExternalLink,
  PlayCircle,
  BarChart3,
  Eye,
  Trash2,
  Edit,
  Search,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { cn } from '../../lib/utils';
import { SearchResultDisplay } from './SearchResultDisplay';
import { MarkdownRenderer } from '../MarkdownRenderer';
import { ImageGallery } from './ImageGallery';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Separator } from '../ui/separator';

import { CopyButton } from '../ui/CopyButton';

export interface AgentAction {
  id: string;
  type: 'file_write' | 'file_read' | 'pdf_read' | 'browser_action' | 'code_execution' |
  'research_result' | 'file_diff' | 'data_analysis' | 'chart' | 'log' | 'tool_call' | 'stream' | 'user_message' | 'thinking';
  timestamp: Date;
  title: string;
  content?: string;
  metadata?: Record<string, any>;
  status?: 'pending' | 'running' | 'completed' | 'error';
  isStreaming?: boolean;
}

interface StreamingWorkspaceProps {
  actions?: AgentAction[];
  onActionClick?: (action: AgentAction) => void;
  autoScroll?: boolean;
  sessionId?: string;
  enableSSE?: boolean;
  onClear?: () => void;
  onActionUpdate?: (actionId: string, updates: Partial<AgentAction>) => void;
  workspaceId?: string;
}

export function StreamingWorkspace({
  actions: externalActions,
  onActionClick,
  autoScroll = true,
  sessionId = 'default',
  enableSSE = true,
  onClear,
  onActionUpdate,
  workspaceId = 'default'
}: StreamingWorkspaceProps) {
  const scrollEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  // Fixed: Initialize empty to prevent flashing stale data from parent
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [editingAction, setEditingAction] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>('');
  const [executingCode, setExecutingCode] = useState<string | null>(null);
  const [expandedActions, setExpandedActions] = useState<Set<string>>(new Set());
  const [editingActions, setEditingActions] = useState<Map<string, string>>(new Map());
  const [processSteps, setProcessSteps] = useState<ProcessStep[]>([]);
  const [totalProgress, setTotalProgress] = useState<number>(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const maxReconnectAttempts = 10;

  // Sync external actions
  useEffect(() => {
    if (externalActions) {
      setActions(externalActions);
    }
  }, [externalActions]);

  // Auto-scroll when new content arrives
  useEffect(() => {
    if (autoScroll && scrollEndRef.current) {
      // Smooth scroll to bottom when actions update
      scrollEndRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [actions, autoScroll]);

  // Connect to SSE stream
  useEffect(() => {
    if (!enableSSE) return;

    const connectStream = () => {
      // Clear any pending reconnect
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Close existing connection if any
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Connect directly to backend (SSE doesn't work well with Next.js proxy)
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      // Only connect if we have a job_id from parent component or URL
      const urlParams = new URLSearchParams(window.location.search);
      const urlJobId = urlParams.get('job_id');

      // Check if parent component passed a job_id via props or context
      // For now, we'll rely on the parent component (ManusStyleLayout) to manage SSE connections
      // StreamingWorkspace will receive actions via props from the parent

      // Don't auto-connect to old jobs on page load - only connect when explicitly requested
      if (!urlJobId && !externalActions?.length) {
        // This is expected - parent will manage connections
        return;
      }

      // If we have a job_id in URL, connect to that stream
      const jobId = urlJobId;

      const streamUrl = `${backendUrl}/api/stream/agent-actions?session_id=${sessionId}&job_id=${jobId}`;

      console.log(`🔗 Connecting to SSE stream: ${streamUrl}`);
      const eventSource = new EventSource(streamUrl);

      eventSource.onopen = () => {
        console.log('SSE stream connected');
        reconnectAttemptsRef.current = 0; // Reset on successful connection
      };

      eventSource.addEventListener('connected', (e) => {
        console.log('Stream connected:', JSON.parse(e.data));
      });

      eventSource.addEventListener('action', (e) => {
        try {
          const actionData = JSON.parse(e.data);
          const action: AgentAction = {
            id: actionData.id || `action-${Date.now()}`,
            type: actionData.type || 'stream',
            timestamp: new Date(actionData.timestamp * 1000 || Date.now()),
            title: actionData.title || 'Agent Action',
            content: actionData.content,
            metadata: actionData.metadata,
            status: actionData.status || 'completed',
            isStreaming: actionData.is_streaming || false,
          };
          setActions(prev => [...prev, action]);
        } catch (error) {
          console.error('Error parsing action:', error);
        }
      });

      // Handle keepalive events (prevent connection timeout)
      eventSource.addEventListener('keepalive', (e) => {
        // Silently acknowledge keepalive
      });

      // Handle log events (real-time updates) - FILTERED to avoid spam
      eventSource.addEventListener('log', (e) => {
        try {
          const logData = JSON.parse(e.data);
          const message = logData.message || '';

          // Skip spam messages
          const skipPatterns = [
            /^progress$/i,
            /^completed$/i,
            /^\d+%/,
            /^step \d/i,
            /^processing/i,
            /^working/i,
            /^generating\.{0,3}$/i,
          ];

          const isSpam = skipPatterns.some(pattern => pattern.test(message.trim()));
          if (isSpam || message.length < 10) {
            return; // Skip spam
          }

          // Only show meaningful milestone messages
          const isMilestone =
            message.includes('✅') ||
            message.includes('❌') ||
            message.includes('📄') ||
            message.includes('Chapter') ||
            message.includes('generated') ||
            message.includes('saved') ||
            message.includes('created') ||
            message.includes('Starting') ||
            logData.level === 'error';

          if (!isMilestone) return;

          const logAction: AgentAction = {
            id: `log-${Date.now()}-${Math.random()}`,
            type: 'log',
            timestamp: new Date(),
            title: message.substring(0, 60) + (message.length > 60 ? '...' : ''),
            content: message.length > 60 ? message : undefined,
            metadata: { level: logData.level || 'info' },
            status: logData.level === 'error' ? 'error' : 'completed',
          };
          setActions(prev => [...prev, logAction]);
        } catch (error) {
          console.error('Error parsing log:', error);
        }
      });

      // Handle reasoning_chunk events (streaming AI thinking)
      eventSource.addEventListener('reasoning_chunk', (e) => {
        try {
          const chunkData = JSON.parse(e.data);
          const chunk = chunkData.chunk || '';
          const accumulated = chunkData.accumulated || '';

          // Find or create reasoning action
          setActions(prev => {
            const existingIndex = prev.findIndex(
              action => action.type === 'thinking' && action.status === 'running'
            );

            if (existingIndex >= 0) {
              // Update existing reasoning action
              const updated = [...prev];
              updated[existingIndex] = {
                ...updated[existingIndex],
                content: accumulated,
                isStreaming: true
              };
              return updated;
            } else {
              // Create new reasoning action - no hardcoded title, just show the content
              const reasoningAction: AgentAction = {
                id: `reasoning-${Date.now()}`,
                type: 'thinking',
                timestamp: new Date(),
                title: '', // No hardcoded title - let content speak
                content: accumulated,
                metadata: {},
                status: 'running',
                isStreaming: true
              };
              return [...prev, reasoningAction];
            }
          });
        } catch (error) {
          console.error('Error parsing reasoning_chunk:', error);
        }
      });

      // Handle agent_activity events (real-time agent actions)
      eventSource.addEventListener('agent_activity', (e) => {
        try {
          const activityData = JSON.parse(e.data);
          const agent = activityData.agent || 'agent';
          const action = activityData.action || 'working';

          // Create action for agent activity
          const activityAction: AgentAction = {
            id: `activity-${agent}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            type: 'tool_call',
            timestamp: new Date(),
            title: `🤖 ${agent} - ${action}`,
            content: activityData.query || activityData.prompt || `${action}...`,
            metadata: activityData,
            status: activityData.status || 'running',
          };
          setActions(prev => [...prev, activityAction]);
        } catch (error) {
          console.error('Error parsing agent_activity:', error);
        }
      });

      // Handle response_chunk events (streaming AI response)
      eventSource.addEventListener('response_chunk', (e) => {
        try {
          const chunkData = JSON.parse(e.data);
          const chunk = chunkData.chunk || '';
          const accumulated = chunkData.accumulated || '';
          const isCompleted = chunkData.completed === true;

          if (!accumulated && !chunk && !isCompleted) return;

          // Find or create response action
          setActions(prev => {
            // Find existing streaming response (check both 'stream' and 'thinking' types)
            const existingIndex = prev.findIndex(
              action => (action.type === 'stream' || action.type === 'thinking') &&
                (action.status === 'running' || action.status === 'pending')
            );

            if (existingIndex >= 0) {
              // Update existing response action
              const updated = [...prev];
              updated[existingIndex] = {
                ...updated[existingIndex],
                type: 'stream',  // Ensure it's a stream type
                content: accumulated || updated[existingIndex].content || '',
                status: isCompleted ? 'completed' : 'running',
                isStreaming: !isCompleted
              };
              return updated;
            } else {
              // Create new response action
              const responseAction: AgentAction = {
                id: `response-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                type: 'stream',
                timestamp: new Date(),
                title: '🤖 AI Response',
                content: accumulated || chunk,
                metadata: {},
                status: isCompleted ? 'completed' : 'running',
                isStreaming: !isCompleted
              };
              return [...prev, responseAction];
            }
          });
        } catch (error) {
          console.error('Error parsing response_chunk:', error);
        }
      });

      // Handle tool_started events
      eventSource.addEventListener('tool_started', (e) => {
        try {
          const toolData = JSON.parse(e.data);
          const toolAction: AgentAction = {
            id: `tool-${toolData.tool}-${Date.now()}`,
            type: 'tool_call',
            timestamp: new Date(),
            title: `🔧 ${toolData.tool}`,
            content: `Executing ${toolData.tool} (step ${toolData.step}/${toolData.total})...\n${toolData.description || ''}`,
            metadata: toolData,
            status: 'running',
          };
          setActions(prev => [...prev, toolAction]);
        } catch (error) {
          console.error('Error parsing tool_started:', error);
        }
      });

      // Handle tool_completed events
      eventSource.addEventListener('tool_completed', (e) => {
        try {
          const toolData = JSON.parse(e.data);
          // Update the corresponding tool_started action
          setActions(prev => prev.map(action => {
            if (action.metadata?.tool === toolData.tool && action.status === 'running') {
              return {
                ...action,
                status: toolData.status === 'success' ? 'completed' : 'error',
                content: `${action.content}\n✓ Completed (${toolData.status})`,
              };
            }
            return action;
          }));
        } catch (error) {
          console.error('Error parsing tool_completed:', error);
        }
      });

      // Handle stage_started events
      eventSource.addEventListener('stage_started', (e) => {
        try {
          const stageData = JSON.parse(e.data);
          const stageAction: AgentAction = {
            id: `stage-${stageData.stage}-${Date.now()}`,
            type: 'thinking',
            timestamp: new Date(),
            title: `📋 ${stageData.stage.charAt(0).toUpperCase() + stageData.stage.slice(1)}`,
            content: stageData.message || `Starting ${stageData.stage}...`,
            metadata: stageData,
            status: 'running',
          };
          setActions(prev => [...prev, stageAction]);
        } catch (error) {
          console.error('Error parsing stage_started:', error);
        }
      });

      // Handle stage_completed events
      eventSource.addEventListener('stage_completed', (e) => {
        try {
          const stageData = JSON.parse(e.data);
          // Update the corresponding stage_started action
          setActions(prev => prev.map(action => {
            if (action.metadata?.stage === stageData.stage && action.status === 'running') {
              return {
                ...action,
                status: 'completed',
                content: `${action.content}\n✓ Completed`,
                metadata: { ...action.metadata, ...stageData.metadata },
              };
            }
            return action;
          }));
        } catch (error) {
          console.error('Error parsing stage_completed:', error);
        }
      });

      // Handle file_created events
      eventSource.addEventListener('file_created', (e) => {
        try {
          const fileData = JSON.parse(e.data);
          const fileAction: AgentAction = {
            id: `file-${Date.now()}-${Math.random()}`,
            type: 'file_write',
            timestamp: new Date(),
            title: `✅ File Created: ${fileData.path}`,
            content: `File created: ${fileData.path}`,
            metadata: { path: fileData.path, type: fileData.type },
            status: 'completed',
          };
          setActions(prev => [...prev, fileAction]);

          // Trigger workspace refresh
          if (onActionUpdate) {
            window.dispatchEvent(new Event('workspace-refresh'));
          }
        } catch (error) {
          console.error('Error parsing file_created:', error);
        }
      });

      eventSource.onerror = (error) => {
        // Only attempt reconnect if closed and we haven't exceeded max attempts
        if (eventSource.readyState === EventSource.CLOSED) {
          reconnectAttemptsRef.current += 1;

          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            const delay = Math.min(5000 * reconnectAttemptsRef.current, 30000); // Exponential backoff, max 30s
            console.warn(`SSE stream closed. Reconnecting in ${delay / 1000}s... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

            reconnectTimeoutRef.current = setTimeout(() => {
              connectStream();
            }, delay);
          } else {
            console.error('SSE stream: Max reconnect attempts reached. Please check backend availability.');
          }
        } else if (eventSource.readyState === EventSource.CONNECTING) {
          // Still connecting, don't log error
        } else {
          console.warn('SSE stream connection issue. Backend may not be available.');
        }
      };

      eventSourceRef.current = eventSource;
    };

    connectStream();

    // Listen for job_id updates to reconnect immediately
    const handleJobIdUpdate = (event: any) => {
      console.log('Job ID updated, reconnecting SSE...', event.detail);
      connectStream();
    };
    window.addEventListener('job-id-updated', handleJobIdUpdate);

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      window.removeEventListener('job-id-updated', handleJobIdUpdate);
    };
  }, [enableSSE, sessionId]);

  // Auto-scroll
  // Handle user messages
  useEffect(() => {
    // This effect listens for new user messages added to the actions list
    // We don't need to do anything specific here as the render loop handles it,
    // but we could add scroll logic or notifications
  }, [actions]);

  const getActionIcon = (type: AgentAction['type']) => {
    switch (type) {
      case 'file_write':
      case 'file_read':
        return <FileText className="w-4 h-4" />;
      case 'pdf_read':
        return <FileText className="w-4 h-4 text-red-600" />;
      case 'browser_action':
        return <Globe className="w-4 h-4 text-blue-600" />;
      case 'code_execution':
        return <Code2 className="w-4 h-4 text-purple-600" />;
      case 'research_result':
        return <Sparkles className="w-4 h-4 text-yellow-600" />;
      case 'data_analysis':
      case 'chart':
        return <BarChart3 className="w-4 h-4 text-green-600" />;
      case 'log':
        return <File className="w-4 h-4" />;
      case 'tool_call':
        return <PlayCircle className="w-4 h-4 text-blue-600" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  // Helper to parse search results from content
  const parseSearchResults = (content: string | undefined) => {
    if (!content) return null;

    try {
      // Try to extract JSON from HTML comment (backend format)
      // Check for base64-encoded version first (new format)
      const commentMatchB64 = content.match(/<!-- SEARCH_RESULTS_JSON_B64: ([A-Za-z0-9+/=]+) -->/);
      if (commentMatchB64 && commentMatchB64[1]) {
        try {
          const jsonStr = atob(commentMatchB64[1]);
          const parsed = JSON.parse(jsonStr);
          if (parsed.results && Array.isArray(parsed.results)) {
            return {
              query: parsed.query || '',
              results: parsed.results
            };
          }
        } catch (parseError) {
          console.warn('Failed to parse base64 JSON:', parseError);
        }
      }

      // Try legacy format (direct JSON in comment)
      const commentMatch = content.match(/<!-- SEARCH_RESULTS_JSON: ([\s\S]*?) -->/);
      if (commentMatch && commentMatch[1]) {
        try {
          let jsonStr = commentMatch[1].trim();
          // Try to fix common JSON issues
          jsonStr = jsonStr.replace(/--&gt;/g, '-->'); // Unescape HTML entities
          jsonStr = jsonStr.replace(/,\s*([}\]])/g, '$1'); // Remove trailing commas
          const parsed = JSON.parse(jsonStr);
          if (parsed.results && Array.isArray(parsed.results)) {
            return {
              query: parsed.query || '',
              results: parsed.results
            };
          }
        } catch (parseError) {
          console.warn('Failed to parse JSON from comment:', parseError);
        }
      }

      // Try to parse as JSON directly (without HTML comment)
      const jsonMatch = content.match(/\{[\s\S]*"results"[\s\S]*\}/);
      if (jsonMatch) {
        try {
          const parsed = JSON.parse(jsonMatch[0]);
          if (parsed.results && Array.isArray(parsed.results)) {
            return {
              query: parsed.query || '',
              results: parsed.results
            };
          }
        } catch (parseError) {
          console.warn('Failed to parse direct JSON:', parseError);
        }
      }

      // Check if content contains search result structure (text format)
      if (content.includes('Search results for') && content.includes('URL:')) {
        // Extract results from text format
        const results: any[] = [];
        const lines = content.split('\n');
        let currentResult: any = null;

        for (const line of lines) {
          if (line.match(/^\d+\.\s+\*\*/)) {
            if (currentResult) results.push(currentResult);
            currentResult = {
              title: line.replace(/^\d+\.\s+\*\*|\*\*/g, '').trim(),
              url: '',
              content: ''
            };
          } else if (line.includes('URL:') && currentResult) {
            currentResult.url = line.replace('URL:', '').trim();
          } else if (currentResult && line.trim() && !line.startsWith('**')) {
            currentResult.content += line.trim() + ' ';
          }
        }
        if (currentResult) results.push(currentResult);

        if (results.length > 0) {
          return {
            query: content.match(/Search results for '([^']+)'/)?.[1] || '',
            results
          };
        }
      }
    } catch (e) {
      // Not JSON or parseable format
      console.log('Failed to parse search results:', e);
    }

    return null;
  };

  // Helper to parse image search results from content
  const parseImageSearchResults = (content: string | undefined) => {
    if (!content) return null;

    try {
      // Check for base64-encoded image search results
      const commentMatchB64 = content.match(/<!-- IMAGE_SEARCH_JSON_B64: ([A-Za-z0-9+/=]+) -->/);
      if (commentMatchB64 && commentMatchB64[1]) {
        try {
          const jsonStr = atob(commentMatchB64[1]);
          const parsed = JSON.parse(jsonStr);
          if (parsed.type === "image_search" && parsed.results && Array.isArray(parsed.results)) {
            return {
              query: parsed.query || '',
              images: parsed.results
            };
          }
        } catch (parseError) {
          console.warn('Failed to parse image search JSON:', parseError);
        }
      }
    } catch (e) {
      console.log('Failed to parse image search results:', e);
    }

    return null;
  };

  // Helper to parse image generation results from content
  const parseImageGenerationResults = (content: string | undefined) => {
    if (!content) return null;

    try {
      // Check for base64-encoded image generation results
      const commentMatchB64 = content.match(/<!-- IMAGE_GENERATION_JSON_B64: ([A-Za-z0-9+/=]+) -->/);
      if (commentMatchB64 && commentMatchB64[1]) {
        try {
          const jsonStr = atob(commentMatchB64[1]);
          const parsed = JSON.parse(jsonStr);
          if (parsed.type === "image_generation" && parsed.success && parsed.url) {
            return parsed;
          }
        } catch (parseError) {
          console.warn('Failed to parse image generation JSON:', parseError);
        }
      }
    } catch (e) {
      console.log('Failed to parse image generation results:', e);
    }

    return null;
  };

  const toggleExpand = (actionId: string) => {
    setExpandedActions(prev => {
      const next = new Set(prev);
      if (next.has(actionId)) {
        next.delete(actionId);
      } else {
        next.add(actionId);
      }
      return next;
    });
  };

  const isExpanded = (actionId: string) => expandedActions.has(actionId);

  const startEditing = (actionId: string, currentContent: string = '') => {
    setEditingActions(prev => new Map(prev).set(actionId, currentContent));
    setExpandedActions(prev => new Set(prev).add(actionId)); // Auto-expand when editing
  };

  const saveEdit = (actionId: string) => {
    const editedContent = editingActions.get(actionId);
    if (editedContent !== undefined) {
      setActions(prev => prev.map(a =>
        a.id === actionId ? { ...a, content: editedContent } : a
      ));
      onActionUpdate?.(actionId, { content: editedContent });
    }
    setEditingActions(prev => {
      const next = new Map(prev);
      next.delete(actionId);
      return next;
    });
  };

  const cancelEdit = (actionId: string) => {
    setEditingActions(prev => {
      const next = new Map(prev);
      next.delete(actionId);
      return next;
    });
  };

  const renderAction = (action: AgentAction) => {
    const isSelected = selectedAction === action.id;
    const expanded = isExpanded(action.id);
    const isEditing = editingActions.has(action.id);
    const editContent = editingActions.get(action.id) || action.content || '';

    // Special handling for user messages
    if (action.type === 'user_message') {
      return (
        <div key={action.id} className="flex justify-end mb-6">
          <div
            className="max-w-[80%] rounded-2xl px-5 py-3 text-white shadow-sm"
            style={{ backgroundColor: 'var(--color-primary, #0F62FE)' }}
          >
            <p className="text-sm whitespace-pre-wrap">{action.content}</p>
          </div>
        </div>
      );
    }

    switch (action.type) {
      case 'file_write':
      case 'file_read':
        return (
          <div
            key={action.id}
            className="group mb-4"
            onClick={() => {
              setSelectedAction(action.id);
              onActionClick?.(action);

              // If this is a file action with a path, also open it in preview
              if (action.metadata?.path) {
                window.dispatchEvent(new CustomEvent('open-file-preview', {
                  detail: {
                    path: action.metadata.path,
                    type: action.metadata.type || 'file'
                  }
                }));
              }
            }}
          >
            <div className="flex items-start gap-4 px-4 py-2 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer">
              <div className="mt-1">{getActionIcon(action.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-sm font-medium text-gray-900">
                    {action.title}
                  </h4>
                  <span className="text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    {action.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                {action.content && (
                  <div className="relative">
                    <pre className="text-xs font-mono text-gray-600 bg-gray-50 p-3 rounded-md overflow-x-auto mt-2 border border-gray-100">
                      {action.content}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'pdf_read':
        return (
          <div
            key={action.id}
            className="rounded-lg border p-4 mb-4"
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
          >
            <div className="flex items-start gap-3">
              {getActionIcon(action.type)}
              <div className="flex-1">
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text, #161616)' }}>
                  {action.title}
                </h4>
                {action.metadata?.page && (
                  <p className="text-xs mb-2" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                    Page {action.metadata.page}
                  </p>
                )}
                {action.content && (
                  <div className="prose prose-sm max-w-none">
                    <p className="text-sm whitespace-pre-wrap">{action.content}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'browser_action':
        return (
          <div
            key={action.id}
            className={cn(
              "rounded-lg border p-4 mb-4 transition-all cursor-pointer hover:shadow-md",
              isSelected && "ring-2 ring-blue-500"
            )}
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
            onClick={() => {
              setSelectedAction(action.id);
              onActionClick?.(action);
            }}
          >
            <div className="flex items-start gap-3">
              {getActionIcon(action.type)}
              <div className="flex-1">
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text, #161616)' }}>
                  {action.title}
                </h4>
                {action.metadata?.url && (
                  <a
                    href={action.metadata.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs text-blue-600 hover:underline flex items-center gap-1 mb-2"
                  >
                    {action.metadata.url}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
                {action.metadata?.screenshot && (
                  <img
                    src={action.metadata.screenshot}
                    alt="Browser screenshot"
                    className="mt-2 rounded border max-w-full cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation();
                      onActionClick?.(action);
                    }}
                  />
                )}
                {action.content && (
                  <p className="text-xs text-gray-600 mt-2 line-clamp-3">{action.content}</p>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onActionClick?.(action);
                  }}
                  className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1"
                >
                  View in Preview Panel
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        );

      case 'code_execution':
        return (
          <div
            key={action.id}
            className="rounded-lg border p-4 mb-4"
            style={{
              backgroundColor: '#1E1E1E',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
          >
            <div className="flex items-start gap-3">
              {getActionIcon(action.type)}
              <div className="flex-1">
                <h4 className="text-sm font-semibold mb-2" style={{ color: '#D4D4D4' }}>
                  {action.title}
                </h4>
                {action.content && (
                  <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap overflow-x-auto">
                    {action.content}
                  </pre>
                )}
                {action.status === 'running' && (
                  <div className="flex items-center gap-2 mt-2">
                    <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
                    <span className="text-xs text-blue-400">Running...</span>
                  </div>
                )}
                {/* Execute Code Button */}
                {action.type === 'code_execution' && action.content && action.status !== 'running' && (
                  <div className="flex items-center gap-2 mt-3">
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        setExecutingCode(action.id);
                        try {
                          // const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
                          const response = await fetch(`/api/code/execute`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              code: action.content,
                              language: action.metadata?.language || 'python',
                              session_id: sessionId,
                              timeout: 30
                            })
                          });
                          const result = await response.json();
                          if (result.success) {
                            onActionUpdate?.(action.id, {
                              content: result.output,
                              status: 'completed'
                            });
                          } else {
                            onActionUpdate?.(action.id, {
                              content: result.error || 'Execution failed',
                              status: 'error'
                            });
                          }
                        } catch (error: any) {
                          console.error('Code execution error:', error);
                          onActionUpdate?.(action.id, {
                            content: `Error: ${error.message}`,
                            status: 'error'
                          });
                        } finally {
                          setExecutingCode(null);
                        }
                      }}
                      disabled={executingCode === action.id}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50"
                      style={{
                        backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
                        color: 'var(--color-primary, #0F62FE)'
                      }}
                    >
                      {executingCode === action.id ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Executing...
                        </>
                      ) : (
                        <>
                          <Play className="w-3 h-3" />
                          Run Code
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'research_result':
      case 'tool_call':
        // Check if this is a web_search result with structured data
        const searchResults = parseSearchResults(action.content);
        const hasSearchMetadata = action.metadata?.tool === 'web_search' || action.metadata?.results;
        const hasSearchContent = action.content?.includes('Search results for') || action.content?.includes('"type":"web_search"') || action.content?.includes('SEARCH_RESULTS_JSON');

        if (searchResults && (hasSearchMetadata || hasSearchContent)) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <SearchResultDisplay
                query={searchResults.query || action.metadata?.query || 'Search'}
                results={searchResults.results}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        // Check for image search results in research_result/tool_call
        const imageSearchResults = parseImageSearchResults(action.content);
        if (imageSearchResults && imageSearchResults.images && imageSearchResults.images.length > 0) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <ImageGallery
                images={imageSearchResults.images}
                query={imageSearchResults.query}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        // Check for image generation in research_result/tool_call
        const imageGenResults = parseImageGenerationResults(action.content);
        if (imageGenResults && imageGenResults.success && imageGenResults.url) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <div className="mb-3">
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text, #161616)' }}>
                  Generated Image: {imageGenResults.prompt}
                </h4>
                <p className="text-xs text-gray-500">Model: {imageGenResults.model} | Size: {imageGenResults.size}</p>
              </div>
              <ImageGallery
                images={[{
                  title: imageGenResults.prompt,
                  url: imageGenResults.url,
                  full: imageGenResults.url,
                  source: imageGenResults.model
                }]}
                query={imageGenResults.prompt}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        // Check for image results in metadata (from parsed results)
        if (action.metadata?.tool === 'image_search' && action.metadata?.images && Array.isArray(action.metadata.images)) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <ImageGallery
                images={action.metadata.images}
                query={action.metadata.query || 'Images'}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        if (action.metadata?.tool === 'image_generate' && action.metadata?.url) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <div className="mb-3">
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text, #161616)' }}>
                  Generated Image: {action.metadata.prompt || 'Image'}
                </h4>
                {action.metadata.model && (
                  <p className="text-xs text-gray-500">Model: {action.metadata.model}</p>
                )}
              </div>
              <ImageGallery
                images={[{
                  title: action.metadata.prompt || 'Generated Image',
                  url: action.metadata.url,
                  full: action.metadata.url,
                  source: action.metadata.model || 'AI Generated'
                }]}
                query={action.metadata.prompt}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        // Regular research result display
        return (
          <div
            key={action.id}
            className={cn(
              "rounded-lg border p-4 mb-4 transition-all cursor-pointer hover:shadow-md",
              isSelected && "ring-2 ring-blue-500"
            )}
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
            onClick={() => {
              setSelectedAction(action.id);
              onActionClick?.(action);
            }}
          >
            <div className="flex items-start gap-3">
              {getActionIcon(action.type)}
              <div className="flex-1">
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text, #161616)' }}>
                  {action.title}
                </h4>
                {action.metadata?.query && (
                  <p className="text-xs text-blue-600 mb-2">Query: {action.metadata.query}</p>
                )}
                {action.content && (
                  <div className="prose prose-sm max-w-none">
                    <p className="text-sm whitespace-pre-wrap line-clamp-4">{action.content}</p>
                  </div>
                )}
                {action.isStreaming && (
                  <span className="inline-block w-2 h-4 ml-1 bg-blue-600 animate-pulse" />
                )}
                {/* Only show button if there are results to view */}
                {(action.metadata?.result?.results || action.metadata?.result?.images ||
                  action.metadata?.results || action.metadata?.images) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onActionClick?.(action);
                      }}
                      className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1"
                    >
                      View Full Results in Preview Panel
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}
              </div>
            </div>
          </div>
        );
      case 'stream':
        // Check if this stream contains search results
        const streamSearchResults = parseSearchResults(action.content);
        if (streamSearchResults && (action.metadata?.tool === 'web_search' || action.content?.includes('SEARCH_RESULTS_JSON'))) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <SearchResultDisplay
                query={streamSearchResults.query || action.metadata?.query || 'Search'}
                results={streamSearchResults.results}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        // Check if this stream contains image search results
        const streamImageSearchResults = parseImageSearchResults(action.content);
        if (streamImageSearchResults && streamImageSearchResults.images && streamImageSearchResults.images.length > 0) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <ImageGallery
                images={streamImageSearchResults.images}
                query={streamImageSearchResults.query}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        // Check if this stream contains image generation results
        const streamImageGenResults = parseImageGenerationResults(action.content);
        if (streamImageGenResults && streamImageGenResults.success && streamImageGenResults.url) {
          return (
            <div
              key={action.id}
              className={cn(
                "rounded-lg border p-4 mb-4 transition-all",
                isSelected && "ring-2 ring-blue-500"
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                borderColor: 'var(--color-border, #E0E0E0)',
              }}
            >
              <div className="mb-3">
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text, #161616)' }}>
                  Generated Image: {streamImageGenResults.prompt}
                </h4>
                <p className="text-xs text-gray-500">Model: {streamImageGenResults.model} | Size: {streamImageGenResults.size}</p>
              </div>
              <ImageGallery
                images={[{
                  title: streamImageGenResults.prompt,
                  url: streamImageGenResults.url,
                  full: streamImageGenResults.url,
                  source: streamImageGenResults.model
                }]}
                query={streamImageGenResults.prompt}
                workspaceId={workspaceId}
              />
            </div>
          );
        }

        return (
          <div
            key={action.id}
            className="rounded-lg border p-4 mb-4"
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
          >
            <div className="flex items-start gap-3">
              {getActionIcon(action.type)}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
                    {action.title}
                  </h4>
                  {action.content && <CopyButton content={action.content} />}
                </div>
                {action.content && (
                  <div className="prose prose-sm max-w-none">
                    {/* Remove HTML comment with search results before rendering */}
                    {action.content.includes('SEARCH_RESULTS_JSON') ? (
                      <MarkdownRenderer content={action.content.replace(/<!-- SEARCH_RESULTS_JSON: [\s\S]*? -->/g, '')} />
                    ) : (
                      <MarkdownRenderer content={action.content} />
                    )}
                  </div>
                )}
                {action.isStreaming && (
                  <span className="inline-block w-2 h-4 ml-1 bg-blue-600 animate-pulse" />
                )}
              </div>
            </div>
          </div>
        );

      case 'chart':
      case 'data_analysis':
        return (
          <div
            key={action.id}
            className="rounded-lg border p-4 mb-4"
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
          >
            <div className="flex items-start gap-3">
              {getActionIcon(action.type)}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
                    {action.title}
                  </h4>
                  {action.metadata?.chart_type && (
                    <span className="text-xs px-2 py-1 rounded" style={{
                      backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
                      color: 'var(--color-primary, #0F62FE)'
                    }}>
                      {action.metadata.chart_type}
                    </span>
                  )}
                </div>
                {action.metadata?.chart_data && (
                  <div className="mt-3 p-4 rounded border" style={{
                    backgroundColor: 'var(--color-bg, #F4F4F4)',
                    borderColor: 'var(--color-border, #E0E0E0)',
                  }}>
                    <div className="flex items-center justify-center h-48">
                      <BarChart3 className="w-12 h-12" style={{ color: 'var(--color-primary, #0F62FE)' }} />
                      <p className="ml-3 text-sm" style={{ color: 'var(--color-text-secondary, #525252)' }}>
                        Chart: {action.metadata.chart_type || 'Data Visualization'}
                      </p>
                    </div>
                    {action.metadata.summary && (
                      <p className="mt-2 text-xs" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                        {action.metadata.summary}
                      </p>
                    )}
                  </div>
                )}
                {action.content && (
                  <div className="mt-2 text-sm whitespace-pre-wrap" style={{ color: 'var(--color-text, #161616)' }}>
                    {action.content}
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'file_diff':
        return (
          <div
            key={action.id}
            className="rounded-lg border p-4 mb-4"
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
          >
            <div className="flex items-start gap-3">
              {getActionIcon(action.type)}
              <div className="flex-1">
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text, #161616)' }}>
                  {action.title}
                </h4>
                {action.metadata?.file_path && (
                  <p className="text-xs mb-2" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                    📁 {action.metadata.file_path}
                  </p>
                )}
                {action.content && (
                  <div className="mt-2 font-mono text-xs">
                    <pre className="whitespace-pre-wrap">{action.content}</pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'log':
        // Skip rendering log items if ProcessPlanner is showing them
        // Log items are now consolidated in the ProcessPlanner above
        if (action.title && (action.title.length < 10 || /^(progress|completed|step \d|processing|working)$/i.test(action.title))) {
          return null; // Skip spam messages
        }

        // Default log display for errors and other logs
        return (
          <div
            key={action.id}
            className={cn(
              "rounded-lg border p-3 mb-3 transition-all cursor-pointer hover:shadow-md",
              isSelected && "ring-2 ring-blue-500"
            )}
            style={{
              backgroundColor: action.metadata?.level === 'error'
                ? 'rgba(218, 30, 40, 0.1)'
                : 'var(--color-panel, #FFFFFF)',
              borderColor: action.metadata?.level === 'error'
                ? 'var(--color-danger, #DA1E28)'
                : 'var(--color-border, #E0E0E0)',
            }}
            onClick={() => {
              setSelectedAction(action.id);
              toggleExpand(action.id);
            }}
          >
            <div className="flex items-start gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(action.id);
                }}
                className="mt-0.5 flex-shrink-0"
              >
                {expanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
              {action.metadata?.level === 'error' ? (
                <AlertCircle className="w-4 h-4 text-red-600" />
              ) : (
                <File className="w-4 h-4" />
              )}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold" style={{
                    color: action.metadata?.level === 'error'
                      ? 'var(--color-danger, #DA1E28)'
                      : 'var(--color-text, #161616)'
                  }}>
                    {action.title}
                  </span>
                  {action.status && (
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded",
                      action.status === 'completed' && "bg-green-100 text-green-700",
                      action.status === 'running' && "bg-blue-100 text-blue-700",
                      action.status === 'error' && "bg-red-100 text-red-700"
                    )}>
                      {action.status}
                    </span>
                  )}
                </div>
                {expanded && (
                  <div className="mt-2">
                    {isEditing ? (
                      <div className="space-y-2">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditingActions(prev => new Map(prev).set(action.id, e.target.value))}
                          className="w-full min-h-[150px] p-2 rounded border font-mono text-xs"
                          style={{
                            backgroundColor: 'var(--color-bg, #F4F4F4)',
                            borderColor: 'var(--color-border, #E0E0E0)',
                            color: 'var(--color-text, #161616)'
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              saveEdit(action.id);
                            }}
                            className="px-2 py-1 rounded text-xs font-medium bg-green-600 text-white hover:bg-green-700"
                          >
                            <Save className="w-3 h-3 inline mr-1" />
                            Save
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              cancelEdit(action.id);
                            }}
                            className="px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700 hover:bg-gray-300"
                          >
                            <X className="w-3 h-3 inline mr-1" />
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <pre className="text-xs font-mono whitespace-pre-wrap" style={{
                          color: action.metadata?.level === 'error'
                            ? 'var(--color-danger, #DA1E28)'
                            : 'var(--color-text, #161616)'
                        }}>
                          {action.content || action.title}
                        </pre>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(action.id, action.content || action.title);
                          }}
                          className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <Edit className="w-3 h-3" />
                          Edit
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'tool_call':
        return (
          <div
            key={action.id}
            className={cn(
              "rounded-lg border p-3 mb-3 transition-all cursor-pointer hover:shadow-md",
              isSelected && "ring-2 ring-blue-500"
            )}
            style={{
              backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
              borderColor: 'var(--color-primary, #0F62FE)',
            }}
            onClick={() => {
              setSelectedAction(action.id);
              toggleExpand(action.id);
            }}
          >
            <div className="flex items-start gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(action.id);
                }}
                className="mt-0.5 flex-shrink-0"
              >
                {expanded ? (
                  <ChevronDown className="w-4 h-4" style={{ color: 'var(--color-primary, #0F62FE)' }} />
                ) : (
                  <ChevronRight className="w-4 h-4" style={{ color: 'var(--color-primary, #0F62FE)' }} />
                )}
              </button>
              {getActionIcon(action.type)}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <h5 className="text-xs font-semibold" style={{ color: 'var(--color-primary, #0F62FE)' }}>
                    {action.title}
                  </h5>
                  {action.status && (
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded",
                      action.status === 'completed' && "bg-green-100 text-green-700",
                      action.status === 'running' && "bg-blue-100 text-blue-700",
                      action.status === 'error' && "bg-red-100 text-red-700"
                    )}>
                      {action.status}
                    </span>
                  )}
                </div>
                {action.metadata?.tool_name && (
                  <p className="text-xs font-mono mb-1" style={{ color: 'var(--color-text-secondary, #525252)' }}>
                    🔧 {action.metadata.tool_name}
                  </p>
                )}
                {expanded && (
                  <div className="mt-2">
                    {isEditing ? (
                      <div className="space-y-2">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditingActions(prev => new Map(prev).set(action.id, e.target.value))}
                          className="w-full min-h-[150px] p-2 rounded border font-mono text-xs"
                          style={{
                            backgroundColor: 'var(--color-bg, #F4F4F4)',
                            borderColor: 'var(--color-border, #E0E0E0)',
                            color: 'var(--color-text, #161616)'
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              saveEdit(action.id);
                            }}
                            className="px-2 py-1 rounded text-xs font-medium bg-green-600 text-white hover:bg-green-700"
                          >
                            <Save className="w-3 h-3 inline mr-1" />
                            Save
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              cancelEdit(action.id);
                            }}
                            className="px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700 hover:bg-gray-300"
                          >
                            <X className="w-3 h-3 inline mr-1" />
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        {action.content && (
                          <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-2 rounded" style={{
                            color: 'var(--color-text, #161616)',
                            backgroundColor: 'var(--color-bg, #F4F4F4)'
                          }}>
                            {action.content}
                          </pre>
                        )}
                        {action.metadata && Object.keys(action.metadata).length > 0 && (
                          <details className="mt-2">
                            <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                              View Metadata
                            </summary>
                            <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-2 rounded mt-1" style={{
                              color: 'var(--color-text, #161616)',
                              backgroundColor: 'var(--color-bg, #F4F4F4)'
                            }}>
                              {JSON.stringify(action.metadata, null, 2)}
                            </pre>
                          </details>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(action.id, action.content || '');
                          }}
                          className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <Edit className="w-3 h-3" />
                          Edit
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'thinking':
        return (
          <div
            key={action.id}
            className={cn(
              "rounded-lg border p-3 mb-3 transition-all cursor-pointer hover:shadow-md",
              isSelected && "ring-2 ring-blue-500"
            )}
            style={{
              backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
              borderColor: 'var(--color-primary, #0F62FE)',
            }}
            onClick={() => {
              setSelectedAction(action.id);
              toggleExpand(action.id);
            }}
          >
            <div className="flex items-start gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(action.id);
                }}
                className="mt-0.5 flex-shrink-0"
              >
                {expanded ? (
                  <ChevronDown className="w-4 h-4" style={{ color: 'var(--color-primary, #0F62FE)' }} />
                ) : (
                  <ChevronRight className="w-4 h-4" style={{ color: 'var(--color-primary, #0F62FE)' }} />
                )}
              </button>
              <Sparkles className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-primary, #0F62FE)' }} />
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold" style={{ color: 'var(--color-primary, #0F62FE)' }}>
                    {action.title}
                  </span>
                  {action.status && (
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded",
                      action.status === 'completed' && "bg-green-100 text-green-700",
                      action.status === 'running' && "bg-blue-100 text-blue-700",
                      action.status === 'error' && "bg-red-100 text-red-700"
                    )}>
                      {action.status}
                    </span>
                  )}
                </div>
                {expanded && (
                  <div className="mt-2">
                    {isEditing ? (
                      <div className="space-y-2">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditingActions(prev => new Map(prev).set(action.id, e.target.value))}
                          className="w-full min-h-[150px] p-2 rounded border font-mono text-xs"
                          style={{
                            backgroundColor: 'var(--color-bg, #F4F4F4)',
                            borderColor: 'var(--color-border, #E0E0E0)',
                            color: 'var(--color-text, #161616)'
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              saveEdit(action.id);
                            }}
                            className="px-2 py-1 rounded text-xs font-medium bg-green-600 text-white hover:bg-green-700"
                          >
                            <Save className="w-3 h-3 inline mr-1" />
                            Save
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              cancelEdit(action.id);
                            }}
                            className="px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700 hover:bg-gray-300"
                          >
                            <X className="w-3 h-3 inline mr-1" />
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        {action.content && (
                          <div className="prose prose-sm max-w-none">
                            <MarkdownRenderer content={action.content} />
                          </div>
                        )}
                        {action.metadata && Object.keys(action.metadata).length > 0 && (
                          <details className="mt-2">
                            <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                              View Metadata
                            </summary>
                            <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-2 rounded mt-1" style={{
                              color: 'var(--color-text, #161616)',
                              backgroundColor: 'var(--color-bg, #F4F4F4)'
                            }}>
                              {JSON.stringify(action.metadata, null, 2)}
                            </pre>
                          </details>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(action.id, action.content || '');
                          }}
                          className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <Edit className="w-3 h-3" />
                          Edit
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div
            key={action.id}
            className={cn(
              "rounded-lg border p-3 mb-3 transition-all cursor-pointer hover:shadow-md",
              isSelected && "ring-2 ring-blue-500"
            )}
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)',
            }}
            onClick={() => {
              setSelectedAction(action.id);
              toggleExpand(action.id);
            }}
          >
            <div className="flex items-start gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(action.id);
                }}
                className="p-1 hover:bg-gray-100 rounded"
                style={{ color: 'var(--color-text, #161616)' }}
              >
                {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </button>
              <div className="flex-1">
                {isEditing ? (
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        saveEdit(action.id);
                      }}
                      className="px-2 py-1 rounded text-xs font-medium bg-green-600 text-white hover:bg-green-700"
                    >
                      <Save className="w-3 h-3 inline mr-1" />
                      Save
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        cancelEdit(action.id);
                      }}
                      className="px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700 hover:bg-gray-300"
                    >
                      <X className="w-3 h-3 inline mr-1" />
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div>
                    {action.content && (
                      <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-2 rounded" style={{
                        color: 'var(--color-text, #161616)',
                        backgroundColor: 'var(--color-bg, #F4F4F4)'
                      }}>
                        {action.content}
                      </pre>
                    )}
                    {action.metadata && Object.keys(action.metadata).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                          View Metadata
                        </summary>
                        <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto p-2 rounded mt-1" style={{
                          color: 'var(--color-text, #161616)',
                          backgroundColor: 'var(--color-bg, #F4F4F4)'
                        }}>
                          {JSON.stringify(action.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        startEditing(action.id, action.content || '');
                      }}
                      className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1"
                    >
                      <Edit className="w-3 h-3" />
                      Edit
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
    }
  };

  if (actions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <div className="w-24 h-24 mx-auto rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-primary-bg, #EDF5FF)' }}>
            <Sparkles className="w-12 h-12" style={{ color: 'var(--color-primary, #0F62FE)' }} />
          </div>
          <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text, #161616)' }}>
            Agent Workspace
          </h2>
          <p className="text-lg" style={{ color: 'var(--color-text-secondary, #525252)' }}>
            Agent actions will stream here in real-time
          </p>
          <p className="text-sm" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
            Send a message below to start
          </p>
        </div>
      </div>
    );
  }

  // Handle saving edited content
  const handleSaveEdit = async (actionId: string) => {
    const action = actions.find(a => a.id === actionId);
    if (!action) return;

    try {
      // Update the action content
      const updatedActions = actions.map(a =>
        a.id === actionId ? { ...a, content: editContent } : a
      );
      setActions(updatedActions);
      onActionUpdate?.(actionId, { content: editContent });
      setEditingAction(null);
      setEditContent('');
    } catch (error) {
      console.error('Failed to save edit:', error);
    }
  };

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: 'var(--color-bg, #F4F4F4)' }}>
      {/* Edit Dialog */}
      {editingAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div
            className="rounded-lg border shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col"
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)'
            }}
          >
            <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
              <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
                Edit File Content
              </h3>
              <button
                onClick={() => {
                  setEditingAction(null);
                  setEditContent('');
                }}
                className="p-2 rounded hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden p-6">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-full font-mono text-sm p-4 rounded border resize-none"
                style={{
                  backgroundColor: 'var(--color-bg, #F4F4F4)',
                  borderColor: 'var(--color-border, #E0E0E0)',
                  color: 'var(--color-text, #161616)'
                }}
              />
            </div>
            <div className="px-6 py-4 border-t flex items-center justify-end gap-3" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
              <button
                onClick={() => {
                  setEditingAction(null);
                  setEditContent('');
                }}
                className="px-4 py-2 rounded text-sm font-medium transition-colors"
                style={{
                  backgroundColor: 'var(--color-bg, #F4F4F4)',
                  color: 'var(--color-text, #161616)'
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => handleSaveEdit(editingAction)}
                className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors"
                style={{
                  backgroundColor: 'var(--color-primary, #0F62FE)',
                  color: 'white'
                }}
              >
                <Save className="w-4 h-4" />
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div
        className="px-6 py-3 border-b flex items-center justify-between"
        style={{
          backgroundColor: 'var(--color-panel, #FFFFFF)',
          borderColor: 'var(--color-border, #E0E0E0)'
        }}
      >
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5" style={{ color: 'var(--color-primary, #0F62FE)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
            Agent Workspace
          </h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
            {actions.filter(a => a.isStreaming || a.status === 'running').length} active
          </span>
          {actions.length > 0 && (
            <button
              onClick={() => {
                setActions([]);
                onClear?.();
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors hover:bg-red-50"
              style={{
                color: 'var(--color-danger, #DA1E28)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(218, 30, 40, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Process Planner - Shows overall progress and steps */}
      {processSteps.length > 0 && (
        <div className="px-6 py-4 border-b bg-white dark:bg-gray-950" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
          <ProcessPlanner
            title="Process Progress"
            steps={processSteps}
            totalPercentage={totalProgress}
            isCompact={false}
            onlyShowActive={false}
          />
        </div>
      )}

      {/* Actions Stream */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {actions.map(action => {
            const rendered = renderAction(action);
            return rendered; // Skip null values from filtered-out log items
          }).filter(Boolean)}
          <div ref={scrollEndRef} />
        </div>
      </div>
    </div>
  );
}

