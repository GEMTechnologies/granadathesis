'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Folder,
  File,
  FileText,
  Image as ImageIcon,
  FileCode,
  Upload,
  Plus,
  MoreVertical,
  Move,
  Trash2,
  Edit,
  Download,
  FolderPlus,
  FilePlus,
  ChevronRight,
  ChevronDown,
  FolderOpen,
  RefreshCw,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { CreateItemDialog } from './CreateItemDialog';

interface WorkspaceItem {
  id: string;
  name: string;
  type: 'folder' | 'file' | 'project';
  path: string;
  parentId?: string | null;
  children?: WorkspaceItem[];
  fileType?: string;
  size?: number;
  createdAt: string;
  updatedAt: string;
  isDefault?: boolean;
  description?: string;
  url?: string;
  shareable?: boolean;
}

interface WorkspaceFileSystemProps {
  workspaceId: string;
  userId: string;
  onFileOpen?: (file: { name: string; path: string; type: string }) => void;
}

export function WorkspaceFileSystem({ workspaceId, userId, onFileOpen }: WorkspaceFileSystemProps) {
  const [items, setItems] = useState<WorkspaceItem[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [selectedItem, setSelectedItem] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; itemPath: string; itemType: string } | null>(null);
  const [draggedItem, setDraggedItem] = useState<WorkspaceItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createDialogType, setCreateDialogType] = useState<'folder' | 'project' | 'file' | undefined>();
  const [createParentId, setCreateParentId] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<{ name: string; type: string; id: string; itemType: string } | null>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  // Load workspace structure
  useEffect(() => {
    loadWorkspaceStructure();
  }, [workspaceId]);

  // Close context menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
        setContextMenu(null);
      }
    };

    if (contextMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [contextMenu]);

  const loadWorkspaceStructure = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/workspace/${workspaceId}/structure`);
      const data = await response.json();
      
      if (response.ok && !data.error) {
        setItems(data.items || []);
        // Auto-expand root level folders and projects
        const rootFolders = data.items?.filter((item: WorkspaceItem) => 
          item.type === 'folder' || item.type === 'project'
        ) || [];
        setExpandedFolders(new Set(rootFolders.map((f: WorkspaceItem) => f.id)));
      } else {
        console.error('Failed to load workspace:', data.error || 'Unknown error');
        setItems([]);
        // Don't show alert for empty workspace (normal state)
        if (data.error && !data.error.includes('empty')) {
          console.warn('Workspace load warning:', data.error);
        }
      }
    } catch (error: any) {
      console.error('Failed to load workspace:', error);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearWorkspace = async () => {
    if (!confirm('Are you sure you want to clear the entire workspace?\n\nThis will delete ALL files, chapters, datasets, and figures.\nEmpty default folders will be recreated.')) {
      return;
    }
    
    try {
      setLoading(true);
      const response = await fetch(`/api/workspace/${workspaceId}/clear`, {
        method: 'POST',
      });
      
      if (response.ok) {
        await loadWorkspaceStructure();
        alert('Workspace cleared successfully. Default folders have been recreated.');
      } else {
        const error = await response.json();
        alert(`Failed to clear workspace: ${error.detail || 'Unknown error'}`);
      }
    } catch (error: any) {
      console.error('Failed to clear workspace:', error);
      alert(`Failed to clear workspace: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  };

  const handleContextMenu = (e: React.MouseEvent, item: WorkspaceItem) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      itemPath: item.path,
      itemType: item.type,
    });
    setSelectedItem(item.path);
  };



  const handleCreateItem = async (parentId?: string | null, itemType: 'folder' | 'project' = 'folder') => {
    setCreateDialogType(itemType);
    setCreateParentId(parentId || null);
    setShowCreateDialog(true);
  };

  const executeCreateFolder = async (name: string) => {
    try {
      const response = await fetch(`/api/workspace/${workspaceId}/folders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          parent_folder_id: createParentId || null,
        }),
      });

      if (response.ok) {
        await loadWorkspaceStructure();
        setContextMenu(null);
      } else {
        const error = await response.json().catch(() => ({}));
        const errorMessage = error.error || error.detail || 'Failed to create folder';
        if (response.status === 500 || response.status === 503) {
          throw new Error('Backend server is not available. Please start the backend server.');
        }
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('Failed to create folder:', error);
      if (error.message?.includes('fetch')) {
        throw new Error('Backend server is not available. Please start the backend server.');
      }
      throw error;
    }
  };

  const executeCreateProject = async (name: string, projectType: string) => {
    try {
      const response = await fetch(`/api/workspace/${workspaceId}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          project_type: projectType,
          folder_id: createParentId || null,
        }),
      });

      if (response.ok) {
        await loadWorkspaceStructure();
        setContextMenu(null);
      } else {
        const error = await response.json().catch(() => ({}));
        const errorMessage = error.error || error.detail || 'Failed to create project';
        if (response.status === 500 || response.status === 503) {
          throw new Error('Backend server is not available. Please start the backend server.');
        }
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('Failed to create project:', error);
      if (error.message?.includes('fetch') || error.name === 'TypeError') {
        throw new Error('Backend server is not available. Please start the backend server.');
      }
      throw error;
    }
  };

  const executeCreateFile = async (name: string) => {
    try {
      const response = await fetch(`/api/workspace/${workspaceId}/files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          folder_id: createParentId || null,
        }),
      });

      if (response.ok) {
        await loadWorkspaceStructure();
        setContextMenu(null);
      } else {
        const error = await response.json().catch(() => ({}));
        const errorMessage = error.error || error.detail || 'Failed to create file';
        if (response.status === 500 || response.status === 503) {
          throw new Error('Backend server is not available. Please start the backend server.');
        }
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('Failed to create file:', error);
      if (error.message?.includes('fetch') || error.name === 'TypeError') {
        throw new Error('Backend server is not available. Please start the backend server.');
      }
      throw error;
    }
  };

  const handleRename = async (itemId: string, itemType: string, newName: string) => {
    try {
      // Use the rename endpoint (will need to be created or use files API)
      const response = await fetch(`/api/workspace/${workspaceId}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_id: itemId,
          item_type: itemType,
          new_name: newName,
        }),
      });

      if (response.ok) {
        await loadWorkspaceStructure();
        return;
      } else {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || 'Failed to rename');
      }
    } catch (error: any) {
      console.error('Failed to rename:', error);
      throw error;
    }
  };

  const handleDelete = async (itemPath: string, itemType: string) => {
    if (!confirm(`Are you sure you want to delete this ${itemType}?`)) return;

    try {
      const response = await fetch(`/api/workspace/${workspaceId}/files/${encodeURIComponent(itemPath)}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await loadWorkspaceStructure();
        setContextMenu(null);
      } else {
        const error = await response.json();
        console.error('Failed to delete:', error);
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to delete:', error);
      alert(`Failed to delete: ${error}`);
    }
  };

  const handleMove = async (itemId: string, itemType: string, targetFolderId: string | null) => {
    try {
      const endpoint = itemType === 'folder' ? 'folders' : itemType === 'project' ? 'projects' : 'files';
      const response = await fetch(`/api/workspace/${workspaceId}/${endpoint}/${itemId}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_folder_id: targetFolderId }),
      });

      if (response.ok) {
        await loadWorkspaceStructure();
        setDraggedItem(null);
      }
    } catch (error) {
      console.error('Failed to move item:', error);
    }
  };

  const handleDragStart = (e: React.DragEvent, item: WorkspaceItem) => {
    setDraggedItem(item);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: React.DragEvent, targetFolder: WorkspaceItem | null) => {
    e.preventDefault();
    if (!draggedItem) return;

    const targetFolderPath = targetFolder?.type === 'folder' ? targetFolder.path : null;
    if (draggedItem.path === targetFolderPath || draggedItem.parentId === targetFolderPath) return;

    await handleMove(draggedItem.path, draggedItem.type, targetFolderPath);
  };

  const getFileIcon = (fileType?: string) => {
    if (!fileType) return <File className="w-4 h-4" />;
    const type = fileType.toLowerCase();
    if (type.includes('pdf')) return <FileText className="w-4 h-4 text-red-600" />;
    if (type.includes('image')) return <ImageIcon className="w-4 h-4 text-blue-600" />;
    if (type.includes('text') || type.includes('document')) return <FileText className="w-4 h-4" />;
    if (type.includes('code')) return <FileCode className="w-4 h-4 text-purple-600" />;
    return <File className="w-4 h-4" />;
  };

  const renderItem = (item: WorkspaceItem, level: number = 0): React.ReactNode => {
    const isExpanded = expandedFolders.has(item.path);
    const isSelected = selectedItem === item.path;

    if (item.type === 'folder') {
      return (
        <div key={item.path}>
          <div
            draggable
            onDragStart={(e) => handleDragStart(e, item)}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, item)}
            onClick={() => toggleFolder(item.path)}
            onContextMenu={(e) => handleContextMenu(e, item)}
            className={cn(
              "flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-all",
              isSelected && "bg-blue-100"
            )}
            style={{
              paddingLeft: `${level * 16 + 8}px`,
              backgroundColor: isSelected ? 'var(--color-primary-bg, #EDF5FF)' : 'transparent',
            }}
            onMouseEnter={(e) => {
              if (!isSelected) {
                e.currentTarget.style.backgroundColor = 'var(--color-bg, #F4F4F4)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isSelected) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" style={{ color: 'var(--color-text-secondary, #525252)' }} />
            ) : (
              <ChevronRight className="w-4 h-4" style={{ color: 'var(--color-text-secondary, #525252)' }} />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4" style={{ color: 'var(--color-primary, #0F62FE)' }} />
            ) : (
              <Folder className="w-4 h-4" style={{ color: 'var(--color-primary, #0F62FE)' }} />
            )}
            <span className="text-sm font-medium flex-1" style={{ color: 'var(--color-text, #161616)' }}>
              {item.name}
            </span>
          </div>
          {isExpanded && item.children && (
            <div>
              {item.children.map(child => <div key={child.id || child.path || child.name}>{renderItem(child, level + 1)}</div>)}
            </div>
          )}
        </div>
      );
    }

    return (
      <div
        key={item.path}
        draggable
        onDragStart={(e) => handleDragStart(e, item)}
            onClick={() => {
              setSelectedItem(item.path);
              // Open file when clicked
              if (item.type === 'file' && onFileOpen) {
                onFileOpen({
                  name: item.name,
                  path: item.path,
                  type: item.fileType || 'file'
                });
              }
            }}
        onContextMenu={(e) => handleContextMenu(e, item)}
        className={cn(
          "flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-all",
          isSelected && "bg-blue-100"
        )}
        style={{
          paddingLeft: `${level * 16 + 24}px`,
          backgroundColor: isSelected ? 'var(--color-primary-bg, #EDF5FF)' : 'transparent',
        }}
        onMouseEnter={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = 'var(--color-bg, #F4F4F4)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = 'transparent';
          }
        }}
      >
        {item.type === 'project' ? (
          <FileText className="w-4 h-4" style={{ color: 'var(--color-success, #24A148)' }} />
        ) : (
          getFileIcon(item.fileType)
        )}
        <span className="text-sm flex-1" style={{ color: 'var(--color-text, #161616)' }}>
          {item.name}
        </span>
        {item.size && (
          <span className="text-xs" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
            {(item.size / 1024).toFixed(1)} KB
          </span>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="p-4 text-center" style={{ color: 'var(--color-text-secondary, #525252)' }}>
        Loading workspace...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--color-border, #E0E0E0)' }}
      >
        <div>
          <h2 className="font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
            Workspace
          </h2>
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
            Create projects, folders, and files here
          </p>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => loadWorkspaceStructure()}
            className="p-1.5 rounded hover:bg-gray-100 transition-colors"
            style={{ color: 'var(--color-text-secondary, #525252)' }}
            title="Refresh Files"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setCreateParentId(null);
              setCreateDialogType(undefined);
              setShowCreateDialog(true);
            }}
            className="p-1.5 rounded hover:bg-gray-100 transition-colors"
            style={{ color: 'var(--color-primary, #0F62FE)' }}
            title="Create Folder, Project, or File"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={handleClearWorkspace}
            className="p-1.5 rounded hover:bg-red-50 transition-colors"
            style={{ color: 'var(--color-danger, #DA1E28)' }}
            title="Clear Workspace (Delete All Files)"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto p-2">
        {items.length === 0 ? (
          <div className="text-center py-8 px-4">
            <Folder className="w-12 h-12 mx-auto mb-3" style={{ color: 'var(--color-text-muted, #8D8D8D)' }} />
            <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text, #161616)' }}>
              Welcome to your Workspace
            </p>
            <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
              Your workspace will auto-create default folders (sources, sections, chapters, uploads, etc.) when initialized.
              <br />
              You can also create custom projects, folders, and files here.
            </p>
            <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <button
              onClick={() => {
                setCreateParentId(null);
                setCreateDialogType(undefined);
                setShowCreateDialog(true);
              }}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                backgroundColor: 'var(--color-primary, #0F62FE)',
                color: 'white'
              }}
            >
              Create Folder, Project, or File
            </button>
            </div>
          </div>
        ) : (
          items.map(item => <div key={item.id || item.path || item.name}>{renderItem(item)}</div>)
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 rounded-lg shadow-xl border py-1 min-w-[180px]"
          style={{
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
            backgroundColor: 'var(--color-panel, #FFFFFF)',
            borderColor: 'var(--color-border, #E0E0E0)',
          }}
        >
          {contextMenu.itemType === 'folder' && (
            <>
              <button
                onClick={() => {
                  setCreateParentId(contextMenu.itemPath);
                  setCreateDialogType(undefined);
                  setShowCreateDialog(true);
                  setContextMenu(null);
                }}
                className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm"
                style={{ color: 'var(--color-text, #161616)' }}
              >
                <FolderPlus className="w-4 h-4" />
                New Folder, Project, or File
              </button>
              <div className="border-t my-1" style={{ borderColor: 'var(--color-border, #E0E0E0)' }} />
            </>
          )}
          <button
            onClick={() => {
              const item = items.find(i => i.path === contextMenu.itemPath);
              if (item) {
                setEditingItem({
                  id: item.path,
                  name: item.name,
                  type: item.type === 'project' ? ((item as any).projectType || 'thesis') : item.type,
                  itemType: item.type,
                });
                setCreateDialogType(item.type as 'folder' | 'project' | 'file');
                setShowCreateDialog(true);
              }
              setContextMenu(null);
            }}
            className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm"
            style={{ color: 'var(--color-text, #161616)' }}
          >
            <Edit className="w-4 h-4" />
            Rename
          </button>
          <button
            onClick={() => {
              handleDelete(contextMenu.itemPath, contextMenu.itemType);
              setContextMenu(null);
            }}
            className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-red-50 transition-colors text-sm"
            style={{ color: 'var(--color-danger, #DA1E28)' }}
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      )}

      {/* Create Item Dialog */}
      <CreateItemDialog
        isOpen={showCreateDialog}
        onClose={() => {
          setShowCreateDialog(false);
          setCreateDialogType(undefined);
          setCreateParentId(null);
          setEditingItem(null);
        }}
        onCreateFolder={executeCreateFolder}
        onCreateProject={executeCreateProject}
        onCreateFile={executeCreateFile}
        itemType={createDialogType}
        parentPath={createParentId ? items.find(i => i.path === createParentId)?.path : undefined}
        editingItem={editingItem ? { name: editingItem.name, type: editingItem.type } : null}
        onRename={editingItem ? async (newName: string) => {
          await handleRename(editingItem.id, editingItem.itemType, newName);
        } : undefined}
      />
    </div>
  );
}

