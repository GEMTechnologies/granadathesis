'use client';

import React, { useState, useEffect } from 'react';
import { Upload, Trash2, FileJson, Plus, Save } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface CustomAgent {
  id: string;
  name: string;
  description: string;
  uploaded_at: string;
  tools: string[];
}

export default function SettingsPage() {
  const [agents, setAgents] = useState<CustomAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/agents/custom`);
      if (response.ok) {
        const data = await response.json();
        setAgents(data.agents || []);
      }
    } catch (error) {
      console.error('Error loading agents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate JSON
    try {
      const text = await file.text();
      JSON.parse(text);
    } catch {
      alert('Invalid JSON file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${backendUrl}/api/agents/upload`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        alert('Agent uploaded successfully!');
        loadAgents();
      } else {
        const error = await response.json();
        alert(`Upload failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Error uploading agent');
    } finally {
      setUploading(false);
      // Reset input
      e.target.value = '';
    }
  };

  const handleDelete = async (agentId: string) => {
    if (!confirm('Delete this agent?')) return;

    try {
      const response = await fetch(`${backendUrl}/api/agents/custom/${agentId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        loadAgents();
      } else {
        alert('Failed to delete agent');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Error deleting agent');
    }
  };

  const downloadTemplate = () => {
    const template = {
      id: "custom-agent-1",
      name: "My Custom Agent",
      description: "A custom agent for specific tasks",
      system_prompt: "You are a helpful assistant specialized in...",
      tools: ["web_search", "read_file", "save_file"],
      temperature: 0.7,
      max_tokens: 2000
    };

    const blob = new Blob([JSON.stringify(template, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'agent-template.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>

        {/* Custom Agents Section */}
        <Card className="p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold mb-2">Custom Agents</h2>
              <p className="text-sm text-gray-600">
                Upload custom agent configurations as JSON files. Agents will be available for use in the chat.
              </p>
            </div>
            <div className="flex gap-2">
              <Button onClick={downloadTemplate} variant="outline" size="sm">
                <FileJson className="w-4 h-4 mr-2" />
                Download Template
              </Button>
              <label>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleUpload}
                  className="hidden"
                  disabled={uploading}
                />
                <Button asChild disabled={uploading}>
                  <span>
                    <Upload className="w-4 h-4 mr-2" />
                    {uploading ? 'Uploading...' : 'Upload Agent'}
                  </span>
                </Button>
              </label>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading agents...</div>
          ) : agents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileJson className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p>No custom agents uploaded yet.</p>
              <p className="text-sm mt-2">Upload a JSON file to get started.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {agents.map((agent) => (
                <Card key={agent.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold">{agent.name}</h3>
                        <Badge variant="secondary">Custom</Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{agent.description}</p>
                      <div className="flex flex-wrap gap-1 mb-2">
                        {agent.tools?.map((tool, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">
                            {tool}
                          </Badge>
                        ))}
                      </div>
                      <p className="text-xs text-gray-400">
                        Uploaded: {new Date(agent.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(agent.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </Card>

        {/* Agent JSON Format Info */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Agent JSON Format</h2>
          <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
            <pre>{`{
  "id": "unique-agent-id",
  "name": "Agent Name",
  "description": "Agent description",
  "system_prompt": "System prompt for the agent",
  "tools": ["tool1", "tool2"],
  "temperature": 0.7,
  "max_tokens": 2000
}`}</pre>
          </div>
          <p className="text-sm text-gray-600 mt-4">
            Required fields: name, description, tools, system_prompt
          </p>
        </Card>
      </div>
    </div>
  );
}


