'use client';

import React, { useState, useEffect, useRef } from 'react';
import { X, FileText, Code2, Image as ImageIcon, File, Sparkles, Loader2, Copy, Download, Save } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface OpenFile {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'text' | 'code' | 'markdown' | 'image' | 'stream' | 'agent';
  content?: string;
  isStreaming?: boolean;
  isDirty?: boolean;
}

interface MainWorkspaceProps {
  openFiles: OpenFile[];
  activeFileId: string | null;
  onCloseFile: (fileId: string) => void;
  onSelectFile: (fileId: string) => void;
  onUpdateFile?: (fileId: string, content: string) => void;
  onSaveFile?: (fileId: string) => void;
}

export function MainWorkspace({
  openFiles,
  activeFileId,
  onCloseFile,
  onSelectFile,
  onUpdateFile,
  onSaveFile
}: MainWorkspaceProps) {
  const activeFile = openFiles.find(f => f.id === activeFileId);
  const [editedContent, setEditedContent] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const streamEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (activeFile) {
      setEditedContent(activeFile.content || '');
      setIsEditing(false);
    }
  }, [activeFile]);

  useEffect(() => {
    // Auto-scroll streaming content
    if (activeFile?.isStreaming && streamEndRef.current) {
      streamEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeFile?.content, activeFile?.isStreaming]);

  const handleSave = () => {
    if (activeFile && onSaveFile) {
      onSaveFile(activeFile.id);
    }
  };

  const handleContentChange = (newContent: string) => {
    setEditedContent(newContent);
    if (onUpdateFile && activeFile) {
      onUpdateFile(activeFile.id, newContent);
    }
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'code':
        return <Code2 className="w-4 h-4" />;
      case 'image':
        return <ImageIcon className="w-4 h-4" />;
      case 'stream':
      case 'agent':
        return <Sparkles className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const renderContent = () => {
    if (!activeFile) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center space-y-4">
            <div className="w-24 h-24 mx-auto rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-primary-bg, #EDF5FF)' }}>
              <FileText className="w-12 h-12" style={{ color: 'var(--color-primary, #0F62FE)' }} />
            </div>
            <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text, #161616)' }}>
              Open a file to get started
            </h2>
            <p className="text-lg" style={{ color: 'var(--color-text-secondary, #525252)' }}>
              Click on a file in the left panel to open it here
            </p>
          </div>
        </div>
      );
    }

    // Streaming/Agent output
    if (activeFile.type === 'stream' || activeFile.type === 'agent') {
      return (
        <div className="h-full flex flex-col">
          <div className="flex-1 overflow-auto p-6">
            <div className="max-w-4xl mx-auto">
              <div className="prose prose-lg max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm" style={{ color: 'var(--color-text, #161616)' }}>
                  {activeFile.content || ''}
                  {activeFile.isStreaming && (
                    <span className="inline-block w-2 h-4 ml-1 bg-blue-600 animate-pulse" />
                  )}
                </pre>
              </div>
              <div ref={streamEndRef} />
            </div>
          </div>
        </div>
      );
    }

    // Image files
    if (activeFile.type === 'image') {
      return (
        <div className="h-full flex items-center justify-center p-6">
          <img
            src={activeFile.content || `http://localhost:8000/api/workspace/${activeFile.path}`}
            alt={activeFile.name}
            className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
          />
        </div>
      );
    }

    // Text/Code/Markdown files
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 overflow-auto">
          {isEditing ? (
            <textarea
              ref={textareaRef}
              value={editedContent}
              onChange={(e) => handleContentChange(e.target.value)}
              className="w-full h-full p-6 font-mono text-sm outline-none resize-none"
              style={{
                backgroundColor: 'var(--color-panel, #FFFFFF)',
                color: 'var(--color-text, #161616)',
              }}
              placeholder="Start typing..."
            />
          ) : (
            <div className="p-6">
              <pre className="whitespace-pre-wrap font-mono text-sm" style={{ color: 'var(--color-text, #161616)' }}>
                {activeFile.content || '(empty file)'}
              </pre>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: 'var(--color-bg, #F4F4F4)' }}>
      {/* Tab Bar */}
      {openFiles.length > 0 && (
        <div
          className="flex items-center gap-1 px-2 border-b overflow-x-auto"
          style={{
            backgroundColor: 'var(--color-panel, #FFFFFF)',
            borderColor: 'var(--color-border, #E0E0E0)'
          }}
        >
          {openFiles.map((file) => (
            <div
              key={file.id}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-t-lg cursor-pointer transition-all group",
                activeFileId === file.id && "shadow-sm"
              )}
              style={{
                backgroundColor: activeFileId === file.id
                  ? 'var(--color-bg, #F4F4F4)'
                  : 'transparent',
                borderBottom: activeFileId === file.id
                  ? '2px solid var(--color-primary, #0F62FE)'
                  : '2px solid transparent',
              }}
              onClick={() => onSelectFile(file.id)}
            >
              {getFileIcon(file.type)}
              <span
                className="text-sm font-medium whitespace-nowrap"
                style={{
                  color: activeFileId === file.id
                    ? 'var(--color-primary, #0F62FE)'
                    : 'var(--color-text-secondary, #525252)'
                }}
              >
                {file.name}
              </span>
              {file.isDirty && (
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--color-warning, #FF832B)' }} />
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCloseFile(file.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-200 transition-all"
                style={{ color: 'var(--color-text-secondary, #525252)' }}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Toolbar */}
      {activeFile && (
        <div
          className="flex items-center justify-between px-4 py-2 border-b"
          style={{
            backgroundColor: 'var(--color-panel, #FFFFFF)',
            borderColor: 'var(--color-border, #E0E0E0)'
          }}
        >
          <div className="flex items-center gap-2">
            {getFileIcon(activeFile.type)}
            <span className="text-sm font-medium" style={{ color: 'var(--color-text, #161616)' }}>
              {activeFile.path}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {activeFile.isStreaming && (
              <div className="flex items-center gap-2 px-3 py-1 rounded-lg" style={{ backgroundColor: 'var(--color-primary-bg, #EDF5FF)' }}>
                <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--color-primary, #0F62FE)' }} />
                <span className="text-xs font-medium" style={{ color: 'var(--color-primary, #0F62FE)' }}>
                  Streaming...
                </span>
              </div>
            )}
            {activeFile.type !== 'stream' && activeFile.type !== 'agent' && (
              <>
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="px-3 py-1 rounded-lg text-sm font-medium transition-colors"
                  style={{
                    backgroundColor: isEditing ? 'var(--color-primary, #0F62FE)' : 'transparent',
                    color: isEditing ? 'white' : 'var(--color-text-secondary, #525252)',
                  }}
                >
                  {isEditing ? 'View' : 'Edit'}
                </button>
                {onSaveFile && (
                  <button
                    onClick={handleSave}
                    disabled={!activeFile.isDirty}
                    className="flex items-center gap-2 px-3 py-1 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{
                      backgroundColor: activeFile.isDirty ? 'var(--color-success, #24A148)' : 'transparent',
                      color: activeFile.isDirty ? 'white' : 'var(--color-text-secondary, #525252)',
                    }}
                  >
                    <Save className="w-4 h-4" />
                    Save
                  </button>
                )}
              </>
            )}
            {activeFile.content && (
              <button
                onClick={() => {
                  navigator.clipboard.writeText(activeFile.content || '');
                }}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                style={{ color: 'var(--color-text-secondary, #525252)' }}
                title="Copy"
              >
                <Copy className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-hidden">
        {renderContent()}
      </div>
    </div>
  );
}












