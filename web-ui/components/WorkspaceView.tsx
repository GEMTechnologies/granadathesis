"use client";

import React, { useState } from 'react';
import FileBrowser from './FileBrowser';
import FilePreview from './FilePreview';
import CodeEditor from './CodeEditor';
import SandboxTerminal from './SandboxTerminal';
import AgentStream from './AgentStream';
import ImageGallery from './ImageGallery';
import BrowserViewer from './BrowserViewer';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Layout, Code, Terminal, Brain, FileText, Globe } from 'lucide-react';

interface WorkspaceViewProps {
    workspaceId: string;
    initialQuery?: string;
}

export default function WorkspaceView({ workspaceId, initialQuery }: WorkspaceViewProps) {
    const [selectedFile, setSelectedFile] = useState<any>(null);
    const [activeTab, setActiveTab] = useState('agent');

    return (
        <div className="h-screen flex flex-col bg-gray-100">
            {/* Header */}
            <div className="h-14 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 flex items-center justify-between shadow-lg">
                <div className="flex items-center space-x-3">
                    <Layout className="h-6 w-6" />
                    <div>
                        <h1 className="font-bold text-lg">Autonomous Workspace</h1>
                        <p className="text-xs text-blue-100">{workspaceId}</p>
                    </div>
                </div>
                <div className="flex items-center space-x-2 text-xs">
                    <span className="px-2 py-1 bg-white/20 rounded">Docker Sandbox</span>
                    <span className="px-2 py-1 bg-green-500/30 rounded">● Active</span>
                </div>
            </div>

            {/* Main Layout */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Sidebar - File Browser */}
                <div className="w-64 border-r border-gray-300 bg-white">
                    <FileBrowser
                        workspaceId={workspaceId}
                        onFileSelect={setSelectedFile}
                    />
                </div>

                {/* Center - Main Content */}
                <div className="flex-1 flex flex-col">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
                        {/* Tab List */}
                        <TabsList className="w-full justify-start rounded-none border-b bg-gray-50 p-0 h-auto">
                            <TabsTrigger
                                value="agent"
                                className="flex items-center space-x-2 px-4 py-3 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
                            >
                                <Brain className="h-4 w-4" />
                                <span>Agent</span>
                            </TabsTrigger>
                            <TabsTrigger
                                value="editor"
                                className="flex items-center space-x-2 px-4 py-3 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
                            >
                                <Code className="h-4 w-4" />
                                <span>Editor</span>
                            </TabsTrigger>
                            <TabsTrigger
                                value="terminal"
                                className="flex items-center space-x-2 px-4 py-3 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
                            >
                                <Terminal className="h-4 w-4" />
                                <span>Terminal</span>
                            </TabsTrigger>
                            <TabsTrigger
                                value="images"
                                className="flex items-center space-x-2 px-4 py-3 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
                            >
                                <FileText className="h-4 w-4" />
                                <span>Images</span>
                            </TabsTrigger>
                            <TabsTrigger
                                value="browser"
                                className="flex items-center space-x-2 px-4 py-3 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
                            >
                                <Globe className="h-4 w-4" />
                                <span>Browser</span>
                            </TabsTrigger>
                            {selectedFile && (
                                <TabsTrigger
                                    value="preview"
                                    className="flex items-center space-x-2 px-4 py-3 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
                                >
                                    <FileText className="h-4 w-4" />
                                    <span>{selectedFile.name}</span>
                                </TabsTrigger>
                            )}
                        </TabsList>

                        {/* Tab Content */}
                        <div className="flex-1 overflow-hidden">
                            <TabsContent value="agent" className="h-full m-0">
                                <AgentStream
                                    workspaceId={workspaceId}
                                    query={initialQuery || "Help me get started"}
                                />
                            </TabsContent>

                            <TabsContent value="editor" className="h-full m-0">
                                <CodeEditor
                                    workspaceId={workspaceId}
                                    language="python"
                                    onRun={(code) => {
                                        // Execute in sandbox
                                        console.log('Running code:', code);
                                    }}
                                />
                            </TabsContent>

                            <TabsContent value="terminal" className="h-full m-0">
                                <SandboxTerminal workspaceId={workspaceId} />
                            </TabsContent>

                            <TabsContent value="images" className="h-full m-0">
                                <ImageGallery workspaceId={workspaceId} />
                            </TabsContent>

                            <TabsContent value="browser" className="h-full m-0">
                                <BrowserViewer workspaceId={workspaceId} />
                            </TabsContent>

                            {selectedFile && (
                                <TabsContent value="preview" className="h-full m-0">
                                    <FilePreview
                                        filePath={selectedFile.path}
                                        fileName={selectedFile.name}
                                        workspaceId={workspaceId}
                                    />
                                </TabsContent>
                            )}
                        </div>
                    </Tabs>
                </div>

                {/* Right Sidebar - Agent Output/Tools */}
                <div className="w-80 border-l border-gray-300 bg-white p-4 overflow-y-auto">
                    <h3 className="font-semibold text-gray-900 mb-3">Created Tools</h3>
                    <div className="space-y-2">
                        <div className="p-3 border border-gray-200 rounded-lg hover:border-blue-300 transition cursor-pointer">
                            <div className="flex items-center space-x-2 mb-1">
                                <Code className="h-4 w-4 text-blue-500" />
                                <span className="font-medium text-sm">calculator.py</span>
                            </div>
                            <p className="text-xs text-gray-500">
                                Basic arithmetic calculator with tests
                            </p>
                        </div>

                        <div className="p-3 border border-gray-200 rounded-lg hover:border-blue-300 transition cursor-pointer">
                            <div className="flex items-center space-x-2 mb-1">
                                <Code className="h-4 w-4 text-green-500" />
                                <span className="font-medium text-sm">scraper.py</span>
                            </div>
                            <p className="text-xs text-gray-500">
                                Web scraper for data extraction
                            </p>
                        </div>
                    </div>

                    <h3 className="font-semibold text-gray-900 mt-6 mb-3">Recent Tasks</h3>
                    <div className="space-y-2 text-sm">
                        <div className="flex items-start space-x-2">
                            <span className="text-green-500">✅</span>
                            <span className="text-gray-700">Created calculator tool</span>
                        </div>
                        <div className="flex items-start space-x-2">
                            <span className="text-green-500">✅</span>
                            <span className="text-gray-700">Installed pandas package</span>
                        </div>
                        <div className="flex items-start space-x-2">
                            <span className="text-blue-500">🔄</span>
                            <span className="text-gray-700">Building React website...</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
