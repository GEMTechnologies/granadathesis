'use client';

import React, { useState, useEffect } from 'react';
import { Upload, Trash2, FileText, Image as ImageIcon, File, MessageSquare, X } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Document {
  id: string;
  filename: string;
  file_type: string;
  uploaded_at: string;
  total_pages: number;
  total_chunks: number;
}

interface DocumentManagerProps {
  workspaceId: string;
  onChatWithDocument?: (docId: string) => void;
}

export function DocumentManager({ workspaceId, onChatWithDocument }: DocumentManagerProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  useEffect(() => {
    loadDocuments();
  }, [workspaceId]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/documents`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp'];
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    
    if (!fileExt || !allowedTypes.includes(fileExt)) {
      alert(`Unsupported file type. Allowed: ${allowedTypes.join(', ')}`);
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/documents/upload`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        await loadDocuments();
      } else {
        const error = await response.json();
        alert(`Upload failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Error uploading document');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Delete this document?')) return;

    try {
      const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/documents/${docId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        loadDocuments();
      } else {
        alert('Failed to delete document');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Error deleting document');
    }
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf':
        return <FileText className="w-5 h-5 text-red-500" />;
      case 'docx':
        return <FileText className="w-5 h-5 text-blue-500" />;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'webp':
        return <ImageIcon className="w-5 h-5 text-purple-500" />;
      default:
        return <File className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-lg font-semibold">Documents</h2>
        <label>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.gif,.webp"
            onChange={handleUpload}
            className="hidden"
            disabled={uploading}
          />
          <Button asChild size="sm" disabled={uploading}>
            <span>
              <Upload className="w-4 h-4 mr-2" />
              {uploading ? 'Uploading...' : 'Upload'}
            </span>
          </Button>
        </label>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>No documents uploaded yet.</p>
            <p className="text-sm mt-2">Upload PDF, DOCX, images, or text files to chat with them.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <Card key={doc.id} className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3">
                  {getFileIcon(doc.file_type)}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium truncate">{doc.filename}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {doc.file_type.toUpperCase()}
                      </Badge>
                      {doc.total_pages > 0 && (
                        <span className="text-xs text-gray-500">
                          {doc.total_pages} page{doc.total_pages !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    {onChatWithDocument && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onChatWithDocument(doc.id)}
                        title="Chat with document"
                      >
                        <MessageSquare className="w-4 h-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(doc.id)}
                      className="text-red-600 hover:text-red-700"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


