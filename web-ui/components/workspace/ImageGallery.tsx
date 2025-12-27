'use client';

import React, { useState } from 'react';
import { Download, Maximize2, X, Image as ImageIcon, ExternalLink, Loader2, CheckSquare, Square, Check } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ImageItem {
  title: string;
  url: string;
  thumbnail?: string;
  full?: string;
  author?: string;
  author_url?: string;
  source?: string;
  source_url?: string;
  width?: number;
  height?: number;
}

interface ImageGalleryProps {
  images: ImageItem[];
  query?: string;
  workspaceId?: string;
  onImageSelect?: (image: ImageItem) => void;
}

export function ImageGallery({ images, query, workspaceId = 'default', onImageSelect }: ImageGalleryProps) {
  const [expandedImage, setExpandedImage] = useState<ImageItem | null>(null);
  const [downloadingImage, setDownloadingImage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'masonry'>('grid');
  const [selectedImages, setSelectedImages] = useState<Set<number>>(new Set());
  const [batchDownloading, setBatchDownloading] = useState(false);

  const toggleSelection = (index: number) => {
    setSelectedImages(prev => {
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
    setSelectedImages(new Set(images.map((_, i) => i)));
  };

  const deselectAll = () => {
    setSelectedImages(new Set());
  };

  const handleDownload = async (image: ImageItem) => {
    setDownloadingImage(image.url);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/download-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_url: image.full || image.url,
          filename: `${query || 'image'}_${image.title.replace(/[^a-z0-9]/gi, '_').slice(0, 30)}.jpg`
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(`✅ Image downloaded successfully!\nSaved to: ${data.path}`);
      } else {
        const error = await response.json();
        alert(`Failed to download image: ${error.detail || 'Unknown error'}`);
      }
    } catch (error: any) {
      console.error('Error downloading image:', error);
      alert(`Error downloading image: ${error.message}`);
    } finally {
      setDownloadingImage(null);
    }
  };

  const handleBatchDownload = async () => {
    if (selectedImages.size === 0) {
      alert('Please select at least one image to download');
      return;
    }

    setBatchDownloading(true);
    try {
      const selected = Array.from(selectedImages).map(i => ({
        url: images[i].full || images[i].url,
        filename: `${query || 'image'}_${images[i].title.replace(/[^a-z0-9]/gi, '_').slice(0, 30)}.jpg`
      }));

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/batch-download-images`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ images: selected }),
      });

      if (response.ok) {
        const data = await response.json();
        alert(`✅ Downloaded ${data.success} of ${data.total} images!\n${data.failed > 0 ? `${data.failed} failed.` : ''}`);
        setSelectedImages(new Set());
      } else {
        const error = await response.json();
        alert(`Failed to download images: ${error.detail || 'Unknown error'}`);
      }
    } catch (error: any) {
      console.error('Error in batch download:', error);
      alert(`Error downloading images: ${error.message}`);
    } finally {
      setBatchDownloading(false);
    }
  };

  if (!images || images.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-500">
        <ImageIcon className="w-12 h-12 mb-4 opacity-50" />
        <p className="text-lg">No images found</p>
        {query && <p className="text-sm mt-2">Try a different search query</p>}
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ImageIcon className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">
            {query ? `Images: ${query}` : `Images (${images.length})`}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {selectedImages.size > 0 && (
            <>
              <span className="text-sm text-gray-600">{selectedImages.size} selected</span>
              <button
                onClick={handleBatchDownload}
                disabled={batchDownloading}
                className="px-3 py-1.5 rounded-lg text-sm bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5"
              >
                {batchDownloading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    Download Selected
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
          <button
            onClick={() => setViewMode(viewMode === 'grid' ? 'masonry' : 'grid')}
            className="px-3 py-1.5 rounded-lg text-sm border transition-colors hover:bg-gray-50"
          >
            {viewMode === 'grid' ? 'Masonry' : 'Grid'}
          </button>
        </div>
      </div>

      {/* Images Grid */}
      <div
        className={cn(
          "gap-4",
          viewMode === 'grid'
            ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            : "columns-1 sm:columns-2 lg:columns-3 xl:columns-4"
        )}
      >
        {images.map((image, index) => {
          const isSelected = selectedImages.has(index);
          
          return (
          <div
            key={index}
            className={cn(
              "group relative rounded-lg border bg-white shadow-sm hover:shadow-lg transition-all overflow-hidden cursor-pointer",
              viewMode === 'masonry' && "break-inside-avoid mb-4",
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
            {/* Image */}
            <div className="relative w-full bg-gray-100 overflow-hidden aspect-square">
              <img
                src={image.thumbnail || image.url}
                alt={image.title}
                className={cn(
                  "w-full h-full object-cover cursor-pointer transition-transform",
                  "group-hover:scale-110"
                )}
                onClick={() => setExpandedImage(image)}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
                loading="lazy"
              />
              
              {/* Overlay Actions */}
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedImage(image);
                  }}
                  className="p-2 bg-white rounded-full shadow hover:bg-gray-50 transition-colors"
                  title="View full size"
                >
                  <Maximize2 className="w-4 h-4 text-gray-700" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownload(image);
                  }}
                  disabled={downloadingImage === image.url}
                  className="p-2 bg-white rounded-full shadow hover:bg-gray-50 transition-colors disabled:opacity-50"
                  title="Download to workspace"
                >
                  {downloadingImage === image.url ? (
                    <Loader2 className="w-4 h-4 text-gray-700 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 text-gray-700" />
                  )}
                </button>
              </div>
            </div>

            {/* Image Info */}
            <div className="p-3">
              <h4 className="font-medium text-sm mb-1 line-clamp-2">{image.title}</h4>
              <div className="flex items-center justify-between text-xs text-gray-500">
                {image.author && (
                  <span className="truncate flex-1">
                    by {image.author}
                  </span>
                )}
                {image.source && (
                  <span className="ml-2 px-2 py-0.5 bg-gray-100 rounded">
                    {image.source}
                  </span>
                )}
              </div>
              {image.source_url && (
                <a
                  href={image.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="mt-2 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 hover:underline"
                >
                  <ExternalLink className="w-3 h-3" />
                  View source
                </a>
              )}
            </div>
          </div>
          );
        })}
      </div>

      {/* Expanded Image Modal */}
      {expandedImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
          onClick={() => setExpandedImage(null)}
        >
          <div className="relative max-w-6xl max-h-full">
            <img
              src={expandedImage.full || expandedImage.url}
              alt={expandedImage.title}
              className="max-w-full max-h-[90vh] object-contain rounded"
            />
            
            {/* Image Info in Modal */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-6 text-white">
              <h3 className="text-xl font-semibold mb-2">{expandedImage.title}</h3>
              {expandedImage.author && (
                <p className="text-sm opacity-90">
                  Photo by {expandedImage.author}
                  {expandedImage.author_url && (
                    <a
                      href={expandedImage.author_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 underline hover:opacity-75"
                    >
                      View profile
                    </a>
                  )}
                </p>
              )}
              {expandedImage.source && (
                <p className="text-xs opacity-75 mt-1">Source: {expandedImage.source}</p>
              )}
            </div>
            
            {/* Action Buttons */}
            <div className="absolute top-4 right-4 flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload(expandedImage);
                }}
                disabled={downloadingImage === expandedImage.url}
                className="p-3 bg-white rounded-full shadow hover:bg-gray-100 transition-colors disabled:opacity-50"
                title="Download to workspace"
              >
                {downloadingImage === expandedImage.url ? (
                  <Loader2 className="w-5 h-5 text-gray-700 animate-spin" />
                ) : (
                  <Download className="w-5 h-5 text-gray-700" />
                )}
              </button>
              <button
                onClick={() => setExpandedImage(null)}
                className="p-3 bg-white rounded-full shadow hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-700" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

