'use client';

import React, { useState, useCallback } from 'react';
import { X, FileText, Image as ImageIcon, Globe, Search, Code, File, BookOpen } from 'lucide-react';
import { cn } from '../../lib/utils';
import { FilePreviewPanel } from './FilePreviewPanel';
import { SearchResultDisplay } from '../workspace/SearchResultDisplay';
import { ImageGallery } from '../workspace/ImageGallery';
import { AgentStreamPanel } from './AgentStreamPanel';
import { SourcesPanel } from '../sources/SourcesPanel';
import { BrowserPreviewPanel } from '../preview/BrowserPreviewPanel';

export type TabType = 'file' | 'search' | 'image' | 'agent' | 'browser' | 'sources';

export interface Tab {
  id: string;
  type: TabType;
  title: string;
  data: any; // File, search results, image data, etc.
  workspaceId?: string;
}

interface TabbedPreviewPanelProps {
  tabs: Tab[];
  activeTabId: string | null;
  onTabChange: (tabId: string | null) => void;
  onTabClose: (tabId: string) => void;
  onTabsChange: (tabs: Tab[]) => void;
}

export function TabbedPreviewPanel({
  tabs,
  activeTabId,
  onTabChange,
  onTabClose,
  onTabsChange
}: TabbedPreviewPanelProps) {
  const activeTab = tabs.find(tab => tab.id === activeTabId) || null;

  const handleCloseTab = useCallback((tabId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (tabs.length === 1) {
      // If last tab, close the panel
      onTabChange(null);
    } else {
      // Switch to another tab if closing active tab
      const currentIndex = tabs.findIndex(t => t.id === tabId);
      if (tabs[currentIndex]?.id === activeTabId) {
        // Find next tab to switch to
        const nextTab = tabs[currentIndex + 1] || tabs[currentIndex - 1];
        if (nextTab) {
          onTabChange(nextTab.id);
        }
      }
      onTabClose(tabId);
    }
  }, [tabs, activeTabId, onTabChange, onTabClose]);

  const getTabIcon = (type: TabType) => {
    switch (type) {
      case 'file':
        return <FileText className="w-4 h-4" />;
      case 'search':
        return <Search className="w-4 h-4" />;
      case 'image':
        return <ImageIcon className="w-4 h-4" />;
      case 'browser':
        return <Globe className="w-4 h-4" />;
      case 'agent':
        return <Code className="w-4 h-4" />;
      case 'sources':
        return <BookOpen className="w-4 h-4" />;
      default:
        return <File className="w-4 h-4" />;
    }
  };

  const renderTabContent = () => {
    if (!activeTab) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400">
          <p className="text-sm">No tabs open. Click on a file, search result, or image to open it.</p>
        </div>
      );
    }

    switch (activeTab.type) {
      case 'file':
        return (
          <FilePreviewPanel
            file={activeTab.data}
            onClose={() => handleCloseTab(activeTab.id)}
            workspaceId={activeTab.workspaceId || 'default'}
          />
        );

      case 'search':
        return (
          <div className="h-full overflow-auto">
            <SearchResultDisplay
              results={activeTab.data.results || []}
              query={activeTab.data.query || ''}
              workspaceId={activeTab.workspaceId || 'default'}
            />
          </div>
        );

      case 'agent':
        return (
          <AgentStreamPanel
            agent={activeTab.data.agent || 'agent'}
            content={activeTab.data.content || ''}
            isStreaming={activeTab.data.isStreaming || false}
            metadata={activeTab.data.metadata || {}}
            onClose={() => handleCloseTab(activeTab.id)}
          />
        );

      case 'image':
        return (
          <div className="h-full overflow-auto">
            <ImageGallery
              images={activeTab.data.images || [activeTab.data]}
              query={activeTab.data.query || ''}
              workspaceId={activeTab.workspaceId || 'default'}
            />
          </div>
        );

      case 'browser':
        return (
          <BrowserPreviewPanel
            sessionId={activeTab.data?.sessionId || 'default'}
            workspaceId={activeTab.workspaceId || 'default'}
            onClose={() => handleCloseTab(activeTab.id)}
          />
        );

      case 'sources':
        return (
          <SourcesPanel
            workspaceId={activeTab.workspaceId || 'default'}
            onClose={() => handleCloseTab(activeTab.id)}
            onSelectSource={(source) => {
              // Source selection could open PDF or details
              console.log('Selected source:', source);
            }}
          />
        );

      default:
        return (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-gray-400">Unknown tab type</p>
          </div>
        );
    }
  };

  if (tabs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <p className="text-sm">No tabs open. Click on a file, search result, or image to open it.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tab Bar */}
      <div
        className="flex items-center gap-1 border-b overflow-x-auto"
        style={{
          backgroundColor: 'var(--color-panel, #FFFFFF)',
          borderColor: 'var(--color-border, #E0E0E0)'
        }}
      >
        {tabs.map((tab) => (
          <div
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all relative group min-w-fit cursor-pointer",
              activeTabId === tab.id
                ? "border-b-2 border-blue-500 text-blue-600"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            )}
            style={{
              borderBottomColor: activeTabId === tab.id ? 'var(--color-primary, #0F62FE)' : 'transparent',
              color: activeTabId === tab.id ? 'var(--color-primary, #0F62FE)' : undefined
            }}
          >
            {getTabIcon(tab.type)}
            <span className="max-w-[150px] truncate">{tab.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCloseTab(tab.id, e);
              }}
              className={cn(
                "ml-1 p-1 rounded hover:bg-gray-200 transition-opacity",
                "opacity-0 group-hover:opacity-100"
              )}
              title="Close tab"
              type="button"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {renderTabContent()}
      </div>
    </div>
  );
}

