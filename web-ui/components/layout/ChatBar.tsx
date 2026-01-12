'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, Upload, X, File as FileIcon, Image, FileText, Square, AtSign, Check, BookOpen, CheckCircle2, AlertCircle, MessageCircle, Zap, Eye } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Alert } from '../ui/alert';
import { Card } from '../ui/card';
import { ParameterCollectionModal } from '../thesis/ParameterCollectionModal';
import { ThesisParameters } from '../../lib/thesisParameters';

interface Agent {
  id: string;
  name: string;
  display_name: string;
  type: string;
  health: string;
}

interface University {
  type: string;
  name: string;
  abbreviation: string;
  description: string;
}

interface Workflow {
  command: string;
  description: string;
  icon: string;
  category: string;
}

interface ChatBarProps {
  onChatStart?: (message: string, mentionedAgents?: string[], parameters?: ThesisParameters) => void;
  onFileUpload?: (files: File[]) => void;
  isProcessing?: boolean;
  placeholder?: string;
  onStop?: () => void;
  currentStatus?: string;
  currentStage?: string;
  workspaceId?: string;
  sessionId?: string;
}

const DEFAULT_WORKFLOWS: Workflow[] = [
  { command: 'good', description: 'Custom love flow (topic, country, case study)', icon: '❤️', category: 'thesis' },
  { command: 'uoj_general', description: 'University of Juba General (Bachelor) Proposal', icon: '🎓', category: 'thesis' },
  { command: 'uoj_phd', description: 'University of Juba PhD Thesis', icon: '🏛️', category: 'thesis' },
  { command: 'generate-full-thesis', description: 'Generate complete PhD thesis (all 6 chapters)', icon: '📚', category: 'thesis' },
  { command: 'generate-chapter1', description: 'Generate Chapter 1 (Introduction)', icon: '📖', category: 'thesis' },
  { command: 'generate-chapter2', description: 'Generate Chapter 2 (Literature Review)', icon: '📚', category: 'thesis' },
];

export function ChatBar({
  onChatStart,
  onFileUpload,
  isProcessing = false,
  placeholder = 'Ask me about your research, request content generation, or seek assistance... (use @ for agents, / for thesis commands)',
  onStop,
  currentStatus,
  currentStage,
  workspaceId,
  sessionId
}: ChatBarProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Agent mention state
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);
  const [mentionedAgents, setMentionedAgents] = useState<string[]>([]);
  const [mentionStartPos, setMentionStartPos] = useState<number | null>(null);

  // Workflow slash command state
  const [workflows, setWorkflows] = useState<Workflow[]>(DEFAULT_WORKFLOWS);
  const [showWorkflows, setShowWorkflows] = useState(false);
  const [workflowQuery, setWorkflowQuery] = useState('');
  const [selectedWorkflowIndex, setSelectedWorkflowIndex] = useState(0);
  const [slashStartPos, setSlashStartPos] = useState<number | null>(null);

  // Parameter collection modal state
  const [showParameterModal, setShowParameterModal] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [initialParameters, setInitialParameters] = useState<Partial<ThesisParameters>>({});

  // Fetch agents on mount
  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${backendUrl}/api/agents/list`);
      const data = await response.json();
      if (data.status === 'ok' && data.agents && data.agents.length > 0) {
        setAgents(data.agents);
      } else {
        setAgents([
          { id: 'research', name: 'research', display_name: 'Research Agent', type: 'agent', health: 'healthy' },
          { id: 'writer', name: 'writer', display_name: 'Writer Agent', type: 'agent', health: 'healthy' },
          { id: 'editor', name: 'editor', display_name: 'Editor Agent', type: 'agent', health: 'healthy' },
          { id: 'planner', name: 'planner', display_name: 'Planner Agent', type: 'agent', health: 'healthy' },
          { id: 'search', name: 'search', display_name: 'Search Agent', type: 'agent', health: 'healthy' },
          { id: 'citation', name: 'citation', display_name: 'Citation Agent', type: 'agent', health: 'healthy' },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error);
      setAgents([
        { id: 'research', name: 'research', display_name: 'Research Agent', type: 'agent', health: 'healthy' },
        { id: 'writer', name: 'writer', display_name: 'Writer Agent', type: 'agent', health: 'healthy' },
        { id: 'editor', name: 'editor', display_name: 'Editor Agent', type: 'agent', health: 'healthy' },
        { id: 'planner', name: 'planner', display_name: 'Planner Agent', type: 'agent', health: 'healthy' },
        { id: 'search', name: 'search', display_name: 'Search Agent', type: 'agent', health: 'healthy' },
        { id: 'citation', name: 'citation', display_name: 'Citation Agent', type: 'agent', health: 'healthy' },
      ]);
    }
  };

  // Fetch workflows on mount
  const fetchWorkflows = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${backendUrl}/api/thesis/workflows`);
      const data = await response.json();
      if (data.workflows && data.workflows.length > 0) {
        console.log('✅ Loaded workflows:', data.workflows);
        // Combine API workflows with our critical defaults to ensure they exist
        const apiWorkflows = data.workflows;
        const missingDefaults = DEFAULT_WORKFLOWS.filter(dw =>
          !apiWorkflows.some((aw: Workflow) => aw.command === dw.command)
        );
        setWorkflows([...missingDefaults, ...apiWorkflows]);
      } else {
        console.log('⚠️ No workflows from API, using defaults');
        setWorkflows(DEFAULT_WORKFLOWS);
      }
    } catch (error) {
      console.error('Failed to fetch workflows:', error);
      setWorkflows(DEFAULT_WORKFLOWS);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() && uploadedFiles.length === 0) return;

    if (uploadedFiles.length > 0 && onFileUpload) {
      onFileUpload(uploadedFiles);
      setUploadedFiles([]);
    }

    if (message.trim()) {
      onChatStart?.(message.trim(), mentionedAgents.length > 0 ? mentionedAgents : undefined);
      setMessage('');
      setMentionedAgents([]);
    }
  };

  const handleMessageChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart;

    setMessage(value);

    const textBeforeCursor = value.substring(0, cursorPos);

    // Check for @ mention
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    const lastSlashIndex = textBeforeCursor.lastIndexOf('/');

    // Determine which command (@ or /) is more recent
    const atIsMoreRecent = lastAtIndex > lastSlashIndex;

    if (atIsMoreRecent && lastAtIndex !== -1) {
      const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);
      // Check if there's a space or newline after @ (mention ended)
      if (textAfterAt.includes(' ') || textAfterAt.includes('\n')) {
        setShowMentions(false);
        setMentionQuery('');
        setMentionStartPos(null);
      } else {
        // Show mentions dropdown
        const query = textAfterAt.toLowerCase();
        setShowMentions(true);
        setMentionQuery(query);
        setMentionStartPos(lastAtIndex);
        setSelectedMentionIndex(0);
        setShowWorkflows(false);
        // console.log('🔍 Showing mentions for query:', query, 'Agents:', agents.length);
      }
    } else {
      setShowMentions(false);
      setMentionQuery('');
      setMentionStartPos(null);
    }

    // Check for / slash command (workflows)
    if (!atIsMoreRecent && lastSlashIndex !== -1) {
      const textAfterSlash = textBeforeCursor.substring(lastSlashIndex + 1);
      // Check if there's a space or newline after / (command ended)
      if (textAfterSlash.includes(' ') || textAfterSlash.includes('\n')) {
        setShowWorkflows(false);
        setWorkflowQuery('');
        setSlashStartPos(null);
      } else {
        // Show workflows dropdown
        const query = textAfterSlash.toLowerCase();
        setShowWorkflows(true);
        setWorkflowQuery(query);
        setSlashStartPos(lastSlashIndex);
        setSelectedWorkflowIndex(0);
        console.log('📚 Showing workflows for query:', query, 'Workflows:', workflows.length);
      }
    } else {
      setShowWorkflows(false);
      setWorkflowQuery('');
      setSlashStartPos(null);
    }
  };

  const insertMention = (agent: Agent) => {
    if (!textareaRef.current || mentionStartPos === null) return;

    const textBefore = message.substring(0, mentionStartPos);
    const textAfter = message.substring(textareaRef.current.selectionStart);
    const newMessage = `${textBefore}@${agent.name} ${textAfter}`;

    setMessage(newMessage);
    setShowMentions(false);
    setMentionQuery('');
    setMentionStartPos(null);

    // Track mentioned agent
    if (!mentionedAgents.includes(agent.id)) {
      setMentionedAgents([...mentionedAgents, agent.id]);
    }

    // Focus back on textarea
    setTimeout(() => {
      textareaRef.current?.focus();
      const newCursorPos = mentionStartPos + agent.name.length + 2; // +2 for @ and space
      textareaRef.current?.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  const extractParametersFromMessage = (msg: string): Partial<ThesisParameters> => {
    const params: Partial<ThesisParameters> = {};

    // Extract topic: topic="Title" or topic: Title
    const topicMatch = msg.match(/topic\s*[:=]\s*['"]?([^'"]+)['"]?/i);
    if (topicMatch) params.topic = topicMatch[1];

    // Extract case study: case_study="Juba"
    const caseMatch = msg.match(/case[ _]study\s*[:=]\s*['"]?([^'"]+)['"]?/i);
    if (caseMatch) params.caseStudy = caseMatch[1];

    // Extract sample size: n=120
    const nMatch = msg.match(/\b(n|sample[ _]size)\s*[:=]\s*(\d+)/i);
    if (nMatch) params.sampleSize = parseInt(nMatch[2]);

    // Extract design: design="mixed"
    const designMatch = msg.match(/design\s*[:=]\s*['"]?(quantitative|qualitative|mixed|mixed_methods|survey|case_study|ethnographic|phenomenological|grounded_theory|experimental|quasi_experimental|clinical|descriptive|correlational|longitudinal|cross_sectional)['"]?/i);
    if (designMatch) params.researchDesign = designMatch[1] as any;

    // Fallback: If no explicit topic tag, use all text after the command as the topic
    if (!params.topic) {
      // Strip the command itself (e.g. /uoj_phd)
      const textWithoutCommand = msg.replace(/^\/[a-zA-Z0-9_-]+/, '').trim();
      if (textWithoutCommand && !textWithoutCommand.includes('=')) {
        params.topic = textWithoutCommand;
      }
    }

    return params;
  };

  const insertWorkflow = (workflow: Workflow) => {
    // Close the workflow dropdown
    setShowWorkflows(false);
    setWorkflowQuery('');
    setSlashStartPos(null);

    const initialParams = extractParametersFromMessage(message);
    setInitialParameters(initialParams);

    // Clear the message
    setMessage('');

    // Show parameter collection modal
    setSelectedWorkflow(workflow);
    setShowParameterModal(true);
  };

  const handleParameterSubmit = (parameters: ThesisParameters) => {
    if (!selectedWorkflow) return;

    // Format the message with workflow command and parameters
    const paramMessage = `/${selectedWorkflow.command} ${parameters.topic}${parameters.caseStudy ? ` in ${parameters.caseStudy}` : ''}`;

    // Send the message with parameters as metadata
    if (onChatStart) {
      onChatStart(paramMessage, mentionedAgents.length > 0 ? mentionedAgents : undefined, parameters);
    }

    setMessage('');
    setMentionedAgents([]);
    setShowParameterModal(false);
    setSelectedWorkflow(null);
    setInitialParameters({});
  };

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(mentionQuery) ||
    agent.display_name.toLowerCase().includes(mentionQuery)
  );

  const filteredWorkflows = workflows.filter(wf =>
    wf.command.toLowerCase().includes(workflowQuery) ||
    wf.description.toLowerCase().includes(workflowQuery)
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (showMentions) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedMentionIndex(prev =>
          prev < filteredAgents.length - 1 ? prev + 1 : prev
        );
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedMentionIndex(prev => prev > 0 ? prev - 1 : 0);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (filteredAgents[selectedMentionIndex]) {
          insertMention(filteredAgents[selectedMentionIndex]);
        }
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowMentions(false);
        setMentionQuery('');
        setMentionStartPos(null);
        return;
      }
    }

    if (showWorkflows) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedWorkflowIndex(prev =>
          prev < filteredWorkflows.length - 1 ? prev + 1 : prev
        );
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedWorkflowIndex(prev => prev > 0 ? prev - 1 : 0);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (filteredWorkflows[selectedWorkflowIndex]) {
          insertWorkflow(filteredWorkflows[selectedWorkflowIndex]);
        }
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowWorkflows(false);
        setWorkflowQuery('');
        setSlashStartPos(null);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey && !showMentions && !showWorkflows) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setUploadedFiles(prev => [...prev, ...files]);
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) return <Image className="w-4 h-4" />;
    if (file.type.includes('pdf')) return <FileText className="w-4 h-4" />;
    return <FileIcon className="w-4 h-4" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getAgentIcon = (agentName: string) => {
    const icons: { [key: string]: string } = {
      research: '🔬',
      writer: '📝',
      editor: '✏️',
      planner: '🧠',
      citation: '✓',
      search: '🔍'
    };
    return icons[agentName.toLowerCase()] || '🤖';
  };

  return (
    <div className={cn(
      "relative z-50 transition-all duration-300",
      isFocused ? "px-2 py-2" : "px-4 py-4"
    )}>
      {/* Redesigned Floating Status Indicator */}
      {isProcessing && (
        <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-auto animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="flex items-center gap-3 px-4 py-1.5 rounded-full bg-background/80 backdrop-blur-md border border-primary/20 shadow-xl">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '200ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '400ms' }} />
            </div>
            <span className="text-[11px] font-bold tracking-tight text-primary/80 uppercase">
              {currentStatus || 'Processing...'}
            </span>
            {onStop && (
              <button
                onClick={onStop}
                className="ml-2 p-1 hover:bg-destructive/10 rounded-full transition-colors group"
              >
                <Square className="w-3 h-3 text-destructive/60 group-hover:text-destructive" fill="currentColor" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Main Input Container */}
      <div className={cn(
        "relative rounded-3xl transition-all duration-500 shadow-2xl overflow-visible",
        isFocused
          ? "bg-background border-primary/30 ring-4 ring-primary/5"
          : "bg-muted/30 border-transparent backdrop-blur-sm"
      )}>
        <form onSubmit={handleSubmit} className="flex flex-col">
          {/* Upload Progress Indicator Overlay */}
          {uploadedFiles.length > 0 && uploadedFiles.some(f => (f as any).progress !== undefined) && (
            <div className="absolute inset-0 z-20 bg-background/90 backdrop-blur-sm flex items-center justify-center rounded-3xl animate-in fade-in duration-200">
              <div className="w-3/4 max-w-sm space-y-3">
                {uploadedFiles.map((file: any, index) => (
                  file.progress !== undefined && (
                    <div key={index} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="truncate max-w-[70%]">{file.name}</span>
                        <span className="text-primary">{file.progress}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300 ease-out"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    </div>
                  )
                ))}
                <div className="text-center text-[10px] text-muted-foreground animate-pulse mt-2">
                  Uploading files to workspace...
                </div>
              </div>
            </div>
          )}

          {/* Files Preview Row (Integrated) */}
          {uploadedFiles.length > 0 && !uploadedFiles.some(f => (f as any).progress !== undefined) && (
            <div className="flex flex-wrap gap-2 p-3 bg-muted/20 border-b border-border/10">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center gap-2 px-2 py-1 rounded-lg bg-background border border-border/40 shadow-sm animate-in zoom-in-95 duration-200">
                  {getFileIcon(file)}
                  <span className="text-[10px] font-semibold truncate max-w-[120px]">{file.name}</span>
                  <button onClick={() => removeFile(index)} className="hover:text-destructive transition-colors" type="button">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="relative flex items-end p-2 gap-2">
            {/* Mention / Slash Overlay Container */}
            <div className="relative flex-1">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={handleMessageChange}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={(e) => {
                  const relatedTarget = e.relatedTarget as HTMLElement;
                  if (relatedTarget?.closest('[data-dropdown]')) return;
                  setTimeout(() => {
                    if (!document.activeElement?.closest('[data-dropdown]')) {
                      setIsFocused(false);
                    }
                  }, 200);
                }}
                placeholder={placeholder}
                rows={1}
                className={cn(
                  "w-full resize-none bg-transparent px-4 py-3 pr-10",
                  "text-sm font-medium text-foreground placeholder:text-muted-foreground/50",
                  "focus:outline-none disabled:opacity-50 max-h-48"
                )}
                disabled={isProcessing}
                style={{ height: textareaRef.current ? Math.min(textareaRef.current.scrollHeight, 192) : 'auto' }}
              />

              {/* Redesigned Mentions & Slash Dropdowns */}
              {(showMentions || showWorkflows) && (
                <div data-dropdown className="absolute bottom-full left-0 mb-4 w-full max-w-[420px] animate-in slide-in-from-bottom-2 duration-200 z-[100]">
                  <div className="p-1.5 shadow-2xl border border-border backdrop-blur-xl bg-card rounded-2xl" style={{ backgroundColor: '#262626', borderColor: '#393939' }}>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-3 py-2" style={{ color: '#8D8D8D' }}>
                      {showMentions ? 'Mention Agent' : 'Thesis Commands'}
                    </div>
                    <div className="max-h-60 overflow-y-auto space-y-0.5 custom-scrollbar">
                      {showMentions ? (
                        filteredAgents.map((agent, index) => (
                          <button
                            key={agent.id}
                            type="button"
                            onMouseDown={(e) => { e.preventDefault(); insertMention(agent); }}
                            className={cn(
                              "w-full text-left px-3 py-2.5 rounded-xl text-xs flex items-center gap-3 transition-all",
                              index === selectedMentionIndex ? "bg-primary text-primary-foreground shadow-lg scale-[1.02]" : "hover:bg-muted text-card-foreground"
                            )}
                          >
                            <span className="text-base">{getAgentIcon(agent.name)}</span>
                            <div className="flex-1">
                              <div className="font-bold">{agent.display_name}</div>
                              <div className={cn("text-[9px] uppercase tracking-tighter", index === selectedMentionIndex ? "text-primary-foreground/70" : "text-muted-foreground")}>{agent.type}</div>
                            </div>
                            {mentionedAgents.includes(agent.id) && <Check className="w-3 h-3" />}
                          </button>
                        ))
                      ) : (
                        filteredWorkflows.map((workflow, index) => (
                          <button
                            key={workflow.command}
                            type="button"
                            onMouseDown={(e) => { e.preventDefault(); insertWorkflow(workflow); }}
                            className={cn(
                              "w-full text-left px-3 py-2.5 rounded-xl text-xs flex items-center gap-3 transition-all",
                              index === selectedWorkflowIndex ? "bg-primary text-primary-foreground shadow-lg scale-[1.02]" : "hover:bg-muted text-card-foreground"
                            )}
                            style={index !== selectedWorkflowIndex ? { color: '#F4F4F4' } : undefined}
                          >
                            <span className="text-lg">{workflow.icon}</span>
                            <div className="flex-1">
                              <div className="font-bold">/{workflow.command}</div>
                              <div className={cn("text-[9px] tracking-tight", index === selectedWorkflowIndex ? "text-primary-foreground/70" : "text-muted-foreground")} style={{ color: index === selectedWorkflowIndex ? undefined : '#8D8D8D' }}>{workflow.description}</div>
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Actions & Send Button */}
            <div className="flex items-center gap-1.5 pb-1 pr-1">
              <input ref={fileInputRef} type="file" multiple onChange={handleFileSelect} className="hidden" />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                className="p-2.5 rounded-2xl hover:bg-muted text-muted-foreground/60 hover:text-foreground transition-all active:scale-90"
              >
                <Upload className="w-5 h-5" />
              </button>

              <button
                type="submit"
                disabled={isProcessing || (!message.trim() && uploadedFiles.length === 0)}
                className={cn(
                  "p-2.5 rounded-2xl transition-all active:scale-95 shadow-lg",
                  isProcessing || (!message.trim() && uploadedFiles.length === 0)
                    ? "bg-muted text-muted-foreground/40"
                    : "bg-primary text-primary-foreground shadow-primary/20 hover:shadow-primary/30 hover:scale-105"
                )}
              >
                {isProcessing ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>

          {/* Bottom Indicators (Integrated) */}
          {mentionedAgents.length > 0 && (
            <div className="flex items-center gap-2 px-4 pb-3 animate-in fade-in slide-in-from-top-1">
              <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/50">Active Agents:</span>
              <div className="flex gap-1">
                {mentionedAgents.map(id => {
                  const agent = agents.find(a => a.id === id);
                  return agent ? (
                    <span key={id} className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/10">
                      {getAgentIcon(agent.name)} {agent.name}
                    </span>
                  ) : null;
                })}
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Footer Text */}
      <div className="mt-3 px-4 flex justify-center">
        <p className="text-[10px] font-medium text-muted-foreground/40 text-center tracking-wide">
          Shift + Enter for new line • @ mention agents • / thesis commands
        </p>
      </div>

      {selectedWorkflow && (
        <ParameterCollectionModal
          isOpen={showParameterModal}
          onClose={() => {
            setShowParameterModal(false);
            setSelectedWorkflow(null);
            setInitialParameters({});
          }}
          onSubmit={handleParameterSubmit}
          workflowCommand={selectedWorkflow.command}
          workflowDescription={selectedWorkflow.description}
          initialParameters={initialParameters}
          workspaceId={workspaceId}
          sessionId={sessionId}
        />
      )}
    </div>
  );
}
