'use client';

import React, { useState, useEffect } from 'react';
import { X, Folder, FileText, FolderPlus } from 'lucide-react';
import { cn } from '../../lib/utils';

interface CreateItemDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateFolder: (name: string) => Promise<void>;
  onCreateProject: (name: string, type: string) => Promise<void>;
  onCreateFile: (name: string) => Promise<void>;
  itemType?: 'folder' | 'project' | 'file';
  parentPath?: string;
  editingItem?: { name: string; type: string } | null;
  onRename?: (newName: string) => Promise<void>;
}

const PROJECT_TYPES = [
  { value: 'thesis', label: 'Thesis', icon: '📚' },
  { value: 'essay', label: 'Essay', icon: '📝' },
  { value: 'article', label: 'Article', icon: '📄' },
  { value: 'journal', label: 'Journal Paper', icon: '📑' },
  { value: 'report', label: 'Report', icon: '📊' },
  { value: 'dissertation', label: 'Dissertation', icon: '📖' },
  { value: 'research-paper', label: 'Research Paper', icon: '🔬' },
  { value: 'analysis', label: 'Analysis Paper', icon: '📈' },
];

export function CreateItemDialog({
  isOpen,
  onClose,
  onCreateFolder,
  onCreateProject,
  onCreateFile,
  itemType,
  parentPath,
  editingItem,
  onRename,
}: CreateItemDialogProps) {
  const isEditMode = !!editingItem;
  const [activeTab, setActiveTab] = useState<'folder' | 'project' | 'file'>(itemType || 'folder');
  const [name, setName] = useState(editingItem?.name || '');
  const [projectType, setProjectType] = useState(editingItem?.type || 'thesis');
  const [error, setError] = useState('');

  // Update name when editingItem changes
  useEffect(() => {
    if (editingItem) {
      setName(editingItem.name);
      setProjectType(editingItem.type || 'thesis');
    } else {
      // Reset to default when not editing
      setName('');
      setProjectType('thesis');
    }
  }, [editingItem]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    // Validate name (no special characters that cause issues)
    if (!/^[a-zA-Z0-9\s_-]+$/.test(name.trim())) {
      setError('Name can only contain letters, numbers, spaces, hyphens, and underscores');
      return;
    }

    try {
      if (isEditMode && onRename) {
        // Rename mode
        await onRename(name.trim());
      } else {
        // Create mode
        if (activeTab === 'folder') {
          await onCreateFolder(name.trim());
        } else if (activeTab === 'project') {
          await onCreateProject(name.trim(), projectType);
        } else {
          await onCreateFile(name.trim());
        }
      }
      handleClose();
    } catch (err: any) {
      const errorMessage = err.message || (isEditMode ? 'Failed to rename item' : 'Failed to create item');
      setError(errorMessage);
      // Show alert for backend connection issues
      if (errorMessage.includes('Backend server is not available')) {
        alert('Backend server is not running. Please start it with: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload');
      }
      // Don't close dialog on error so user can fix and retry
    }
  };

  const handleClose = () => {
    setName('');
    setProjectType('thesis');
    setError('');
    setActiveTab(itemType || 'folder');
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={handleClose}
      />

      {/* Dialog */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="w-full max-w-md rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
          style={{
            backgroundColor: 'var(--color-panel, #FFFFFF)',
            border: '1px solid var(--color-border, #E0E0E0)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-6 py-4 border-b"
            style={{ borderColor: 'var(--color-border, #E0E0E0)' }}
          >
          <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
            {isEditMode ? 'Rename' : 'Create New'}
          </h3>
            <button
              onClick={handleClose}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              style={{ color: 'var(--color-text-secondary, #525252)' }}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tabs - Hide in edit mode */}
          {!isEditMode && (
            <div className="flex border-b" style={{ borderColor: 'var(--color-border, #E0E0E0)' }}>
                <button
                onClick={() => {
                  setActiveTab('folder');
                  setError('');
                }}
                className={cn(
                  "flex-1 px-4 py-3 text-sm font-medium transition-all",
                  activeTab === 'folder' && "border-b-2"
                )}
                style={{
                  color: activeTab === 'folder'
                    ? 'var(--color-primary, #0F62FE)'
                    : 'var(--color-text-secondary, #525252)',
                  borderBottomColor: activeTab === 'folder'
                    ? 'var(--color-primary, #0F62FE)'
                    : 'transparent',
                  backgroundColor: activeTab === 'folder'
                    ? 'var(--color-primary-bg, #EDF5FF)'
                    : 'transparent',
                }}
              >
                <div className="flex items-center justify-center gap-2">
                  <Folder className="w-4 h-4" />
                  <span>Folder</span>
                </div>
              </button>
              <button
                onClick={() => {
                  setActiveTab('project');
                  setError('');
                }}
                className={cn(
                  "flex-1 px-4 py-3 text-sm font-medium transition-all",
                  activeTab === 'project' && "border-b-2"
                )}
                style={{
                  color: activeTab === 'project'
                    ? 'var(--color-primary, #0F62FE)'
                    : 'var(--color-text-secondary, #525252)',
                  borderBottomColor: activeTab === 'project'
                    ? 'var(--color-primary, #0F62FE)'
                    : 'transparent',
                  backgroundColor: activeTab === 'project'
                    ? 'var(--color-primary-bg, #EDF5FF)'
                    : 'transparent',
                }}
              >
                <div className="flex items-center justify-center gap-2">
                  <FileText className="w-4 h-4" />
                  <span>Project</span>
                </div>
              </button>
              <button
                onClick={() => {
                  setActiveTab('file');
                  setError('');
                }}
                className={cn(
                  "flex-1 px-4 py-3 text-sm font-medium transition-all",
                  activeTab === 'file' && "border-b-2"
                )}
                style={{
                  color: activeTab === 'file'
                    ? 'var(--color-primary, #0F62FE)'
                    : 'var(--color-text-secondary, #525252)',
                  borderBottomColor: activeTab === 'file'
                    ? 'var(--color-primary, #0F62FE)'
                    : 'transparent',
                  backgroundColor: activeTab === 'file'
                    ? 'var(--color-primary-bg, #EDF5FF)'
                    : 'transparent',
                }}
              >
                <div className="flex items-center justify-center gap-2">
                  <FolderPlus className="w-4 h-4" />
                  <span>File</span>
                </div>
              </button>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {/* Name Input */}
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-text, #161616)' }}
              >
                Name {activeTab === 'project' && '(e.g., "My PhD Thesis")'}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setError('');
                }}
                placeholder={
                  activeTab === 'folder' ? 'Enter folder name...' :
                  activeTab === 'project' ? 'Enter project name...' :
                  'Enter file name...'
                }
                className="w-full px-4 py-2.5 rounded-lg border transition-colors focus:outline-none focus:ring-2"
                style={{
                  backgroundColor: 'var(--color-panel, #FFFFFF)',
                  borderColor: error ? 'var(--color-danger, #DA1E28)' : 'var(--color-border, #E0E0E0)',
                  color: 'var(--color-text, #161616)',
                }}
                autoFocus
              />
              {error && (
                <p className="mt-1.5 text-xs" style={{ color: 'var(--color-danger, #DA1E28)' }}>
                  {error}
                </p>
              )}
            </div>

            {/* Project Type Selector */}
            {activeTab === 'project' && !isEditMode && (
              <div>
                <label
                  className="block text-sm font-medium mb-2"
                  style={{ color: 'var(--color-text, #161616)' }}
                >
                  Project Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {PROJECT_TYPES.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => {
                        const suggestedName = `My ${type.label}`;
                        setProjectType(type.value);
                        // Always update name if it's empty or looks like an auto-filled name
                        // Check if the current name matches any auto-filled pattern from project types
                        const isAutoFilledName = !name.trim() || 
                          PROJECT_TYPES.some(t => name.trim() === `My ${t.label}`);
                        if (isAutoFilledName) {
                          setName(suggestedName);
                        }
                      }}
                      className={cn(
                        "flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-all text-left",
                        projectType === type.value && "ring-2"
                      )}
                      style={{
                        backgroundColor: projectType === type.value
                          ? 'var(--color-primary-bg, #EDF5FF)'
                          : 'var(--color-panel, #FFFFFF)',
                        borderColor: projectType === type.value
                          ? 'var(--color-primary, #0F62FE)'
                          : 'var(--color-border, #E0E0E0)',
                        color: 'var(--color-text, #161616)',
                      }}
                    >
                      <span className="text-lg">{type.icon}</span>
                      <span className="text-sm font-medium">{type.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {parentPath && (
              <p className="text-xs" style={{ color: 'var(--color-text-muted, #8D8D8D)' }}>
                Will be created in: <span className="font-mono">{parentPath}</span>
              </p>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="flex-1 px-4 py-2.5 rounded-lg font-medium transition-colors"
                style={{
                  backgroundColor: 'var(--color-bg, #F4F4F4)',
                  color: 'var(--color-text, #161616)',
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2.5 rounded-lg font-medium transition-colors shadow-sm"
                style={{
                  backgroundColor: 'var(--color-primary, #0F62FE)',
                  color: 'white',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-primary-hover, #0050E6)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-primary, #0F62FE)';
                }}
              >
                {isEditMode ? 'Rename' : `Create ${activeTab === 'folder' ? 'Folder' : activeTab === 'project' ? 'Project' : 'File'}`}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

