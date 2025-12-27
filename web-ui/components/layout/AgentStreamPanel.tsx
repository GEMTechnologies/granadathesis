'use client';

import React, { useEffect, useRef, useState } from 'react';
import { X, Loader2, Save, FileText, Search, Globe, Sparkles, CheckCircle2, Clock } from 'lucide-react';
import { MarkdownRenderer } from '../MarkdownRenderer';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

interface AgentStreamPanelProps {
  agent: string;
  content: string;
  isStreaming: boolean;
  metadata?: Record<string, any>;
  onClose?: () => void;
}

export function AgentStreamPanel({
  agent,
  content,
  isStreaming,
  metadata = {},
  onClose
}: AgentStreamPanelProps) {
  const contentEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [typingIndicator, setTypingIndicator] = useState('');

  // Auto-scroll as content streams
  useEffect(() => {
    if (contentEndRef.current && (isStreaming || content)) {
      contentEndRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [content, isStreaming]);

  // Typing animation
  useEffect(() => {
    if (isStreaming) {
      const dots = ['.', '..', '...'];
      let index = 0;
      const interval = setInterval(() => {
        setTypingIndicator(dots[index % dots.length]);
        index++;
      }, 500);
      return () => clearInterval(interval);
    } else {
      setTypingIndicator('');
    }
  }, [isStreaming]);

  const getAgentIcon = () => {
    switch (agent.toLowerCase()) {
      case 'writer':
      case 'writer_swarm':
      case 'intro_writer':
      case 'background_writer':
      case 'problem_writer':
      case 'scope_writer':
      case 'justification_writer':
        return '✍️';
      case 'editor':
        return '✏️';
      case 'researcher':
      case 'search':
      case 'research_swarm':
        return '🔍';
      case 'internet_search':
        return '🌐';
      case 'planner':
        return '📋';
      case 'image_search':
        return '🖼️';
      case 'image_generator':
        return '🎨';
      case 'quality_control':
      case 'quality_swarm':
        return '🔍';
      case 'structural_analyst':
        return '📐';
      case 'stylistic_agent':
        return '✏️';
      case 'citation_agent':
        return '📚';
      case 'coherence_agent':
        return '🔗';
      case 'chapter_generator':
        return '📖';
      case 'objectives_writer':
        return '🎯';
      default:
        return metadata?.icon || '🤖';
    }
  };

  const getAgentColor = () => {
    switch (agent.toLowerCase()) {
      case 'writer':
      case 'writer_swarm':
      case 'intro_writer':
      case 'background_writer':
      case 'problem_writer':
      case 'scope_writer':
      case 'justification_writer':
        return 'bg-blue-50 border-blue-200';
      case 'editor':
        return 'bg-purple-50 border-purple-200';
      case 'researcher':
      case 'search':
      case 'research_swarm':
        return 'bg-green-50 border-green-200';
      case 'internet_search':
        return 'bg-cyan-50 border-cyan-200';
      case 'planner':
        return 'bg-yellow-50 border-yellow-200';
      case 'image_search':
      case 'image_generator':
        return 'bg-pink-50 border-pink-200';
      case 'quality_control':
      case 'quality_swarm':
        return 'bg-emerald-50 border-emerald-200';
      case 'structural_analyst':
        return 'bg-amber-50 border-amber-200';
      case 'stylistic_agent':
        return 'bg-violet-50 border-violet-200';
      case 'citation_agent':
        return 'bg-rose-50 border-rose-200';
      case 'coherence_agent':
        return 'bg-teal-50 border-teal-200';
      case 'objectives_writer':
        return 'bg-indigo-50 border-indigo-200';
      case 'chapter_generator':
        return 'bg-orange-50 border-orange-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = () => {
    if (metadata.status === 'completed') {
      return <CheckCircle2 className="w-4 h-4 text-green-600" />;
    }
    if (metadata.status === 'running' || isStreaming) {
      return <Loader2 className="w-4 h-4 animate-spin text-blue-600" />;
    }
    return <Clock className="w-4 h-4 text-gray-400" />;
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header with animations */}
      <div className={`flex items-center justify-between px-4 py-3 border-b ${getAgentColor()} transition-all duration-300`}>
        <div className="flex items-center gap-2">
          <span className="text-xl animate-pulse">{getAgentIcon()}</span>
          <h3 className="font-semibold">{agent.charAt(0).toUpperCase() + agent.slice(1)} Agent</h3>
          {getStatusIcon()}
          {isStreaming && (
            <Badge variant="secondary" className="flex items-center gap-1 animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span className="animate-pulse">Streaming{typingIndicator}</span>
            </Badge>
          )}
          {metadata.word_count && (
            <Badge variant="outline" className="text-xs">
              {metadata.word_count} words
            </Badge>
          )}
          {metadata.results && (
            <Badge variant="outline" className="text-xs bg-green-100">
              {metadata.results.length || metadata.count || 0} results
            </Badge>
          )}
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Progress bar for streaming */}
      {isStreaming && (
        <div className="px-4 py-2 bg-gray-50 border-b">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full animate-pulse" style={{ width: '100%' }}>
                <div className="h-full bg-blue-400 rounded-full animate-[shimmer_2s_infinite] w-full" />
              </div>
            </div>
            <span className="text-xs text-gray-600">Processing...</span>
          </div>
        </div>
      )}

      {/* Content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-white to-gray-50"
      >
        {/* Query display */}
        {metadata.query && (
          <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200 shadow-sm animate-fade-in">
            <div className="flex items-center gap-2 mb-2">
              <Search className="w-4 h-4 text-blue-600" />
              <p className="text-sm font-medium text-blue-900">Search Query:</p>
            </div>
            <p className="text-sm text-blue-700 font-medium">{metadata.query}</p>
            {metadata.status === 'searching' && (
              <div className="mt-2 flex items-center gap-2 text-xs text-blue-600">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Searching the web...</span>
              </div>
            )}
          </div>
        )}

        {/* Search Results */}
        {metadata.results && Array.isArray(metadata.results) && metadata.results.length > 0 && (
          <div className="mb-4 animate-fade-in">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-4 h-4 text-green-600" />
              <h4 className="text-sm font-semibold">Search Results ({metadata.results.length}):</h4>
            </div>
            <div className="space-y-3">
              {metadata.results.map((result: any, idx: number) => (
                <div
                  key={idx}
                  className="p-4 border rounded-lg hover:bg-gray-50 hover:shadow-md transition-all duration-200 bg-white animate-slide-in"
                  style={{ animationDelay: `${idx * 100}ms` }}
                >
                  <div className="flex items-start gap-2 mb-2">
                    <span className="text-xs font-bold text-blue-600 bg-blue-100 px-2 py-1 rounded">
                      #{idx + 1}
                    </span>
                    <h5 className="font-medium text-sm flex-1">{result.title || 'No title'}</h5>
                  </div>
                  <p className="text-xs text-gray-600 mb-2 line-clamp-2">{result.snippet || result.description || ''}</p>
                  {result.url && (
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                    >
                      <Globe className="w-3 h-3" />
                      {result.url.length > 50 ? result.url.substring(0, 50) + '...' : result.url}
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Main content */}
        {content ? (
          <div className="prose prose-sm max-w-none animate-fade-in">
            <MarkdownRenderer content={content} />
            {isStreaming && (
              <div className="flex items-center gap-2 mt-4 text-blue-600">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm animate-pulse">Writing{typingIndicator}</span>
              </div>
            )}
          </div>
        ) : metadata.status === 'running' || isStreaming ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center animate-pulse">
              <div className="mb-4">
                <Loader2 className="w-12 h-12 animate-spin mx-auto text-blue-600" />
              </div>
              <p className="text-lg font-medium mb-2">{agent.charAt(0).toUpperCase() + agent.slice(1)} is working...</p>
              {metadata.query && (
                <p className="text-sm mt-1 text-gray-500">Query: {metadata.query}</p>
              )}
              {metadata.action && (
                <p className="text-xs mt-2 text-gray-400">{metadata.action}</p>
              )}
              <div className="mt-4 flex justify-center gap-1">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <Clock className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p className="text-lg">Waiting for {agent} to start...</p>
            </div>
          </div>
        )}
        <div ref={contentEndRef} />
      </div>

      {/* Footer with metadata */}
      {metadata && Object.keys(metadata).length > 0 && (
        <div className="border-t px-4 py-2 bg-gray-50 text-xs text-gray-600">
          <div className="flex items-center justify-between">
            {metadata.filename && (
              <div className="flex items-center gap-2">
                <FileText className="w-3 h-3" />
                <span>{metadata.filename}</span>
              </div>
            )}
            {metadata.status && (
              <Badge variant={metadata.status === 'completed' ? 'default' : 'secondary'} className="text-xs">
                {metadata.status}
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
