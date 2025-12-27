'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, Upload, X, File as FileIcon, Image, FileText, Square, AtSign, Check, BookOpen, CheckCircle2, AlertCircle, MessageCircle, Zap, Eye } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Alert } from '../ui/alert';
import { Card } from '../ui/card';

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

interface ChatBarProps {
  onChatStart?: (message: string, mentionedAgents?: string[]) => void;
  onFileUpload?: (files: File[]) => void;
  isProcessing?: boolean;
  placeholder?: string;
  onStop?: () => void;
  currentStatus?: string;
  currentStage?: string;
}

export function ChatBar({
  onChatStart,
  onFileUpload,
  isProcessing = false,
  placeholder = 'Ask me about your research, request content generation, or seek assistance... (use @ for agents, / for universities)',
  onStop,
  currentStatus,
  currentStage
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

  // University slash command state
  const [universities, setUniversities] = useState<University[]>([]);
  const [showUniversities, setShowUniversities] = useState(false);
  const [universityQuery, setUniversityQuery] = useState('');
  const [selectedUniversityIndex, setSelectedUniversityIndex] = useState(0);
  const [selectedUniversity, setSelectedUniversity] = useState<University | null>(null);
  const [slashStartPos, setSlashStartPos] = useState<number | null>(null);

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
        // console.log('✅ Loaded agents:', data.agents);
        setAgents(data.agents);
      } else {
        // Use default agents if API returns empty
        // console.log('⚠️ No agents from API, using defaults');
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
      // Set default agents on error
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

  // Fetch universities on mount
  const fetchUniversities = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${backendUrl}/api/thesis/universities`);
      const data = await response.json();
      if (data.universities && data.universities.length > 0) {
        // console.log('✅ Loaded universities:', data.universities);
        setUniversities(data.universities);
      } else {
        // Use default universities if API returns empty
        // console.log('⚠️ No universities from API, using defaults');
        setUniversities([
          { type: 'uoj_phd', name: 'University of Juba PhD', abbreviation: 'UoJ', description: 'PhD thesis template for University of Juba' },
          { type: 'generic', name: 'Generic University', abbreviation: 'GEN', description: 'Generic thesis template' },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch universities:', error);
      // Set default universities on error
      setUniversities([
        { type: 'uoj_phd', name: 'University of Juba PhD', abbreviation: 'UoJ', description: 'PhD thesis template for University of Juba' },
        { type: 'generic', name: 'Generic University', abbreviation: 'GEN', description: 'Generic thesis template' },
      ]);
    }
  };

  useEffect(() => {
    fetchUniversities();
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
        setShowUniversities(false);
        // console.log('🔍 Showing mentions for query:', query, 'Agents:', agents.length);
      }
    } else {
      setShowMentions(false);
      setMentionQuery('');
      setMentionStartPos(null);
    }

    // Check for / slash command (universities)
    if (!atIsMoreRecent && lastSlashIndex !== -1) {
      const textAfterSlash = textBeforeCursor.substring(lastSlashIndex + 1);
      // Check if there's a space or newline after / (command ended)
      if (textAfterSlash.includes(' ') || textAfterSlash.includes('\n')) {
        setShowUniversities(false);
        setUniversityQuery('');
        setSlashStartPos(null);
      } else {
        // Show universities dropdown
        const query = textAfterSlash.toLowerCase();
        setShowUniversities(true);
        setUniversityQuery(query);
        setSlashStartPos(lastSlashIndex);
        setSelectedUniversityIndex(0);
        // console.log('📚 Showing universities for query:', query, 'Universities:', universities.length);
      }
    } else {
      setShowUniversities(false);
      setUniversityQuery('');
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

  const insertUniversity = (university: University) => {
    if (!textareaRef.current || slashStartPos === null) return;

    const textBefore = message.substring(0, slashStartPos);
    const textAfter = message.substring(textareaRef.current.selectionStart);
    const newMessage = `${textBefore}/${university.type} ${textAfter}`;

    setMessage(newMessage);
    setSelectedUniversity(university);
    setShowUniversities(false);
    setUniversityQuery('');
    setSlashStartPos(null);

    // Focus back on textarea
    setTimeout(() => {
      textareaRef.current?.focus();
      const newCursorPos = slashStartPos + university.type.length + 2; // +2 for / and space
      textareaRef.current?.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(mentionQuery) ||
    agent.display_name.toLowerCase().includes(mentionQuery)
  );

  const filteredUniversities = universities.filter(uni =>
    uni.type.toLowerCase().includes(universityQuery) ||
    uni.name.toLowerCase().includes(universityQuery)
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

    if (showUniversities) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedUniversityIndex(prev =>
          prev < filteredUniversities.length - 1 ? prev + 1 : prev
        );
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedUniversityIndex(prev => prev > 0 ? prev - 1 : 0);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (filteredUniversities[selectedUniversityIndex]) {
          insertUniversity(filteredUniversities[selectedUniversityIndex]);
        }
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowUniversities(false);
        setUniversityQuery('');
        setSlashStartPos(null);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey && !showMentions && !showUniversities) {
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
        "relative rounded-3xl transition-all duration-500 shadow-2xl overflow-hidden",
        isFocused
          ? "bg-background border-primary/30 ring-4 ring-primary/5"
          : "bg-muted/30 border-transparent backdrop-blur-sm"
      )}>
        <form onSubmit={handleSubmit} className="flex flex-col">
          {/* Files Preview Row (Integrated) */}
          {uploadedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 p-3 bg-muted/20 border-b border-border/10">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center gap-2 px-2 py-1 rounded-lg bg-background border border-border/40 shadow-sm animate-in zoom-in-95 duration-200">
                  {getFileIcon(file)}
                  <span className="text-[10px] font-semibold truncate max-w-[120px]">{file.name}</span>
                  <button onClick={() => removeFile(index)} className="hover:text-destructive transition-colors">
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
                  "text-sm font-medium placeholder:text-muted-foreground/50",
                  "focus:outline-none disabled:opacity-50 max-h-48"
                )}
                disabled={isProcessing}
                style={{ height: textareaRef.current ? Math.min(textareaRef.current.scrollHeight, 192) : 'auto' }}
              />

              {/* Redesigned Mentions & Slash Dropdowns */}
              {(showMentions || showUniversities) && (
                <div data-dropdown className="absolute bottom-full left-0 mb-4 w-full max-w-[320px] animate-in slide-in-from-bottom-2 duration-200">
                  <Card className="p-1.5 shadow-2xl border-primary/10 backdrop-blur-xl bg-background/95 rounded-2xl">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 px-3 py-2">
                      {showMentions ? 'Mention Agent' : 'Select Template'}
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
                              index === selectedMentionIndex ? "bg-primary text-primary-foreground shadow-lg scale-[1.02]" : "hover:bg-muted text-foreground"
                            )}
                          >
                            <span className="text-base">{getAgentIcon(agent.name)}</span>
                            <div className="flex-1">
                              <div className="font-bold">{agent.display_name}</div>
                              <div className={cn("text-[9px] uppercase tracking-tighter", index === selectedMentionIndex ? "text-primary-foreground/70" : "text-muted-foreground/70")}>{agent.type}</div>
                            </div>
                            {mentionedAgents.includes(agent.id) && <Check className="w-3 h-3" />}
                          </button>
                        ))
                      ) : (
                        filteredUniversities.map((uni, index) => (
                          <button
                            key={uni.type}
                            type="button"
                            onMouseDown={(e) => { e.preventDefault(); insertUniversity(uni); }}
                            className={cn(
                              "w-full text-left px-3 py-2.5 rounded-xl text-xs flex items-center gap-3 transition-all",
                              index === selectedUniversityIndex ? "bg-primary text-primary-foreground shadow-lg scale-[1.02]" : "hover:bg-muted text-foreground"
                            )}
                          >
                            <BookOpen className="w-4 h-4" />
                            <div className="flex-1">
                              <div className="font-bold">{uni.name}</div>
                              <div className={cn("text-[9px] uppercase tracking-tighter text-muted-foreground/70", index === selectedUniversityIndex && "text-primary-foreground/70")}>{uni.abbreviation}</div>
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  </Card>
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
          Shift + Enter for new line • @ mention agents • / university templates
        </p>
      </div>
    </div>
  );
}
