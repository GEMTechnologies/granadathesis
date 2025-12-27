'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, FileText, X } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface DocumentChatProps {
  workspaceId: string;
  docIds?: string[]; // If provided, chat with specific documents
  onClose?: () => void;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{ doc: string; page: number }>;
}

export function DocumentChat({ workspaceId, docIds, onClose }: DocumentChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch(`${backendUrl}/api/workspace/${workspaceId}/documents/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          doc_ids: docIds
        })
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          citations: data.sources
        }]);
      } else {
        const error = await response.json();
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${error.detail || 'Failed to get response'}`
        }]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error connecting to server. Please try again.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          <h2 className="font-semibold">Document Chat</h2>
          {docIds && docIds.length > 0 && (
            <Badge variant="secondary">{docIds.length} document{docIds.length !== 1 ? 's' : ''}</Badge>
          )}
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>Ask questions about your uploaded documents.</p>
            <p className="text-sm mt-2">The AI will search through the documents and cite sources with page numbers.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <Card
                className={`max-w-[80%] p-3 ${
                  msg.role === 'user'
                    ? 'bg-blue-50 border-blue-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-300">
                    <p className="text-xs font-medium mb-1">Sources:</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.citations.map((cite, i) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {cite.doc} (p. {cite.page})
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <Card className="bg-gray-50 border-gray-200 p-3">
              <p className="text-sm text-gray-500">Thinking...</p>
            </Card>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask about your documents..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}


