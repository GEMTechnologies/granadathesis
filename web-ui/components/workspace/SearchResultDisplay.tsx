'use client';

import React, { useState } from 'react';
import { Globe, ExternalLink, Image as ImageIcon, Map, FileText, X, Maximize2, Download, Loader2, CheckSquare, Square, Save, Check } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SearchResult {
  title: string;
  url: string;
  content: string;
  image?: string;
}

interface SearchResultDisplayProps {
  query: string;
  results: SearchResult[];
  onClose?: () => void;
  workspaceId?: string;
}

export function SearchResultDisplay({ query, results, onClose, workspaceId = 'default' }: SearchResultDisplayProps) {
  const [expandedImage, setExpandedImage] = useState<string | null>(null);
  const [downloadingImage, setDownloadingImage] = useState<string | null>(null);
  const [selectedResults, setSelectedResults] = useState<Set<number>>(new Set());
  const [savingToMemory, setSavingToMemory] = useState(false);

  // Check if URL is a map/image service
  const isMapUrl = (url: string) => {
    return url.includes('map') || url.includes('atlas') || url.includes('gis') || url.includes('geography');
  };

  const getImageUrl = (result: SearchResult) => {
    // Try to get image from result data
    if (result.image) return result.image;
    
    // For map services, try to construct an embed URL
    if (isMapUrl(result.url)) {
      // Return a placeholder or map embed URL
      return null;
    }
    
    return null;
  };

  const toggleSelection = (index: number) => {
    setSelectedResults(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedResults(new Set(results.map((_, i) => i)));
  };

  const deselectAll = () => {
    setSelectedResults(new Set());
  };

  const handleSaveToMemory = async () => {
    if (selectedResults.size === 0) {
      alert('Please select at least one result to save');
      return;
    }

    setSavingToMemory(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const selected = Array.from(selectedResults).map(i => results[i]);
      const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/save-search-results`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          results: selected,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        alert(`✅ Saved ${selectedResults.size} results to workspace!\nFile: ${data.filename}`);
        setSelectedResults(new Set());
      } else {
        const error = await response.json();
        alert(`Failed to save: ${error.detail || 'Unknown error'}`);
      }
    } catch (error: any) {
      console.error('Error saving to memory:', error);
      alert(`Error saving to memory: ${error.message}`);
    } finally {
      setSavingToMemory(false);
    }
  };

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Globe className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">Search Results: {query}</h3>
          <span className="text-sm text-gray-500">({results.length} results)</span>
        </div>
        <div className="flex items-center gap-2">
          {selectedResults.size > 0 && (
            <>
              <span className="text-sm text-gray-600">{selectedResults.size} selected</span>
              <button
                onClick={handleSaveToMemory}
                disabled={savingToMemory}
                className="px-3 py-1.5 rounded-lg text-sm bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5"
              >
                {savingToMemory ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save to Memory
                  </>
                )}
              </button>
            </>
          )}
          <div className="flex items-center gap-1">
            <button
              onClick={selectAll}
              className="px-2 py-1 rounded text-xs border hover:bg-gray-50 transition-colors"
              title="Select all"
            >
              All
            </button>
            <button
              onClick={deselectAll}
              className="px-2 py-1 rounded text-xs border hover:bg-gray-50 transition-colors"
              title="Deselect all"
            >
              None
            </button>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-gray-100 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Results Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.map((result, index) => {
          const imageUrl = getImageUrl(result);
          
          const isSelected = selectedResults.has(index);
          
          return (
            <div
              key={index}
              className={cn(
                "relative rounded-lg border bg-white shadow-sm hover:shadow-md transition-all overflow-hidden cursor-pointer",
                isSelected && "ring-2 ring-blue-500 border-blue-500"
              )}
              onClick={() => toggleSelection(index)}
            >
              {/* Selection Checkbox */}
              <div className="absolute top-2 left-2 z-10">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleSelection(index);
                  }}
                  className={cn(
                    "p-1 rounded bg-white shadow-sm hover:bg-gray-50 transition-colors",
                    isSelected && "bg-blue-100"
                  )}
                >
                  {isSelected ? (
                    <CheckSquare className="w-5 h-5 text-blue-600" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400" />
                  )}
                </button>
              </div>
              {/* Image Section */}
              {imageUrl && (
                <div className="relative w-full h-48 bg-gray-100 overflow-hidden">
                  <img
                    src={imageUrl}
                    alt={result.title}
                    className="w-full h-full object-cover cursor-pointer hover:scale-105 transition-transform"
                    onClick={() => setExpandedImage(imageUrl)}
                    onError={(e) => {
                      // Hide image on error
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  <button
                    onClick={() => setExpandedImage(imageUrl)}
                    className="absolute top-2 right-2 p-1.5 bg-white rounded shadow hover:bg-gray-50 transition-colors"
                  >
                    <Maximize2 className="w-4 h-4 text-gray-700" />
                  </button>
                </div>
              )}
              
              {/* Map Placeholder */}
              {!imageUrl && isMapUrl(result.url) && (
                <div className="relative w-full h-48 bg-gradient-to-br from-blue-50 to-green-50 flex items-center justify-center">
                  <div className="text-center">
                    <Map className="w-12 h-12 text-blue-600 mx-auto mb-2" />
                    <p className="text-sm text-gray-600">Map Content</p>
                  </div>
                </div>
              )}

              {/* Content Section */}
              <div className="p-4">
                <h4 className="font-semibold text-base mb-2 line-clamp-2">{result.title}</h4>
                
                <p className="text-sm text-gray-600 mb-3 line-clamp-3">{result.content}</p>
                
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 hover:underline"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span className="truncate">
                    {(() => {
                      try {
                        if (result.url && result.url.trim()) {
                          return new URL(result.url).hostname;
                        }
                        return 'View Link';
                      } catch {
                        return result.url || 'View Link';
                      }
                    })()}
                  </span>
                </a>
              </div>
            </div>
          );
        })}
      </div>

      {/* Expanded Image Modal */}
      {expandedImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
          onClick={() => setExpandedImage(null)}
        >
          <div className="relative max-w-5xl max-h-full">
            <img
              src={expandedImage}
              alt="Expanded view"
              className="max-w-full max-h-[90vh] object-contain rounded"
            />
            <button
              onClick={() => setExpandedImage(null)}
              className="absolute top-4 right-4 p-2 bg-white rounded-full shadow hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

