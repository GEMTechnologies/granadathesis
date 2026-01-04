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
import { SourcesPanel } from '../sources/SourcesPanel';
import { TopMenuBar } from './TopMenuBar';
import { ProcessStatus } from '../ProcessStatus';
import { cn } from '../../lib/utils';
import UniversalProgressOverlay from '../UniversalProgressOverlay';
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

  // Tabbed Preview State
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(true); // Default to open for 3-column layout
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] = useState(false);

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
  const [progressType, setProgressType] = useState<'thesis' | 'general'>('general');

  // Store interval ref for cleanup
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Load chat messages from localStorage on mount
  useEffect(() => {
    try {
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

    const browserTab: Tab = {
      id: `browser-${Date.now()}`,
      type: 'browser',
      title: detail.title || '🌐 Live Browser',
      data: {
        sessionId: detail.sessionId || 'default',
        url: detail.url || ''
      },
      workspaceId: workspaceId
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
        setIsProcessing(false);
        return;
      }

      // Parse user input for thesis details
      // User can provide: "Title: X Topic: Y" or just "Topic: Y" or even just "Y"
      const titleMatch = userInput.match(/(?:Title|title):\s*(.+?)(?:\n|Topic|topic|$)/);
      const topicMatch = userInput.match(/(?:Topic|topic):\s*(.+?)(?:\n|Objectives|objectives|$)/);
      const objectivesMatch = userInput.match(/(?:Objectives|objectives):\s*([\s\S]+?)$/i);

      const title = titleMatch ? titleMatch[1].trim() : 'Research Thesis';
      const topic = topicMatch ? topicMatch[1].trim() : userInput;

      // Parse objectives - handle numbered lists (1. 2. 3.) and bullet points
      const objectives = objectivesMatch
        ? objectivesMatch[1]
          .split(/\n/)
          .map(obj => obj.replace(/^\s*\d+\.\s*/, '').replace(/^\s*[-•]\s*/, '').trim())
          .filter(obj => obj.length > 5) // Filter out empty or very short lines
        : []; // Empty array means backend will auto-generate 6 objectives

      // Call thesis generation API
      const thesisResponse = await fetch(`${backendUrl}/api/thesis/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          university_type: universityType,
          title: title,
          topic: topic,
          objectives: objectives.length > 0 ? objectives : [topic],
          workspace_id: workspaceId,
          parameters: parameters
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
| 5 | Synthetic Dataset (Hypothetical Data) | ⏳ Pending |
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
| 5 | Synthetic Dataset (385 respondents) | ⏳ Pending |
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

        // Subscribe to SSE for progress updates - using Redis-based endpoint
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const sessionForStream = sessionId || 'new';
        const streamUrl = `${backendUrl}/api/stream/agent-actions?session_id=${sessionForStream}&job_id=${thesisData.job_id}`;
        const eventSource = new EventSource(streamUrl);

        eventSource.onopen = () => {
          // console.log('✅ SSE connection opened for thesis generation');
        };

        let accumulatedContent = '';

        // Helper function to handle incoming events
        const handleEvent = (eventType: string, data: any) => {
          // console.log(`📥 SSE event [${eventType}]:`, data);

          if (eventType === 'response_chunk' && data?.chunk) {
            accumulatedContent += data.chunk;
            setLiveResponse(accumulatedContent);

            // Update the streaming message with accumulated content
            setChatMessages(prev => prev.map(msg =>
              msg.id === statusMessage.id
                ? { ...msg, content: accumulatedContent }
                : msg
            ));
          }

          if (eventType === 'log' && data?.message) {
            setCurrentStatus(data.message);
            // Also add log messages to the chat as progress updates
            // console.log('📋 Status:', data.message);
          }

          if (eventType === 'agent_activity' || eventType === 'agent_working') {
            setCurrentAgent(data.agent_name || data.agent || '');
            setCurrentAction(data.action || '');
          }

          if (eventType === 'figure_generated' && data?.message) {
            setCurrentStatus(`📈 ${data.message}`);
          }

          if (eventType === 'file_created' && data?.path) {
            // Dispatch event to refresh file explorer
            window.dispatchEvent(new CustomEvent('workspace-refresh'));

            // File was created - add completion message
            const completionMessage: ChatMessage = {
              id: `assistant-complete-${Date.now()}`,
              type: 'assistant',
              content: `✅ **Thesis File Created!**

📄 **File:** \`${data.filename}\`
📁 **Path:** ${data.path}

The thesis has been saved and is ready for download!`,
              timestamp: new Date(),
              isStreaming: false
            };
            setChatMessages(prev => [...prev, completionMessage]);
          }

          if (eventType === 'stage_completed') {
            if (data?.status === 'success') {
              window.dispatchEvent(new CustomEvent('workspace-refresh'));
              eventSource.close();
              setIsProcessing(false);
              setStreamingMessageId(null);
              setCurrentJobId(null);
              setCurrentStatus('✅ Thesis generated successfully!');

              // Mark the streaming message as complete
              setChatMessages(prev => prev.map(msg =>
                msg.id === statusMessage.id
                  ? { ...msg, isStreaming: false }
                  : msg
              ));
            } else if (data?.status === 'error') {
              eventSource.close();
              setIsProcessing(false);
              setStreamingMessageId(null);
              setCurrentJobId(null);
              setCurrentStatus('❌ Thesis generation failed');
            }
          }
        };

        // Listen for named events (SSE sends event: type)
        eventSource.addEventListener('connected', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          // console.log('🔗 SSE connected:', data);
        });

        eventSource.addEventListener('response_chunk', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          handleEvent('response_chunk', data);
        });

        eventSource.addEventListener('log', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          handleEvent('log', data);
        });

        eventSource.addEventListener('agent_activity', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          handleEvent('agent_activity', data);
        });

        eventSource.addEventListener('agent_working', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          handleEvent('agent_activity', data);
        });

        eventSource.addEventListener('file_created', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          handleEvent('file_created', data);
        });

        eventSource.addEventListener('stage_completed', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          handleEvent('stage_completed', data);
        });

        eventSource.addEventListener('stage_started', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          // console.log('🚀 Stage started:', data);
        });

        eventSource.addEventListener('progress', (e) => {
          const data = JSON.parse((e as MessageEvent).data);
          // console.log('📊 Progress:', data);
          if (data.percentage) {
            setCurrentStatus(`Progress: ${data.percentage}% - ${data.current_section || ''}`);
          }
        });

        // Fallback for unnamed events
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type) {
              handleEvent(data.type, data.data || data);
            }
          } catch (e) {
            console.error('Error parsing SSE message:', e);
          }
        };

        eventSource.onerror = (error) => {
          console.error('SSE error:', error);
          // Don't close immediately - might be temporary
        };

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
      setIsProcessing(false);
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
      setIsProcessing(false);
    }
  };

  // Handle PDF file uploads
  const handleFileUpload = async (files: File[]) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const pdfFiles = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));

      if (pdfFiles.length === 0) {
        console.warn('No PDF files selected');
        return;
      }

      // 1. Create a persistent progress message
      const progressId = `upload-progress-${Date.now()}`;
      setChatMessages(prev => [...prev, {
        id: progressId,
        role: 'assistant',
        content: `🚀 Starting upload of ${pdfFiles.length} PDF(s)...`,
        timestamp: new Date(),
        type: 'assistant',
      }]);

      const allResults = [];
      const failed = [];

      // 2. Upload files one by one to show progress
      for (let i = 0; i < pdfFiles.length; i++) {
        const file = pdfFiles[i];

        // Update progress message
        setChatMessages(prev => prev.map(msg =>
          msg.id === progressId
            ? { ...msg, content: `⏳ Uploading file ${i + 1} of ${pdfFiles.length}:\n**${file.name}**...` }
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

      // 3. Remove progress message (or update it to completion)
      setChatMessages(prev => prev.filter(msg => msg.id !== progressId));

      // 4. Show final summary
      const successCount = allResults.length;
      const failCount = failed.length;

      let summary = `✅ **Upload Complete**\nSuccessfully added ${successCount} source(s).`;

      if (allResults.length > 0) {
        summary += `\n\n**📚 Added Sources:**\n` +
          allResults.map((r: any) => `• [${r.original_filename || r.filename}] ${r.title}`).join('\n');
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

  const handleChatStart = async (message?: string, mentionedAgents?: string[], parameters?: ThesisParameters) => {
    if (!message || !message.trim()) return;

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

    // Clear old job_id when starting a new request
    // DON'T clear actions - keep chat history visible
    localStorage.removeItem('current_job_id');

    // Don't auto-open progress panel - user can open manually with Cmd+P
    if (eventSourceRef.current) {
      // console.log("🔌 Closing existing SSE connection before new request");
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

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

    try {
      // Use backend directly - proxy is causing issues
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

      // Build conversation history for context (last 10 messages)
      const recentHistory = chatMessages.slice(-10).map(msg => ({
        role: msg.type === 'assistant' ? 'assistant' : 'user',
        content: msg.content
      }));

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
            const streamingMessageId = `chat-direct-${Date.now()}`;
            const streamingMessage: ChatMessage = {
              id: streamingMessageId,
              type: 'assistant',
              content: '',
              timestamp: new Date(),
              isStreaming: true,
              agent: 'assistant'
            };
            setChatMessages(prev => [...prev, streamingMessage]);

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
                        // Update the streaming message with accumulated content
                        setChatMessages(prev => prev.map(msg =>
                          msg.id === streamingMessageId
                            ? { ...msg, content: accumulatedResponse }
                            : msg
                        ));
                      } else if (eventData.accumulated) {
                        accumulatedResponse = eventData.accumulated;
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

              // If we got a complete response, we're done
              if (accumulatedResponse) {
                setIsProcessing(false);
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
              setIsProcessing(false);
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
            id: `chat-${jobId}-response`,
            type: 'assistant',
            content: data.response,
            timestamp: new Date(),
            isStreaming: false,
            agent: 'assistant'
          };
          setChatMessages(prev => [...prev, assistantChatMessage]);

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

        // Connect to real-time SSE stream for this job
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const streamSessionId = currentSessionId || sessionId || 'new';
        const streamUrl = `${backendUrl}/api/stream/agent-actions?session_id=${streamSessionId}&job_id=${jobId}`;
        streamUrl;

        const eventSource = new EventSource(streamUrl);

        eventSource.onopen = () => {
          // console.log(`✅ SSE stream opened for job: ${jobId}`);
          setCurrentStatus('✅ Connected - receiving updates...');
        };

        // Handle connected event
        eventSource.addEventListener('connected', (e) => {
          // console.log(`✅ SSE connected event:`, e.data);
          try {
            const connData = JSON.parse(e.data);
            if (connData.job_id === jobId) {
              setCurrentStatus('✅ Connected to real-time stream');
            }
          } catch (err) {
            console.error('Error parsing connected event:', err);
          }
        });

        // Handle real-time events
        eventSource.addEventListener('log', (e) => {
          // console.log(`📨 Received log event:`, e.data);
          try {
            const eventData = JSON.parse(e.data);
            const message = eventData.message || '';

            // Update status in real-time (shown in status bar, not timeline)
            setCurrentStatus(message);

            // FILTER: Only show TRULY important milestones in timeline
            // Skip generic progress/completed messages that cause spam
            const skipPatterns = [
              /^progress$/i,
              /^completed$/i,
              /^\d+%/,  // Percentage updates
              /^step \d/i,  // Step X of Y
              /^processing/i,
              /^working/i,
              /^generating\.{0,3}$/i,  // Just "generating..." without details
            ];

            const isSpam = skipPatterns.some(pattern => pattern.test(message.trim()));
            if (isSpam || message.length < 10) {
              return; // Skip spam messages
            }

            // Only show messages with substantial content and clear meaning
            const isMilestone =
              message.includes('✅') ||  // Completion markers
              message.includes('❌') ||  // Error markers  
              message.includes('📄') ||  // File operations
              message.includes('Chapter') ||  // Chapter progress
              message.includes('generated') ||
              message.includes('saved') ||
              message.includes('created') ||
              message.includes('Starting');  // Phase starts

            if (isMilestone) {
              const logAction: AgentAction = {
                id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
                type: 'log' as any,
                timestamp: new Date(),
                title: message.substring(0, 60) + (message.length > 60 ? '...' : ''),  // Use message as title, not generic "Progress"
                content: message.length > 60 ? message : undefined,  // Only show content if long
                status: 'completed'
              };
              setAgentActions(prev => [...prev, logAction]);
            }

            // Update status display
            setCurrentStatus(message);
          } catch (err) {
            console.error('Error parsing log event:', err);
          }
        });

        // Handle agent_activity events (what agents are currently doing)
        eventSource.addEventListener('agent_activity', (e) => {
          try {
            const activityData = JSON.parse(e.data);
            const agent = activityData.agent || 'agent';
            const action = activityData.action || 'working';
            const description = activityData.description || activityData.details || '';
            const progress = activityData.progress || 0;

            // Update current agent display
            setCurrentAgent(agent);
            setCurrentAction(action);
            setCurrentDescription(description);
            setCurrentProgress(progress);

            // Add to status updates history
            setStatusUpdates(prev => [...prev, {
              timestamp: new Date(),
              agent: agent,
              action: action,
              description: description,
              status: 'running'
            }].slice(-10)); // Keep last 10

          } catch (err) {
            console.error('Error parsing agent_activity event:', err);
          }
        });

        eventSource.addEventListener('agent_stream', (e) => {
          try {
            const streamData = JSON.parse(e.data);
            const tabId = streamData.tab_id;
            const chunk = streamData.chunk || '';
            const content = streamData.content || '';
            const isCompleted = streamData.completed === true;

            // Find or create agent tab
            setTabs(prev => {
              const existingTab = prev.find(t => t.id === tabId);

              if (existingTab) {
                // Update existing tab content
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
                // Create new agent tab
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

                // Auto-open agent tab
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

            // Auto-open file in preview panel
            // Handle both relative path (filename) and full path
            const filePath = eventData.full_path || eventData.path || '';
            const wsId = eventData.workspace_id || workspaceId;
            const filename = eventData.filename || filePath.split('/').pop() || filePath;

            // Open file tab
            const fileTab: Tab = {
              id: `file-${filePath}-${Date.now()}`,
              type: 'file',
              title: filename,
              data: {
                path: filePath, // Use full_path if available, otherwise path
                workspaceId: wsId
              },
              workspaceId: wsId,
            };

            setTabs(prev => {
              const exists = prev.find(t => t.data?.path === filePath);
              if (exists) {
                setActiveTabId(exists.id);
                return prev;
              }
              return [...prev, fileTab];
            });
            setActiveTabId(fileTab.id);
            setIsRightPanelOpen(true); // Open right panel if collapsed

            // Refresh workspace
            window.dispatchEvent(new Event('workspace-refresh'));
          } catch (err) {
            console.error('Error parsing file_created event:', err);
          }
        });

        // Handle agent_activity events (search, research, etc.)
        eventSource.addEventListener('agent_activity', (e) => {
          try {
            const activityData = JSON.parse(e.data);
            const agent = activityData.agent || 'agent';
            const action = activityData.action || 'working';
            const query = activityData.query || '';
            const status = activityData.status || 'running';

            // Create or update agent tab for search/research/writing activities
            // Include chapter generator agents
            const agentTypes = [
              'search', 'research', 'researcher', 'image_search', 'image_generator',
              'research_swarm', 'writer_swarm', 'quality_control', 'chapter_generator',
              'intro_writer', 'background_writer', 'problem_writer', 'scope_writer', 'justification_writer'
            ];

            if (agentTypes.includes(agent)) {
              const tabId = `${agent}-${jobId}`;
              const icon = activityData.icon || '🤖';
              const agentName = activityData.agent_name || agent.charAt(0).toUpperCase() + agent.slice(1).replace(/_/g, ' ');

              setTabs(prev => {
                const existingTab = prev.find(t => t.id === tabId);

                if (existingTab) {
                  // Update existing tab
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
                  // Create new agent tab
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

                  // Auto-open agent tab for chapter generators and research
                  if (agent === 'chapter_generator' || agent === 'research_swarm' || agent === 'writer_swarm' || agent === 'research') {
                    setActiveTabId(tabId);
                    setIsRightPanelOpen(true);

                    // Also trigger browser tab if it's a research agent performing an action
                    if (agent === 'research' || agent === 'search') {
                      window.dispatchEvent(new CustomEvent('open-browser-tab', {
                        detail: {
                          title: `🌐 ${agentName}`,
                          sessionId: sessionId || 'default'
                        }
                      }));
                    }
                  }

                  return [...prev, agentTab];
                }
              });
            }

            // Update status
            setCurrentStage(agent);
            setCurrentStatus(`${agent} ${action}: ${query || ''}`);
          } catch (err) {
            console.error('Error parsing agent_activity event:', err);
          }
        });

        // Handle tool_started events
        eventSource.addEventListener('tool_started', (e) => {
          // console.log(`📨 Received tool_started event:`, e.data);
          try {
            const toolData = JSON.parse(e.data);
            // console.log(`🔧 Tool started: ${toolData.tool}, step ${toolData.step}/${toolData.total}`);
            setCurrentStage(toolData.tool || '');
            setCurrentStatus(`Executing ${toolData.tool} (step ${toolData.step}/${toolData.total})...`);
          } catch (err) {
            console.error('Error parsing tool_started event:', err);
          }
        });

        // Handle tool_completed events
        eventSource.addEventListener('tool_completed', (e) => {
          try {
            const toolData = JSON.parse(e.data);
            setCurrentStatus(`✓ ${toolData.tool} completed`);
          } catch (err) {
            console.error('Error parsing tool_completed event:', err);
          }
        });

        // Handle agent_working events - show clickable badges in chat
        eventSource.addEventListener('agent_working', (e) => {
          try {
            const agentData = JSON.parse(e.data);
            const { agent, agent_name, status, action, icon } = agentData;

            setActiveAgents(prev => {
              const existing = prev.find(a => a.agent === agent);
              if (existing) {
                // Update existing agent
                return prev.map(a => a.agent === agent
                  ? { ...a, status, action, icon }
                  : a
                );
              } else {
                // Add new agent
                return [...prev, { agent, agent_name, status, action, icon }];
              }
            });

            // If completed, focus on the agent tab
            if (status === 'running') {
              const tabId = `${agent}-${localStorage.getItem('current_job_id') || 'default'}`;
              setActiveTabId(tabId);
              setIsRightPanelOpen(true);
            }
          } catch (err) {
            console.error('Error parsing agent_working event:', err);
          }
        });

        // Handle stage_started events
        eventSource.addEventListener('stage_started', (e) => {
          // console.log(`📨 Received stage_started event:`, e.data);
          try {
            const stageData = JSON.parse(e.data);
            // console.log(`📋 Stage started: ${stageData.stage}`);
            setCurrentStage(stageData.stage || '');
            setCurrentStatus(stageData.message || `Starting ${stageData.stage}...`);

            // Open browser tab for web search or browse stages
            if (stageData.stage === 'web_search' || stageData.stage === 'browse' || stageData.stage === 'browser') {
              window.dispatchEvent(new CustomEvent('open-browser-tab', {
                detail: {
                  title: stageData.message || '🌐 Live Browser',
                  sessionId: sessionId || 'default'
                }
              }));
            }

            // Add dynamic progress step from real-time event
            const newStep = {
              id: `stage-${stageData.stage}-${Date.now()}`,
              label: stageData.message || `Starting ${stageData.stage}...`,
              status: 'running' as const,
              timestamp: new Date()
            };
            setProgressSteps(prev => [...prev, newStep]);
          } catch (err) {
            console.error('Error parsing stage_started event:', err);
          }
        });

        // Handle reasoning_chunk events (streaming AI thinking)
        eventSource.addEventListener('reasoning_chunk', (e) => {
          // console.log(`📨 Received reasoning_chunk event:`, e.data);
          try {
            const chunkData = JSON.parse(e.data);
            const accumulated = chunkData.accumulated || '';

            // Update or create reasoning action
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
                  title: '', // No hardcoded title - show real content only
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

        // Handle response_chunk events (streaming AI response)
        eventSource.addEventListener('response_chunk', (e) => {
          // console.log(`📨 Received response_chunk event:`, e.data);
          try {
            const chunkData = JSON.parse(e.data);
            const accumulated = chunkData.accumulated || '';

            // Update or create chat message for this response
            setChatMessages(prev => {
              const existingIndex = prev.findIndex(
                msg => msg.id === `chat-${jobId}-response`
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
                // Create new chat message
                const chatMessage: ChatMessage = {
                  id: `chat-${jobId}-response`,
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

            // Update or create response action
            setAgentActions(prev => {
              // Always look for the main response action first
              const existingIndex = prev.findIndex(
                action => action.type === 'stream' && action.id.startsWith(`job-${jobId}-response`)
              );

              if (existingIndex >= 0) {
                const updated = [...prev];
                // Only update if content length increased (avoid out-of-order updates)
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
                // Create new only if it doesn't exist
                const streamAction: AgentAction = {
                  id: `job-${jobId}-response-main`, // FIXED: Stable ID
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

        // Fallback for 'content' events (some routes might still use this)
        eventSource.addEventListener('content', (e: any) => {
          try {
            const contentData = JSON.parse(e.data);
            const chunk = contentData.text || contentData.chunk || '';

            // Update chat messages
            setChatMessages(prev => {
              const existingIndex = prev.findIndex(msg => msg.id === `chat-${jobId}-response`);
              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = {
                  ...updated[existingIndex],
                  content: updated[existingIndex].content + chunk,
                  isStreaming: true
                };
                return updated;
              }
              return [...prev, {
                id: `chat-${jobId}-response`,
                type: 'assistant',
                content: chunk,
                timestamp: new Date(),
                isStreaming: true
              }];
            });
          } catch (err) {
            console.error('Error parsing content event:', err);
          }
        });

        // Handle explicit 'error' events from backend
        eventSource.addEventListener('error', (e: any) => {
          try {
            const errorData = JSON.parse(e.data);
            const errorMessage = errorData.message || 'An unknown error occurred';

            // Add error to chat
            const errorMsg: ChatMessage = {
              id: `error-${Date.now()}`,
              type: 'assistant',
              content: `❌ **Error**: ${errorMessage}`,
              timestamp: new Date(),
              isStreaming: false
            };
            setChatMessages(prev => [...prev, errorMsg]);
            setIsProcessing(false);
          } catch (err) {
            // This might be a generic EventSource error (not JSON)
            console.error('SSE Error event:', e);
          }
        });

        eventSource.addEventListener('stage_completed', (e) => {
          try {
            const eventData = JSON.parse(e.data);
            const stage = eventData.stage || '';

            // Mark streaming actions as completed silently (no UI message)
            if (stage === 'response' || stage === 'complete' || stage === 'completed') {
              setAgentActions(prev => prev.map(action => {
                if (action.isStreaming && action.status === 'running') {
                  return { ...action, status: 'completed', isStreaming: false };
                }
                return action;
              }));
            }

            // If the "complete" stage is completed, stop processing silently
            if (stage === 'complete' || stage === 'completed') {
              setIsProcessing(false);
              setCurrentStatus('');
              setCurrentStage('');
            }

            // Mark progress step as completed
            setProgressSteps(prev => prev.map(step =>
              step.id.includes(`stage-${stage}`) ? { ...step, status: 'completed' } : step
            ));

            // Don't show stage completion messages - they're generic progress updates
            // Only real content (reasoning_chunk, response_chunk) should be visible
          } catch (err) {
            console.error('Error parsing stage_completed event:', err);
          }
        });

        eventSource.addEventListener('done', async (e) => {
          // console.log(`🏁 Received done event for job: ${jobId}`);

          // Persist the final response when the job is done
          try {
            // Get the final content from the current state (need to be careful with closures here)
            // In React, we'd ideally use a ref or the updater function.
            // Since this is an event listener added once, it might have stale sessionId.
            setChatMessages(prev => {
              const finalMsg = prev.find(m => m.id === `chat-${jobId}-response`);
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
              return prev;
            });
          } catch (err) {
            console.error('Error during final message persistence:', err);
          }

          setIsProcessing(false);
          setCurrentStatus('');
          setCurrentStage('');
          if (eventSourceRef.current === eventSource) {
            eventSource.close();
            eventSourceRef.current = null;
          }
        });

        eventSource.onerror = (error) => {
          console.error('SSE stream error for job:', jobId, error);
          // Don't close on error - EventSource will auto-reconnect
          if (eventSource.readyState === EventSource.CLOSED) {
            console.error('SSE stream closed permanently for job:', jobId);
            setCurrentStatus('❌ Stream connection lost');
            setIsProcessing(false);
          }
        };

        // Store eventSource reference for cleanup
        eventSourceRef.current = eventSource;
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
          setIsProcessing(false);
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
          setIsProcessing(false);
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
          id: `chat-response-${Date.now()}`,
          type: 'assistant',
          content: responseText,
          timestamp: new Date(),
          isStreaming: false,
          agent: 'assistant'
        };
        setChatMessages(prev => [...prev, assistantChatMessage]);

        setIsProcessing(false);
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
        const filePath = data.file_created.path;
        const wsId = data.file_created.workspace_id || workspaceId;

        // Open file in preview panel
        const fileTab: Tab = {
          id: `file-${filePath}-${Date.now()}`,
          type: 'file',
          title: filePath.split('/').pop() || filePath,
          data: {
            path: filePath,
            workspaceId: wsId
          },
          workspaceId: wsId,
        };

        setTabs(prev => {
          const exists = prev.find(t => t.data?.path === filePath);
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

      setIsProcessing(false);
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
      setIsProcessing(false);
      setCurrentStatus('');
      setCurrentStage('');
    }
  };

  const handleProcessingComplete = () => {
    setIsProcessing(false);
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
      setAgentActions([]);
      setReasoning('');
      setCurrentStatus('');
      setCurrentStage('');
      setIsProcessing(false);

      // Crucial: Clear messages and localStorage for the old workspace
      setChatMessages([]);
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
          <div className="flex flex-col h-full overflow-hidden bg-white" style={{ backgroundColor: 'var(--color-panel, #FFFFFF)' }}>
            {/* Enhanced Chat Display - Shows messages with real streaming */}
            <EnhancedChatDisplay
              messages={chatMessages}
              isProcessing={isProcessing}
              currentAgent={currentAgent}
              currentAction={currentAction}
              currentDescription={currentDescription}
              currentProgress={currentProgress}
              processSteps={progressSteps}
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
