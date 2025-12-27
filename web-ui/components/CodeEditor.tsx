"use client";

import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Save, Play, Settings } from 'lucide-react';

interface CodeEditorProps {
    initialCode?: string;
    language?: string;
    workspaceId?: string;
    onSave?: (code: string) => void;
    onRun?: (code: string) => void;
}

export default function CodeEditor({
    initialCode = '# Write your code here\nprint("Hello, World!")',
    language = 'python',
    workspaceId,
    onSave,
    onRun
}: CodeEditorProps) {
    const [code, setCode] = useState(initialCode);
    const [theme, setTheme] = useState<'vs-dark' | 'light'>('vs-dark');
    const [fontSize, setFontSize] = useState(14);

    const handleSave = () => {
        if (onSave) {
            onSave(code);
        }
    };

    const handleRun = () => {
        if (onRun) {
            onRun(code);
        }
    };

    const handleEditorChange = (value: string | undefined) => {
        if (value !== undefined) {
            setCode(value);
        }
    };

    return (
        <div className="h-full flex flex-col bg-gray-900">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
                <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-300 font-mono">{language}</span>
                    {workspaceId && (
                        <span className="text-xs text-gray-500 font-mono">
                            {workspaceId.slice(0, 12)}
                        </span>
                    )}
                </div>

                <div className="flex items-center space-x-2">
                    {/* Font Size */}
                    <select
                        value={fontSize}
                        onChange={(e) => setFontSize(Number(e.target.value))}
                        className="px-2 py-1 text-xs bg-gray-700 text-gray-300 border border-gray-600 rounded"
                    >
                        <option value={12}>12px</option>
                        <option value={14}>14px</option>
                        <option value={16}>16px</option>
                        <option value={18}>18px</option>
                    </select>

                    {/* Theme Toggle */}
                    <button
                        onClick={() => setTheme(theme === 'vs-dark' ? 'light' : 'vs-dark')}
                        className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded transition"
                        title="Toggle theme"
                    >
                        <Settings className="h-4 w-4 text-gray-300" />
                    </button>

                    {/* Run Button */}
                    {onRun && (
                        <button
                            onClick={handleRun}
                            className="flex items-center space-x-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded transition text-sm"
                        >
                            <Play className="h-4 w-4" />
                            <span>Run</span>
                        </button>
                    )}

                    {/* Save Button */}
                    {onSave && (
                        <button
                            onClick={handleSave}
                            className="flex items-center space-x-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded transition text-sm"
                        >
                            <Save className="h-4 w-4" />
                            <span>Save</span>
                        </button>
                    )}
                </div>
            </div>

            {/* Monaco Editor */}
            <div className="flex-1">
                <Editor
                    height="100%"
                    language={language}
                    value={code}
                    theme={theme}
                    onChange={handleEditorChange}
                    options={{
                        fontSize,
                        minimap: { enabled: false },
                        scrollBeyondLastLine: false,
                        wordWrap: 'on',
                        automaticLayout: true,
                        tabSize: 4,
                        formatOnPaste: true,
                        formatOnType: true,
                        suggestOnTriggerCharacters: true,
                        quickSuggestions: true,
                        parameterHints: { enabled: true },
                        lineNumbers: 'on',
                        renderLineHighlight: 'all',
                        cursorStyle: 'line',
                        cursorBlinking: 'smooth'
                    }}
                />
            </div>

            {/* Status Bar */}
            <div className="px-4 py-1.5 bg-gray-800 border-t border-gray-700 flex items-center justify-between text-xs">
                <span className="text-gray-400">
                    {code.split('\n').length} lines • {code.length} characters
                </span>
                <span className="text-gray-500 font-mono">
                    VSCode Monaco Editor
                </span>
            </div>
        </div>
    );
}
