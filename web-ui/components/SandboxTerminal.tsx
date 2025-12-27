"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Terminal as TerminalIcon, Play, Loader2, XCircle, CheckCircle2 } from 'lucide-react';

interface SandboxTerminalProps {
    workspaceId: string;
}

export default function SandboxTerminal({ workspaceId }: SandboxTerminalProps) {
    const [code, setCode] = useState('# Write Python code here\nprint("Hello from secure sandbox!")');
    const [output, setOutput] = useState('');
    const [isRunning, setIsRunning] = useState(false);
    const [exitCode, setExitCode] = useState<number | null>(null);
    const outputRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Auto-scroll output
        if (outputRef.current) {
            outputRef.current.scrollTop = outputRef.current.scrollHeight;
        }
    }, [output]);

    const executeCode = async () => {
        setIsRunning(true);
        setOutput('>>> Executing code in secure sandbox...\n');
        setExitCode(null);

        try {
            const response = await fetch(`/api/sandbox/workspace/${workspaceId}/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code,
                    language: 'python',
                    timeout: 30
                })
            });

            if (!response.ok) {
                throw new Error('Execution failed');
            }

            const result = await response.json();

            // Display output
            let outputText = '';
            if (result.stdout) {
                outputText += result.stdout;
            }
            if (result.stderr) {
                outputText += `\n[stderr]\n${result.stderr}`;
            }

            outputText += `\n\n[Completed in ${result.execution_time}s with exit code ${result.exit_code}]`;

            setOutput(outputText);
            setExitCode(result.exit_code);

        } catch (error) {
            setOutput(`[Error]\n${error instanceof Error ? error.message : 'Unknown error'}`);
            setExitCode(1);
        } finally {
            setIsRunning(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Ctrl+Enter to run
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            executeCode();
        }
    };

    return (
        <div className="h-full flex flex-col bg-gray-900 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
                <div className="flex items-center space-x-2">
                    <TerminalIcon className="h-5 w-5 text-green-400" />
                    <span className="text-sm font-medium text-gray-200">Secure Sandbox Terminal</span>
                    <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                        Isolated
                    </span>
                </div>
                <button
                    onClick={executeCode}
                    disabled={isRunning}
                    className={`flex items-center space-x-2 px-4 py-1.5 rounded transition ${isRunning
                            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                        }`}
                >
                    {isRunning ? (
                        <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Running...</span>
                        </>
                    ) : (
                        <>
                            <Play className="h-4 w-4" />
                            <span className="text-sm">Run (Ctrl+Enter)</span>
                        </>
                    )}
                </button>
            </div>

            {/* Code Editor */}
            <div className="flex-1 flex flex-col md:flex-row min-h-0">
                {/* Input */}
                <div className="flex-1 flex flex-col border-r border-gray-700">
                    <div className="px-4 py-2 bg-gray-800 border-b border-gray-700">
                        <span className="text-xs text-gray-400">CODE</span>
                    </div>
                    <textarea
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className="flex-1 p-4 bg-gray-900 text-gray-100 font-mono text-sm resize-none focus:outline-none"
                        placeholder="Write your code here..."
                        spellCheck={false}
                    />
                </div>

                {/* Output */}
                <div className="flex-1 flex flex-col">
                    <div className="px-4 py-2 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
                        <span className="text-xs text-gray-400">OUTPUT</span>
                        {exitCode !== null && (
                            <div className="flex items-center space-x-1">
                                {exitCode === 0 ? (
                                    <>
                                        <CheckCircle2 className="h-3 w-3 text-green-400" />
                                        <span className="text-xs text-green-400">Success</span>
                                    </>
                                ) : (
                                    <>
                                        <XCircle className="h-3 w-3 text-red-400" />
                                        <span className="text-xs text-red-400">Error</span>
                                    </>
                                )}
                            </div>
                        )}
                    </div>
                    <div
                        ref={outputRef}
                        className="flex-1 p-4 bg-gray-950 text-gray-300 font-mono text-sm overflow-y-auto whitespace-pre-wrap"
                    >
                        {output || '# Output will appear here...'}
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-gray-800 border-t border-gray-700 flex items-center justify-between text-xs text-gray-400">
                <div className="flex items-center space-x-4">
                    <span>🔒 No network access</span>
                    <span>💾 512MB RAM limit</span>
                    <span>⏱️ 30s timeout</span>
                </div>
                <span className="font-mono">{workspaceId.slice(0, 12)}</span>
            </div>
        </div>
    );
}
