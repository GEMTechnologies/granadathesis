'use client';

import React, { useState, useEffect, useRef } from 'react';
import { X, Download, Edit, Save, FileText, Code as CodeIcon, Image as ImageIcon, Play, Loader2, Globe, Search, FileDown, ChevronDown, Copy, Check, Table } from 'lucide-react';
import { cn } from '../../lib/utils';
import { MarkdownRenderer } from '../MarkdownRenderer';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface FilePreviewPanelProps {
    file: { name: string; path: string; type: string } | null;
    onClose: () => void;
    workspaceId: string;
    browserAction?: {
        type: 'browser_action' | 'search_result';
        url?: string;
        query?: string;
        screenshot?: string;
        content?: string;
    } | null;
}

// Copy button component
const CopyButton = ({ text, className = '' }: { text: string; className?: string }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            onClick={handleCopy}
            className={cn("p-2 rounded-md bg-gray-700 hover:bg-gray-600 transition-colors", className)}
            title="Copy code"
        >
            {copied ? (
                <Check className="w-4 h-4 text-green-400" />
            ) : (
                <Copy className="w-4 h-4 text-gray-300" />
            )}
        </button>
    );
};

export function FilePreviewPanel({ file, onClose, workspaceId, browserAction }: FilePreviewPanelProps) {
    const [content, setContent] = useState<string>('');
    const [isLoading, setIsLoading] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState('');
    const [executingCode, setExecutingCode] = useState<string | null>(null);
    const [codeOutput, setCodeOutput] = useState<{ stdout: string; stderr: string } | null>(null);
    const [isExportingDocx, setIsExportingDocx] = useState(false);
    const [showDownloadMenu, setShowDownloadMenu] = useState(false);
    const [spreadsheetData, setSpreadsheetData] = useState<any[] | null>(null);
    const downloadMenuRef = useRef<HTMLDivElement>(null);
    const iframeRef = useRef<HTMLIFrameElement>(null);

    useEffect(() => {
        if (file && file.name && !browserAction) {
            const fileType = getFileType(file.name);
            const hasExtension = file.name.includes('.') && file.name.lastIndexOf('.') < file.name.length - 1;
            const isDirectory = !hasExtension || file.type === 'directory' || (file.path && file.path.endsWith('/'));

            // Skip loading for directories or paths without extensions
            if (isDirectory) {
                setIsLoading(false);
                setContent('This is a directory. Select a file to view its contents.');
                return;
            }

            // Skip loading text content for images, PDFs, and DOCX - they're loaded directly via URL
            if (fileType !== 'image' && fileType !== 'pdf' && fileType !== 'docx') {
                loadFileContent();
            } else {
                setIsLoading(false); // Binary files don't need text loading
                setContent(''); // Clear content for binary files
            }
            setIsEditing(false);
            setSpreadsheetData(null);
        }
    }, [file]);

    // Close download menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (downloadMenuRef.current && !downloadMenuRef.current.contains(event.target as Node)) {
                setShowDownloadMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const getFileType = (path: string | undefined): 'markdown' | 'image' | 'pdf' | 'docx' | 'code' | 'text' | 'spreadsheet' | 'unknown' => {
        if (!path) return 'unknown';
        const extension = path.split('.').pop()?.toLowerCase() || 'unknown';
        if (['md', 'markdown'].includes(extension || '')) return 'markdown';
        if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(extension || '')) return 'image';
        if (extension === 'pdf') return 'pdf';
        if (['docx', 'doc'].includes(extension || '')) return 'docx';
        if (['xlsx', 'xls', 'csv', 'tsv'].includes(extension || '')) return 'spreadsheet';
        if (['py', 'js', 'ts', 'tsx', 'jsx', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php', 'html', 'css', 'sql', 'sh', 'bash', 'json', 'yaml', 'yml'].includes(extension || '')) return 'code';
        return 'text';
    };

    const getLanguageFromExtension = (path: string): string => {
        const extension = path.split('.').pop()?.toLowerCase() || '';
        const langMap: Record<string, string> = {
            'py': 'python', 'js': 'javascript', 'ts': 'typescript', 'tsx': 'tsx', 'jsx': 'jsx',
            'java': 'java', 'cpp': 'cpp', 'c': 'c', 'go': 'go', 'rs': 'rust', 'rb': 'ruby',
            'php': 'php', 'html': 'html', 'css': 'css', 'sql': 'sql', 'sh': 'bash', 'bash': 'bash',
            'json': 'json', 'yaml': 'yaml', 'yml': 'yaml', 'xml': 'xml', 'md': 'markdown'
        };
        return langMap[extension] || 'text';
    };

    const loadFileContent = async () => {
        if (!file) return;
        setIsLoading(true);
        setCodeOutput(null);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/files/${encodeURIComponent(file.path)}`);
            if (response.ok) {
                const data = await response.json();
                setContent(data.content || '');
                setEditContent(data.content || '');
            } else {
                setContent('Error loading file content');
            }
        } catch (error) {
            console.error('Failed to load file:', error);
            setContent('Error loading file content. Backend may not be available.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        if (!file) return;
        try {
            const blob = new Blob([editContent], { type: 'text/plain' });
            const formData = new FormData();
            formData.append('file', blob, file.name);

            const parentDir = file.path.split('/').slice(0, -1).join('/');
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

            const response = await fetch(`${backendUrl}/api/files/${workspaceId}/upload?path=${encodeURIComponent(parentDir)}`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                setContent(editContent);
                setIsEditing(false);
                await loadFileContent(); // Reload to sync
            } else {
                console.error('Failed to save');
            }
        } catch (error) {
            console.error('Error saving:', error);
        }
    };

    const handleExportDocx = async () => {
        if (!file) return;
        setIsExportingDocx(true);
        setShowDownloadMenu(false);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const baseFilename = file.name.replace(/\.(md|txt|text)$/i, '');

            // Convert markdown to DOCX using workspace endpoint
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/convert/docx`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    filename: baseFilename
                }),
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${baseFilename}.docx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                const errorText = await response.text();
                console.error('Failed to export DOCX:', errorText);
                alert('Failed to export to DOCX. Please try again.');
            }
        } catch (error) {
            console.error('Error exporting DOCX:', error);
            alert('Error exporting to DOCX. Please try again.');
        } finally {
            setIsExportingDocx(false);
        }
    };

    const handleExportMd = () => {
        if (!file || !content) return;
        setShowDownloadMenu(false);
        try {
            const blob = new Blob([content], { type: 'text/markdown' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const baseFilename = file.name.replace(/\.(md|txt|text)$/i, '');
            a.download = `${baseFilename}.md`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting MD:', error);
            alert('Error exporting to MD. Please try again.');
        }
    };

    const handleExecuteCode = async (code: string, language: string) => {
        setExecutingCode(code);
        setCodeOutput(null);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/api/code/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code,
                    language: language === 'python' ? 'python' : 'bash',
                    timeout: 30
                })
            });

            const data = await response.json();
            setCodeOutput({
                stdout: data.stdout || '',
                stderr: data.stderr || ''
            });
        } catch (error) {
            setCodeOutput({
                stdout: '',
                stderr: `Error executing code: ${error}`
            });
        } finally {
            setExecutingCode(null);
        }
    };

    const extractCodeBlocks = (content: string): Array<{ language: string; code: string }> => {
        const codeBlocks: Array<{ language: string; code: string }> = [];
        const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
        let match;
        while ((match = codeBlockRegex.exec(content)) !== null) {
            codeBlocks.push({
                language: match[1] || 'text',
                code: match[2].trim()
            });
        }
        return codeBlocks;
    };

    // If browser action is provided, show browser/search view
    if (browserAction) {
        return (
            <div className="flex flex-col h-full bg-white border-l">
                <div className="flex items-center justify-between px-4 py-3 border-b">
                    <div className="flex items-center gap-2">
                        {browserAction.type === 'search_result' ? (
                            <Search className="w-4 h-4 text-blue-500" />
                        ) : (
                            <Globe className="w-4 h-4 text-blue-500" />
                        )}
                        <span className="font-medium text-sm">
                            {browserAction.type === 'search_result' ? `Search: ${browserAction.query}` : browserAction.url}
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-gray-100 rounded text-gray-500"
                        title="Close Preview"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
                <div className="flex-1 overflow-auto p-4">
                    {browserAction.screenshot && (
                        <div className="mb-4">
                            <img
                                src={browserAction.screenshot}
                                alt="Browser screenshot"
                                className="max-w-full rounded-lg border"
                            />
                        </div>
                    )}
                    {browserAction.content && (
                        <div className="prose max-w-none">
                            <MarkdownRenderer content={browserAction.content} workspaceId={workspaceId} />
                        </div>
                    )}
                    {browserAction.url && !browserAction.screenshot && (
                        <iframe
                            ref={iframeRef}
                            src={browserAction.url}
                            className="w-full h-full border-0"
                            title="Browser Preview"
                        />
                    )}
                </div>
            </div>
        );
    }

    if (!file) {
        return (
            <div className="flex flex-col h-full items-center justify-center text-gray-400">
                <FileText className="w-12 h-12 mb-2 opacity-20" />
                <p className="text-sm">Select a file to preview</p>
                <p className="text-xs mt-2 text-gray-300">Or view browser/search results</p>
            </div>
        );
    }

    const fileType = getFileType(file.name);
    // Use serve endpoint for binary files (images, PDFs, DOCX), files endpoint for text files
    const isBinaryFile = fileType === 'image' || fileType === 'pdf' || fileType === 'docx';
    const fileUrl = file.path.startsWith('http')
        ? file.path
        : isBinaryFile
            ? `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/workspace/${workspaceId}/serve/${encodeURIComponent(file.path)}`
            : `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/workspace/${workspaceId}/files/${encodeURIComponent(file.path)}`;

    return (
        <div className="flex flex-col h-full bg-white border-l">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0">
                <div className="flex items-center gap-2 overflow-hidden flex-1 min-w-0">
                    {fileType === 'markdown' && <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />}
                    {fileType === 'image' && <ImageIcon className="w-4 h-4 text-green-500 flex-shrink-0" />}
                    {fileType === 'pdf' && <FileText className="w-4 h-4 text-red-500 flex-shrink-0" />}
                    {fileType === 'code' && <CodeIcon className="w-4 h-4 text-purple-500 flex-shrink-0" />}
                    {fileType === 'spreadsheet' && <Table className="w-4 h-4 text-emerald-500 flex-shrink-0" />}
                    {fileType === 'text' && <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />}
                    <span className="font-medium text-sm truncate" title={file.path}>{file.name}</span>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    {fileType !== 'pdf' && fileType !== 'image' && !isEditing && (
                        <button
                            onClick={() => setIsEditing(true)}
                            className="p-1.5 hover:bg-gray-100 rounded text-gray-500"
                            title="Edit"
                        >
                            <Edit className="w-4 h-4" />
                        </button>
                    )}
                    {isEditing && (
                        <button
                            onClick={handleSave}
                            className="p-1.5 hover:bg-blue-50 text-blue-600 rounded"
                            title="Save"
                        >
                            <Save className="w-4 h-4" />
                        </button>
                    )}
                    {/* Download Menu Button */}
                    <div className="relative" ref={downloadMenuRef}>
                        <button
                            onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                            className="p-1.5 hover:bg-gray-100 rounded text-gray-500 flex items-center gap-1"
                            title="Download options"
                        >
                            <Download className="w-4 h-4" />
                            <ChevronDown className="w-3 h-3" />
                        </button>
                        {showDownloadMenu && (
                            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 min-w-[140px]">
                                <button
                                    onClick={() => {
                                        const a = document.createElement('a');
                                        a.href = fileUrl;
                                        a.download = file.name;
                                        a.click();
                                        setShowDownloadMenu(false);
                                    }}
                                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                                >
                                    <Download className="w-4 h-4" />
                                    Download Original
                                </button>
                                {(fileType === 'markdown' || fileType === 'text') && !isEditing && (
                                    <>
                                        <button
                                            onClick={handleExportDocx}
                                            disabled={isExportingDocx}
                                            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2 disabled:opacity-50"
                                        >
                                            {isExportingDocx ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <FileDown className="w-4 h-4" />
                                            )}
                                            Export as DOCX
                                        </button>
                                        <button
                                            onClick={handleExportMd}
                                            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                                        >
                                            <FileText className="w-4 h-4" />
                                            Export as MD
                                        </button>
                                    </>
                                )}
                            </div>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-gray-100 rounded text-gray-500"
                        title="Close Preview"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden relative">
                {isLoading ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-80">
                        <div className="flex flex-col items-center gap-2">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                            <p className="text-sm text-gray-500">Loading file...</p>
                        </div>
                    </div>
                ) : isEditing ? (
                    <textarea
                        className="w-full h-full p-4 font-mono text-sm resize-none focus:outline-none"
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        style={{
                            backgroundColor: 'var(--color-bg, #F4F4F4)',
                            color: 'var(--color-text, #161616)'
                        }}
                    />
                ) : (
                    <div className="h-full overflow-y-auto overflow-x-hidden">
                        {fileType === 'markdown' && (
                            <div className="p-6 max-w-full">
                                <MarkdownRenderer content={content} workspaceId={workspaceId} />
                            </div>
                        )}
                        {fileType === 'image' && (
                            <div className="flex items-center justify-center h-full p-4">
                                <img
                                    src={fileUrl}
                                    alt={file.name}
                                    className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                                />
                            </div>
                        )}
                        {fileType === 'pdf' && (
                            <div className="h-full w-full flex flex-col">
                                {/* Use object tag with iframe fallback for better PDF compatibility */}
                                <object
                                    data={fileUrl}
                                    type="application/pdf"
                                    className="flex-1 w-full"
                                    title={file.name}
                                >
                                    {/* Fallback iframe if object doesn't work */}
                                    <iframe
                                        src={fileUrl}
                                        className="w-full h-full border-0"
                                        title={file.name}
                                    />
                                </object>
                                {/* Fallback message if neither works */}
                                <div className="absolute bottom-4 right-4">
                                    <a
                                        href={fileUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm shadow-lg"
                                    >
                                        <Globe className="w-4 h-4" />
                                        Open in New Tab
                                    </a>
                                </div>
                            </div>
                        )}
                        {fileType === 'docx' && (
                            <div className="h-full flex flex-col items-center justify-center p-8 bg-gray-50">
                                <FileText className="w-16 h-16 text-blue-500 mb-4" />
                                <h3 className="text-lg font-semibold mb-2">{file.name}</h3>
                                <p className="text-gray-500 mb-6 text-center">
                                    Word documents cannot be previewed directly in browser.
                                </p>
                                <div className="flex gap-3">
                                    <a
                                        href={fileUrl}
                                        download={file.name}
                                        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                                    >
                                        <Download className="w-5 h-5" />
                                        Download DOCX
                                    </a>
                                    <a
                                        href={`https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(fileUrl)}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center gap-2 border"
                                    >
                                        <Globe className="w-5 h-5" />
                                        Open in Office Online
                                    </a>
                                </div>
                                <p className="text-xs text-gray-400 mt-4">
                                    Note: Office Online only works with publicly accessible files
                                </p>
                            </div>
                        )}
                        {fileType === 'code' && (
                            <div className="h-full flex flex-col">
                                {/* Code with syntax highlighting */}
                                <div className="flex-1 overflow-auto relative">
                                    <div className="absolute top-2 right-2 z-10">
                                        <CopyButton text={content} />
                                    </div>
                                    <SyntaxHighlighter
                                        language={getLanguageFromExtension(file.path)}
                                        style={oneDark}
                                        showLineNumbers={true}
                                        wrapLines={true}
                                        customStyle={{
                                            margin: 0,
                                            borderRadius: 0,
                                            minHeight: '100%',
                                            fontSize: '13px',
                                        }}
                                    >
                                        {content}
                                    </SyntaxHighlighter>
                                </div>
                                {/* Executable code blocks */}
                                {extractCodeBlocks(content).length > 0 && (
                                    <div className="border-t p-4 bg-gray-50 max-h-48 overflow-auto">
                                        <div className="space-y-2">
                                            {extractCodeBlocks(content).map((block, idx) => (
                                                <div key={idx} className="flex items-center justify-between p-2 bg-gray-100 rounded border">
                                                    <span className="font-mono text-xs text-gray-600 uppercase">{block.language} block #{idx + 1}</span>
                                                    <div className="flex items-center gap-2">
                                                        <CopyButton text={block.code} />
                                                        <button
                                                            onClick={() => handleExecuteCode(block.code, block.language)}
                                                            disabled={executingCode === block.code}
                                                            className="flex items-center gap-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-xs disabled:opacity-50"
                                                        >
                                                            {executingCode === block.code ? (
                                                                <>
                                                                    <Loader2 className="w-3 h-3 animate-spin" />
                                                                    Running...
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <Play className="w-3 h-3" />
                                                                    Run
                                                                </>
                                                            )}
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        {codeOutput && (
                                            <div className="mt-3 p-3 bg-gray-900 rounded text-green-400 font-mono text-xs">
                                                {codeOutput.stdout && (
                                                    <div className="mb-2">
                                                        <div className="text-gray-400 mb-1 text-[10px] uppercase">Output:</div>
                                                        <pre className="whitespace-pre-wrap text-green-300">{codeOutput.stdout}</pre>
                                                    </div>
                                                )}
                                                {codeOutput.stderr && (
                                                    <div className="text-red-400">
                                                        <div className="text-gray-400 mb-1 text-[10px] uppercase">Error:</div>
                                                        <pre className="whitespace-pre-wrap">{codeOutput.stderr}</pre>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                        {fileType === 'spreadsheet' && (
                            <div className="h-full flex flex-col bg-gray-50">
                                <div className="flex-1 overflow-auto p-4">
                                    {content ? (
                                        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
                                            <div className="flex items-center gap-2 px-4 py-3 bg-emerald-50 border-b">
                                                <Table className="w-5 h-5 text-emerald-600" />
                                                <span className="font-medium text-emerald-700">Spreadsheet Preview</span>
                                            </div>
                                            <div className="overflow-x-auto">
                                                <table className="w-full text-sm">
                                                    <tbody>
                                                        {content.split('\n').filter(row => row.trim()).map((row, rowIdx) => {
                                                            const cells = row.includes(',') ? row.split(',') : row.split('\t');
                                                            return (
                                                                <tr key={rowIdx} className={rowIdx === 0 ? 'bg-gray-100 font-semibold' : 'hover:bg-gray-50'}>
                                                                    <td className="px-2 py-1 border-r bg-gray-50 text-gray-500 text-xs font-mono w-10 text-center">{rowIdx + 1}</td>
                                                                    {cells.map((cell, cellIdx) => (
                                                                        <td
                                                                            key={cellIdx}
                                                                            className={cn(
                                                                                "px-3 py-2 border-b border-r whitespace-nowrap",
                                                                                rowIdx === 0 && "bg-gray-100"
                                                                            )}
                                                                        >
                                                                            {cell.trim().replace(/^"|"$/g, '')}
                                                                        </td>
                                                                    ))}
                                                                </tr>
                                                            );
                                                        })}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center justify-center h-full text-gray-400">
                                            <Table className="w-12 h-12 mb-2 opacity-30" />
                                            <p className="text-sm">Loading spreadsheet data...</p>
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-2 px-4 py-2 border-t bg-white text-xs text-gray-500">
                                    <span>📊 {content.split('\n').filter(r => r.trim()).length} rows</span>
                                    <span>•</span>
                                    <span>{(content.split('\n')[0] || '').split(/[,\t]/).length} columns</span>
                                </div>
                            </div>
                        )}
                        {fileType === 'text' && (
                            <div className="h-full relative">
                                <div className="absolute top-2 right-2 z-10">
                                    <CopyButton text={content} />
                                </div>
                                <pre className="w-full h-full p-4 font-mono text-sm overflow-y-auto overflow-x-hidden whitespace-pre-wrap break-words bg-gray-50">
                                    {content}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
