'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Image, Sparkles, BookOpen } from 'lucide-react';

interface CleanChatInputProps {
    onSend: (message: string, images?: File[]) => void;
    placeholder?: string;
    disabled?: boolean;
}

interface University {
    type: string;
    name: string;
    abbreviation: string;
    description: string;
}

const DEFAULT_WORKFLOWS: University[] = [
    {
        type: 'combine-thesis',
        name: 'Combine Thesis',
        abbreviation: 'JOIN',
        description: 'Combine all chapters into single thesis document'
    },
    {
        type: 'generate-chapter1',
        name: 'Generate Chapter 1',
        abbreviation: 'CH1',
        description: 'Generate Chapter 1 (Introduction)'
    },
    {
        type: 'generate-chapter2',
        name: 'Generate Chapter 2',
        abbreviation: 'CH2',
        description: 'Generate Chapter 2 (Literature Review)'
    },
    {
        type: 'generate-chapter3',
        name: 'Generate Chapter 3',
        abbreviation: 'CH3',
        description: 'Generate Chapter 3 (Methodology)'
    },
    {
        type: 'generate-chapter4',
        name: 'Generate Chapter 4',
        abbreviation: 'CH4',
        description: 'Generate Chapter 4 (Data Analysis)'
    },
    {
        type: 'generate-dataset',
        name: 'Generate Dataset',
        abbreviation: 'DATA',
        description: 'Generate synthetic research dataset'
    },
    {
        type: 'generate-full-thesis',
        name: 'Generate Full Thesis',
        abbreviation: 'FULL',
        description: 'Generate complete PhD thesis (all 6 chapters)'
    },
    {
        type: 'generate-study-tools',
        name: 'Generate Study Tools',
        abbreviation: 'TOOLS',
        description: 'Generate study tools (questionnaire, interview guides)'
    }
];

export function CleanChatInput({ onSend, placeholder = "What do you want to create?", disabled }: CleanChatInputProps) {
    const [message, setMessage] = useState('');
    const [images, setImages] = useState<File[]>([]);
    const [showWorkflows, setShowWorkflows] = useState(false);
    const [workflows, setWorkflows] = useState<University[]>(DEFAULT_WORKFLOWS);
    const [selectedWorkflow, setSelectedWorkflow] = useState<University | null>(null);
    const [cursorPosition, setCursorPosition] = useState(0);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const suggestionsRef = useRef<HTMLDivElement>(null);

    // Load workflows on mount
    useEffect(() => {
        const loadWorkflows = async () => {
            try {
                console.log('Loading universities from API...');
                const response = await fetch('http://localhost:8000/api/thesis/universities');
                const data = await response.json();
                console.log('Universities loaded:', data.universities);
                if (data.universities && data.universities.length > 0) {
                    setWorkflows(data.universities);
                }
            } catch (error) {
                console.error('Failed to load universities:', error);
                // Keep defaults
            }
        };
        loadWorkflows();
    }, []);

    // Handle paste (with image support)
    const handlePaste = (e: React.ClipboardEvent) => {
        const items = e.clipboardData?.items;
        if (!items) return;

        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                e.preventDefault();
                const file = items[i].getAsFile();
                if (file) {
                    setImages(prev => [...prev, file]);
                }
            }
        }
    };

    // Check if user is typing a slash command
    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const value = e.target.value;
        setMessage(value);
        setCursorPosition(e.target.selectionStart);

        // Check if last typed character is "/" or if we're at the start with "/"
        const lastCharIsSlash = value[value.length - 1] === '/';
        const startsWithSlash = value.trim().startsWith('/');

        console.log('Input changed:', { value, lastCharIsSlash, startsWithSlash, workflowsCount: workflows.length });

        if (lastCharIsSlash || startsWithSlash) {
            console.log('Slash detected! Showing workflows dropdown');
            setShowWorkflows(true);
        } else {
            setShowWorkflows(false);
        }
    };

    // Select a workflow
    const selectWorkflow = (wf: University) => {
        // Replace the "/" with the workflow command
        const newMessage = message.replace(/\/$/, `/${wf.type} `);
        setMessage(newMessage);
        setSelectedWorkflow(wf);
        setShowWorkflows(false);

        // Focus back on textarea
        setTimeout(() => textareaRef.current?.focus(), 0);
    };

    // Handle file selection
    const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        setImages(prev => [...prev, ...files]);
    };

    // Remove image
    const removeImage = (index: number) => {
        setImages(prev => prev.filter((_, i) => i !== index));
    };

    // Send message
    const handleSend = () => {
        if (!message.trim() && images.length === 0) return;

        onSend(message, images);
        setMessage('');
        setImages([]);
        setSelectedWorkflow(null);
        setShowWorkflows(false);
    };

    // Handle Enter key
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // Close suggestions when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
                setShowWorkflows(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-[#0B0B0B] p-4">
            {/* Image Previews */}
            {images.length > 0 && (
                <div className="mb-3 flex gap-2 flex-wrap">
                    {images.map((img, idx) => (
                        <div key={idx} className="relative group">
                            <img
                                src={URL.createObjectURL(img)}
                                alt="Pasted"
                                className="w-20 h-20 object-cover rounded border border-gray-300"
                            />
                            <button
                                onClick={() => removeImage(idx)}
                                className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                ×
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Selected Workflow Badge */}
            {selectedWorkflow && (
                <div className="mb-3 inline-flex items-center gap-2 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-full px-3 py-1 text-sm">
                    <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    <span className="text-blue-700 dark:text-blue-300 font-medium">{selectedWorkflow.name}</span>
                    <button
                        onClick={() => {
                            setSelectedWorkflow(null);
                            setMessage(message.replace(/\/\w+\s?/, '/'));
                        }}
                        className="text-blue-400 hover:text-blue-600 dark:hover:text-blue-200 ml-1"
                    >
                        ×
                    </button>
                </div>
            )}

            {/* Input Area */}
            <div className="flex gap-2 items-end">
                <div className="flex-1 relative">
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyDown}
                        onPaste={handlePaste}
                        placeholder={placeholder}
                        disabled={disabled}
                        rows={1}
                        className="w-full resize-none rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
                        style={{ maxHeight: '150px', minHeight: '48px' }}
                    />

                    {/* Workflow Suggestions */}
                    {showWorkflows && workflows.length > 0 && (
                        <div
                            ref={suggestionsRef}
                            className="absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-[100] max-h-64 overflow-y-auto"
                        >
                            <div className="p-2 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                                <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 px-2 py-1">
                                    Select Workflow
                                </p>
                            </div>
                            {workflows.map((wf) => (
                                <button
                                    key={wf.type}
                                    onClick={() => selectWorkflow(wf)}
                                    className="w-full text-left px-3 py-2 hover:bg-blue-50 dark:hover:bg-blue-900/20 border-b border-gray-100 dark:border-gray-700 last:border-b-0 transition-colors"
                                >
                                    <div className="flex items-start gap-2">
                                        <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                                                /{wf.type}
                                            </p>
                                            <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                                                {wf.description}
                                            </p>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Image Button */}
                    <label className="absolute right-3 bottom-3 cursor-pointer text-gray-400 hover:text-blue-500 transition-colors">
                        <Image className="w-5 h-5" />
                        <input
                            type="file"
                            accept="image/*"
                            multiple
                            onChange={handleImageSelect}
                            className="hidden"
                        />
                    </label>
                </div>

                {/* Send Button */}
                <button
                    onClick={handleSend}
                    disabled={disabled || (!message.trim() && images.length === 0)}
                    className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                    <Send className="w-4 h-4" />
                    Send
                </button>
            </div>

            <p className="text-xs text-gray-400 mt-2">
                Type "/" to select a university • Paste images directly • Shift+Enter for new line
            </p>
        </div>
    );
}

// Welcome Screen Component
export function WelcomeScreen({ onStart }: { onStart: (message?: string) => void }) {
    const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
    const [inputValue, setInputValue] = useState('');
    const [showUniversities, setShowUniversities] = useState(false);
    const [universities, setUniversities] = useState<University[]>(DEFAULT_UNIVERSITIES);

    // Load universities on mount
    useEffect(() => {
        const loadUniversities = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/thesis/universities');
                const data = await response.json();
                setUniversities(data.universities);
            } catch (error) {
                console.error('Failed to load universities:', error);
            }
        };
        loadUniversities();
    }, []);

    const topics = [
        "Interpretable large language models",
        "High-throughput methods for protein structure prediction and analysis",
        "Next-generation battery materials for high-energy-density and long-life storage solutions",
        "Real-time detection and mitigation of cyber threats in large-scale networks",
        "Autonomous swarms of robots to achieve complex collective behaviors"
    ];

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (inputValue.trim()) {
            onStart(inputValue);
        } else if (selectedTopic) {
            onStart(selectedTopic);
        }
    };

    const selectUniversity = (uni: University) => {
        setInputValue(`/${uni.type} `);
        setShowUniversities(false);
    };

    return (
        <div className="flex flex-col h-full bg-white p-8 max-w-4xl mx-auto font-sans">
            <div className="flex-1 mt-10">
                <h1 className="text-xl text-gray-800 mb-6 leading-relaxed">
                    Hi, I'm Gatsbi! I can assist you with technical innovation. Please choose from
                    the following research topics or enter your own topic in the input box:
                </h1>

                <div className="space-y-4 ml-1">
                    {topics.map((topic, idx) => (
                        <label key={idx} className="flex items-start gap-3 cursor-pointer group">
                            <div className="relative flex items-center mt-1">
                                <input
                                    type="radio"
                                    name="research-topic"
                                    className="peer h-5 w-5 appearance-none rounded-full border border-gray-300 checked:border-gray-500 checked:bg-gray-500 hover:border-gray-400 transition-all"
                                    onChange={() => setSelectedTopic(topic)}
                                    checked={selectedTopic === topic}
                                />
                                <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                            </div>
                            <span className="text-gray-700 text-[15px] leading-relaxed group-hover:text-gray-900">
                                {topic}
                            </span>
                        </label>
                    ))}
                </div>
            </div>

            {/* Bottom Input Area */}
            <div className="mt-8 mb-4">
                <form onSubmit={handleSubmit} className="relative">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => {
                            setInputValue(e.target.value);
                            if (selectedTopic) setSelectedTopic(null);
                            // Show universities if user types "/"
                            if (e.target.value.endsWith('/')) {
                                setShowUniversities(true);
                            }
                        }}
                        placeholder="Type / to select a university or enter your research topic"
                        className="w-full bg-gray-100/50 hover:bg-gray-100 focus:bg-white text-gray-800 rounded-full py-4 pl-6 pr-14 outline-none ring-1 ring-transparent focus:ring-gray-200 transition-all text-[15px] placeholder:text-gray-400"
                    />
                    {/* University Suggestions on Welcome */}
                    {showUniversities && universities.length > 0 && (
                        <div className="absolute bottom-full left-0 right-0 mb-2 bg-white text-gray-900 border border-gray-200 rounded-lg shadow-xl z-[100] max-h-64 overflow-y-auto">
                            <div className="p-2 border-b border-gray-100 bg-gray-50">
                                <p className="text-xs font-semibold text-gray-600 px-2 py-1">
                                    Select University
                                </p>
                            </div>
                            {universities.map((uni) => (
                                <button
                                    key={uni.type}
                                    type="button"
                                    onClick={() => selectUniversity(uni)}
                                    className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-100 last:border-b-0 transition-colors"
                                >
                                    <div className="flex items-start gap-2">
                                        <BookOpen className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium text-gray-900 text-sm">
                                                /{uni.type}
                                            </p>
                                            <p className="text-xs text-gray-600 truncate">
                                                {uni.name}
                                            </p>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                    <button
                        type="submit"
                        disabled={!inputValue.trim() && !selectedTopic}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-white rounded-full shadow-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all border border-gray-100"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-600">
                            <line x1="12" y1="19" x2="12" y2="5"></line>
                            <polyline points="5 12 12 5 19 12"></polyline>
                        </svg>
                    </button>
                </form>
            </div>
        </div>
    );
}
