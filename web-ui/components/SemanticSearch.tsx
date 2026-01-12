"use client";

import React, { useState, useCallback, useEffect } from 'react';
import { Search, FileText, Calendar, User, Link as LinkIcon, Sparkles } from 'lucide-react';

const debounce = <T extends (...args: any[]) => void>(fn: T, delay: number) => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    return (...args: Parameters<T>) => {
        if (timer) {
            clearTimeout(timer);
        }
        timer = setTimeout(() => fn(...args), delay);
    };
};

interface SearchResult {
    text: string;
    metadata: {
        title?: string;
        author?: string;
        document_id: string;
        chunk_index: number;
        source: string;
    };
    distance: number;
    id: string;
}

interface SemanticSearchProps {
    workspaceId: string;
}

export default function SemanticSearch({ workspaceId }: SemanticSearchProps) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [searchTime, setSearchTime] = useState<number | null>(null);

    // Debounced search for instant results
    const performSearch = useCallback(
        debounce(async (searchQuery: string) => {
            if (!searchQuery.trim()) {
                setResults([]);
                return;
            }

            setIsSearching(true);

            try {
                const response = await fetch('/api/rag/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: searchQuery,
                        workspace_id: workspaceId,
                        n_results: 10
                    })
                });

                if (!response.ok) throw new Error('Search failed');

                const data = await response.json();
                setResults(data.results || []);
                setSearchTime(data.processing_time * 1000); // Convert to ms
            } catch (error) {
                console.error('Search error:', error);
                setResults([]);
            } finally {
                setIsSearching(false);
            }
        }, 300),
        [workspaceId]
    );

    useEffect(() => {
        performSearch(query);
    }, [query, performSearch]);

    const highlightText = (text: string, query: string) => {
        if (!query) return text;

        const parts = text.split(new RegExp(`(${query})`, 'gi'));
        return parts.map((part, i) =>
            part.toLowerCase() === query.toLowerCase()
                ? <mark key={i} className="bg-yellow-200 font-medium">{part}</mark>
                : part
        );
    };

    const getRelevanceColor = (distance: number) => {
        const relevance = 1 - distance;
        if (relevance > 0.9) return 'text-green-600 bg-green-50';
        if (relevance > 0.7) return 'text-blue-600 bg-blue-50';
        if (relevance > 0.5) return 'text-purple-600 bg-purple-50';
        return 'text-gray-600 bg-gray-50';
    };

    return (
        <div className="space-y-4">
            {/* Search Bar */}
            <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    {isSearching ? (
                        <Sparkles className="h-5 w-5 text-blue-500 animate-pulse" />
                    ) : (
                        <Search className="h-5 w-5 text-gray-400" />
                    )}
                </div>
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search your documents semantically..."
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                {searchTime !== null && (
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs text-gray-500">
                        {searchTime.toFixed(0)}ms
                    </div>
                )}
            </div>

            {/* Results */}
            {results.length > 0 && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-medium text-gray-700">
                            {results.length} relevant chunks found
                        </h3>
                        <button className="text-xs text-blue-600 hover:text-blue-700">
                            Export results
                        </button>
                    </div>

                    {results.map((result, idx) => {
                        const relevance = 1 - result.distance;
                        return (
                            <div key={result.id} className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition">
                                {/* Header */}
                                <div className="flex items-start justify-between mb-2">
                                    <div className="flex items-center space-x-2">
                                        <FileText className="h-4 w-4 text-gray-400" />
                                        <span className="text-sm font-medium text-gray-900">
                                            {result.metadata.title || `Document ${result.metadata.document_id.slice(0, 8)}`}
                                        </span>
                                    </div>
                                    <div className={`px-2 py-0.5 rounded text-xs font-medium ${getRelevanceColor(result.distance)}`}>
                                        {(relevance * 100).toFixed(0)}% match
                                    </div>
                                </div>

                                {/* Content */}
                                <p className="text-sm text-gray-700 leading-relaxed mb-3">
                                    {highlightText(result.text, query)}
                                </p>

                                {/* Metadata */}
                                <div className="flex items-center space-x-4 text-xs text-gray-500">
                                    {result.metadata.author && (
                                        <div className="flex items-center space-x-1">
                                            <User className="h-3 w-3" />
                                            <span>{result.metadata.author}</span>
                                        </div>
                                    )}
                                    <div className="flex items-center space-x-1">
                                        <LinkIcon className="h-3 w-3" />
                                        <span>Chunk {result.metadata.chunk_index + 1}</span>
                                    </div>
                                    <span className="px-2 py-0.5 bg-gray-100 rounded">
                                        {result.metadata.source}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Empty State */}
            {query && results.length === 0 && !isSearching && (
                <div className="text-center py-12 text-gray-500">
                    <Search className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No results found for "{query}"</p>
                    <p className="text-sm mt-1">Try different keywords or upload more documents</p>
                </div>
            )}
        </div>
    );
}
