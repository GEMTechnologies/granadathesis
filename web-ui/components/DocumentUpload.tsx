"use client";

import React, { useState, useCallback } from 'react';
import { Upload, FileText, X, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface UploadedFile {
    id: string;
    filename: string;
    status: 'uploading' | 'processing' | 'complete' | 'error';
    progress: number;
    chunks?: number;
    citations?: number;
    error?: string;
}

interface DocumentUploadProps {
    workspaceId: string;
    onUploadComplete?: (file: UploadedFile) => void;
}

export default function DocumentUpload({ workspaceId, onUploadComplete }: DocumentUploadProps) {
    const [files, setFiles] = useState<UploadedFile[]>([]);
    const [isDragging, setIsDragging] = useState(false);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const droppedFiles = Array.from(e.dataTransfer.files);
        handleFiles(droppedFiles);
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const selectedFiles = Array.from(e.target.files);
            handleFiles(selectedFiles);
        }
    };

    const handleFiles = async (fileList: File[]) => {
        const pdfFiles = fileList.filter(f => f.name.endsWith('.pdf'));

        if (pdfFiles.length === 0) {
            alert('Please upload PDF files only');
            return;
        }

        // Add files to queue with uploading status
        const newFiles: UploadedFile[] = pdfFiles.map(f => ({
            id: `${Date.now()}-${f.name}`,
            filename: f.name,
            status: 'uploading',
            progress: 0
        }));

        setFiles(prev => [...prev, ...newFiles]);

        // Upload each file
        for (let i = 0; i < pdfFiles.length; i++) {
            await uploadFile(pdfFiles[i], newFiles[i].id);
        }
    };

    const uploadFile = async (file: File, fileId: string) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('workspace_id', workspaceId);
        formData.append('title', file.name.replace('.pdf', ''));

        try {
            // Update to uploading
            updateFileStatus(fileId, { status: 'uploading', progress: 50 });

            const response = await fetch('/api/rag/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const result = await response.json();

            // Update to processing
            updateFileStatus(fileId, { status: 'processing', progress: 75 });

            // Listen for SSE events for completion
            // TODO: Implement SSE listener for job_id

            // For now, mark as complete after delay
            setTimeout(() => {
                updateFileStatus(fileId, {
                    status: 'complete',
                    progress: 100,
                    chunks: result.chunks_indexed || 0,
                    citations: result.citations_found || 0
                });

                if (onUploadComplete) {
                    onUploadComplete(files.find(f => f.id === fileId)!);
                }
            }, 2000);

        } catch (error) {
            updateFileStatus(fileId, {
                status: 'error',
                progress: 0,
                error: error instanceof Error ? error.message : 'Upload failed'
            });
        }
    };

    const updateFileStatus = (fileId: string, updates: Partial<UploadedFile>) => {
        setFiles(prev => prev.map(f =>
            f.id === fileId ? { ...f, ...updates } : f
        ));
    };

    const removeFile = (fileId: string) => {
        setFiles(prev => prev.filter(f => f.id !== fileId));
    };

    return (
        <div className="space-y-4">
            {/* Drop Zone */}
            <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-all
          ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
        `}
            >
                <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <p className="text-lg font-medium text-gray-700 mb-2">
                    Drop PDF files here or click to browse
                </p>
                <p className="text-sm text-gray-500 mb-4">
                    Supports multiple files • Max 50MB per file
                </p>
                <input
                    type="file"
                    multiple
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                />
                <label htmlFor="file-upload">
                    <span className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition">
                        Select Files
                    </span>
                </label>
            </div>

            {/* Upload Queue */}
            {files.length > 0 && (
                <div className="space-y-2">
                    <h3 className="font-medium text-gray-900">Upload Queue ({files.length})</h3>
                    {files.map(file => (
                        <div key={file.id} className="border rounded-lg p-4 bg-white shadow-sm">
                            <div className="flex items-start justify-between">
                                <div className="flex items-start space-x-3 flex-1">
                                    <FileText className="h-5 w-5 text-gray-400 mt-0.5" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-900 truncate">
                                            {file.filename}
                                        </p>

                                        {/* Status */}
                                        <div className="mt-1 flex items-center space-x-2">
                                            {file.status === 'uploading' && (
                                                <>
                                                    <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                                                    <span className="text-xs text-gray-600">Uploading...</span>
                                                </>
                                            )}
                                            {file.status === 'processing' && (
                                                <>
                                                    <Loader2 className="h-4 w-4 text-purple-500 animate-spin" />
                                                    <span className="text-xs text-gray-600">Processing & indexing...</span>
                                                </>
                                            )}
                                            {file.status === 'complete' && (
                                                <>
                                                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                                                    <span className="text-xs text-green-600">
                                                        Complete • {file.chunks} chunks • {file.citations} citations
                                                    </span>
                                                </>
                                            )}
                                            {file.status === 'error' && (
                                                <>
                                                    <AlertCircle className="h-4 w-4 text-red-500" />
                                                    <span className="text-xs text-red-600">{file.error}</span>
                                                </>
                                            )}
                                        </div>

                                        {/* Progress Bar */}
                                        {file.status !== 'complete' && file.status !== 'error' && (
                                            <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                                                <div
                                                    className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                                                    style={{ width: `${file.progress}%` }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <button
                                    onClick={() => removeFile(file.id)}
                                    className="ml-4 text-gray-400 hover:text-gray-600"
                                >
                                    <X className="h-5 w-5" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
