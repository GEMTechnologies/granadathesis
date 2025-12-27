'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { cn } from '../lib/utils';
import { Check, Copy } from 'lucide-react';
import 'katex/dist/katex.min.css';

interface MarkdownRendererProps {
    content: string;
    className?: string;
    workspaceId?: string;
}

const CopyButton = ({ text }: { text: string }) => {
    const [copied, setCopied] = React.useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            onClick={handleCopy}
            className="absolute right-2 top-2 p-2 rounded-md bg-gray-700 hover:bg-gray-600 transition-colors"
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

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
    content,
    className,
    workspaceId
}) => {
    return (
        <div className={cn('markdown-content', className)}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeRaw]}
                components={{
                    // Headings
                    h1: ({ node, ...props }) => (
                        <h1
                            className="text-3xl font-bold mt-6 mb-4 text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2"
                            {...props}
                        />
                    ),
                    h2: ({ node, ...props }) => (
                        <h2
                            className="text-2xl font-bold mt-5 mb-3 text-gray-900 dark:text-gray-100"
                            {...props}
                        />
                    ),
                    h3: ({ node, ...props }) => (
                        <h3
                            className="text-xl font-semibold mt-4 mb-2 text-gray-900 dark:text-gray-100"
                            {...props}
                        />
                    ),
                    h4: ({ node, ...props }) => (
                        <h4
                            className="text-lg font-semibold mt-3 mb-2 text-gray-900 dark:text-gray-100"
                            {...props}
                        />
                    ),
                    h5: ({ node, ...props }) => (
                        <h5
                            className="text-base font-semibold mt-2 mb-1 text-gray-900 dark:text-gray-100"
                            {...props}
                        />
                    ),
                    h6: ({ node, ...props }) => (
                        <h6
                            className="text-sm font-semibold mt-2 mb-1 text-gray-700 dark:text-gray-300"
                            {...props}
                        />
                    ),

                    // Paragraphs
                    p: ({ node, ...props }) => (
                        <p
                            className="mb-4 leading-7 text-gray-700 dark:text-gray-300"
                            {...props}
                        />
                    ),

                    // Lists
                    ul: ({ node, ...props }) => (
                        <ul
                            className="mb-4 ml-6 list-disc space-y-2 text-gray-700 dark:text-gray-300"
                            {...props}
                        />
                    ),
                    ol: ({ node, ...props }) => (
                        <ol
                            className="mb-4 ml-6 list-decimal space-y-2 text-gray-700 dark:text-gray-300"
                            {...props}
                        />
                    ),
                    li: ({ node, ...props }) => (
                        <li
                            className="leading-7"
                            {...props}
                        />
                    ),

                    // Blockquotes
                    blockquote: ({ node, ...props }) => (
                        <blockquote
                            className="border-l-4 border-blue-500 dark:border-blue-400 pl-4 py-2 my-4 italic bg-gray-50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300"
                            {...props}
                        />
                    ),

                    // Code blocks
                    code: ({ node, inline, className, children, ...props }: any) => {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        const codeString = String(children).replace(/\n$/, '');

                        if (!inline && language) {
                            return (
                                <div className="relative my-4 rounded-lg overflow-hidden">
                                    <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
                                        <span className="text-xs font-mono text-gray-300 uppercase">
                                            {language}
                                        </span>
                                        <CopyButton text={codeString} />
                                    </div>
                                    <SyntaxHighlighter
                                        style={oneDark}
                                        language={language}
                                        PreTag="div"
                                        customStyle={{
                                            margin: 0,
                                            borderRadius: 0,
                                            fontSize: '0.875rem',
                                            lineHeight: '1.7',
                                        }}
                                        {...props}
                                    >
                                        {codeString}
                                    </SyntaxHighlighter>
                                </div>
                            );
                        }

                        // Inline code
                        return (
                            <code
                                className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-pink-600 dark:text-pink-400 font-mono text-sm border border-gray-200 dark:border-gray-700"
                                {...props}
                            >
                                {children}
                            </code>
                        );
                    },

                    // Tables
                    table: ({ node, ...props }) => (
                        <div className="my-4 overflow-x-auto">
                            <table
                                className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700"
                                {...props}
                            />
                        </div>
                    ),
                    thead: ({ node, ...props }) => (
                        <thead
                            className="bg-gray-50 dark:bg-gray-800"
                            {...props}
                        />
                    ),
                    tbody: ({ node, ...props }) => (
                        <tbody
                            className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700"
                            {...props}
                        />
                    ),
                    tr: ({ node, ...props }) => (
                        <tr
                            className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                            {...props}
                        />
                    ),
                    th: ({ node, ...props }) => (
                        <th
                            className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider"
                            {...props}
                        />
                    ),
                    td: ({ node, ...props }) => (
                        <td
                            className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300"
                            {...props}
                        />
                    ),

                    // Links
                    a: ({ node, ...props }) => (
                        <a
                            className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                            target="_blank"
                            rel="noopener noreferrer"
                            {...props}
                        />
                    ),

                    // Horizontal rules
                    hr: ({ node, ...props }) => (
                        <hr
                            className="my-6 border-gray-200 dark:border-gray-700"
                            {...props}
                        />
                    ),

                    // Images
                    img: ({ node, ...props }) => {
                        let src = props.src || '';
                        
                        // Handle image src rewriting for local files
                        if (src && !src.startsWith('http') && !src.startsWith('data:')) {
                            if (workspaceId) {
                                const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
                                
                                // Case 1: Absolute filesystem path (e.g., /home/gemtech/Desktop/thesis/workspaces/default/figures/image.png)
                                // Extract the path after '/workspaces/{workspace_id}/' or just get filename and subdirs
                                if (src.includes('/workspaces/') || src.includes('/figures/') || src.includes('/images/') || src.includes('/static/') || src.includes('/assets/')) {
                                    // Extract relative path from workspace onwards
                                    const match = src.match(/\/workspaces\/[^\/]+\/(.*)/);
                                    const relativePath = match ? match[1] : src.replace(/^.*\/(workspaces\/[^\/]+\/)?/, '');
                                    src = `${backendUrl}/api/workspace/${workspaceId}/serve/${encodeURIComponent(relativePath)}`;
                                }
                                // Case 2: Relative path without leading slash (e.g., figures/image.png)
                                else if (!src.startsWith('/')) {
                                    src = `${backendUrl}/api/workspace/${workspaceId}/serve/${encodeURIComponent(src)}`;
                                }
                                // Case 3: Absolute path starting with / but not a full filesystem path
                                // Keep as-is and let backend handle
                                else if (src.startsWith('/')) {
                                    src = `${backendUrl}/api/workspace/${workspaceId}/serve/${encodeURIComponent(src.substring(1))}`;
                                }
                            }
                        }

                        return (
                            <img
                                className="max-w-full h-auto rounded-lg my-4 border border-gray-200 dark:border-gray-700"
                                {...props}
                                src={src}
                            />
                        );
                    },

                    // Strong (bold)
                    strong: ({ node, ...props }) => (
                        <strong
                            className="font-bold text-gray-900 dark:text-gray-100"
                            {...props}
                        />
                    ),

                    // Emphasis (italic)
                    em: ({ node, ...props }) => (
                        <em
                            className="italic text-gray-700 dark:text-gray-300"
                            {...props}
                        />
                    ),

                    // Strikethrough
                    del: ({ node, ...props }) => (
                        <del
                            className="line-through text-gray-500 dark:text-gray-400"
                            {...props}
                        />
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default MarkdownRenderer;
