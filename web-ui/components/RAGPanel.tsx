"use client";

/**
 * RAG Document Panel Component
 * 
 * Integrates DocumentUpload and SemanticSearch into a single panel
 * for easy integration into ManusStyleLayout
 */

import React, { useState } from 'react';
import { FileText, Search, Upload as UploadIcon } from 'lucide-react';
import DocumentUpload from './DocumentUpload';
import SemanticSearch from './SemanticSearch';

interface RAGPanelProps {
    workspaceId: string;
}

export default function RAGPanel({ workspaceId }: RAGPanelProps) {
    const [activeTab, setActiveTab] = useState<'upload' | 'search'>('upload');
    const [uploadCount, setUploadCount] = useState(0);

    const handleUploadComplete = () => {
        setUploadCount(prev => prev + 1);
        // Auto-switch to search after upload
        setTimeout(() => setActiveTab('search'), 1000);
    };

    return (
        <div className="h-full flex flex-col bg-white">
            {/* Tabs */}
            <div className="flex border-b">
                <button
                    onClick={() => setActiveTab('upload')}
                    className={`flex-1 flex items-center justify-center space-x-2 px-4 py-3 font-medium transition ${activeTab === 'upload'
                            ? 'border-b-2 border-blue-600 text-blue-600'
                            : 'text-gray-600 hover:text-gray-900'
                        }`}
                >
                    <UploadIcon className="h-4 w-4" />
                    <span>Upload Documents</span>
                </button>
                <button
                    onClick={() => setActiveTab('search')}
                    className={`flex-1 flex items-center justify-center space-x-2 px-4 py-3 font-medium transition ${activeTab === 'search'
                            ? 'border-b-2 border-blue-600 text-blue-600'
                            : 'text-gray-600 hover:text-gray-900'
                        }`}
                >
                    <Search className="h-4 w-4" />
                    <span>Search</span>
                    {uploadCount > 0 && (
                        <span className="ml-1 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                            {uploadCount}
                        </span>
                    )}
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                {activeTab === 'upload' ? (
                    <DocumentUpload
                        workspaceId={workspaceId}
                        onUploadComplete={handleUploadComplete}
                    />
                ) : (
                    <SemanticSearch workspaceId={workspaceId} />
                )}
            </div>

            {/* Footer Stats */}
            <div className="border-t px-6 py-3 bg-gray-50 text-sm text-gray-600">
                <div className="flex items-center justify-between">
                    <span className="flex items-center space-x-2">
                        <FileText className="h-4 w-4" />
                        <span>Workspace: {workspaceId}</span>
                    </span>
                    <span className="text-xs">
                        {uploadCount} {uploadCount === 1 ? 'document' : 'documents'} uploaded
                    </span>
                </div>
            </div>
        </div>
    );
}
