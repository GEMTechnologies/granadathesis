"use client";

import React, { useState, useEffect } from 'react';
import { File, Folder, FolderOpen, Code, FileText, Image as ImageIcon, Download, Eye } from 'lucide-react';

interface FileNode {
    name: string;
    path: string;
    type: 'file' | 'directory';
    size?: number;
    children?: FileNode[];
}

interface FileBrowserProps {
    workspaceId: string;
    onFileSelect?: (file: FileNode) => void;
}

export default function FileBrowser({ workspaceId, onFileSelect }: FileBrowserProps) {
    const [files, setFiles] = useState<FileNode[]>([]);
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
    const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);

    useEffect(() => {
        loadFiles();
    }, [workspaceId]);

    const loadFiles = async () => {
        try {
            // Mock data for now - replace with actual API call
            const mockFiles: FileNode[] = [
                {
                    name: 'tools',
                    path: '/workspace/tools',
                    type: 'directory',
                    children: [
                        { name: 'calculator.py', path: '/workspace/tools/calculator.py', type: 'file', size: 1234 },
                        { name: 'scraper.py', path: '/workspace/tools/scraper.py', type: 'file', size: 2456 }
                    ]
                },
                {
                    name: 'projects',
                    path: '/workspace/projects',
                    type: 'directory',
                    children: [
                        {
                            name: 'website', path: '/workspace/projects/website', type: 'directory', children: [
                                { name: 'index.html', path: '/workspace/projects/website/index.html', type: 'file', size: 3456 },
                                { name: 'style.css', path: '/workspace/projects/website/style.css', type: 'file', size: 890 }
                            ]
                        }
                    ]
                },
                { name: 'output.txt', path: '/workspace/output.txt', type: 'file', size: 567 }
            ];

            setFiles(mockFiles);
        } catch (error) {
            console.error('Failed to load files:', error);
        }
    };

    const toggleFolder = (path: string) => {
        const newExpanded = new Set(expandedFolders);
        if (newExpanded.has(path)) {
            newExpanded.delete(path);
        } else {
            newExpanded.add(path);
        }
        setExpandedFolders(newExpanded);
    };

    const handleFileClick = (file: FileNode) => {
        if (file.type === 'file') {
            setSelectedFile(file);
            if (onFileSelect) {
                onFileSelect(file);
            }
        } else {
            toggleFolder(file.path);
        }
    };

    const getFileIcon = (fileName: string) => {
        const ext = fileName.split('.').pop()?.toLowerCase();

        if (['js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c'].includes(ext || '')) {
            return <Code className="h-4 w-4 text-blue-500" />;
        }
        if (['txt', 'md', 'json', 'yaml'].includes(ext || '')) {
            return <FileText className="h-4 w-4 text-gray-500" />;
        }
        if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(ext || '')) {
            return <ImageIcon className="h-4 w-4 text-purple-500" />;
        }
        return <File className="h-4 w-4 text-gray-400" />;
    };

    const renderTree = (nodes: FileNode[], depth: number = 0) => {
        return nodes.map((node) => (
            <div key={node.path}>
                <div
                    className={`flex items-center space-x-2 px-2 py-1.5 cursor-pointer hover:bg-gray-100 rounded transition ${selectedFile?.path === node.path ? 'bg-blue-50 border-l-2 border-blue-500' : ''
                        }`}
                    style={{ paddingLeft: `${depth * 16 + 8}px` }}
                    onClick={() => handleFileClick(node)}
                >
                    {node.type === 'directory' ? (
                        expandedFolders.has(node.path) ? (
                            <FolderOpen className="h-4 w-4 text-yellow-600" />
                        ) : (
                            <Folder className="h-4 w-4 text-yellow-600" />
                        )
                    ) : (
                        getFileIcon(node.name)
                    )}
                    <span className="text-sm text-gray-700 flex-1">{node.name}</span>
                    {node.type === 'file' && node.size && (
                        <span className="text-xs text-gray-400">
                            {(node.size / 1024).toFixed(1)}KB
                        </span>
                    )}
                </div>

                {node.type === 'directory' && expandedFolders.has(node.path) && node.children && (
                    renderTree(node.children, depth + 1)
                )}
            </div>
        ));
    };

    return (
        <div className="h-full flex flex-col bg-white border-r border-gray-200">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <h3 className="font-semibold text-gray-900">Workspace Files</h3>
                <p className="text-xs text-gray-500 mt-0.5">Agent-generated content</p>
            </div>

            {/* File Tree */}
            <div className="flex-1 overflow-y-auto p-2">
                {files.length > 0 ? (
                    renderTree(files)
                ) : (
                    <div className="text-center py-12 text-gray-400">
                        <Folder className="h-12 w-12 mx-auto mb-3 opacity-50" />
                        <p className="text-sm">No files yet</p>
                        <p className="text-xs mt-1">Agent will create files here</p>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
                {files.length} items • {workspaceId.slice(0, 12)}
            </div>
        </div>
    );
}
