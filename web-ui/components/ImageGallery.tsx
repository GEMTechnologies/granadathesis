"use client";

import React, { useState, useEffect } from 'react';
import { Image as ImageIcon, Download, Edit2, Copy, Sparkles, Search, Code } from 'lucide-react';

interface ImageGalleryProps {
    workspaceId: string;
}

interface ImageItem {
    image_id: string;
    filename: string;
    url: string;
    size_bytes: number;
}

export default function ImageGallery({ workspaceId }: ImageGalleryProps) {
    const [images, setImages] = useState<ImageItem[]>([]);
    const [selectedImage, setSelectedImage] = useState<ImageItem | null>(null);
    const [loading, setLoading] = useState(false);

    // Generation form
    const [prompt, setPrompt] = useState('');
    const [method, setMethod] = useState<'auto' | 'dalle' | 'python' | 'search'>('auto');
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        loadImages();
    }, [workspaceId]);

    const loadImages = async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/image/workspace/${workspaceId}/images`);
            const data = await response.json();
            setImages(data.images || []);
        } catch (error) {
            console.error('Failed to load images:', error);
        } finally {
            setLoading(false);
        }
    };

    const generateImage = async () => {
        if (!prompt.trim()) return;

        setGenerating(true);
        try {
            const response = await fetch('/api/image/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    workspace_id: workspaceId,
                    method,
                    size: '1024x1024'
                })
            });

            const data = await response.json();

            // Reload images
            await loadImages();

            // Select new image
            setSelectedImage(data);
            setPrompt('');
        } catch (error) {
            console.error('Failed to generate image:', error);
        } finally {
            setGenerating(false);
        }
    };

    const downloadImage = (image: ImageItem) => {
        const link = document.createElement('a');
        link.href = image.url;
        link.download = image.filename;
        link.click();
    };

    return (
        <div className="h-full flex flex-col bg-white">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50">
                <h2 className="text-xl font-bold text-gray-900 flex items-center space-x-2">
                    <ImageIcon className="h-6 w-6 text-purple-600" />
                    <span>Image Studio</span>
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                    Generate, edit, and manage images with AI
                </p>
            </div>

            {/* Generation Form */}
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <div className="space-y-3">
                    <input
                        type="text"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && generateImage()}
                        placeholder="Describe the image you want to create..."
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />

                    <div className="flex items-center space-x-2">
                        <select
                            value={method}
                            onChange={(e) => setMethod(e.target.value as any)}
                            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        >
                            <option value="auto">Auto (Agent chooses)</option>
                            <option value="dalle">DALL-E (AI Art)</option>
                            <option value="python">Python (Diagrams)</option>
                            <option value="search">Search (Real Photos)</option>
                        </select>

                        <button
                            onClick={generateImage}
                            disabled={generating || !prompt.trim()}
                            className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                            {generating ? (
                                <>
                                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                    <span>Generating...</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles className="h-4 w-4" />
                                    <span>Generate Image</span>
                                </>
                            )}
                        </button>
                    </div>

                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                        <Code className="h-3 w-3" />
                        <span>Agent will choose the best method automatically</span>
                    </div>
                </div>
            </div>

            {/* Image Grid */}
            <div className="flex-1 overflow-y-auto p-6">
                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin h-8 w-8 border-4 border-purple-500 border-t-transparent rounded-full"></div>
                    </div>
                ) : images.length === 0 ? (
                    <div className="text-center py-16">
                        <ImageIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
                        <p className="text-gray-500 text-lg">No images yet</p>
                        <p className="text-gray-400 text-sm mt-2">Generate your first image above!</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {images.map((image) => (
                            <div
                                key={image.image_id}
                                className="group relative aspect-square rounded-lg overflow-hidden border-2 border-gray-200 hover:border-purple-400 cursor-pointer transition"
                                onClick={() => setSelectedImage(image)}
                            >
                                <img
                                    src={image.url}
                                    alt={image.filename}
                                    className="w-full h-full object-cover"
                                />

                                {/* Overlay on hover */}
                                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition flex items-center justify-center space-x-2">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            downloadImage(image);
                                        }}
                                        className="opacity-0 group-hover:opacity-100 p-2 bg-white rounded-full hover:bg-gray-100 transition"
                                        title="Download"
                                    >
                                        <Download className="h-4 w-4 text-gray-700" />
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setSelectedImage(image);
                                        }}
                                        className="opacity-0 group-hover:opacity-100 p-2 bg-white rounded-full hover:bg-gray-100 transition"
                                        title="Edit"
                                    >
                                        <Edit2 className="h-4 w-4 text-gray-700" />
                                    </button>
                                </div>

                                {/* File size */}
                                <div className="absolute bottom-2 right-2 px-2 py-1 bg-black bg-opacity-60 text-white text-xs rounded">
                                    {(image.size_bytes / 1024).toFixed(0)}KB
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Selected Image Modal */}
            {selectedImage && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
                    onClick={() => setSelectedImage(null)}
                >
                    <div className="max-w-4xl max-h-full" onClick={(e) => e.stopPropagation()}>
                        <img
                            src={selectedImage.url}
                            alt={selectedImage.filename}
                            className="max-w-full max-h-[80vh] object-contain rounded-lg"
                        />
                        <div className="mt-4 flex items-center justify-center space-x-2">
                            <button
                                onClick={() => downloadImage(selectedImage)}
                                className="px-4 py-2 bg-white text-gray-900 rounded-lg hover:bg-gray-100 transition flex items-center space-x-2"
                            >
                                <Download className="h-4 w-4" />
                                <span>Download</span>
                            </button>
                            <button
                                onClick={() => setSelectedImage(null)}
                                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
