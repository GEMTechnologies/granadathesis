'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
    BookOpen, Search, ExternalLink, Download, FileText,
    Calendar, Users, Quote, Filter, SortAsc, SortDesc,
    ChevronDown, ChevronUp, X, Star, Bookmark, Tag
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface Source {
    id: string;
    title: string;
    authors: (string | { name: string })[];
    year: number;
    type: string;
    doi?: string;
    url?: string;
    abstract?: string;
    venue?: string;
    citation_count: number;
    citation_key: string;
    added_at: string;
    file_path?: string;
    text_extracted: boolean;
}

interface SourcesPanelProps {
    workspaceId: string;
    onClose?: () => void;
    onSelectSource?: (source: Source) => void;
}

type SortField = 'title' | 'year' | 'citation_count' | 'added_at';
type SortOrder = 'asc' | 'desc';

export function SourcesPanel({ workspaceId, onClose, onSelectSource }: SourcesPanelProps) {
    const [sources, setSources] = useState<Source[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedSource, setSelectedSource] = useState<Source | null>(null);
    const [sortField, setSortField] = useState<SortField>('added_at');
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
    const [filterYear, setFilterYear] = useState<number | null>(null);
    const [showFilters, setShowFilters] = useState(false);

    // Fetch sources on mount
    useEffect(() => {
        fetchSources();
    }, [workspaceId]);

    const fetchSources = async () => {
        setLoading(true);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/sources`);
            if (response.ok) {
                const data = await response.json();
                setSources(data.sources || []);
            }
        } catch (error) {
            console.error('Failed to fetch sources:', error);
        } finally {
            setLoading(false);
        }
    };

    // Filter and sort sources
    const filteredSources = useMemo(() => {
        let result = [...sources];

        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            result = result.filter(source =>
                source.title.toLowerCase().includes(query) ||
                source.abstract?.toLowerCase().includes(query) ||
                source.authors.some(a => {
                    const authorName = typeof a === 'string' ? a : a?.name || '';
                    return authorName.toLowerCase().includes(query);
                }) ||
                source.venue?.toLowerCase().includes(query) ||
                source.citation_key.toLowerCase().includes(query)
            );
        }

        // Year filter
        if (filterYear) {
            result = result.filter(source => source.year === filterYear);
        }

        // Sort
        result.sort((a, b) => {
            let aVal: any = a[sortField];
            let bVal: any = b[sortField];

            if (sortField === 'title') {
                aVal = aVal?.toLowerCase() || '';
                bVal = bVal?.toLowerCase() || '';
            }

            if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        return result;
    }, [sources, searchQuery, filterYear, sortField, sortOrder]);

    // Get unique years for filter
    const years = useMemo(() => {
        const uniqueYears = Array.from(new Set(sources.map(s => s.year))).sort((a, b) => b - a);
        return uniqueYears;
    }, [sources]);

    const formatAuthors = (authors: (string | { name: string })[]) => {
        if (!authors || authors.length === 0) return 'Unknown';

        // Helper to get author name whether string or object
        const getName = (a: string | { name: string }) => typeof a === 'string' ? a : a?.name || 'Unknown';

        if (authors.length === 1) return getName(authors[0]);
        if (authors.length === 2) return `${getName(authors[0])} & ${getName(authors[1])}`;
        return `${getName(authors[0])} et al.`;
    };

    const handleCopyCitation = (source: Source) => {
        const citation = `${formatAuthors(source.authors)} (${source.year}). ${source.title}.`;
        navigator.clipboard.writeText(citation);
    };

    return (
        <div className="h-full flex flex-col bg-gradient-to-br from-gray-50 to-white">
            {/* Header */}
            <div className="flex-shrink-0 border-b bg-white/80 backdrop-blur-sm">
                <div className="px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                            <BookOpen className="w-4 h-4 text-white" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-gray-900">Sources Library</h2>
                            <p className="text-xs text-gray-500">{sources.length} papers saved</p>
                        </div>
                    </div>
                    {onClose && (
                        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
                            <X className="w-4 h-4" />
                        </button>
                    )}
                </div>

                {/* Search Bar */}
                <div className="px-4 pb-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search papers by title, author, keyword..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2.5 bg-gray-100 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:bg-white transition-all"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-200 rounded"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        )}
                    </div>
                </div>

                {/* Filters & Sort */}
                <div className="px-4 pb-3 flex items-center gap-2 flex-wrap">
                    <button
                        onClick={() => setShowFilters(!showFilters)}
                        className={cn(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                            showFilters ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                    >
                        <Filter className="w-3 h-3" />
                        Filters
                        {filterYear && <span className="w-2 h-2 rounded-full bg-purple-500" />}
                    </button>

                    <div className="flex items-center gap-1 bg-gray-100 rounded-lg px-1">
                        <button
                            onClick={() => setSortField('added_at')}
                            className={cn(
                                "px-2 py-1 rounded text-xs",
                                sortField === 'added_at' ? "bg-white shadow-sm" : "hover:bg-gray-50"
                            )}
                        >
                            Recent
                        </button>
                        <button
                            onClick={() => setSortField('year')}
                            className={cn(
                                "px-2 py-1 rounded text-xs",
                                sortField === 'year' ? "bg-white shadow-sm" : "hover:bg-gray-50"
                            )}
                        >
                            Year
                        </button>
                        <button
                            onClick={() => setSortField('citation_count')}
                            className={cn(
                                "px-2 py-1 rounded text-xs",
                                sortField === 'citation_count' ? "bg-white shadow-sm" : "hover:bg-gray-50"
                            )}
                        >
                            Citations
                        </button>
                    </div>

                    <button
                        onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                        className="p-1.5 rounded-lg bg-gray-100 hover:bg-gray-200"
                    >
                        {sortOrder === 'asc' ? <SortAsc className="w-3.5 h-3.5" /> : <SortDesc className="w-3.5 h-3.5" />}
                    </button>
                </div>

                {/* Filter Panel */}
                {showFilters && (
                    <div className="px-4 pb-3 flex items-center gap-2 flex-wrap border-t pt-3">
                        <span className="text-xs text-gray-500">Year:</span>
                        <button
                            onClick={() => setFilterYear(null)}
                            className={cn(
                                "px-2 py-1 rounded text-xs",
                                !filterYear ? "bg-purple-100 text-purple-700" : "bg-gray-100 hover:bg-gray-200"
                            )}
                        >
                            All
                        </button>
                        {years.slice(0, 8).map(year => (
                            <button
                                key={year}
                                onClick={() => setFilterYear(year)}
                                className={cn(
                                    "px-2 py-1 rounded text-xs",
                                    filterYear === year ? "bg-purple-100 text-purple-700" : "bg-gray-100 hover:bg-gray-200"
                                )}
                            >
                                {year}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Sources List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {loading ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
                    </div>
                ) : filteredSources.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-gray-400">
                        <BookOpen className="w-10 h-10 mb-2 opacity-30" />
                        <p className="text-sm">
                            {searchQuery ? 'No papers match your search' : 'No papers saved yet'}
                        </p>
                        <p className="text-xs mt-1">
                            {!searchQuery && 'Use "search for papers on..." to find and save papers'}
                        </p>
                    </div>
                ) : (
                    filteredSources.map(source => (
                        <div
                            key={source.id}
                            onClick={() => {
                                setSelectedSource(selectedSource?.id === source.id ? null : source);
                                onSelectSource?.(source);
                            }}
                            className={cn(
                                "bg-white rounded-xl border p-4 cursor-pointer transition-all hover:shadow-md",
                                selectedSource?.id === source.id ? "ring-2 ring-purple-500 shadow-md" : "hover:border-purple-200"
                            )}
                        >
                            {/* Paper Header */}
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-medium text-gray-900 text-sm leading-tight line-clamp-2">
                                        {source.title}
                                    </h3>
                                    <div className="flex items-center gap-2 mt-1.5 text-xs text-gray-500">
                                        <span className="flex items-center gap-1">
                                            <Users className="w-3 h-3" />
                                            {formatAuthors(source.authors)}
                                        </span>
                                        <span>•</span>
                                        <span className="flex items-center gap-1">
                                            <Calendar className="w-3 h-3" />
                                            {source.year}
                                        </span>
                                        {source.citation_count > 0 && (
                                            <>
                                                <span>•</span>
                                                <span className="flex items-center gap-1">
                                                    <Quote className="w-3 h-3" />
                                                    {source.citation_count} citations
                                                </span>
                                            </>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-1">
                                    {source.file_path && (
                                        <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium">
                                            PDF
                                        </span>
                                    )}
                                    {source.text_extracted && (
                                        <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-medium">
                                            Text
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Venue */}
                            {source.venue && (
                                <div className="mt-2 text-xs text-gray-500 truncate">
                                    📍 {source.venue}
                                </div>
                            )}

                            {/* Citation Key */}
                            <div className="mt-2 flex items-center gap-2">
                                <code className="px-2 py-0.5 bg-gray-100 rounded text-xs font-mono text-purple-600">
                                    @{source.citation_key}
                                </code>
                            </div>

                            {/* Expanded Details */}
                            {selectedSource?.id === source.id && (
                                <div className="mt-4 pt-4 border-t space-y-4">
                                    {/* Abstract */}
                                    {source.abstract && (
                                        <div>
                                            <h4 className="text-xs font-medium text-gray-700 mb-1">Abstract</h4>
                                            <p className="text-xs text-gray-600 leading-relaxed line-clamp-4">
                                                {source.abstract}
                                            </p>
                                        </div>
                                    )}

                                    {/* Real URL Display */}
                                    {source.url && (
                                        <div className="bg-gray-50 rounded-lg p-2">
                                            <h4 className="text-xs font-medium text-gray-700 mb-1">📎 Paper URL</h4>
                                            <a
                                                href={source.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-xs text-blue-600 hover:underline break-all"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                {source.url}
                                            </a>
                                        </div>
                                    )}

                                    {/* DOI with Link */}
                                    {source.doi && (
                                        <div className="bg-gray-50 rounded-lg p-2">
                                            <h4 className="text-xs font-medium text-gray-700 mb-1">🔗 DOI</h4>
                                            <a
                                                href={`https://doi.org/${source.doi}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-xs text-purple-600 hover:underline"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                {source.doi}
                                            </a>
                                        </div>
                                    )}

                                    {/* Primary Actions Row */}
                                    <div className="flex flex-wrap items-center gap-2">
                                        {source.url && (
                                            <a
                                                href={source.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                onClick={(e) => e.stopPropagation()}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg text-xs font-medium hover:bg-purple-200 transition-colors"
                                            >
                                                <ExternalLink className="w-3 h-3" />
                                                Open Paper
                                            </a>
                                        )}

                                        {source.file_path && (
                                            <a
                                                href={`${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/workspace/${workspaceId}/serve/${source.file_path}`}
                                                download
                                                onClick={(e) => e.stopPropagation()}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-medium hover:bg-green-200 transition-colors"
                                            >
                                                <Download className="w-3 h-3" />
                                                Download PDF
                                            </a>
                                        )}

                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleCopyCitation(source);
                                            }}
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200 transition-colors"
                                        >
                                            <Quote className="w-3 h-3" />
                                            Copy Citation
                                        </button>
                                    </div>

                                    {/* Insert & Research Actions */}
                                    <div className="border-t pt-3">
                                        <h4 className="text-xs font-medium text-gray-600 mb-2">📝 Insert & Cite</h4>
                                        <div className="flex flex-wrap gap-2">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    const citation = `(${formatAuthors(source.authors)}, ${source.year})`;
                                                    navigator.clipboard.writeText(citation);
                                                    alert('In-text citation copied!');
                                                }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 text-blue-700 rounded text-xs hover:bg-blue-100 transition-colors"
                                            >
                                                📋 In-text Citation
                                            </button>

                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    const bibtex = `@article{${source.citation_key},
  title={${source.title}},
  author={${source.authors.map(a => typeof a === 'string' ? a : a?.name).join(' and ')}},
  year={${source.year}},
  doi={${source.doi || 'N/A'}}
}`;
                                                    navigator.clipboard.writeText(bibtex);
                                                    alert('BibTeX copied!');
                                                }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 bg-orange-50 text-orange-700 rounded text-xs hover:bg-orange-100 transition-colors"
                                            >
                                                📚 BibTeX
                                            </button>

                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    // Dispatch event to insert citation into active document
                                                    window.dispatchEvent(new CustomEvent('insert-citation', {
                                                        detail: { source, workspaceId }
                                                    }));
                                                    alert('Citation will be inserted at cursor position');
                                                }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded text-xs hover:bg-indigo-100 transition-colors"
                                            >
                                                ➕ Insert into Paper
                                            </button>
                                        </div>
                                    </div>

                                    {/* Research Tools */}
                                    <div className="border-t pt-3">
                                        <h4 className="text-xs font-medium text-gray-600 mb-2">🔬 Research Tools</h4>
                                        <div className="flex flex-wrap gap-2">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    // Trigger literature mapping
                                                    window.dispatchEvent(new CustomEvent('generate-literature-map', {
                                                        detail: { sources: filteredSources.slice(0, 20), workspaceId }
                                                    }));
                                                    alert('Literature map generation started. Check the chat for results.');
                                                }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 bg-teal-50 text-teal-700 rounded text-xs hover:bg-teal-100 transition-colors"
                                            >
                                                🗺️ Literature Map
                                            </button>

                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    // Trigger mind map generation
                                                    window.dispatchEvent(new CustomEvent('generate-mind-map', {
                                                        detail: { source, workspaceId }
                                                    }));
                                                    alert('Mind map generation started. Check the chat for results.');
                                                }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 bg-pink-50 text-pink-700 rounded text-xs hover:bg-pink-100 transition-colors"
                                            >
                                                🧠 Mind Map
                                            </button>

                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    // Find related papers
                                                    window.dispatchEvent(new CustomEvent('find-related-papers', {
                                                        detail: { source, workspaceId }
                                                    }));
                                                    alert('Searching for related papers...');
                                                }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 text-amber-700 rounded text-xs hover:bg-amber-100 transition-colors"
                                            >
                                                🔍 Find Related
                                            </button>

                                            {source.doi && (
                                                <a
                                                    href={`https://www.semanticscholar.org/search?q=${encodeURIComponent(source.title)}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 text-gray-700 rounded text-xs hover:bg-gray-100 transition-colors"
                                                >
                                                    🔗 Semantic Scholar
                                                </a>
                                            )}
                                        </div>
                                    </div>

                                    {/* Full Paper Download (if available) */}
                                    {!source.file_path && source.url && (
                                        <div className="border-t pt-3">
                                            <button
                                                onClick={async (e) => {
                                                    e.stopPropagation();
                                                    try {
                                                        alert('Attempting to download full paper. This may take a moment...');
                                                        const response = await fetch(
                                                            `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/workspace/${workspaceId}/sources/download-pdf`,
                                                            {
                                                                method: 'POST',
                                                                headers: { 'Content-Type': 'application/json' },
                                                                body: JSON.stringify({ source_id: source.id, url: source.url })
                                                            }
                                                        );
                                                        if (response.ok) {
                                                            alert('PDF downloaded! Refresh to see it.');
                                                            fetchSources();
                                                        } else {
                                                            alert('Could not download PDF. It may require institutional access.');
                                                        }
                                                    } catch (err) {
                                                        alert('Download failed. The paper may not be freely available.');
                                                    }
                                                }}
                                                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg text-xs font-medium hover:from-green-600 hover:to-emerald-600 transition-all"
                                            >
                                                <Download className="w-4 h-4" />
                                                Download Full Paper (if available)
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Footer Stats */}
            <div className="flex-shrink-0 px-4 py-2 bg-gray-50 border-t text-xs text-gray-500 flex items-center justify-between">
                <span>
                    {filteredSources.length} of {sources.length} papers
                    {searchQuery && ` matching "${searchQuery}"`}
                </span>
                <button
                    onClick={fetchSources}
                    className="text-purple-600 hover:text-purple-700 font-medium"
                >
                    Refresh
                </button>
            </div>
        </div>
    );
}

export default SourcesPanel;
