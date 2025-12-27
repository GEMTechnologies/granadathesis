'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { cn } from '../../lib/utils';

interface ResizableLayoutProps {
  leftPanel: React.ReactNode;
  middlePanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultLeftWidth?: number;
  defaultRightWidth?: number;
  minLeftWidth?: number;
  minRightWidth?: number;
  isLeftCollapsed?: boolean;
  isRightCollapsed?: boolean;
  onLeftCollapse?: (collapsed: boolean) => void;
  onRightCollapse?: (collapsed: boolean) => void;
}

export function ResizableLayout({
  leftPanel,
  middlePanel,
  rightPanel,
  defaultLeftWidth = 20,
  defaultRightWidth = 30,
  minLeftWidth = 200,
  minRightWidth = 300,
  isLeftCollapsed = false,
  isRightCollapsed = false,
  onLeftCollapse,
  onRightCollapse
}: ResizableLayoutProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [rightWidth, setRightWidth] = useState(defaultRightWidth);

  return (
    <div className="w-full h-full overflow-hidden">
      <PanelGroup direction="horizontal">
        {/* Left Panel */}
        {!isLeftCollapsed && (
          <>
            <Panel 
              defaultSize={defaultLeftWidth} 
              minSize={15}
              maxSize={40}
              collapsible={true}
              onCollapse={() => onLeftCollapse?.(true)}
              className="flex flex-col"
            >
              {leftPanel}
            </Panel>
            
            <PanelResizeHandle className="w-2 hover:w-3 transition-all cursor-col-resize bg-transparent hover:bg-blue-200 active:bg-blue-400" />
          </>
        )}

        {/* Middle Panel (Workspace) */}
        <Panel 
          defaultSize={isLeftCollapsed && !isRightCollapsed ? 100 - defaultRightWidth : isLeftCollapsed && isRightCollapsed ? 100 : !isLeftCollapsed && isRightCollapsed ? 100 - defaultLeftWidth : 100 - defaultLeftWidth - defaultRightWidth}
          minSize={30}
          className="flex flex-col"
        >
          {middlePanel}
        </Panel>

        {/* Right Panel */}
        {!isRightCollapsed && (
          <>
            <PanelResizeHandle className="w-2 hover:w-3 transition-all cursor-col-resize bg-transparent hover:bg-blue-200 active:bg-blue-400" />
            
            <Panel 
              defaultSize={defaultRightWidth} 
              minSize={20}
              maxSize={60}
              collapsible={true}
              onCollapse={() => onRightCollapse?.(true)}
              className="flex flex-col"
            >
              {rightPanel}
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  );
}




