'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, Menu, LogOut, Settings, Sparkles } from 'lucide-react';
import { StreamingWorkspace, AgentAction } from '../workspace/StreamingWorkspace';
import { FilePreviewPanel } from './FilePreviewPanel';
import { TabbedPreviewPanel, Tab, TabType } from './TabbedPreviewPanel';
import { ResizableLayout } from './ResizableLayout';
import { ChatBar } from './ChatBar';
import { WorkspaceFileSystem } from '../workspace/WorkspaceFileSystem';
import { FileExplorer } from '../workspace/FileExplorer';
import { CleanChatInput, WelcomeScreen } from '../chat/CleanChatInput';
import { AgentActivityTracker } from '../chat/AgentActivityBadge';
import { EnhancedChatDisplay } from '../chat/EnhancedChatDisplay';
import UniversalProgressOverlay from '../UniversalProgressOverlay';
import { SourcesPanel } from '../sources/SourcesPanel';
import { TopMenuBar } from './TopMenuBar';
import { ProcessPlanner } from '../ProcessPlanner';
import { cn } from '../../lib/utils';
import { ChatHistoryService } from '../../lib/chat-history';
import { ThesisParameters } from '../../lib/thesisParameters';
import { Button } from '../ui/button';
import { LoginScreen } from '../auth/LoginScreen'; // 1. Import LoginScreen

interface ManusStyleLayoutProps {
  children?: React.ReactNode;
  leftPanel?: React.ReactNode;
  workspaceId?: string; // Optional prop to override default/local storage
}

export function ManusStyleLayout({ children, leftPanel, workspaceId: propWorkspaceId }: ManusStyleLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  // Auth State
  const [isAuthenticated, setIsAuthenticated] = useState(false); // 2. Add isAuthenticated state
  const [hasCheckedAuth, setHasCheckedAuth] = useState(false); // Add hasCheckedAuth state
  const [currentUser, setCurrentUser] = useState<any>(null);

  // Check auth on mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    const user = localStorage.getItem('auth_user');
    if (token && user) {
      const parsedUser = JSON.parse(user);
      setIsAuthenticated(true);
      setCurrentUser(parsedUser);

      // Load user's private workspace ONLY if not already in a specific workspace
      if (parsedUser.workspaces && parsedUser.workspaces.length > 0 && (!propWorkspaceId || propWorkspaceId === 'default')) {
        const userWs = parsedUser.workspaces[0];
        setWorkspaceId(userWs);
        localStorage.setItem('workspace_id', userWs);
      }
    }
    setHasCheckedAuth(true); // Mark check as complete
  }, []);

  const handleLoginSuccess = (token: string, user: any) => {
    setIsAuthenticated(true);
    setCurrentUser(user);

    // Switch to user's private workspace immediately
    if (user.workspaces && user.workspaces.length > 0) {
      const userWs = user.workspaces[0];
      setWorkspaceId(userWs);
      localStorage.setItem('workspace_id', userWs);

      // Clear previous chat messages from view (they will reload from new key)
      setChatMessages([]);
    }
  };

  // Logout Handler
  const handleLogout = () => {
    // Clear all auth storage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    localStorage.removeItem('workspace_id');

    // Reset React state
    setIsAuthenticated(false);
    setCurrentUser(null);
    setWorkspaceId('default');

    // Force reload to clear any lingering memory/cache state
    window.location.reload();
  };

  const [isProgressPanelOpen, setIsProgressPanelOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [messageQueue, setMessageQueue] = useState<string[]>([]);
  const [isInterrupted, setIsInterrupted] = useState(false);
  const [isLeftPanelCollapsed, setIsLeftPanelCollapsed] = useState(false);
  const [liveResponse, setLiveResponse] = useState('');
  // Force empty state on load - ignore any potential caching
  const [progressSteps, setProgressSteps] = useState<any[]>([]);
  const [plannerSteps, setPlannerSteps] = useState<any[]>([]);
  const [agentActions, setAgentActions] = useState<AgentAction[]>([]);
  const [leftPanelTab, setLeftPanelTab] = useState<'files' | 'menu'>('files');
  const [reasoning, setReasoning] = useState<string>('');
  const [currentStatus, setCurrentStatus] = useState<string>(''); // Real-time status message
  const [currentStage, setCurrentStage] = useState<string>(''); // Current stage (planning, tool, content, etc.)
  const [activeAgents, setActiveAgents] = useState<any[]>([]); // Track which agents are working
  const [currentAgent, setCurrentAgent] = useState<string>(''); // Current agent name
  const [currentAction, setCurrentAction] = useState<string>(''); // Current action
  const [currentDescription, setCurrentDescription] = useState<string>(''); // Current action description
  const [currentProgress, setCurrentProgress] = useState<number>(0); // Current progress percentage
  const [statusUpdates, setStatusUpdates] = useState<any[]>([]); // History of status updates
  const [showProgressTracker, setShowProgressTracker] = useState(true);

  // Tabbed Preview State
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [sourcesRefreshKey, setSourcesRefreshKey] = useState(0);
  const activeTabIdRef = useRef<string | null>(null);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(true); // Default to open for 3-column layout
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] = useState(false);

  const scheduleAutoCloseTab = useCallback((tabId: string) => {
    setTimeout(() => {
      setTabs(prev => {
        const next = prev.filter(t => t.id !== tabId);
        if (next.length === prev.length) return prev;
        const activeId = activeTabIdRef.current;
        if (activeId === tabId) {
          const fallback = next[next.length - 1];
          setActiveTabId(fallback ? fallback.id : null);
          if (!fallback) {
            setIsRightPanelOpen(false);
          }
        }
        return next;
      });
    }, 1200);
  }, []);

  // Chat Messages State
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
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [assistantVariants, setAssistantVariants] = useState<Record<string, string[]>>({});
  const [assistantVariantIndex, setAssistantVariantIndex] = useState<Record<string, number>>({});
  const latestAssistantContentRef = useRef<Record<string, string>>({});
  const jobReplacementRef = useRef<Record<string, string>>({});
  type ActiveJob = {
    jobId: string;
    workspaceId: string;
    sessionId?: string;
    type?: 'thesis' | 'general' | 'good';
    responseMessageId?: string;
    startedAt?: number;
  };

  useEffect(() => {
    activeTabIdRef.current = activeTabId;
  }, [activeTabId]);

  // Workspace State
  const [workspaceId, setWorkspaceId] = useState<string>(propWorkspaceId || 'default');

  // Sync state with URL when workspaceId changes
  useEffect(() => {
    if (workspaceId && workspaceId !== 'default' && !pathname.includes(workspaceId)) {
      // Only update if not already on that path
      router.push(`/workspace/${workspaceId}`);
    } else if (workspaceId === 'default' && pathname !== '/' && !pathname.startsWith('/workspace/default')) {
      // Optional: Redirect default to specialized path if desired, or keep at root
      // router.push('/workspace/default');
    }
  }, [workspaceId, router, pathname]);

  // If prop changes, sync internal state
  useEffect(() => {
    if (propWorkspaceId && propWorkspaceId !== workspaceId) {
      setWorkspaceId(propWorkspaceId);
    }
  }, [propWorkspaceId]);
  const [sessionId, setSessionId] = useState<string>(''); // Session ID for chat isolation

  // Restore workspace/session from localStorage on mount - only if not in a specific workspace
  useEffect(() => {
    if (!propWorkspaceId || propWorkspaceId === 'default') {
      const savedWs = localStorage.getItem('workspace_id');
      const savedSession = localStorage.getItem('session_id');
      if (savedWs) setWorkspaceId(savedWs);
      if (savedSession) setSessionId(savedSession);
    }
  }, [propWorkspaceId]);

  // Fetch workspace details if propWorkspaceId is provided (sharable URL)
  useEffect(() => {
    if (propWorkspaceId && propWorkspaceId !== 'default') {
      const loadWorkspace = async () => {
        try {
          const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
          const response = await fetch(`${backendUrl}/api/workspace/${propWorkspaceId}/load`);
          if (response.ok) {
            const data = await response.json();

            // Only update if it's different to prevent loops
            setSessionId(data.session_id);
            // setWorkspaceId is already handled by the sync useEffect or the initial state

            // Update messages
            const messages = (data.messages || []).map((msg: any) => ({
              id: msg.id,
              type: msg.role === 'user' ? 'user' : (msg.role === 'system' ? 'system' : 'assistant'),
              content: msg.content,
              timestamp: new Date(msg.timestamp),
              isStreaming: false,
              agent: msg.role === 'assistant' ? 'assistant' : undefined
            }));

            setChatMessages(messages);
            setShowWelcome(false);
            setWorkspaceFiles(data.files || []);

            // Persist to local storage so other parts of the app know
            localStorage.setItem('workspace_id', data.workspace_id);
            localStorage.setItem('session_id', data.session_id);
          }
        } catch (error) {
          console.error('Failed to load shared workspace:', error);
        }
      };

      loadWorkspace();
    }
  }, [propWorkspaceId]);
  const [workspaceFiles, setWorkspaceFiles] = useState<any[]>([]); // Workspace files list
  const [showWelcome, setShowWelcome] = useState(false); // Skip welcome screen
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [selectedUniversity, setSelectedUniversity] = useState<string | null>(null); // Track selected university for thesis generation

  // Universal Progress Overlay State
  const [showProgressOverlay, setShowProgressOverlay] = useState(false);
  const [progressJobId, setProgressJobId] = useState<string | null>(null);
  const [progressTopic, setProgressTopic] = useState<string>('');
  const [progressType, setProgressType] = useState<'thesis' | 'general' | 'good'>('general');

  const normalizePlannerSteps = useCallback((steps: any[]) => {
    return steps.map((step: any) => {
      const status = step.status === 'done'
        ? 'completed'
        : step.status === 'running'
          ? 'running'
          : step.status === 'error'
            ? 'error'
            : 'pending';
      return {
        id: step.id || step.name || `${step.icon || 'step'}-${Math.random().toString(36).slice(2)}`,
        name: step.name || step.title || 'Step',
        status,
        description: step.description,
        icon: step.icon
      };
    });
  }, []);

  const persistActiveJobs = useCallback((nextJobs?: Record<string, ActiveJob>) => {
    const payload = Object.values(nextJobs || activeJobsRef.current);
    try {
      localStorage.setItem('active_jobs', JSON.stringify(payload));
    } catch (error) {
      console.error('Failed to persist active jobs:', error);
    }
  }, []);

  const registerActiveJob = useCallback((job: ActiveJob) => {
    const mergedJob: ActiveJob = {
      workspaceId: workspaceId,
      ...job
    };
    activeJobsRef.current[job.jobId] = mergedJob;
    const ids = Object.keys(activeJobsRef.current);
    setActiveJobIds(ids);
    persistActiveJobs();
    setIsProcessing(true);
    setCurrentJobId(job.jobId);
    localStorage.setItem('current_job_id', job.jobId);
  }, [persistActiveJobs, workspaceId]);

  const unregisterActiveJob = useCallback((jobId: string) => {
    const stream = jobStreamsRef.current[jobId];
    if (stream) {
      stream.close();
      delete jobStreamsRef.current[jobId];
    }
    delete activeJobsRef.current[jobId];
    const ids = Object.keys(activeJobsRef.current);
    setActiveJobIds(ids);
    persistActiveJobs();
    setIsProcessing(Object.values(activeJobsRef.current).some(job => job.workspaceId === workspaceId));
  }, [persistActiveJobs, workspaceId]);

  const syncProcessingState = useCallback(() => {
    const activeInWorkspace = Object.values(activeJobsRef.current)
      .some(job => job.workspaceId === workspaceId);
    setIsProcessing(activeInWorkspace);
  }, [workspaceId]);

  const ensureAssistantVariantBase = useCallback((messageId: string, content: string) => {
    if (!content.trim()) return;
    setAssistantVariants(prev => {
      if (prev[messageId] && prev[messageId].length > 0) {
        return prev;
      }
      return { ...prev, [messageId]: [content] };
    });
    setAssistantVariantIndex(prev => {
      if (prev[messageId] !== undefined) return prev;
      return { ...prev, [messageId]: 0 };
    });
  }, []);

  const appendAssistantVariant = useCallback((messageId: string, content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    setAssistantVariants(prev => {
      const existing = prev[messageId] || [];
      const last = existing[existing.length - 1];
      if (last === trimmed) {
        return prev;
      }
      const next = [...existing, trimmed];
      setAssistantVariantIndex(prevIndex => ({ ...prevIndex, [messageId]: next.length - 1 }));
      return { ...prev, [messageId]: next };
    });
  }, []);

  const deriveWorkspaceId = useCallback((rawPath: string) => {
    if (!rawPath) return null;
    const path = rawPath.replace(/\\/g, '/');
    const match = path.match(/thesis_data\/([^/]+)\//);
    return match ? match[1] : null;
  }, []);

  const normalizeWorkspacePath = useCallback((rawPath: string, wsId: string) => {
    if (!rawPath) return rawPath;
    const path = rawPath.replace(/\\/g, '/');
    const markers = [
      `/thesis_data/${wsId}/`,
      `thesis_data/${wsId}/`,
    ];
    for (const marker of markers) {
      const idx = path.indexOf(marker);
      if (idx >= 0) {
        return path.slice(idx + marker.length);
      }
    }
    if (path.startsWith(`${wsId}/`)) {
      return path.slice(wsId.length + 1);
    }
    return path;
  }, []);

  const pruneAssistantVariants = useCallback((allowedIds: Set<string>) => {
    setAssistantVariants(prev => {
      const next: Record<string, string[]> = {};
      Object.entries(prev).forEach(([key, value]) => {
        if (allowedIds.has(key)) {
          next[key] = value;
        }
      });
      return next;
    });
    setAssistantVariantIndex(prev => {
      const next: Record<string, number> = {};
      Object.entries(prev).forEach(([key, value]) => {
        if (allowedIds.has(key)) {
          next[key] = value;
        }
      });
      return next;
    });
  }, []);

  const startJobStream = useCallback((params: {
    jobId: string;
    streamSessionId: string;
    responseMessageId?: string;
    type?: 'thesis' | 'general' | 'good';
    resume?: boolean;
  }) => {
    const { jobId, streamSessionId, responseMessageId, type } = params;
    if (!jobId) return;
    if (jobStreamsRef.current[jobId]) return;

    const resolvedMessageId = responseMessageId || `chat-${jobId}-response`;
    registerActiveJob({
      jobId,
      sessionId: streamSessionId,
      type: type || 'general',
      responseMessageId: resolvedMessageId,
      startedAt: Date.now(),
      workspaceId: workspaceId
    });

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const streamUrl = `${backendUrl}/api/stream/agent-actions?session_id=${streamSessionId}&job_id=${jobId}`;
    const eventSource = new EventSource(streamUrl);
    jobStreamsRef.current[jobId] = eventSource;

    const finalizeJob = (shouldPersist: boolean) => {
      const targetMessageId = jobReplacementRef.current[jobId] || resolvedMessageId;
      setChatMessages(prev => {
        const updated = prev.map(msg =>
          msg.id === targetMessageId ? { ...msg, isStreaming: false } : msg
        );
        if (shouldPersist) {
          const finalMsg = updated.find(msg => msg.id === targetMessageId);
          if (finalMsg && finalMsg.content) {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            fetch(`${backendUrl}/api/workspace/${workspaceId}/conversations/${sessionId || 'default'}/messages`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                role: 'assistant',
                content: finalMsg.content,
                job_id: jobId
              })
            }).catch(err => console.error('Failed to persist final streaming message:', err));
          }
        }
        return updated;
      });

      if (jobReplacementRef.current[jobId]) {
        const finalContent = latestAssistantContentRef.current[targetMessageId] || '';
        if (finalContent) {
          appendAssistantVariant(targetMessageId, finalContent);
        }
        delete jobReplacementRef.current[jobId];
      }

      setCurrentStatus('');
      setCurrentStage('');
      unregisterActiveJob(jobId);
    };

    eventSource.onopen = () => {
      setCurrentStatus('✅ Connected - receiving updates...');
    };

    eventSource.addEventListener('connected', (e) => {
      try {
        const connData = JSON.parse(e.data);
        if (connData.job_id === jobId) {
          setCurrentStatus('✅ Connected to real-time stream');
        }
      } catch (err) {
        console.error('Error parsing connected event:', err);
      }
    });

    eventSource.addEventListener('log', (e) => {
      try {
        const eventData = JSON.parse(e.data);
        const message = eventData.message || '';

        setCurrentStatus(message);

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
          return;
        }

        const isMilestone =
          message.includes('✅') ||
          message.includes('❌') ||
          message.includes('📄') ||
          message.includes('Chapter') ||
          message.includes('generated') ||
          message.includes('saved') ||
          message.includes('created') ||
          message.includes('Starting');

        if (isMilestone) {
          const logAction: AgentAction = {
            id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
            type: 'log' as any,
            timestamp: new Date(),
            title: message.substring(0, 60) + (message.length > 60 ? '...' : ''),
            content: message.length > 60 ? message : undefined,
            status: 'completed'
          };
          setAgentActions(prev => [...prev, logAction]);
        }
      } catch (err) {
        console.error('Error parsing log event:', err);
      }
    });

    eventSource.addEventListener('agent_activity', (e) => {
      try {
        const activityData = JSON.parse(e.data);
        const agent = activityData.agent || 'agent';
        const action = activityData.action || 'working';
        const description = activityData.description || activityData.details || '';
        const progress = activityData.progress || 0;
        const agentName = activityData.agent_name || agent.charAt(0).toUpperCase() + agent.slice(1).replace(/_/g, ' ');

        setCurrentAgent(agent);
        setCurrentAction(action);
        setCurrentDescription(description);
        setCurrentProgress(progress);

        setStatusUpdates(prev => [...prev, {
          timestamp: new Date(),
          agent: agent,
          action: action,
          description: description,
          status: 'running'
        }].slice(-10));

        const statusText = (activityData.status || 'running').toLowerCase();
        const normalizedStatus = statusText.includes('error') || statusText.includes('failed')
          ? 'error'
          : statusText.includes('completed') || statusText.includes('done')
            ? 'completed'
            : 'running';

        setAgentActions(prev => {
          const last = prev[prev.length - 1];
          if (
            last &&
            last.type === 'agent_activity' &&
            last.metadata?.agent === agent &&
            last.metadata?.action === action &&
            last.content === description
          ) {
            return prev;
          }
          const activityAction: AgentAction = {
            id: `activity-${jobId}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            type: 'agent_activity',
            timestamp: new Date(),
            title: `${agentName} · ${action}`,
            content: description || activityData.query || '',
            metadata: { ...activityData, agent, action, agent_name: agentName },
            status: normalizedStatus
          };
          return [...prev, activityAction];
        });

      } catch (err) {
        console.error('Error parsing agent_activity event:', err);
      }
    });

    eventSource.addEventListener('agent_working', (e) => {
      try {
        const activityData = JSON.parse(e.data);
        const agent = activityData.agent || 'agent';
        const action = activityData.action || 'working';
        const description = activityData.description || activityData.details || '';
        const progress = activityData.progress || 0;
        const agentName = activityData.agent_name || agent.charAt(0).toUpperCase() + agent.slice(1).replace(/_/g, ' ');

        setCurrentAgent(agent);
        setCurrentAction(action);
        setCurrentDescription(description);
        setCurrentProgress(progress);

        setStatusUpdates(prev => [...prev, {
          timestamp: new Date(),
          agent: agent,
          action: action,
          description: description,
          status: 'running'
        }].slice(-10));

        const statusText = (activityData.status || 'running').toLowerCase();
        const normalizedStatus = statusText.includes('error') || statusText.includes('failed')
          ? 'error'
          : statusText.includes('completed') || statusText.includes('done')
            ? 'completed'
            : 'running';

        setAgentActions(prev => {
          const last = prev[prev.length - 1];
          if (
            last &&
            last.type === 'agent_activity' &&
            last.metadata?.agent === agent &&
            last.metadata?.action === action &&
            last.content === description
          ) {
            return prev;
          }
          const activityAction: AgentAction = {
            id: `activity-${jobId}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            type: 'agent_activity',
            timestamp: new Date(),
            title: `${agentName} · ${action}`,
            content: description || activityData.query || '',
            metadata: { ...activityData, agent, action, agent_name: agentName },
            status: normalizedStatus
          };
          return [...prev, activityAction];
        });
      } catch (err) {
        console.error('Error parsing agent_working event:', err);
      }
    });

    eventSource.addEventListener('agent_stream', (e) => {
      try {
        const streamData = JSON.parse(e.data);
        const tabId = streamData.tab_id;
        const chunk = streamData.chunk || '';
        const content = streamData.content || '';
        const isCompleted = streamData.completed === true;

        if (streamData.agent === 'planner' && Array.isArray(streamData.metadata?.steps)) {
          setPlannerSteps(normalizePlannerSteps(streamData.metadata.steps));
        }

        setTabs(prev => {
          const existingTab = prev.find(t => t.id === tabId);

          if (existingTab) {
            const updatedTabs = prev.map(tab => {
              if (tab.id === tabId) {
                return {
                  ...tab,
                  data: {
                    ...tab.data,
                    content: content || (tab.data?.content || '') + chunk,
                    isStreaming: !isCompleted,
                    agent: streamData.agent || 'agent',
                    metadata: streamData.metadata || {}
                  }
                };
              }
              return tab;
            });
            return updatedTabs;
          } else {
            const agentName = streamData.agent || 'agent';
            const agentTab: Tab = {
              id: tabId,
              type: 'agent',
              title: `${agentName.charAt(0).toUpperCase() + agentName.slice(1)} Agent`,
              data: {
                content: content || chunk,
                isStreaming: !isCompleted,
                agent: agentName,
                type: streamData.type || 'content',
                metadata: streamData.metadata || {}
              },
              workspaceId: streamData.workspace_id || workspaceId,
            };

            setActiveTabId(tabId);
            setIsRightPanelOpen(true);

            return [...prev, agentTab];
          }
        });
      } catch (err) {
        console.error('Error parsing agent_stream event:', err);
      }
    });

    eventSource.addEventListener('file_created', (e) => {
      try {
        const eventData = JSON.parse(e.data);
        const fileAction: AgentAction = {
          id: `job-${jobId}-file-${Date.now()}`,
          type: 'file_write',
          timestamp: new Date(),
          title: `✅ File Created: ${eventData.path}`,
          content: `File created: ${eventData.path}`,
          metadata: { path: eventData.path, type: eventData.type },
          status: 'completed',
        };
        setAgentActions(prev => [...prev, fileAction]);

        const rawPath = eventData.full_path || eventData.path || '';
        const wsId = eventData.workspace_id || deriveWorkspaceId(rawPath) || workspaceId;
        const normalizedPath = normalizeWorkspacePath(rawPath, wsId);
        const filename = eventData.filename || normalizedPath.split('/').pop() || normalizedPath;
        const fileType = normalizedPath.includes('.') ? 'file' : 'folder';

        const fileTab: Tab = {
          id: `file-${normalizedPath}-${Date.now()}`,
          type: 'file',
          title: filename,
          data: {
            name: filename,
            path: normalizedPath,
            type: fileType,
            workspaceId: wsId
          },
          workspaceId: wsId,
        };

        setTabs(prev => {
          const exists = prev.find(t => t.data?.path === normalizedPath);
          if (exists) {
            setActiveTabId(exists.id);
            return prev;
          }
          return [...prev, fileTab];
        });
        setActiveTabId(fileTab.id);
        setIsRightPanelOpen(true);

        window.dispatchEvent(new Event('workspace-refresh'));
      } catch (err) {
        console.error('Error parsing file_created event:', err);
      }
    });

    eventSource.addEventListener('file_updated', (e) => {
      try {
        const eventData = JSON.parse(e.data);
        const rawPath = eventData.full_path || eventData.path || '';
        const wsId = eventData.workspace_id || deriveWorkspaceId(rawPath) || workspaceId;
        const normalizedPath = normalizeWorkspacePath(rawPath, wsId);

        setTabs(prev => prev.map(tab => {
          if (tab.type !== 'file') return tab;
          if (tab.data?.path !== normalizedPath) return tab;
          return {
            ...tab,
            data: {
              ...tab.data,
              refreshedAt: Date.now()
            }
          };
        }));

        window.dispatchEvent(new Event('workspace-refresh'));
        window.dispatchEvent(new CustomEvent('workspace-file-updated', {
          detail: {
            path: normalizedPath,
            workspaceId: wsId
          }
        }));
      } catch (err) {
        console.error('Error parsing file_updated event:', err);
      }
    });

    eventSource.addEventListener('sources_updated', (e) => {
      try {
        const eventData = JSON.parse(e.data);
        if (eventData?.count) {
          setSourcesRefreshKey(prev => prev + 1);
        }
      } catch (err) {
        console.error('Error parsing sources_updated event:', err);
      }
    });

    eventSource.addEventListener('agent_activity', (e) => {
      try {
        const activityData = JSON.parse(e.data);
        const agent = activityData.agent || 'agent';
        const action = activityData.action || 'working';
        const query = activityData.query || '';
        const status = activityData.status || 'running';

        const normalizedAgent = agent.toLowerCase();
        const agentType = (activityData.agent_type || '').toLowerCase();
        const explicitAgents = new Set([
          'search',
          'research',
          'researcher',
          'image_search',
          'image_generator',
          'research_swarm',
          'writer_swarm',
          'quality_control',
          'quality_swarm',
          'chapter_generator',
          'intro_writer',
          'background_writer',
          'problem_writer',
          'scope_writer',
          'justification_writer',
          'objectives_writer',
          'planner'
        ]);
        const agentPattern = /(writer|swarm|quality|research|search|chapter|dataset|tool|analysis|discussion|conclusion|methodology|literature|framework|empirical)/i;
        const shouldOpenAgentTab = !['assistant', 'system'].includes(normalizedAgent)
          && (explicitAgents.has(normalizedAgent)
            || agentPattern.test(normalizedAgent)
            || ['understanding', 'research', 'action', 'verification'].includes(agentType));
        const agentActivityStatusText = (status || '').toLowerCase();
        const isAgentActivityCompleted = agentActivityStatusText.includes('completed') || agentActivityStatusText.includes('done') || agentActivityStatusText.includes('success');
        const agentActivityAutoCloseAgents = new Set([
          'research_swarm',
          'writer_swarm',
          'quality_swarm',
          'quality_control',
          'analysis_swarm',
          'discussion_swarm',
          'conclusion_swarm'
        ]);
        const agentActivityAutoClosePattern = /(writer|swarm|quality|research|analysis|discussion|conclusion|methodology|literature|framework|empirical|dataset|tool)/i;
        const shouldAutoCloseAgentActivity = isAgentActivityCompleted && (agentActivityAutoCloseAgents.has(normalizedAgent) || agentActivityAutoClosePattern.test(normalizedAgent));

        if (shouldOpenAgentTab) {
          const tabId = `${agent}-${jobId}`;
          const icon = activityData.icon || '🤖';
          const agentName = activityData.agent_name || agent.charAt(0).toUpperCase() + agent.slice(1).replace(/_/g, ' ');

          setTabs(prev => {
            const existingTab = prev.find(t => t.id === tabId);

            if (existingTab) {
              if (status === 'running') {
                setActiveTabId(tabId);
                setIsRightPanelOpen(true);
              }
              return prev.map(tab => {
                if (tab.id === tabId) {
                  return {
                    ...tab,
                    title: `${icon} ${agentName}`,
                    data: {
                      ...tab.data,
                      query: query,
                      action: action,
                      status: status,
                      results: activityData.results || tab.data?.results,
                      content: activityData.content || tab.data?.content || '',
                      isStreaming: status === 'running'
                    }
                  };
                }
                return tab;
              });
            } else {
              const agentTab: Tab = {
                id: tabId,
                type: 'agent',
                title: `${icon} ${agentName}`,
                data: {
                  agent: agent,
                  query: query,
                  action: action,
                  status: status,
                  results: activityData.results,
                  content: activityData.content || '',
                  isStreaming: status === 'running',
                  type: agent.includes('search') ? 'search' : 'activity',
                  metadata: activityData
                },
                workspaceId: workspaceId,
              };

              if (agent === 'chapter_generator' || agent === 'research_swarm' || agent === 'writer_swarm' || agent === 'research') {
                setActiveTabId(tabId);
                setIsRightPanelOpen(true);

                if (/(search|research|internet_search)/i.test(agent)) {
                  window.dispatchEvent(new CustomEvent('open-browser-tab', {
                    detail: {
                      title: `🌐 ${agentName}`,
                      sessionId: sessionId || 'default',
                      workspaceId: workspaceId
                    }
                  }));
                }
              }

              return [...prev, agentTab];
            }
          });

          if (shouldAutoCloseAgentActivity) {
            scheduleAutoCloseTab(tabId);
          }
        }

        setCurrentStage(agent);
        setCurrentStatus(`${agent} ${action}: ${query || ''}`);
      } catch (err) {
        console.error('Error parsing agent_activity event:', err);
      }
    });

    eventSource.addEventListener('agent_working', (e) => {
      try {
        const activityData = JSON.parse(e.data);
        const agent = activityData.agent || 'agent';
        const action = activityData.action || 'working';
        const query = activityData.query || '';
        const status = activityData.status || 'running';

        const normalizedAgent = agent.toLowerCase();
        const agentType = (activityData.agent_type || '').toLowerCase();
        const explicitAgents = new Set([
          'search',
          'research',
          'researcher',
          'image_search',
          'image_generator',
          'research_swarm',
          'writer_swarm',
          'quality_control',
          'quality_swarm',
          'chapter_generator',
          'intro_writer',
          'background_writer',
          'problem_writer',
          'scope_writer',
          'justification_writer',
          'objectives_writer',
          'planner'
        ]);
        const agentPattern = /(writer|swarm|quality|research|search|chapter|dataset|tool|analysis|discussion|conclusion|methodology|literature|framework|empirical)/i;
        const shouldOpenAgentTab = !['assistant', 'system'].includes(normalizedAgent)
          && (explicitAgents.has(normalizedAgent)
            || agentPattern.test(normalizedAgent)
            || ['understanding', 'research', 'action', 'verification'].includes(agentType));
        const agentWorkingStatusText = (status || '').toLowerCase();
        const isAgentWorkingCompleted = agentWorkingStatusText.includes('completed') || agentWorkingStatusText.includes('done') || agentWorkingStatusText.includes('success');
        const agentWorkingAutoCloseAgents = new Set([
          'research_swarm',
          'writer_swarm',
          'quality_swarm',
          'quality_control',
          'analysis_swarm',
          'discussion_swarm',
          'conclusion_swarm'
        ]);
        const agentWorkingAutoClosePattern = /(writer|swarm|quality|research|analysis|discussion|conclusion|methodology|literature|framework|empirical|dataset|tool)/i;
        const shouldAutoCloseAgentWorking = isAgentWorkingCompleted && (agentWorkingAutoCloseAgents.has(normalizedAgent) || agentWorkingAutoClosePattern.test(normalizedAgent));

        if (shouldOpenAgentTab) {
          const tabId = `${agent}-${jobId}`;
          const icon = activityData.icon || '🤖';
          const agentName = activityData.agent_name || agent.charAt(0).toUpperCase() + agent.slice(1).replace(/_/g, ' ');

          setTabs(prev => {
            const existingTab = prev.find(t => t.id === tabId);

            if (existingTab) {
              if (status === 'running') {
                setActiveTabId(tabId);
                setIsRightPanelOpen(true);
              }
              return prev.map(tab => {
                if (tab.id === tabId) {
                  return {
                    ...tab,
                    title: `${icon} ${agentName}`,
                    data: {
                      ...tab.data,
                      query: query,
                      action: action,
                      status: status,
                      results: activityData.results || tab.data?.results,
                      content: activityData.content || tab.data?.content || '',
                      isStreaming: status === 'running'
                    }
                  };
                }
                return tab;
              });
            } else {
              const agentTab: Tab = {
                id: tabId,
                type: 'agent',
                title: `${icon} ${agentName}`,
                data: {
                  agent: agent,
                  query: query,
                  action: action,
                  status: status,
                  results: activityData.results,
                  content: activityData.content || '',
                  isStreaming: status === 'running',
                  type: agent.includes('search') ? 'search' : 'activity',
                  metadata: activityData
                },
                workspaceId: workspaceId,
              };

              if (agent === 'chapter_generator' || agent === 'research_swarm' || agent === 'writer_swarm' || agent === 'research') {
                setActiveTabId(tabId);
                setIsRightPanelOpen(true);

                if (/(search|research|internet_search)/i.test(agent)) {
                  window.dispatchEvent(new CustomEvent('open-browser-tab', {
                    detail: {
                      title: `🌐 ${agentName}`,
                      sessionId: sessionId || 'default',
                      workspaceId: workspaceId
                    }
                  }));
                }
              }

              return [...prev, agentTab];
            }
          });

          if (shouldAutoCloseAgentWorking) {
            scheduleAutoCloseTab(tabId);
          }
        }

        setCurrentStage(agent);
        setCurrentStatus(`${agent} ${action}: ${query || ''}`);
      } catch (err) {
        console.error('Error parsing agent_working event:', err);
      }
    });

    eventSource.addEventListener('tool_started', (e) => {
      try {
        const toolData = JSON.parse(e.data);
        setCurrentStage(toolData.tool || '');
        setCurrentStatus(`Executing ${toolData.tool} (step ${toolData.step}/${toolData.total})...`);
        const toolName = toolData.tool || 'tool';
        const toolAction: AgentAction = {
          id: `tool-${jobId}-${toolName}-${toolData.step || Date.now()}`,
          type: 'tool_call',
          timestamp: new Date(),
          title: `🧰 ${toolName}`,
          content: toolData.message || (toolData.step ? `Step ${toolData.step}/${toolData.total || '?'}` : ''),
          metadata: toolData,
          status: 'running'
        };
        setAgentActions(prev => [...prev, toolAction]);
      } catch (err) {
        console.error('Error parsing tool_started event:', err);
      }
    });

    eventSource.addEventListener('tool_completed', (e) => {
      try {
        const toolData = JSON.parse(e.data);
        setCurrentStatus(`✓ ${toolData.tool} completed`);
        const toolName = toolData.tool || 'tool';
        setAgentActions(prev => {
          const index = [...prev].reverse().findIndex(action =>
            action.type === 'tool_call' &&
            action.metadata?.tool === toolName &&
            action.status === 'running'
          );
          if (index < 0) return prev;
          const targetIndex = prev.length - 1 - index;
          const updated = [...prev];
          updated[targetIndex] = {
            ...updated[targetIndex],
            status: 'completed',
            content: toolData.message || updated[targetIndex].content,
            metadata: { ...updated[targetIndex].metadata, ...toolData }
          };
          return updated;
        });
      } catch (err) {
        console.error('Error parsing tool_completed event:', err);
      }
    });

    eventSource.addEventListener('agent_working', (e) => {
      try {
        const agentData = JSON.parse(e.data);
        const { agent, agent_name, status, action, icon } = agentData;

        setActiveAgents(prev => {
          const existing = prev.find(a => a.agent === agent);
          if (existing) {
            return prev.map(a => a.agent === agent
              ? { ...a, status, action, icon }
              : a
            );
          } else {
            return [...prev, { agent, agent_name, status, action, icon }];
          }
        });

        if (status === 'running') {
          const tabId = `${agent}-${jobId}`;
          setActiveTabId(tabId);
          setIsRightPanelOpen(true);
        }

        if (agent) {
          const activityTitle = `${agent_name || agent} · ${action || 'working'}`;
          setAgentActions(prev => {
            const last = prev[prev.length - 1];
            if (last && last.type === 'agent_activity' && last.title === activityTitle && last.status === status) {
              return prev;
            }
            const activityAction: AgentAction = {
              id: `agent-working-${jobId}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              type: 'agent_activity',
              timestamp: new Date(),
              title: activityTitle,
              content: agentData.details || agentData.description || '',
              metadata: agentData,
              status: status === 'completed' ? 'completed' : status === 'error' ? 'error' : 'running'
            };
            return [...prev, activityAction];
          });
        }
      } catch (err) {
        console.error('Error parsing agent_working event:', err);
      }
    });

    eventSource.addEventListener('step_started', (e) => {
      try {
        const stepData = JSON.parse(e.data);
        const stepId = `step-${stepData.step || stepData.name || 'unknown'}`;
        const label = stepData.name || `Step ${stepData.step || ''}`.trim();
        setProgressSteps(prev => {
          const existingIndex = prev.findIndex(step => step.id === stepId);
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = { ...updated[existingIndex], label, name: label, status: 'running' };
            return updated;
          }
          return [...prev, { id: stepId, label, name: label, status: 'running', timestamp: new Date() }];
        });
        setCurrentStatus(label);
      } catch (err) {
        console.error('Error parsing step_started event:', err);
      }
    });

    eventSource.addEventListener('step_completed', (e) => {
      try {
        const stepData = JSON.parse(e.data);
        const stepId = `step-${stepData.step || stepData.name || 'unknown'}`;
        const label = stepData.name || `Step ${stepData.step || ''}`.trim();
        setProgressSteps(prev => {
          const existingIndex = prev.findIndex(step => step.id === stepId);
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = { ...updated[existingIndex], label, name: label, status: 'completed' };
            return updated;
          }
          return [...prev, { id: stepId, label, name: label, status: 'completed', timestamp: new Date() }];
        });
      } catch (err) {
        console.error('Error parsing step_completed event:', err);
      }
    });

    eventSource.addEventListener('stage_started', (e) => {
      try {
        const stageData = JSON.parse(e.data);
        setCurrentStage(stageData.stage || '');
        setCurrentStatus(stageData.message || `Starting ${stageData.stage}...`);

        if (stageData.stage === 'web_search' || stageData.stage === 'browse' || stageData.stage === 'browser') {
          window.dispatchEvent(new CustomEvent('open-browser-tab', {
            detail: {
              title: stageData.message || '🌐 Live Browser',
              sessionId: sessionId || 'default',
              workspaceId: workspaceId
            }
          }));
        }

        const label = stageData.message || `Starting ${stageData.stage}...`;
        const newStep = {
          id: `stage-${stageData.stage}-${Date.now()}`,
          label,
          name: label,
          status: 'running' as const,
          timestamp: new Date()
        };
        setProgressSteps(prev => [...prev, newStep]);
      } catch (err) {
        console.error('Error parsing stage_started event:', err);
      }
    });

    eventSource.addEventListener('reasoning_chunk', (e) => {
      try {
        const chunkData = JSON.parse(e.data);
        const accumulated = chunkData.accumulated || '';

        setAgentActions(prev => {
          const existingIndex = prev.findIndex(
            action => action.type === 'thinking' && action.id?.startsWith(`job-${jobId}-reasoning`)
          );

          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = {
              ...updated[existingIndex],
              content: accumulated,
              isStreaming: true,
              status: 'running'
            };
            return updated;
          } else {
            const reasoningAction: AgentAction = {
              id: `job-${jobId}-reasoning-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              type: 'thinking',
              timestamp: new Date(),
              title: '',
              content: accumulated,
              metadata: {},
              status: 'running',
              isStreaming: true
            };
            return [...prev, reasoningAction];
          }
        });
      } catch (err) {
        console.error('Error parsing reasoning_chunk event:', err);
      }
    });

    eventSource.addEventListener('response_chunk', (e) => {
      try {
        const jobType = activeJobsRef.current[jobId]?.type;
        if (jobType === 'good') {
          return;
        }
        const chunkData = JSON.parse(e.data);
        const accumulated = chunkData.accumulated || '';
        const targetMessageId = jobReplacementRef.current[jobId] || resolvedMessageId;
        latestAssistantContentRef.current[targetMessageId] = accumulated;

        setChatMessages(prev => {
          const existingIndex = prev.findIndex(
            msg => msg.id === targetMessageId
          );

          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = {
              ...updated[existingIndex],
              content: accumulated,
              isStreaming: true,
              agent: 'assistant',
              metadata: {
                ...updated[existingIndex].metadata,
                progress: currentProgress
              }
            };
            return updated;
          } else {
            const chatMessage: ChatMessage = {
              id: targetMessageId,
              type: 'assistant',
              content: accumulated,
              timestamp: new Date(),
              isStreaming: true,
              agent: 'assistant',
              metadata: {
                progress: currentProgress
              }
            };
            return [...prev, chatMessage];
          }
        });

        setAgentActions(prev => {
          const existingIndex = prev.findIndex(
            action => action.type === 'stream' && action.id.startsWith(`job-${jobId}-response`)
          );

          if (existingIndex >= 0) {
            const updated = [...prev];
            if (accumulated.length >= (updated[existingIndex].content?.length || 0)) {
              updated[existingIndex] = {
                ...updated[existingIndex],
                content: accumulated,
                isStreaming: true,
                status: 'running'
              };
            }
            return updated;
          } else {
            const streamAction: AgentAction = {
              id: `job-${jobId}-response-main`,
              type: 'stream',
              timestamp: new Date(),
              title: '✨ Response',
              content: accumulated,
              metadata: {},
              status: 'running',
              isStreaming: true
            };
            return [...prev, streamAction];
          }
        });
      } catch (err) {
        console.error('Error parsing response_chunk event:', err);
      }
    });

    eventSource.addEventListener('content', (e: any) => {
      try {
        const contentData = JSON.parse(e.data);
        const chunk = contentData.text || contentData.chunk || '';
        const targetMessageId = jobReplacementRef.current[jobId] || resolvedMessageId;

        setChatMessages(prev => {
          const existingIndex = prev.findIndex(msg => msg.id === targetMessageId);
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = {
              ...updated[existingIndex],
              content: (updated[existingIndex].content || '') + chunk,
              isStreaming: true
            };
            return updated;
          }
          return [...prev, {
            id: targetMessageId,
            type: 'assistant',
            content: chunk,
            timestamp: new Date(),
            isStreaming: true,
            agent: 'assistant'
          }];
        });
      } catch (err) {
        console.error('Error parsing content event:', err);
      }
    });

    eventSource.addEventListener('stage_completed', (e) => {

    eventSource.addEventListener('archived_response', (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload && payload.path) {
          const fileName = payload.path.split('/').pop() || 'response.md';
          addLog(`📝 Saved Markdown: ${fileName} (${payload.path})`);
          openTab('file', fileName, { name: fileName, path: payload.path, type: 'markdown' }, workspaceId);
        }
      } catch (err) {
        console.error('Failed to handle archived response event', err);
      }
    });
      try {
        const stageData = JSON.parse(e.data);
        const stage = stageData.stage || '';

        setProgressSteps(prev => prev.map(step =>
          step.id.includes(`stage-${stage}`) ? { ...step, status: 'completed' } : step
        ));

        if (stage === 'complete') {
          finalizeJob(true);
        }
      } catch (err) {
        console.error('Error parsing stage_completed event:', err);
      }
    });

    eventSource.addEventListener('done', () => {
      finalizeJob(true);
    });

    eventSource.onerror = (error) => {
      console.error('SSE stream error for job:', jobId, error);
      if (eventSource.readyState === EventSource.CLOSED) {
        console.error('SSE stream closed permanently for job:', jobId);
        setCurrentStatus('❌ Stream connection lost');
      }
    };
  }, [
    appendAssistantVariant,
    normalizePlannerSteps,
    registerActiveJob,
    sessionId,
    unregisterActiveJob,
    workspaceId,
    currentProgress
  ]);

  // Store interval ref for cleanup
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const jobStreamsRef = useRef<Record<string, EventSource>>({});
  const activeJobsRef = useRef<Record<string, ActiveJob>>({});
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);

  // Load chat messages from localStorage on mount
  useEffect(() => {
    try {
      setAssistantVariants({});
      setAssistantVariantIndex({});
      const saved = localStorage.getItem(`chat-messages-${workspaceId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Convert timestamp strings back to Date objects
        const messages = parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        setChatMessages(messages);
      }
    } catch (e) {
      console.error('Failed to load chat messages:', e);
    }
  }, [workspaceId]);

  // Save chat messages to localStorage when they change
  useEffect(() => {
    if (chatMessages.length > 0) {
      try {
        localStorage.setItem(`chat-messages-${workspaceId}`, JSON.stringify(chatMessages));
      } catch (e) {
        console.error('Failed to save chat messages:', e);
      }
    }
  }, [chatMessages, workspaceId]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('active_jobs');
      if (!saved) return;
      const parsed = JSON.parse(saved);
      if (!Array.isArray(parsed)) return;
      parsed
        .filter((job: ActiveJob) => job && job.jobId && (!job.workspaceId || job.workspaceId === workspaceId))
        .forEach((job: ActiveJob) => {
          const streamSessionId = job.sessionId || sessionId || 'new';
          const responseMessageId = job.responseMessageId || `chat-${job.jobId}-response`;
          startJobStream({
            jobId: job.jobId,
            streamSessionId,
            responseMessageId,
            type: job.type || 'general',
            resume: true
          });
        });
    } catch (error) {
      console.error('Failed to restore active jobs:', error);
    }
  }, [workspaceId, sessionId, startJobStream]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
        streamIntervalRef.current = null;
      }
    };
  }, []);

  // Handle file opening from workspace - opens as a new tab
  const handleOpenFilePreview = useCallback((e: any) => {
    const { path, type } = e.detail;
    // console.log('📂 Opening file from notification:', path);

    const fileTab: Tab = {
      id: `file-${path}-${Date.now()}`,
      type: 'file',
      title: path.split('/').pop() || path,
      data: { path, workspaceId },
      workspaceId,
    };

    setTabs(prev => {
      const exists = prev.find(t => t.data?.path === path);
      if (exists) {
        setActiveTabId(exists.id);
        return prev;
      }
      return [...prev, fileTab];
    });
    setActiveTabId(fileTab.id);
    setIsRightPanelOpen(true);
  }, [workspaceId]);

  const handleOpenDetailsPreview = useCallback((e: Event) => {
    const detail = (e as CustomEvent).detail;
    if (!detail || !detail.content) return;

    const newTab: Tab = {
      id: `details-${Date.now()}`,
      type: 'agent',
      title: detail.title || 'Details',
      data: {
        content: detail.content,
        type: detail.type || 'text'
      },
      workspaceId: workspaceId
    };

    setTabs(prev => {
      const existing = prev.find(t => t.data?.content === detail.content);
      if (existing) {
        setActiveTabId(existing.id);
        return prev;
      }
      return [...prev, newTab];
    });
    setActiveTabId(newTab.id);
    setIsRightPanelOpen(true);
  }, [workspaceId]);

  // Handler for opening browser preview tab
  const handleOpenBrowserTab = useCallback((e: Event) => {
    const detail = (e as CustomEvent).detail || {};

    const derivedWorkspaceId = detail.workspaceId || workspaceId || (detail.sessionId ? `ws_${detail.sessionId.substring(0, 12)}` : 'default');
    const browserTab: Tab = {
      id: `browser-${Date.now()}`,
      type: 'browser',
      title: detail.title || '🌐 Live Browser',
      data: {
        sessionId: detail.sessionId || 'default',
        url: detail.url || ''
      },
      workspaceId: derivedWorkspaceId
    };

    setTabs(prev => {
      // Check if browser tab already exists
      const existing = prev.find(t => t.type === 'browser');
      if (existing) {
        setActiveTabId(existing.id);
        return prev;
      }
      return [...prev, browserTab];
    });
    setActiveTabId(browserTab.id);
    setIsRightPanelOpen(true);
  }, [workspaceId]);

  // Add event listeners
  useEffect(() => {
    window.addEventListener('open-file-preview', handleOpenFilePreview as EventListener);
    window.addEventListener('open-details-preview', handleOpenDetailsPreview as EventListener);
    window.addEventListener('open-browser-tab', handleOpenBrowserTab as EventListener);

    return () => {
      window.removeEventListener('open-file-preview', handleOpenFilePreview as EventListener);
      window.removeEventListener('open-details-preview', handleOpenDetailsPreview as EventListener);
      window.removeEventListener('open-browser-tab', handleOpenBrowserTab as EventListener);
      if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
    };
  }, [handleOpenFilePreview, handleOpenDetailsPreview]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + P to toggle progress panel (optional/insights panel)
      if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
        e.preventDefault();
        setIsProgressPanelOpen(prev => !prev);
      }
      // Cmd/Ctrl + B to toggle left panel
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        setIsLeftPanelCollapsed(prev => !prev);
      }
      // Escape to close progress panel
      if (e.key === 'Escape' && isProgressPanelOpen) {
        setIsProgressPanelOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isProgressPanelOpen]);

  // Handle university thesis generation
  const handleUniversityThesisGeneration = async (universityType: string, userInput: string, parameters?: ThesisParameters) => {
    setIsProcessing(true);
    setLiveResponse('');
    setCurrentStatus(`📚 Generating thesis for ${universityType}...`);
    setCurrentStage('thesis_generation');

    // Add user message
    const userChatMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: userInput ? `/${universityType} ${userInput}` : `/${universityType}`,
      timestamp: new Date(),
      isStreaming: false
    };
    setChatMessages(prev => [...prev, userChatMessage]);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

      // If no additional input, ask the user for thesis details
      if (!userInput || userInput.length < 10) {
        // Track selected university for follow-up messages (only when asking for details)
        setSelectedUniversity(universityType);

        const assistantResponse: ChatMessage = {
          id: `assistant-${Date.now()}`,
          type: 'assistant',
          content: `Great! I'll help you generate a **COMPLETE PhD thesis** for **${universityType}**. 

## What I'll Generate:
- 📖 **Chapter 1:** Introduction (with citations)
- 📚 **Chapter 2:** Literature Review (50+ academic sources)
- 🔬 **Chapter 3:** Methodology
- 📋 **Study Tools:** Questionnaire, Interview Guide
- 📊 **Dataset:** Synthetic research data (385 respondents)
- 📈 **Chapter 4:** Data Presentation & Analysis
- 💬 **Chapter 5:** Discussion of Findings
- 🎯 **Chapter 6:** Conclusion & Recommendations

---

## How to Start:

**Option 1 - Just Topic (I'll auto-generate objectives):**
\`\`\`
THE ROLE OF MODERN MILITARY TECHNOLOGY IN STRENGTHENING SOUTH SUDAN'S DEFENSE CAPABILITIES
\`\`\`

**Option 2 - Topic + Your Own Objectives:**
\`\`\`
Topic: THE ROLE OF MODERN MILITARY TECHNOLOGY IN STRENGTHENING SOUTH SUDAN'S DEFENSE CAPABILITIES
Objectives:
1. To evaluate the current state of SSPDF's technological infrastructure
2. To examine strategic opportunities for defense modernization
3. To analyze political, financial, and legal impediments
4. To formulate a strategic roadmap for phased technology integration
\`\`\`

⏱️ **Time:** 10-15 minutes for complete thesis
📄 **Output:** Combined PDF-ready thesis + individual chapter files`,
          timestamp: new Date(),
          isStreaming: false
        };
        setChatMessages(prev => [...prev, assistantResponse]);
        syncProcessingState();
        return;
      }

      // Parse user input for thesis details
      // User can provide: "Title: X Topic: Y" or just "Topic: Y" or even just "Y"
      const titleMatch = userInput.match(/(?:Title|title):\s*(.+?)(?:\n|Topic|topic|$)/);
      const topicMatch = userInput.match(/(?:Topic|topic):\s*(.+?)(?:\n|Objectives|objectives|$)/);
      const objectivesMatch = userInput.match(/(?:Objectives|objectives):\s*([\s\S]+?)$/i);

      const title = titleMatch ? titleMatch[1].trim() : 'Research Thesis';
      const topic = topicMatch ? topicMatch[1].trim() : userInput;

      const parseObjectiveLines = (text: string) => text
        .split(/\n/)
        .map(obj => obj.replace(/^\s*\d+\.\s*/, '').replace(/^\s*[-•]\s*/, '').trim())
        .filter(obj => obj.length > 5);

      const paramObjectives: string[] = [];
      const generalObjective = parameters?.generalObjective?.trim();
      if (generalObjective) {
        const normalized = generalObjective.toLowerCase().startsWith('general objective')
          ? generalObjective
          : `General Objective: ${generalObjective}`;
        paramObjectives.push(normalized);
      }
      const specificObjectives = parameters?.specificObjectives || [];
      if (specificObjectives.length > 0) {
        paramObjectives.push(...specificObjectives);
      }

      // Parse objectives - handle numbered lists (1. 2. 3.) and bullet points
      const objectives = objectivesMatch
        ? parseObjectiveLines(objectivesMatch[1])
        : []; // Empty array means backend will auto-generate objectives

      const sampleSizeMatch = userInput.match(/\b(n|sample[ _]size)\s*[:=]\s*(\d+)/i);
      const mergedParameters = parameters ? { ...parameters } : undefined;
      if (mergedParameters?.studyType) {
        const studyNote = `Study Type: ${mergedParameters.studyType}`;
        mergedParameters.customInstructions = mergedParameters.customInstructions
          ? `${mergedParameters.customInstructions}\n${studyNote}`
          : studyNote;
      }

      const sampleSize = mergedParameters?.sampleSize
        || (sampleSizeMatch ? parseInt(sampleSizeMatch[2], 10) : undefined)
        || 385;

      // Call thesis generation API
      const objectivePayload = paramObjectives.length > 0
        ? {
            general: paramObjectives.find((obj) => obj.toLowerCase().startsWith('general objective')) || '',
            specific: paramObjectives.filter((obj) => !obj.toLowerCase().startsWith('general objective'))
          }
        : (objectives.length > 0 ? objectives : [topic]);

      const thesisResponse = await fetch(`${backendUrl}/api/thesis/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          university_type: universityType,
          title: title,
          topic: topic,
          objectives: objectivePayload,
          workspace_id: workspaceId,
          parameters: mergedParameters
        }),
      });

      if (!thesisResponse.ok) {
        throw new Error(`Thesis generation failed: ${thesisResponse.statusText}`);
      }

      const thesisData = await thesisResponse.json();

      // Check if this is async generation (background job)
      if (thesisData.status === 'generating' && thesisData.job_id) {
        // Build objectives display
        const objectivesDisplay = thesisData.objectives && thesisData.objectives.length > 0
          ? thesisData.objectives.map((obj: string, i: number) => `${i + 1}. ${obj}`).join('\n')
          : 'Auto-generating 6 research objectives...';

        // Conditional Pipeline Display
        const isGeneral = universityType === 'uoj_general';
        const pipelineTitle = isGeneral ? '🚀 GENERAL ACADEMIC THESIS GENERATION STARTED! (5 CHAPTERS)' : '🚀 COMPLETE PhD THESIS GENERATION STARTED!';

        let pipelineTable = '';
        if (isGeneral) {
          pipelineTable = `## 📊 Generation Pipeline (7 Steps)

| Step | Component | Status |
|------|-----------|--------|
| 1 | Chapter 1: Introduction | ⏳ Pending |
| 2 | Chapter 2: Literature Review (General + Empirical) | ⏳ Pending |
| 3 | Chapter 3: Methodology (8 Sections) | ⏳ Pending |
| 4 | Study Tools (Questionnaire, Interview Guide) | ⏳ Pending |
| 5 | Synthetic Dataset (n=${sampleSize}) | ⏳ Pending |
| 6 | Chapter 4: Data Analysis (Tables & Figures) | ⏳ Pending |
| 7 | Chapter 5: Discussion, Conclusion & Recommendations | ⏳ Pending |`;
        } else {
          pipelineTable = `## 📊 Generation Pipeline (8 Steps)

| Step | Component | Status |
|------|-----------|--------|
| 1 | Chapter 1: Introduction | ⏳ Pending |
| 2 | Chapter 2: Literature Review (50+ sources) | ⏳ Pending |
| 3 | Chapter 3: Methodology | ⏳ Pending |
| 4 | Study Tools (Questionnaire, Interview Guide) | ⏳ Pending |
| 5 | Synthetic Dataset (n=${sampleSize}) | ⏳ Pending |
| 6 | Chapter 4: Data Analysis | ⏳ Pending |
| 7 | Chapter 5: Discussion | ⏳ Pending |
| 8 | Chapter 6: Conclusion & Recommendations | ⏳ Pending |`;
        }

        // Add status message - thesis is being generated in background
        const statusMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          type: 'assistant',
          content: `# ${pipelineTitle}

**University:** ${universityType}
**Title:** ${title}
**Topic:** ${topic}

## 📋 Research Objectives:
${objectivesDisplay}

---

${pipelineTable}

⏱️ **Estimated time:** ${isGeneral ? '5-8' : '10-15'} minutes for complete thesis

📡 **Job ID:** \`${thesisData.job_id}\`

---

*Progress updates will appear below as each chapter is generated...*`,
          timestamp: new Date(),
          isStreaming: true
        };
        setChatMessages(prev => [...prev, statusMessage]);
        setStreamingMessageId(statusMessage.id);
        setCurrentJobId(thesisData.job_id);

        // Show the universal progress overlay
        setProgressJobId(thesisData.job_id);
        setProgressTopic(topic);
        setProgressType('thesis');
        setShowProgressOverlay(true);

        // The popup now handles its own SSE connection
        // We can still keep a lightweight listener here for chat updates

        const streamSessionId = sessionId || 'new';
        startJobStream({ jobId: thesisData.job_id, streamSessionId, responseMessageId: statusMessage.id, type: 'thesis' });

        return; // Don't show the fake success message
      }

      // Synchronous generation (fallback for simple cases)
      const successMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: `✅ **Thesis Generated Successfully!**

**University:** ${universityType}
**Title:** ${title}
**File:** ${thesisData.file_path || 'No file created'}

${thesisData.message || 'Your thesis document has been created.'}`,
        timestamp: new Date(),
        isStreaming: false
      };
      setChatMessages(prev => [...prev, successMessage]);

      setCurrentStatus('✅ Thesis generated successfully!');
      syncProcessingState();
    } catch (error) {
      console.error('Thesis generation error:', error);
      const errorMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: `❌ Error generating thesis: ${error instanceof Error ? error.message : 'Unknown error'}

Please try again with the format:
\`\`\`
Title: Your thesis title
Topic: Your research topic
Objectives:
- Objective 1
- Objective 2
- Objective 3
\`\`\``,
        timestamp: new Date(),
        isStreaming: false
      };
      setChatMessages(prev => [...prev, errorMessage]);
      setCurrentStatus('Error: Thesis generation failed');
      syncProcessingState();
    }
  };

  const handleGoodFlow = async (userInput: string, parameters?: ThesisParameters) => {
    setIsProcessing(true);
    setLiveResponse('');
    setCurrentStatus('💾 Saving /good configuration...');
    setCurrentStage('good_flow');

    const userChatMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: userInput ? `/good ${userInput}` : '/good',
      timestamp: new Date(),
      isStreaming: false
    };
    setChatMessages(prev => [...prev, userChatMessage]);

    const fallbackTopic = userInput?.trim() || '';
    const topicMatch = fallbackTopic.match(/(?:Topic|topic|Title|title)\s*[:=]\s*(.+)/);
    const topic = (parameters?.topic || (topicMatch ? topicMatch[1] : fallbackTopic)).trim();
    const country = (parameters?.country || 'South Sudan').trim();
    const caseStudy = (parameters?.caseStudy || 'Juba, Central Equatoria State, South Sudan').trim();

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/good/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: workspaceId,
          session_id: sessionId || 'default',
          topic,
          country,
          case_study: caseStudy,
          objectives: parameters?.specificObjectives || [],
          uploaded_materials: parameters?.uploadedMaterials || [],
          literature_year_start: parameters?.literatureYearStart,
          literature_year_end: parameters?.literatureYearEnd,
          study_type: parameters?.studyType,
          population: parameters?.population,
          extra: {
            raw_input: userInput || ''
          }
        })
      });
      if (!response.ok) {
        throw new Error('Failed to save /good config');
      }
      const saved = await response.json();
      const configId = saved?.config?.id;

      const objectivesResponse = await fetch(`${backendUrl}/api/good/objectives`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: workspaceId,
          session_id: sessionId || 'default',
          config_id: configId,
          topic,
          case_study: caseStudy,
          country
        })
      });
      if (!objectivesResponse.ok) {
        throw new Error('Failed to start /good objectives generation');
      }
      const objectivesData = await objectivesResponse.json();
      if (objectivesData?.job_id) {
        startJobStream({
          jobId: objectivesData.job_id,
          streamSessionId: sessionId || 'default',
          type: 'good'
        });
      }

      setCurrentStatus('🧠 Generating specific objectives...');
    } catch (err) {
      const assistantResponse: ChatMessage = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: '❌ Failed to save /good configuration. Please try again.',
        timestamp: new Date(),
        isStreaming: false
      };
      setChatMessages(prev => [...prev, assistantResponse]);
      setCurrentStatus('❌ /good configuration failed');
    } finally {
      syncProcessingState();
    }
  };

  // Handle PDF + dataset uploads
  const handleFileUpload = async (files: File[]) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const pdfFiles = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
      const datasetExtensions = ['.csv', '.tsv', '.xlsx', '.xls', '.sav', '.dta', '.json'];
      const datasetFiles = files.filter(file =>
        datasetExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
      );

      if (pdfFiles.length === 0 && datasetFiles.length === 0) {
        console.warn('No supported files selected');
        return;
      }

      // 1. Create a persistent progress message
      const progressId = `upload-progress-${Date.now()}`;
      const totalUploads = pdfFiles.length + datasetFiles.length;
      setChatMessages(prev => [...prev, {
        id: progressId,
        role: 'assistant',
        content: `🚀 Starting upload of ${totalUploads} file(s)...`,
        timestamp: new Date(),
        type: 'assistant',
      }]);

      const allResults = [];
      const datasetResults: Array<{ filename: string }> = [];
      const failed = [];

      // 2. Upload files one by one to show progress
      let uploadedCount = 0;
      for (let i = 0; i < pdfFiles.length; i++) {
        const file = pdfFiles[i];
        uploadedCount += 1;

        // Update progress message
        setChatMessages(prev => prev.map(msg =>
          msg.id === progressId
            ? { ...msg, content: `⏳ Uploading file ${uploadedCount} of ${totalUploads}:\n**${file.name}**...` }
            : msg
        ));

        const formData = new FormData();
        formData.append('files', file);

        try {
          const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/upload-pdfs`, {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) throw new Error(response.statusText);

          const result = await response.json();
          if (result.results && result.results.length > 0) {
            allResults.push(...result.results);
          }
          if (result.errors && result.errors.length > 0) {
            failed.push(...result.errors);
          }
        } catch (err) {
          failed.push({ filename: file.name, error: String(err) });
        }
      }

      for (let i = 0; i < datasetFiles.length; i++) {
        const file = datasetFiles[i];
        uploadedCount += 1;

        setChatMessages(prev => prev.map(msg =>
          msg.id === progressId
            ? { ...msg, content: `⏳ Uploading file ${uploadedCount} of ${totalUploads}:\n**${file.name}**...` }
            : msg
        ));

        const formData = new FormData();
        formData.append('file', file);
        formData.append('description', '');

        try {
          const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/register-dataset`, {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) throw new Error(response.statusText);

          const result = await response.json();
          if (result.dataset) {
            datasetResults.push({ filename: result.dataset.filename || file.name });
          }
        } catch (err) {
          failed.push({ filename: file.name, error: String(err) });
        }
      }

      // 3. Remove progress message (or update it to completion)
      setChatMessages(prev => prev.filter(msg => msg.id !== progressId));

      // 4. Show final summary
      const successCount = allResults.length;
      const datasetCount = datasetResults.length;
      const failCount = failed.length;

      let summary = `✅ **Upload Complete**\nSuccessfully added ${successCount} source(s) and ${datasetCount} dataset(s).`;

      if (allResults.length > 0) {
        summary += `\n\n**📚 Added Sources:**\n` +
          allResults.map((r: any) => `• [${r.original_filename || r.filename}] ${r.title}`).join('\n');
      }

      if (datasetResults.length > 0) {
        summary += `\n\n**📊 Registered Datasets:**\n` +
          datasetResults.map((d) => `• ${d.filename}`).join('\n');
      }

      if (failCount > 0) {
        summary += `\n\n⚠️ **Failed:**\n` +
          failed.map((f: any) => `• ${f.filename}: ${f.error}`).join('\n');
      }

      setChatMessages(prev => [...prev, {
        id: `upload-report-${Date.now()}`,
        role: 'assistant',
        content: summary,
        timestamp: new Date(),
        type: 'assistant',
      }]);

      // Refresh workspace files
      window.dispatchEvent(new Event('workspace-refresh'));

      // Open sources tab if successful
      if (successCount > 0) {
        const sourcesTab: Tab = {
          id: `sources-${Date.now()}`,
          type: 'sources',
          title: '📚 Uploaded Sources',
          data: {
            sources: allResults,
            workspace_id: workspaceId
          },
          workspaceId: workspaceId,
        };

        setTabs(prev => {
          const existing = prev.find(t => t.type === 'sources');
          return existing ? prev.map(t => t.type === 'sources' ? sourcesTab : t) : [...prev, sourcesTab];
        });
        setActiveTabId(sourcesTab.id);
      }

    } catch (error) {
      console.error('PDF upload workflow error:', error);
      setChatMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `❌ Error during upload: ${String(error)}`,
        timestamp: new Date(),
        type: 'assistant',
      }]);
    }
  };

  const shouldUseAgentMode = useCallback((message: string): boolean => {
    const normalized = message.trim().toLowerCase();
    if (normalized.length > 180) {
      return true;
    }
    const keywords = [
      '/thesis',
      '/general',
      '/rag',
      '/agent',
      'generate chapter',
      'write chapter',
      'analysis',
      'analyze',
      'dataset',
      'xls',
      'csv',
      'pdf',
      'research',
      'methodology',
      'plot',
      'objective',
      'findings',
      'conclude',
      'recommendation',
      'experiment',
      'survey'
    ];
    return keywords.some(keyword => normalized.includes(keyword));
  }, []);

  const streamAgentTask = useCallback(async (message: string) => {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const agentMessageId = `agent-${Date.now()}`;
    const streamingMessage: ChatMessage = {
      id: agentMessageId,
      type: 'assistant',
      content: '🤖 Agent thinking...',
      timestamp: new Date(),
      isStreaming: true,
      agent: 'autonomous-agent'
    };
    setIsProcessing(true);
    setCurrentStatus('📡 Agent planning...');
    setChatMessages(prev => [...prev, streamingMessage]);

    try {
      const response = await fetch(`${backendUrl}/api/agent/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: message.trim(),
          workspace_id: workspaceId
        })
      });

      if (!response.ok) {
        throw new Error(`Agent error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          if (!event.startsWith('data:')) continue;
          try {
            const payload = JSON.parse(event.replace(/^data:\s*/, ''));
            if (payload.type === 'complete') {
              const resultText = payload.result?.result || payload.result || payload.result_text || '✅ Agent task complete.';
              setChatMessages(prev => prev.map(msg =>
                msg.id === agentMessageId ? { ...msg, content: resultText, isStreaming: false } : msg
              ));
              setCurrentStatus('✅ Agent complete');
              setIsProcessing(false);
            } else if (payload.type === 'error') {
              setChatMessages(prev => prev.map(msg =>
                msg.id === agentMessageId ? { ...msg, content: `❌ Agent error: ${payload.error}`, isStreaming: false } : msg
              ));
              setCurrentStatus('❌ Agent failed');
              setIsProcessing(false);
            } else if (payload.type === 'thought') {
              setChatMessages(prev => prev.map(msg =>
                msg.id === agentMessageId
                  ? { ...msg, content: `${msg.content}\n🧠 ${payload.content}` }
                  : msg
              ));
            }
          } catch (e) {
            console.warn('Failed to parse agent event', e);
          }
        }
      }

      reader?.releaseLock();
    } catch (error) {
      console.error('Agent task failed', error);
      setChatMessages(prev => prev.map(msg =>
        msg.id === agentMessageId ? { ...msg, content: `🛑 Agent error: ${error.message}`, isStreaming: false } : msg
      ));
      setCurrentStatus('❌ Agent error');
      setIsProcessing(false);
    }
  }, [workspaceId]);

  const handleChatStart = async (
    message?: string,
    mentionedAgents?: string[],
    parameters?: ThesisParameters,
    options?: {
      skipUserMessage?: boolean;
      replaceAssistantMessageId?: string;
      historyOverride?: ChatMessage[];
    }
  ) => {
    if (!message || !message.trim()) return;
    const skipUserMessage = options?.skipUserMessage === true;
    const replaceAssistantMessageId = options?.replaceAssistantMessageId;
    const historyForContext = options?.historyOverride || chatMessages;

    const goodMatch = message.trim().match(/^\/good(?:\s+([\s\S]*))?$/);
    if (goodMatch) {
      await handleGoodFlow((goodMatch[1] || '').trim(), parameters);
      return;
    }

    // Check if this is a university slash command
    // Match both: /uoj_phd and /uoj_phd some details
    const universityMatch = message.trim().match(/^\/(\w+)(?:\s+([\s\S]*))?$/);
    if (universityMatch) {
      const universityType = universityMatch[1];
      const restOfMessage = (universityMatch[2] || '').trim();

      // Check if it's a known university
      const validUniversities = ['uoj_phd', 'uoj_general', 'generic'];
      if (validUniversities.includes(universityType)) {
        // Handle university thesis generation
        // console.log(`📚 University selected: ${universityType}`);
        await handleUniversityThesisGeneration(universityType, restOfMessage, parameters);
        return;
      }
    }

    // Check if user is providing thesis details after selecting a university
    // If a university is selected, treat ANY non-slash message as thesis details
    if (selectedUniversity && !message.trim().startsWith('/')) {
      // console.log(`📚 Thesis details provided for ${selectedUniversity}: ${message.substring(0, 50)}...`);
      await handleUniversityThesisGeneration(selectedUniversity, message);
      setSelectedUniversity(null); // Clear selection after generation
      return;
    }

    // Keep previous jobs active; only reset planner for the new request
    setPlannerSteps([]);

    if (!skipUserMessage) {
      // Add user message to workspace immediately
      const userAction: AgentAction = {
        id: `user-${Date.now()}`,
        type: 'user_message',
        timestamp: new Date(),
        title: 'You',
        content: message.trim(),
        status: 'completed'
      };
      setAgentActions(prev => [...prev, userAction]);

      // Also add to chat messages
      const userChatMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        type: 'user',
        content: message.trim(),
        timestamp: new Date(),
        isStreaming: false
      };
      setChatMessages(prev => [...prev, userChatMessage]);
    }

    // Ensure we have a conversation context
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const convResponse = await fetch(`${backendUrl}/api/workspace/${workspaceId}/conversations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: message.trim().slice(0, 50) })
        });
        if (convResponse.ok) {
          const convData = await convResponse.json();
          currentSessionId = convData.conversation_id;
          setSessionId(currentSessionId);
        }
      } catch (e) {
        console.error('Failed to create conversation:', e);
        currentSessionId = 'new';
      }
    }

    if (!skipUserMessage) {
      // Post user message to backend memory
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        await fetch(`${backendUrl}/api/workspace/${workspaceId}/conversations/${currentSessionId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: 'user', content: message.trim() })
        });
      } catch (e) {
        console.error('Failed to persist user message:', e);
      }
    }

    if (shouldUseAgentMode(message)) {
      await streamAgentTask(message);
      return;
    }

    try {
      // Use backend directly - proxy is causing issues
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

      // Build conversation history for context (last 10 messages)
      const recentHistory = historyForContext.slice(-10).map(msg => ({
        role: msg.type === 'assistant' ? 'assistant' : 'user',
        content: msg.content
      }));

      console.log(`📤 Sending chat: workspace_id=${workspaceId}, session_id=${currentSessionId || sessionId}`);
      const response = await fetch(`${backendUrl}/api/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message.trim(),
          mentioned_agents: mentionedAgents || [],
          conversation_history: recentHistory,
          session_id: currentSessionId || sessionId,
          workspace_id: workspaceId
        }),
      });

      let data;
      if (!response.ok) {
        // Try to parse error response - it might still have job_id
        try {
          data = await response.json();
          // If we have job_id, continue to connect to stream even on error
          if (!data.job_id) {
            throw new Error(`Backend error: ${response.statusText}`);
          }
        } catch {
          throw new Error(`Backend error: ${response.statusText}`);
        }
      } else {
        // Check if response is SSE or JSON
        const contentType = response.headers.get('content-type');

        if (contentType?.includes('text/event-stream')) {
          // SSE response - consume the stream directly (for simple greetings/questions)
          // These are direct LLM responses that don't use job_id-based streaming
          const reader = response.body?.getReader();
          if (reader) {
            let accumulatedResponse = '';
            let jobId: string | null = null;
            const decoder = new TextDecoder();

            // Create a streaming chat message immediately
            const streamingMessageId = replaceAssistantMessageId || `chat-direct-${Date.now()}`;
            const streamingMessage: ChatMessage = {
              id: streamingMessageId,
              type: 'assistant',
              content: '',
              timestamp: new Date(),
              isStreaming: true,
              agent: 'assistant'
            };
            setChatMessages(prev => {
              const existingIndex = prev.findIndex(msg => msg.id === streamingMessageId);
              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = { ...updated[existingIndex], ...streamingMessage };
                return updated;
              }
              return [...prev, streamingMessage];
            });

            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value, { stream: true });

                // Parse SSE events from the text
                const lines = text.split('\n');
                for (const line of lines) {
                  // Check for job_id
                  const jobIdMatch = line.match(/"job_id":\s*"([^"]+)"/);
                  if (jobIdMatch) {
                    jobId = jobIdMatch[1];
                  }

                  // Parse "data:" lines for response content
                  if (line.startsWith('data:')) {
                    try {
                      const eventData = JSON.parse(line.slice(5).trim());
                      if (eventData.chunk) {
                        accumulatedResponse += eventData.chunk;
                        latestAssistantContentRef.current[streamingMessageId] = accumulatedResponse;
                        // Update the streaming message with accumulated content
                        setChatMessages(prev => prev.map(msg =>
                          msg.id === streamingMessageId
                            ? { ...msg, content: accumulatedResponse }
                            : msg
                        ));
                      } else if (eventData.accumulated) {
                        accumulatedResponse = eventData.accumulated;
                        latestAssistantContentRef.current[streamingMessageId] = accumulatedResponse;
                        setChatMessages(prev => prev.map(msg =>
                          msg.id === streamingMessageId
                            ? { ...msg, content: accumulatedResponse }
                            : msg
                        ));
                      }
                    } catch {
                      // Not valid JSON, skip
                    }
                  }
                }
              }

              // Mark message as complete
              setChatMessages(prev => prev.map(msg =>
                msg.id === streamingMessageId
                  ? { ...msg, isStreaming: false }
                  : msg
              ));
              if (replaceAssistantMessageId && accumulatedResponse) {
                appendAssistantVariant(replaceAssistantMessageId, accumulatedResponse);
              }

              // If we got a complete response, we're done
              if (accumulatedResponse) {
                syncProcessingState();
                setCurrentStatus('');
                return; // Exit early - response is complete
              }

              // If we extracted a job_id, use it for SSE connection
              data = { job_id: jobId };
            } catch (streamError) {
              console.error('Error reading SSE stream:', streamError);
              // Mark message as error state
              setChatMessages(prev => prev.map(msg =>
                msg.id === streamingMessageId
                  ? { ...msg, content: 'Error receiving response', isStreaming: false }
                  : msg
              ));
              syncProcessingState();
              return;
            }
          } else {
            data = { job_id: null };
          }
        } else {
          // JSON response
          data = await response.json();
        }
      }

      // Handle jobs with job_id - connect to real-time SSE stream (both queued and direct execution)
      if (data.job_id) {
        const jobId = data.job_id;
        const responseMessageId = replaceAssistantMessageId || `chat-${jobId}-response`;
        if (replaceAssistantMessageId) {
          jobReplacementRef.current[jobId] = replaceAssistantMessageId;
        }
        // console.log(`🔗 Connecting to SSE stream for job: ${jobId}`);
        setCurrentStatus('🔗 Connecting to real-time stream...');
        setIsProcessing(true); // Ensure processing state is set

        // Store job_id for SSE connection
        localStorage.setItem('current_job_id', jobId);

        // Show universal progress overlay for general agent job
        setProgressJobId(jobId);
        setProgressTopic(message.trim());
        setProgressType('general');
        setShowProgressOverlay(true);

        // Trigger SSE reconnect with new job_id
        window.dispatchEvent(new CustomEvent('job-id-updated', { detail: { jobId } }));

        // Don't show generic processing action - let streaming events handle display
        // Only show if there's actual meaningful content
        if (data.response && data.response.length > 100 && !data.response.toLowerCase().includes("processing")) {
          const responseAction: AgentAction = {
            id: `job-${jobId}-response-${Date.now()}`,
            type: 'stream',
            timestamp: new Date(),
            title: '🤖 AI Response',
            content: data.response,
            status: 'completed',
            isStreaming: false
          };
          setAgentActions(prev => [...prev, responseAction]);

          // ALSO add to chat messages so it displays in the chat UI
          const assistantChatMessage: ChatMessage = {
            id: responseMessageId,
            type: 'assistant',
            content: data.response,
            timestamp: new Date(),
            isStreaming: false,
            agent: 'assistant'
          };
          latestAssistantContentRef.current[responseMessageId] = data.response;
          setChatMessages(prev => {
            const existingIndex = prev.findIndex(msg => msg.id === responseMessageId);
            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = { ...updated[existingIndex], ...assistantChatMessage };
              return updated;
            }
            return [...prev, assistantChatMessage];
          });

          // Persist assistant message to backend memory
          try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            await fetch(`${backendUrl}/api/workspace/${workspaceId}/conversations/${currentSessionId || sessionId}/messages`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ role: 'assistant', content: data.response, job_id: jobId })
            });
          } catch (e) {
            console.error('Failed to persist assistant message:', e);
          }
        }

        const streamSessionId = currentSessionId || sessionId || 'new';
        startJobStream({ jobId, streamSessionId, responseMessageId, type: 'general' });
      }

      // Handle image generation directly - skip planning steps
      if (data.image_generation) {
        const imgGen = data.image_generation;
        if (imgGen.success && (imgGen.image_url || imgGen.image_data)) {
          // Create image action immediately
          const imageGenAction: AgentAction = {
            id: `image-gen-${Date.now()}`,
            type: 'research_result',
            timestamp: new Date(),
            title: `Generated Image: ${imgGen.prompt || 'Image'}`,
            content: data.response || 'Image generated successfully!',
            metadata: {
              tool: 'image_generate',
              prompt: imgGen.prompt,
              url: imgGen.image_url,
              image_data: imgGen.image_data,
              query: imgGen.prompt,
              images: [{
                url: imgGen.image_url,
                full: imgGen.image_url,
                title: imgGen.prompt || 'Generated Image',
                thumbnail: imgGen.image_url,
                source: 'generated'
              }]
            },
            status: 'completed',
          };

          setAgentActions(prev => [...prev, imageGenAction]);

          // Open in preview panel - show image directly, no progress panel
          const newTab: Tab = {
            id: `image-${Date.now()}`,
            type: 'image',
            title: `Generated: ${imgGen.prompt || 'Image'}`,
            data: {
              images: imageGenAction.metadata.images,
              query: imgGen.prompt,
              url: imgGen.image_url,
              image_data: imgGen.image_data
            },
            workspaceId: workspaceId,
          };
          setTabs(prev => {
            const exists = prev.find(t => t.id === newTab.id);
            if (exists) return prev;
            return [...prev, newTab];
          });
          setActiveTabId(newTab.id);

          // Don't show progress panel or reasoning - just show the image directly
          setReasoning(''); // Clear reasoning - don't show it
          syncProcessingState();
          setCurrentStatus('');
          setCurrentStage('');
          return; // Exit early - no planning steps, no progress panel, no reasoning
        } else {
          // Image generation failed - show error in workspace only
          const errorAction: AgentAction = {
            id: `image-gen-error-${Date.now()}`,
            type: 'stream',
            timestamp: new Date(),
            title: 'Image Generation Failed',
            content: data.response || `❌ Failed to generate image: ${imgGen.error || 'Unknown error'}`,
            status: 'completed',
          };
          setAgentActions(prev => [...prev, errorAction]);
          syncProcessingState();
          setCurrentStatus('');
          setCurrentStage('');
          return;
        }
      }

      const responseText = data.response || 'I apologize, but I could not generate a response. Please try again.';

      // If no job_id, this is a direct response (like greetings) - stop processing immediately
      if (!data.job_id) {
        // Add response to chat messages so it displays in the chat UI
        const assistantChatMessage: ChatMessage = {
          id: replaceAssistantMessageId || `chat-response-${Date.now()}`,
          type: 'assistant',
          content: responseText,
          timestamp: new Date(),
          isStreaming: false,
          agent: 'assistant'
        };
        latestAssistantContentRef.current[assistantChatMessage.id] = responseText;
        setChatMessages(prev => {
          const existingIndex = prev.findIndex(msg => msg.id === assistantChatMessage.id);
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = { ...updated[existingIndex], ...assistantChatMessage };
            return updated;
          }
          return [...prev, assistantChatMessage];
        });
        if (replaceAssistantMessageId) {
          appendAssistantVariant(replaceAssistantMessageId, responseText);
        }

        syncProcessingState();
        setCurrentStatus('');
        setCurrentStage('');
      }

      // REMOVED: Don't add hardcoded reasoning - only show real-time streaming

      // Add plan steps as actions in the main chat window
      if (data.plan && Array.isArray(data.plan) && data.plan.length > 0) {
        // Get tool results from response if available
        const toolResults = data.tool_results || {};

        data.plan.forEach((step: any) => {
          const toolName = step.tool;
          const toolResult = toolResults[toolName] || null;

          const planAction: AgentAction = {
            id: `plan-${step.step}-${Date.now()}`,
            type: 'tool_call',
            timestamp: new Date(),
            title: `Step ${step.step}: ${step.tool || 'Operation'}`,
            content: step.description || 'Executing...',
            metadata: {
              tool: step.tool,
              arguments: step.arguments,
              description: step.description,
              result: toolResult ? {
                status: 'success',
                [toolName === 'web_search' ? 'results' : toolName === 'image_search' ? 'images' : 'data']: toolResult
              } : null
            },
            status: 'completed',
          };
          setAgentActions(prev => [...prev, planAction]);
        });
      }

      // Check if response contains search results (base64 encoded)
      const parseBase64JSON = (commentTag: string) => {
        const match = responseText.match(new RegExp(`<!-- ${commentTag}: ([A-Za-z0-9+/=]+) -->`));
        if (match && match[1]) {
          try {
            const jsonStr = atob(match[1]);
            return JSON.parse(jsonStr);
          } catch (e) {
            console.error(`Failed to parse ${commentTag}:`, e);
            return null;
          }
        }
        return null;
      };

      // Parse web search results
      const searchResultsData = parseBase64JSON('SEARCH_RESULTS_JSON_B64');
      if (searchResultsData && searchResultsData.results && Array.isArray(searchResultsData.results)) {
        const searchAction: AgentAction = {
          id: `search-${Date.now()}`,
          type: 'research_result',
          timestamp: new Date(),
          title: `Search: ${searchResultsData.query || 'Web Search'}`,
          content: responseText,
          metadata: {
            tool: 'web_search',
            query: searchResultsData.query,
            results: searchResultsData.results
          },
          status: 'completed',
        };
        setAgentActions(prev => [...prev, searchAction]);
      }

      // Parse image search results
      const imageSearchData = parseBase64JSON('IMAGE_SEARCH_JSON_B64');
      if (imageSearchData && imageSearchData.type === 'image_search' && imageSearchData.results && Array.isArray(imageSearchData.results)) {
        const imageSearchAction: AgentAction = {
          id: `image-search-${Date.now()}`,
          type: 'research_result',
          timestamp: new Date(),
          title: `Images: ${imageSearchData.query || 'Image Search'}`,
          content: responseText,
          metadata: {
            tool: 'image_search',
            query: imageSearchData.query,
            images: imageSearchData.results
          },
          status: 'completed',
        };
        setAgentActions(prev => [...prev, imageSearchAction]);
      }

      // Parse image generation results
      const imageGenData = parseBase64JSON('IMAGE_GENERATION_JSON_B64');
      if (imageGenData && imageGenData.type === 'image_generation' && imageGenData.success && imageGenData.url) {
        const imageGenAction: AgentAction = {
          id: `image-gen-${Date.now()}`,
          type: 'research_result',
          timestamp: new Date(),
          title: `Generated: ${imageGenData.prompt || 'Image'}`,
          content: responseText,
          metadata: {
            tool: 'image_generate',
            prompt: imageGenData.prompt,
            url: imageGenData.url,
            model: imageGenData.model
          },
          status: 'completed',
        };
        setAgentActions(prev => [...prev, imageGenAction]);
      }

      // Auto-open file if one was created
      if (data.file_created && data.file_created.path) {
        const rawPath = data.file_created.path;
        const wsId = data.file_created.workspace_id || deriveWorkspaceId(rawPath) || workspaceId;
        const normalizedPath = normalizeWorkspacePath(rawPath, wsId);

        // Open file in preview panel
        const fileTab: Tab = {
          id: `file-${normalizedPath}-${Date.now()}`,
          type: 'file',
          title: normalizedPath.split('/').pop() || normalizedPath,
          data: {
            name: normalizedPath.split('/').pop() || normalizedPath,
            path: normalizedPath,
            type: normalizedPath.includes('.') ? 'file' : 'folder',
            workspaceId: wsId
          },
          workspaceId: wsId,
        };

        setTabs(prev => {
          const exists = prev.find(t => t.data?.path === normalizedPath);
          if (exists) {
            setActiveTabId(exists.id);
            return prev;
          }
          return [...prev, fileTab];
        });
        setActiveTabId(fileTab.id);

        // Trigger workspace refresh
        window.dispatchEvent(new Event('workspace-refresh'));
      }

      // Real streaming is now handled by SSE response_chunk events
      // No need for fake streaming animation

    } catch (error: any) {
      console.error('Chat error:', error);

      // Update progress steps with error
      setProgressSteps([
        { id: '1', label: 'Processing your message', status: 'completed', timestamp: new Date() },
        { id: '2', label: 'Generating AI response', status: 'error', timestamp: new Date() },
      ]);

      // Show error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        content: `❌ **Connection Error**

I'm having trouble connecting to the backend server. Please check:
1. Is the backend server running? (Try \`./start_backend.sh\`)
2. Are you using the correct port? (Default: 8000)

*Error details: ${error.message || 'Unknown network error'}*`,
        timestamp: new Date(),
        isStreaming: false
      };
      setChatMessages(prev => [...prev, errorMessage]);

      syncProcessingState();
      setCurrentStatus('');
      setCurrentStage('');
    } finally {
      // Process queued messages after current request completes
      if (!isInterrupted && messageQueue.length > 0) {
        const nextMessage = messageQueue[0];
        setMessageQueue(prev => prev.slice(1));
        setTimeout(() => {
          handleChatStart(nextMessage);
        }, 500);
      } else if (isInterrupted) {
        setIsInterrupted(false);
        if (messageQueue.length > 0) {
          setMessageQueue([]);
        }
      }
      syncProcessingState();
      setCurrentStatus('');
      setCurrentStage('');
    }
  };

  const handleProcessingComplete = () => {
    syncProcessingState();
    setCurrentStatus('');
    setCurrentStage('');
  };

  // Tab Management Functions
  const openTab = useCallback((tabType: TabType, title: string, data: any, workspaceId?: string) => {
    const tabId = `${tabType}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newTab: Tab = {
      id: tabId,
      type: tabType,
      title: title.substring(0, 50), // Limit title length
      data,
      workspaceId: workspaceId || 'default'
    };

    setTabs(prev => {
      // Check if tab with same content already exists
      const existingTab = prev.find(t =>
        t.type === tabType &&
        JSON.stringify(t.data) === JSON.stringify(data)
      );

      if (existingTab) {
        // Switch to existing tab
        setActiveTabId(existingTab.id);
        return prev;
      }

      // Add new tab
      setActiveTabId(tabId);
      setIsRightPanelOpen(true);
      return [...prev, newTab];
    });
  }, []);

  const closeTab = useCallback((tabId: string) => {
    setTabs(prev => {
      const newTabs = prev.filter(t => t.id !== tabId);

      // If closing active tab, switch to another
      if (activeTabId === tabId) {
        if (newTabs.length > 0) {
          setActiveTabId(newTabs[newTabs.length - 1].id);
        } else {
          setActiveTabId(null);
          setIsRightPanelOpen(false);
        }
      }

      return newTabs;
    });
  }, [activeTabId]);

  // Handle file opening from workspace - opens as a new tab
  const handleFileOpen = useCallback(async (file: { name: string; path: string; type: string }) => {
    const currentWorkspaceId = workspaceId || `ws_${sessionId.substring(0, 12)}`;
    openTab('file', file.name, file, currentWorkspaceId);
  }, [openTab, workspaceId, sessionId]);

  // Handle browser/search actions from agent actions - auto-open as tabs
  useEffect(() => {
    const browserActions = agentActions.filter(a =>
      (a.type === 'browser_action' || a.type === 'research_result') && (a.status === 'completed' || a.status === 'running')
    );

    if (browserActions.length > 0) {
      const latest = browserActions[browserActions.length - 1];

      // Determine tab type and data based on action
      if (latest.metadata?.tool === 'web_search' && latest.metadata?.results) {
        openTab('search', `Search: ${latest.metadata.query || 'Web Search'}`, {
          results: latest.metadata.results,
          query: latest.metadata.query
        }, workspaceId);
      } else if (latest.metadata?.tool === 'image_search' && latest.metadata?.images) {
        openTab('image', `Images: ${latest.metadata.query || 'Image Search'}`, {
          images: latest.metadata.images,
          query: latest.metadata.query
        }, workspaceId);
      } else if (latest.metadata?.tool === 'image_generate' && latest.metadata?.url) {
        openTab('image', `Generated: ${latest.metadata.prompt || 'Image'}`, {
          images: [{
            title: latest.metadata.prompt || 'Generated Image',
            url: latest.metadata.url,
            full: latest.metadata.url
          }],
          query: latest.metadata.prompt
        }, workspaceId);
      } else if (latest.type === 'browser_action' || latest.type === 'research_result') {
        openTab('browser', latest.title || 'Browser Action', {
          type: latest.type === 'research_result' ? 'search_result' : 'browser_action',
          url: latest.metadata?.url,
          query: latest.metadata?.query,
          screenshot: latest.metadata?.screenshot,
          content: latest.content
        }, workspaceId);
      }
    }
  }, [agentActions, openTab, workspaceId]);

  // Handle new chat - create new session and clear workspace
  const handleNewChat = useCallback(async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

      // 1. Create new session with auto-created workspace
      const response = await fetch(`${backendUrl}/api/session/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'default' })
      });

      if (!response.ok) {
        throw new Error('Failed to create new session');
      }

      const newSession = await response.json();

      // 2. Update state and persistence
      setSessionId(newSession.session_id);
      setWorkspaceId(newSession.workspace_id);
      localStorage.setItem('session_id', newSession.session_id);
      localStorage.setItem('workspace_id', newSession.workspace_id);

      // 3. Clear all chat-related state
      setCurrentJobId(null);
      setLiveResponse('');
      setProgressSteps([]);
      setPlannerSteps([]);
      setAgentActions([]);
      setReasoning('');
      setCurrentStatus('');
      setCurrentStage('');
      setIsProcessing(false);

      // Crucial: Clear messages and localStorage for the old workspace
      setChatMessages([]);
      setAssistantVariants({});
      setAssistantVariantIndex({});
      setWorkspaceFiles([]);
      setStreamingMessageId(null);
      setActiveAgents([]);

      // 4. Load new workspace files (should be empty for new workspace)
      try {
        const filesResponse = await fetch(`${backendUrl}/api/workspace/${newSession.workspace_id}/structure`);
        if (filesResponse.ok) {
          const filesData = await filesResponse.json();
          setWorkspaceFiles(filesData.files || []);
        }
      } catch (error) {
        console.error('Failed to load new workspace files:', error);
        // Non-critical, continue anyway
      }

      console.log('✅ New chat created:', {
        sessionId: newSession.session_id,
        workspaceId: newSession.workspace_id
      });

    } catch (error) {
      console.error('Failed to create new chat:', error);

      // Fallback: just clear state without creating new session
      setCurrentJobId(null);
      setLiveResponse('');
      setProgressSteps([]);
      setAgentActions([]);
      setReasoning('');
      setCurrentStatus('');
      setCurrentStage('');
      setIsProcessing(false);
      setChatMessages([]);
      setAssistantVariants({});
      setAssistantVariantIndex({});
    }
  }, []);

  // Handle selecting an item from history
  const handleSelectHistoryItem = useCallback(async (id: string, type: 'job' | 'conversation') => {
    if (type === 'job') {
      setCurrentJobId(id);
      // Existing job selection logic...
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
        const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/jobs/${id}`);
        if (response.ok) {
          const data = await response.json();
          const job = data.job;
          if (job.status === 'running' || job.status === 'paused') {
            setIsProcessing(job.status === 'running');
            setCurrentStatus(job.current_step || 'Processing...');
          } else if (job.result?.content) {
            const resultMessage: ChatMessage = {
              id: `job-${job.job_id}-result`,
              type: 'assistant',
              content: job.result.content,
              timestamp: new Date(job.created_at || Date.now()),
              isStreaming: false,
              agent: 'assistant'
            };
            setChatMessages(prev => [...prev, resultMessage]);
          }
        }
      } catch (error) {
        console.error('Failed to load job:', error);
      }
    } else {
      // Load conversation/session
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
        const response = await fetch(`${backendUrl}/api/session/${id}/load`);
        if (response.ok) {
          const data = await response.json();

          // Update both session and workspace
          setSessionId(data.session_id);
          setWorkspaceId(data.workspace_id);

          // Update messages
          const messages = (data.messages || []).map((msg: any) => ({
            id: msg.id,
            type: msg.role === 'user' ? 'user' : (msg.role === 'system' ? 'system' : 'assistant'),
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            isStreaming: false,
            agent: msg.role === 'assistant' ? 'assistant' : undefined
          }));

          setChatMessages(messages);
          setShowWelcome(false);

          // Update workspace files
          setWorkspaceFiles(data.files || []);

          // Update localStorage for persistence
          localStorage.setItem('workspace_id', data.workspace_id);
          localStorage.setItem('session_id', data.session_id);
        }
      } catch (error) {
        console.error('Failed to load conversation session:', error);
      }
    }
  }, [workspaceId]);

  // Authentication Gate
  if (!hasCheckedAuth) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          <p className="text-sm text-muted-foreground">Initializing...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden" style={{ backgroundColor: 'var(--color-bg, #F4F4F4)' }}>
      {/* Universal Progress Overlay - Fixed position bottom-right */}
      {showProgressOverlay && progressJobId && (
        <UniversalProgressOverlay
          jobId={progressJobId}
          title={progressTopic}
          type={progressType}
          onClose={() => {
            setShowProgressOverlay(false);
            setProgressJobId(null);
          }}
          backendUrl={process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'}
        />
      )}

      {/* Top Menu Bar */}
      <TopMenuBar
        workspaceId={workspaceId}
        onNewChat={handleNewChat}
        onSelectHistoryItem={handleSelectHistoryItem}
        currentHistoryId={sessionId || currentJobId}
        chatTitle={chatMessages.find(a => a.type === 'user')?.content?.slice(0, 50) || undefined}
      />

      <ResizableLayout
        isLeftCollapsed={isLeftPanelCollapsed}
        isRightCollapsed={isRightPanelCollapsed}
        onLeftCollapse={setIsLeftPanelCollapsed}
        onRightCollapse={setIsRightPanelCollapsed}
        leftPanel={
          <div
            className="h-full flex flex-col relative"
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              borderColor: 'var(--color-border, #E0E0E0)'
            }}
          >
            {!isLeftPanelCollapsed && (
              leftPanel || (
                <div className="h-full flex flex-col">
                  {/* Header */}
                  <div className="flex h-16 items-center px-4 border-b border-border/40 justify-between">
                    {!isLeftPanelCollapsed ? (
                      <>
                        <div className="flex items-center gap-2 animate-in fade-in duration-300">
                          <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-primary" />
                          </div>
                          <span className="font-bold text-lg tracking-tight">Thesis Platform</span>
                        </div>

                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-70 hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
                          onClick={handleLogout}
                          title="Sign Out"
                        >
                          <LogOut className="w-4 h-4" />
                        </Button>
                      </>
                    ) : (
                      <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center mx-auto">
                        <Sparkles className="w-5 h-5 text-primary" />
                      </div>
                    )}
                  </div>

                  {/* Left Panel Tabs */}
                  <div className="flex border-b text-sm" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
                    <button
                      onClick={() => setLeftPanelTab('files')}
                      className={cn(
                        "flex-1 py-2 text-center transition-colors border-b-2 text-foreground",
                        leftPanelTab === 'files'
                          ? "border-blue-500 text-blue-600 font-medium"
                          : "border-transparent text-gray-500 hover:text-gray-700"
                      )}
                    >
                      📁 Files
                    </button>
                    <button
                      onClick={() => setLeftPanelTab('menu')}
                      className={cn(
                        "flex-1 py-2 text-center transition-colors border-b-2 text-foreground",
                        leftPanelTab === 'menu'
                          ? "border-blue-500 text-blue-600 font-medium"
                          : "border-transparent text-gray-500 hover:text-gray-700"
                      )}
                    >
                      ≡ Menu
                    </button>
                  </div>

                  {/* File Explorer / Menu */}
                  <div className="flex-1 overflow-hidden">
                    {leftPanelTab === 'files' ? (
                      <FileExplorer
                        workspaceId={workspaceId}
                        onFileSelect={(file) => {
                          // Special handling for sources folder - open SourcesPanel in right panel
                          if (file.path === 'sources' || file.path.endsWith('/sources')) {
                            openTab('sources', '📚 Sources Library', { workspaceId }, workspaceId);
                          } else {
                            handleFileOpen(file);
                          }
                        }}
                        refreshTrigger={agentActions.length}
                      />
                    ) : (
                      <DefaultLeftPanel onFileOpen={handleFileOpen} workspaceId={workspaceId} />
                    )}
                  </div>
                </div>
              )
            )}

            {/* Collapse Toggle Button */}
            <button
              onClick={() => setIsLeftPanelCollapsed(!isLeftPanelCollapsed)}
              className={cn(
                "absolute top-4 -right-3 z-50 p-1.5 rounded-full shadow-lg transition-all hover:scale-110",
                isLeftPanelCollapsed ? "right-0" : ""
              )}
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                border: '2px solid var(--color-border, #E0E0E0)',
                color: 'var(--color-text, #161616)'
              }}
              title={isLeftPanelCollapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)"}
            >
              {isLeftPanelCollapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </button>
          </div>
        }
        middlePanel={
          <div className="flex flex-col h-full overflow-hidden" style={{ backgroundColor: 'var(--chat-panel, #fff6ec)' }}>
            {activeAgents.length > 0 && (
              <div className="border-b" style={{ borderColor: 'rgba(31, 122, 140, 0.12)' }}>
                <AgentActivityTracker activities={activeAgents} />
              </div>
            )}
            {(plannerSteps.length > 0 || progressSteps.length > 0 || isProcessing) && (
              <div
                className="border-b px-4 py-3 space-y-2"
                style={{ borderColor: 'rgba(31, 122, 140, 0.12)' }}
              >
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground/60">
                    Progress Tracker
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowProgressTracker(prev => !prev)}
                    className="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
                  >
                    {showProgressTracker ? 'Hide' : 'Show'}
                  </button>
                </div>
                {showProgressTracker && (
                  <div className="max-h-56 overflow-y-auto">
                    <ProcessPlanner
                      steps={plannerSteps.length > 0 ? plannerSteps : progressSteps}
                      totalPercentage={currentProgress > 0 ? currentProgress : undefined}
                      isCompact={true}
                    />
                  </div>
                )}
              </div>
            )}
            {/* Enhanced Chat Display - Shows messages with real streaming */}
            <EnhancedChatDisplay
              messages={chatMessages}
              isProcessing={isProcessing}
              currentAgent={currentAgent}
              currentAction={currentAction}
              currentDescription={currentDescription}
              currentProgress={currentProgress}
              processSteps={plannerSteps.length > 0 ? plannerSteps : progressSteps}
              agentActions={agentActions}
              assistantVariants={assistantVariants}
              activeVariantIndex={assistantVariantIndex}
              onVariantSelect={(messageId, index) => {
                setAssistantVariantIndex(prev => ({ ...prev, [messageId]: index }));
              }}
              onSuggestionClick={(suggestion) => handleChatStart(suggestion)}
              onEditMessage={(messageId, content, options) => {
                const messageIndex = chatMessages.findIndex(msg => msg.id === messageId);
                if (messageIndex < 0) return;
                const trimmedMessages = chatMessages
                  .slice(0, messageIndex + 1)
                  .map(msg => (msg.id === messageId ? { ...msg, content } : msg));
                setChatMessages(trimmedMessages);
                pruneAssistantVariants(new Set(trimmedMessages.map(msg => msg.id)));
                setPlannerSteps([]);
                setProgressSteps([]);
                setActiveAgents([]);
                setCurrentStatus('');
                setCurrentStage('');
                setCurrentJobId(null);
                setLiveResponse('');
                setIsProcessing(Object.keys(activeJobsRef.current).length > 0);
                if (options?.redo) {
                  handleChatStart(content, undefined, undefined, {
                    skipUserMessage: true,
                    historyOverride: trimmedMessages
                  });
                }
              }}
              onRegenerate={(messageId) => {
                const index = chatMessages.findIndex(msg => msg.id === messageId);
                let userText = '';
                if (index >= 0) {
                  for (let i = index - 1; i >= 0; i -= 1) {
                    if (chatMessages[i].type === 'user') {
                      userText = chatMessages[i].content;
                      break;
                    }
                  }
                }
                if (!userText) {
                  const lastUser = [...chatMessages].reverse().find(msg => msg.type === 'user');
                  userText = lastUser?.content || '';
                }
                const targetMessage = chatMessages.find(msg => msg.id === messageId);
                if (targetMessage?.content) {
                  ensureAssistantVariantBase(messageId, targetMessage.content);
                }
                setChatMessages(prev => prev.map(msg =>
                  msg.id === messageId ? { ...msg, isStreaming: true } : msg
                ));
                if (userText) {
                  handleChatStart(userText, undefined, undefined, {
                    skipUserMessage: true,
                    replaceAssistantMessageId: messageId
                  });
                }
              }}
            />

            {/* Chat Bar at Bottom - Always Visible - Fixed Position */}
            {!showWelcome && (
              <div
                className="flex-shrink-0 w-full"
                style={{
                  position: 'sticky',
                  bottom: 0,
                  zIndex: 1000,
                  backgroundColor: 'var(--color-panel, #FFFFFF)'
                }}
              >
                <ChatBar
                  onChatStart={(message, mentionedAgents, parameters) => {
                    if (showWelcome) setShowWelcome(false);
                    handleChatStart(message, mentionedAgents, parameters);
                  }}
                  onFileUpload={handleFileUpload}
                  isProcessing={isProcessing}
                  placeholder="Type a message... (use @ to mention agents)"
                  currentStatus={currentStatus}
                  currentStage={currentStage}
                  workspaceId={workspaceId}
                  sessionId={sessionId}
                />
              </div>
            )}
          </div>
        }
        rightPanel={
          tabs.length > 0 ? (
            <div className="h-full flex flex-col border-l bg-white" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
              <TabbedPreviewPanel
                tabs={tabs}
                activeTabId={activeTabId}
                onTabChange={setActiveTabId}
                onTabClose={closeTab}
                onTabsChange={setTabs}
                sourcesRefreshKey={sourcesRefreshKey}
              />
            </div>
          ) : null
        }
      />

      {/* Floating Menu Button when left panel collapsed */}
      {isLeftPanelCollapsed && (
        <button
          onClick={() => setIsLeftPanelCollapsed(false)}
          className="fixed left-4 top-4 z-40 p-3 rounded-lg shadow-lg transition-all hover:scale-110"
          style={{
            backgroundColor: 'var(--color-panel, #FFFFFF)',
            border: '1px solid var(--color-border, #E0E0E0)',
            color: 'var(--color-primary, #0F62FE)'
          }}
          title="Show sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}

// Default Left Panel Component
function DefaultLeftPanel({ onFileOpen, workspaceId }: { onFileOpen?: (file: { name: string; path: string; type: string }) => void, workspaceId: string }) {
  const pathname = usePathname();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['research']));
  const [activeTab, setActiveTab] = useState<'navigation' | 'workspace'>('navigation');
  // Get workspace and user from session - will update to use SessionContext next
  const [userId, setUserId] = useState<string>('user-1'); // Get from auth



  const navigationSections = [
    {
      id: 'research',
      label: 'Research',
      icon: '🔬',
      items: [
        { id: 'search', label: 'Search Papers', path: '/research/search' },
        { id: 'bibliography', label: 'Bibliography', path: '/research/bibliography' },
        { id: 'citations', label: 'Citations', path: '/research/citations' },
        { id: 'citation-network', label: 'Citation Network', path: '/research/citation-network' },
        { id: 'literature-review', label: 'Literature Review', path: '/research/literature-review' },
        { id: 'research-gaps', label: 'Research Gaps', path: '/research/research-gaps' },
      ]
    },
    {
      id: 'tools',
      label: 'Tools',
      icon: '🔧',
      items: [
        { id: 'analysis', label: 'Analysis', path: '/tools/analysis' },
        { id: 'fulltext-search', label: 'Full-Text Search', path: '/tools/fulltext-search' },
        { id: 'citation-formatter', label: 'Citation Formatter', path: '/tools/citation-formatter' },
        { id: 'zotero', label: 'Zotero Sync', path: '/tools/zotero' },
        { id: 'pdf-manager', label: 'PDF Manager', path: '/tools/pdf-manager' },
      ]
    },
    {
      id: 'generators',
      label: 'Generators',
      icon: '✨',
      items: [
        { id: 'chapter-generator', label: 'Chapter Generator', path: '/generators/chapter' },
        { id: 'section-generator', label: 'Section Generator', path: '/generators/section' },
        { id: 'cited-content', label: 'Cited Content', path: '/generators/cited-content' },
        { id: 'objectives-generator', label: 'Objectives Generator', path: '/generators/objectives' },
        { id: 'essay-generator', label: 'Essay Generator', path: '/generators/essay' },
        { id: 'framework-generator', label: 'Framework Designer', path: '/generators/framework' },
        { id: 'methodology-generator', label: 'Methodology Generator', path: '/generators/methodology' },
      ]
    },
    {
      id: 'editing',
      label: 'Editing Services',
      icon: '✏️',
      items: [
        { id: 'grammar-check', label: 'Grammar Check', path: '/editing/grammar' },
        { id: 'plagiarism-check', label: 'Plagiarism Check', path: '/editing/plagiarism' },
        { id: 'humanizing', label: 'Humanizing', path: '/editing/humanizing' },
        { id: 'style-editor', label: 'Style Editor', path: '/editing/style' },
        { id: 'proofreading', label: 'Proofreading', path: '/editing/proofreading' },
        { id: 'academic-tone', label: 'Academic Tone', path: '/editing/academic-tone' },
        { id: 'formatting', label: 'Formatting', path: '/editing/formatting' },
        { id: 'peer-review', label: 'Peer Review', path: '/editing/peer-review' },
      ]
    },
    {
      id: 'frameworks',
      label: 'Frameworks & Design',
      icon: '🎨',
      items: [
        { id: 'conceptual-framework', label: 'Conceptual Framework', path: '/frameworks/conceptual' },
        { id: 'theoretical-framework', label: 'Theoretical Framework', path: '/frameworks/theoretical' },
        { id: 'research-design', label: 'Research Design', path: '/frameworks/research-design' },
        { id: 'methodology-framework', label: 'Methodology Framework', path: '/frameworks/methodology' },
        { id: 'model-builder', label: 'Model Builder', path: '/frameworks/model-builder' },
        { id: 'diagram-maker', label: 'Diagram Maker', path: '/frameworks/diagram-maker' },
        { id: 'flowchart', label: 'Flowchart Designer', path: '/frameworks/flowchart' },
      ]
    },
    {
      id: 'pipelines',
      label: 'Pipelines',
      icon: '⚙️',
      items: [
        { id: 'history', label: 'History', path: '/pipelines/history' },
        { id: 'export-pipeline', label: 'Export Pipeline', path: '/pipelines/export' },
        { id: 'import-pipeline', label: 'Import Pipeline', path: '/pipelines/import' },
      ]
    },
    {
      id: 'reports',
      label: 'Reports',
      icon: '📄',
      items: [
        { id: 'export', label: 'Export', path: '/reports/export' },
        { id: 'analysis', label: 'Analysis', path: '/reports/analysis' },
        { id: 'chapters', label: 'Chapters', path: '/reports/chapters' },
        { id: 'citation-report', label: 'Citation Report', path: '/reports/citation-report' },
        { id: 'progress-report', label: 'Progress Report', path: '/reports/progress' },
      ]
    },
    {
      id: 'templates',
      label: 'Templates',
      icon: '📋',
      items: [
        { id: 'essay-template', label: 'Essay Template', path: '/templates/essay' },
        { id: 'report-template', label: 'Report Template', path: '/templates/report' },
        { id: 'article-template', label: 'Article Template', path: '/templates/article' },
        { id: 'journal-template', label: 'Journal Template', path: '/templates/journal' },
        { id: 'thesis-template', label: 'Thesis Template', path: '/templates/thesis' },
        { id: 'custom-template', label: 'Custom Template', path: '/templates/custom' },
      ]
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: '⚙️',
      items: [
        { id: 'project-settings', label: 'Project Settings', path: '/settings/project' },
        { id: 'document-type', label: 'Document Type', path: '/settings/document-type' },
        { id: 'citation-style', label: 'Citation Style', path: '/settings/citation-style' },
        { id: 'export-formats', label: 'Export Formats', path: '/settings/export-formats' },
        { id: 'integrations', label: 'Integrations', path: '/settings/integrations' },
        { id: 'preferences', label: 'Preferences', path: '/settings/preferences' },
      ]
    },
  ];

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  // Auto-expand section if current path matches
  useEffect(() => {
    navigationSections.forEach(section => {
      const isActive = section.items.some(item => pathname?.startsWith(item.path));
      if (isActive) {
        setExpandedSections(prev => new Set(prev).add(section.id));
      }
    });
  }, [pathname]);

  return (
    <div className="flex flex-col h-full">
      {/* Logo/Header */}
      <div
        className="px-6 py-4 border-b"
        style={{ borderColor: 'var(--color-border, #E0E0E0)' }}
      >
        <h1
          className="text-xl font-bold"
          style={{ color: 'var(--color-text, #161616)' }}
        >
          Thesis Platform
        </h1>
      </div>

      {/* Tabs */}
      <div className="flex border-b" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
        <button
          onClick={() => setActiveTab('navigation')}
          className={cn(
            "flex-1 px-4 py-2 text-sm font-medium transition-colors",
            activeTab === 'navigation' && "border-b-2"
          )}
          style={{
            color: activeTab === 'navigation' ? 'var(--color-primary, #0F62FE)' : 'var(--color-text-secondary, #525252)',
            borderBottomColor: activeTab === 'navigation' ? 'var(--color-primary, #0F62FE)' : 'transparent'
          }}
        >
          Navigation
        </button>
        <button
          onClick={() => setActiveTab('workspace')}
          className={cn(
            "flex-1 px-4 py-2 text-sm font-medium transition-colors",
            activeTab === 'workspace' && "border-b-2"
          )}
          style={{
            color: activeTab === 'workspace' ? 'var(--color-primary, #0F62FE)' : 'var(--color-text-secondary, #525252)',
            borderBottomColor: activeTab === 'workspace' ? 'var(--color-primary, #0F62FE)' : 'transparent'
          }}
        >
          Workspace
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'navigation' ? (
          <NavigationContent
            pathname={pathname}
            expandedSections={expandedSections}
            setExpandedSections={setExpandedSections}
            navigationSections={navigationSections}
            toggleSection={(sectionId: string) => {
              setExpandedSections(prev => {
                const newSet = new Set(prev);
                if (newSet.has(sectionId)) {
                  newSet.delete(sectionId);
                } else {
                  newSet.add(sectionId);
                }
                return newSet;
              });
            }}
          />
        ) : (
          <WorkspaceContent
            workspaceId={workspaceId}
            userId={userId}
            onFileOpen={onFileOpen}
          />
        )}
      </div>

      {/* Footer */}
      <div
        className="px-4 py-4 border-t"
        style={{ borderColor: 'var(--color-border, #E0E0E0)' }}
      >
        <p
          className="text-xs"
          style={{ color: 'var(--color-text-muted, #8D8D8D)' }}
        >
          Press Cmd+P for progress, Cmd+B to toggle sidebar
        </p>
      </div>
    </div>
  );
}

// Navigation Content Component
function NavigationContent({ pathname, expandedSections, setExpandedSections, navigationSections, toggleSection }: any) {
  return (
    <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
      {navigationSections.map((section: any) => {
        const isExpanded = expandedSections.has(section.id);
        return (
          <div key={section.id} className="mb-1">
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all hover:bg-opacity-50"
              style={{
                backgroundColor: 'transparent',
                color: 'var(--color-text, #161616)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-primary-bg, #EDF5FF)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <span className="text-lg">{section.icon}</span>
              <span className="font-medium flex-1">{section.label}</span>
              <span className="text-sm">{isExpanded ? '▼' : '▶'}</span>
            </button>

            {isExpanded && (
              <div className="ml-4 mt-1 space-y-1">
                {section.items.map((item) => {
                  const isActive = pathname === item.path;
                  return (
                    <Link
                      key={item.id}
                      href={item.path}
                      className={cn(
                        "w-full flex items-center gap-2 px-4 py-2 rounded-lg text-left text-sm transition-all block",
                        isActive && "font-semibold"
                      )}
                      style={{
                        backgroundColor: isActive ? 'var(--color-primary-bg, #EDF5FF)' : 'transparent',
                        color: isActive ? 'var(--color-primary, #0F62FE)' : 'var(--color-text-secondary, #525252)',
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          e.currentTarget.style.backgroundColor = 'var(--color-primary-bg, #EDF5FF)';
                          e.currentTarget.style.color = 'var(--color-primary, #0F62FE)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = 'var(--color-text-secondary, #525252)';
                        }
                      }}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50"></span>
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}

// Workspace Content Component
function WorkspaceContent({
  workspaceId,
  userId,
  onFileOpen
}: {
  workspaceId: string;
  userId: string;
  onFileOpen?: (file: { name: string; path: string; type: string }) => void;
}) {
  return (
    <div className="h-full">
      <WorkspaceFileSystem
        workspaceId={workspaceId}
        userId={userId}
        onFileOpen={onFileOpen}
      />
    </div>
  );
}
