'use client';

import React, { useState, useEffect } from 'react';
import {
    ChevronRight,
    ChevronDown,
    File,
    Folder,
    FileText,
    Image as ImageIcon,
    Code,
    FileJson,
    RefreshCw,
    Plus,
    MoreVertical,
    Trash2,
    Download,
    Archive,
    CheckSquare,
    Square
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface FileNode {
    name: string;
    path: string;
    type: 'file' | 'folder';
    children?: FileNode[];
    extension?: string;
    icon?: string;
}

interface FileExplorerProps {
    workspaceId: string;
    onFileSelect: (file: FileNode) => void;
    className?: string;
    refreshTrigger?: any; // Prop to trigger refresh
}

export function FileExplorer({ workspaceId, onFileSelect, className, refreshTrigger }: FileExplorerProps) {
    const [files, setFiles] = useState<FileNode[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set()); // Multi-select
    const [isSelectMode, setIsSelectMode] = useState(false);

    const fetchFiles = async () => {
        setIsLoading(true);
        try {
            // Use the correct workspace structure endpoint
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/structure`);
            if (!response.ok) {
                throw new Error(`Failed to fetch files: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            // Workspace structure returns a flat list of items with paths
            const fileList = (data.items || []).map((item: any) => ({
                ...item,
                path: item.path || item.name,
                type: item.type || (item.path?.includes('.') ? 'file' : 'folder'),
                size: item.size || 0,
                modified: item.updatedAt || item.createdAt
            }));

            // Convert flat list to tree structure
            const tree = buildFileTree(fileList);
            setFiles(tree);
        } catch (error) {
            console.error('Error fetching files:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchFiles();
    }, [workspaceId, refreshTrigger]);

    // Listen for workspace refresh events (e.g., when files are created)
    useEffect(() => {
        const handleRefresh = () => {
            fetchFiles();
        };

        window.addEventListener('workspace-refresh', handleRefresh);
        return () => {
            window.removeEventListener('workspace-refresh', handleRefresh);
        };
    }, []);

    const toggleFolder = (path: string, e?: React.MouseEvent) => {
        if (e) {
            e.stopPropagation();
        }
        setExpandedFolders(prev => {
            const next = new Set(prev);
            if (next.has(path)) {
                next.delete(path);
            } else {
                next.add(path);
            }
            return next;
        });
    };

    const handleFileClick = (file: FileNode, e?: React.MouseEvent) => {
        if (isSelectMode) {
            // Toggle selection
            setSelectedFiles(prev => {
                const next = new Set(prev);
                if (next.has(file.path)) {
                    next.delete(file.path);
                } else {
                    next.add(file.path);
                }
                return next;
            });
        } else {
            if (file.type === 'folder') {
                toggleFolder(file.path, e);
                // Also notify parent about folder click (for special folders like 'sources')
                onFileSelect(file);
            } else {
                setSelectedFile(file.path);
                onFileSelect(file);
            }
        }
    };

    const toggleSelectMode = () => {
        setIsSelectMode(!isSelectMode);
        if (isSelectMode) {
            setSelectedFiles(new Set()); // Clear selection when exiting
        }
    };

    const selectAll = () => {
        const allPaths = new Set<string>();
        const collectPaths = (nodes: FileNode[]) => {
            nodes.forEach(node => {
                allPaths.add(node.path);
                if (node.children) {
                    collectPaths(node.children);
                }
            });
        };
        collectPaths(files);
        setSelectedFiles(allPaths);
    };

    const handleBatchDelete = async () => {
        if (selectedFiles.size === 0) return;
        if (!confirm(`Delete ${selectedFiles.size} item(s)?`)) return;

        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        try {
            setIsLoading(true);
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/batch-delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paths: Array.from(selectedFiles) })
            });

            if (response.ok) {
                setSelectedFiles(new Set());
                setIsSelectMode(false);
                await fetchFiles();
            } else {
                alert('Failed to delete files');
            }
        } catch (error) {
            console.error('Batch delete error:', error);
            alert('Error deleting files');
        } finally {
            setIsLoading(false);
        }
    };

    const handleBatchDownload = async () => {
        if (selectedFiles.size === 0) return;

        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        try {
            setIsLoading(true);
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/batch-download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paths: Array.from(selectedFiles) })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `files-${Date.now()}.zip`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                setSelectedFiles(new Set());
                setIsSelectMode(false);
            } else {
                alert('Failed to download files');
            }
        } catch (error) {
            console.error('Batch download error:', error);
            alert('Error downloading files');
        } finally {
            setIsLoading(false);
        }
    };

    const handleBatchZip = async () => {
        if (selectedFiles.size === 0) return;

        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        try {
            setIsLoading(true);
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/zip`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paths: Array.from(selectedFiles) })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `workspace-${workspaceId}-${Date.now()}.zip`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                setSelectedFiles(new Set());
                setIsSelectMode(false);
            } else {
                alert('Failed to create zip');
            }
        } catch (error) {
            console.error('Zip error:', error);
            alert('Error creating zip');
        } finally {
            setIsLoading(false);
        }
    };

    // Helper to build tree from flat paths
    const buildFileTree = (flatFiles: any[]): FileNode[] => {
        const root: FileNode[] = [];
        const map: Record<string, FileNode> = {};

        // Sort: folders first, then files, then alphabetical
        flatFiles.sort((a, b) => {
            if (a.type === b.type) return a.name.localeCompare(b.name);
            return a.type === 'folder' ? -1 : 1;
        });

        // First pass: create nodes
        flatFiles.forEach(f => {
            map[f.path] = {
                ...f,
                children: []
            };
        });

        // Second pass: build hierarchy
        flatFiles.forEach(f => {
            const parts = f.path.split('/');
            if (parts.length === 1) {
                root.push(map[f.path]);
            } else {
                const parentPath = parts.slice(0, -1).join('/');
                if (map[parentPath]) {
                    map[parentPath].children?.push(map[f.path]);
                } else {
                    // If parent doesn't exist in list (shouldn't happen if backend is good), add to root
                    root.push(map[f.path]);
                }
            }
        });

        return root;
    };

    const getFileIcon = (file: FileNode) => {
        if (file.type === 'folder') return <Folder className="w-4 h-4 text-blue-500" />;

        const ext = file.name.split('.').pop()?.toLowerCase();
        switch (ext) {
            case 'md': return <FileText className="w-4 h-4 text-gray-500" />;
            case 'json': return <FileJson className="w-4 h-4 text-yellow-500" />;
            case 'js':
            case 'ts':
            case 'tsx':
            case 'py': return <Code className="w-4 h-4 text-blue-400" />;
            case 'png':
            case 'jpg':
            case 'jpeg': return <ImageIcon className="w-4 h-4 text-purple-500" />;
            default: return <File className="w-4 h-4 text-gray-400" />;
        }
    };

    const renderNode = (node: FileNode, depth: number = 0) => {
        const isExpanded = expandedFolders.has(node.path);
        const isSelected = selectedFile === node.path;
        const isChecked = selectedFiles.has(node.path);
        const hasChildren = node.children && node.children.length > 0;

        return (
            <div key={node.path}>
                <div
                    className={cn(
                        "flex items-center gap-2 px-3 py-1.5 cursor-pointer text-sm transition-colors select-none",
                        isSelected && !isSelectMode ? "bg-blue-50 text-blue-600" : "hover:bg-gray-100 text-gray-700",
                        isChecked && isSelectMode && "bg-blue-100"
                    )}
                    style={{ paddingLeft: `${depth * 12 + 12}px` }}
                    onClick={(e) => handleFileClick(node, e)}
                >
                    {isSelectMode && (
                        <span className="flex-shrink-0">
                            {isChecked ? (
                                <CheckSquare className="w-4 h-4 text-blue-600" />
                            ) : (
                                <Square className="w-4 h-4 text-gray-400" />
                            )}
                        </span>
                    )}
                    <span
                        className="p-0.5 rounded-sm hover:bg-gray-200 text-gray-400"
                        onClick={(e) => {
                            e.stopPropagation();
                            if (node.type === 'folder' && !isSelectMode) {
                                toggleFolder(node.path, e);
                            }
                        }}
                    >
                        {node.type === 'folder' && (
                            isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />
                        )}
                        {node.type !== 'folder' && <span className="w-3 h-3 block" />}
                    </span>

                    {getFileIcon(node)}
                    <span className="truncate">{node.name}</span>
                </div>

                {node.type === 'folder' && isExpanded && node.children && (
                    <div>
                        {node.children.map(child => renderNode(child, depth + 1))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className={cn("flex flex-col h-full bg-white border-r", className)}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b">
                <span className="text-sm font-semibold text-gray-700">EXPLORER</span>
                <div className="flex items-center gap-1">
                    <button
                        onClick={toggleSelectMode}
                        className={cn(
                            "p-1 hover:bg-gray-100 rounded text-gray-500",
                            isSelectMode && "bg-blue-100 text-blue-600"
                        )}
                        title="Select Mode"
                    >
                        {isSelectMode ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                    </button>
                    <button
                        onClick={fetchFiles}
                        className="p-1 hover:bg-gray-100 rounded text-gray-500"
                        title="Refresh"
                    >
                        <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                    </button>
                    <label className="p-1 hover:bg-gray-100 rounded text-gray-500 cursor-pointer" title="Upload File">
                        <input
                            type="file"
                            className="hidden"
                            onChange={async (e) => {
                                const file = e.target.files?.[0];
                                if (!file) return;

                                const formData = new FormData();
                                formData.append('file', file);

                                try {
                                    setIsLoading(true);
                                    const response = await fetch(`/api/files/${workspaceId}/upload`, {
                                        method: 'POST',
                                        body: formData
                                    });

                                    if (response.ok) {
                                        await fetchFiles();
                                    } else {
                                        console.error('Upload failed');
                                    }
                                } catch (error) {
                                    console.error('Upload error:', error);
                                } finally {
                                    setIsLoading(false);
                                }
                            }}
                        />
                        <Plus className="w-4 h-4" />
                    </label>
                </div>
            </div>

            {/* Batch Operations Toolbar */}
            {isSelectMode && selectedFiles.size > 0 && (
                <div className="flex items-center justify-between px-4 py-2 border-b bg-blue-50">
                    <span className="text-sm text-blue-700 font-medium">
                        {selectedFiles.size} selected
                    </span>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={selectAll}
                            className="text-xs text-blue-600 hover:underline"
                        >
                            Select All
                        </button>
                        <button
                            onClick={handleBatchZip}
                            className="p-1.5 hover:bg-blue-100 rounded text-blue-600"
                            title="Zip & Download"
                        >
                            <Archive className="w-4 h-4" />
                        </button>
                        <button
                            onClick={handleBatchDownload}
                            className="p-1.5 hover:bg-blue-100 rounded text-blue-600"
                            title="Download"
                        >
                            <Download className="w-4 h-4" />
                        </button>
                        <button
                            onClick={handleBatchDelete}
                            className="p-1.5 hover:bg-red-100 rounded text-red-600"
                            title="Delete"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}

            {/* File Tree */}
            <div className="flex-1 overflow-y-auto py-2">
                {isLoading && files.length === 0 ? (
                    <div className="flex items-center justify-center h-20 text-gray-400 text-sm">
                        Loading...
                    </div>
                ) : files.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-20 text-gray-400 text-sm">
                        <span>No files found</span>
                        <button onClick={fetchFiles} className="text-blue-500 hover:underline mt-1">Refresh</button>
                    </div>
                ) : (
                    files.map(node => renderNode(node))
                )}
            </div>
        </div>
    );
}
