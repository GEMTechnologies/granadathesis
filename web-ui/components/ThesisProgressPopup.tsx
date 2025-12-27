'use client';

import React, { useState, useEffect, useRef } from 'react';

interface ThesisProgressPopupProps {
  jobId: string | null;
  topic: string;
  onClose: () => void;
  backendUrl?: string;
}

interface ProgressStep {
  id: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  wordCount?: number;
}

export default function ThesisProgressPopup({ 
  jobId, 
  topic, 
  onClose,
  backendUrl = 'http://127.0.0.1:8000'
}: ThesisProgressPopupProps) {
  const [isMinimized, setIsMinimized] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [currentStatus, setCurrentStatus] = useState('Connecting...');
  const [currentAgent, setCurrentAgent] = useState('');
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<ProgressStep[]>([
    { id: 1, name: 'Chapter 1: Introduction', status: 'pending' },
    { id: 2, name: 'Chapter 2: Literature Review', status: 'pending' },
    { id: 3, name: 'Chapter 3: Methodology', status: 'pending' },
    { id: 4, name: 'Study Tools Generation', status: 'pending' },
    { id: 5, name: 'Synthetic Dataset', status: 'pending' },
    { id: 6, name: 'Chapter 4: Data Analysis', status: 'pending' },
    { id: 7, name: 'Chapter 5: Discussion', status: 'pending' },
    { id: 8, name: 'Chapter 6: Conclusion', status: 'pending' },
  ]);
  const [logs, setLogs] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Connect to SSE when jobId is available
  useEffect(() => {
    if (!jobId) return;

    const sessionId = 'default';
    const streamUrl = `${backendUrl}/api/stream/agent-actions?session_id=${sessionId}&job_id=${jobId}`;
    console.log('🔌 Progress popup connecting to:', streamUrl);

    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('✅ Progress popup SSE connected');
      setIsConnected(true);
      setCurrentStatus('Connected - Generating thesis...');
    };

    // Helper to update step status
    const updateStep = (stepNum: number, status: 'running' | 'completed' | 'error', wordCount?: number, filePath?: string) => {
      setSteps(prev => {
        const newSteps = prev.map(step => 
          step.id === stepNum 
            ? { ...step, status, wordCount: wordCount || step.wordCount }
            : step
        );
        
        // Update progress based on completed steps
        if (status === 'completed') {
          const completedCount = newSteps.filter(s => s.status === 'completed').length;
          console.log(`📊 Step ${stepNum} completed. Total completed: ${completedCount}/8`);
          setProgress(Math.round((completedCount / 8) * 100));
        }
        
        return newSteps;
      });
    };

    // Connected event
    eventSource.addEventListener('connected', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      console.log('🔗 Connected:', data);
      setIsConnected(true);
      addLog('✅ Connected to thesis generation server');
    });

    // EXPLICIT STEP EVENTS - These are the authoritative step status updates
    eventSource.addEventListener('step_started', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      console.log('🚀 Step started:', data);
      const stepNum = data.step;
      const stepName = data.name || '';
      
      if (stepNum && stepNum >= 1 && stepNum <= 8) {
        updateStep(stepNum, 'running');
        setCurrentStatus(`Working on: ${stepName}`);
        addLog(`🔄 Starting: ${stepName}`);
        
        // Calculate progress based on which step we're on
        setProgress(Math.round(((stepNum - 1) / 8) * 100));
      }
    });

    eventSource.addEventListener('step_completed', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      console.log('✅ Step completed:', data);
      const stepNum = data.step;
      const stepName = data.name || '';
      const wordCount = data.wordCount || data.word_count;
      const filePath = data.file;
      
      if (stepNum && stepNum >= 1 && stepNum <= 8) {
        updateStep(stepNum, 'completed', wordCount, filePath);
        setCurrentStatus(`Completed: ${stepName}`);
        addLog(`✅ Completed: ${stepName}${wordCount ? ` (${wordCount.toLocaleString()} words)` : ''}`);
        
        // Calculate progress based on completed step
        setProgress(Math.round((stepNum / 8) * 100));
        
        // Check if all steps are complete
        if (stepNum === 8) {
          setIsComplete(true);
          setCurrentStatus('🎉 Thesis generation complete!');
          addLog('🎉 All chapters generated successfully!');
        }
      }
    });

    // Log events - just show logs, don't detect steps (use explicit step events instead)
    eventSource.addEventListener('log', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      const message = data.message || '';
      console.log('📋 Log:', message);
      addLog(message);
    });

    // Response chunk events - just log content, don't detect steps
    eventSource.addEventListener('response_chunk', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      if (data.chunk) {
        // Just show streaming status - step completion is handled by step_completed events
        console.log('📝 Chunk received');
      }
    });

    // Agent activity
    eventSource.addEventListener('agent_activity', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setCurrentAgent(data.agent_name || data.agent || '');
      if (data.action) {
        setCurrentStatus(data.action);
      }
    });

    eventSource.addEventListener('agent_working', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setCurrentAgent(data.agent_name || data.agent || '');
      if (data.action) {
        setCurrentStatus(data.action);
      }
    });

    // Progress percentage
    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      if (data.percentage) {
        setProgress(data.percentage);
      }
      if (data.current_section) {
        setCurrentStatus(`Working on: ${data.current_section}`);
      }
    });

    // Stage completed - only mark complete if we actually finished all steps
    eventSource.addEventListener('stage_completed', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      console.log('🏁 Stage completed:', data);
      
      if (data.status === 'success') {
        // Check how many steps are actually completed before marking all complete
        setSteps(prev => {
          const actuallyCompleted = prev.filter(s => s.status === 'completed').length;
          console.log(`📊 Actually completed steps: ${actuallyCompleted}/8`);
          
          // Only mark as fully complete if we have all 8 steps OR this is a proposal (3 chapters only)
          if (actuallyCompleted >= 8) {
            setIsComplete(true);
            setProgress(100);
            setCurrentStatus('✅ Thesis generation complete!');
            addLog('🎉 All chapters generated successfully!');
            return prev.map(step => ({ ...step, status: 'completed' }));
          } else if (actuallyCompleted >= 3 && actuallyCompleted < 8) {
            // This was likely a proposal (3 chapters) - mark only those as complete
            setProgress(Math.round((actuallyCompleted / 8) * 100));
            setCurrentStatus(`✅ Proposal complete! (${actuallyCompleted}/8 steps)`);
            addLog(`📝 Proposal generated (${actuallyCompleted} chapters). Full thesis requires all 8 steps.`);
            return prev; // Don't change step statuses - keep as-is
          } else {
            // Less than 3 - something went wrong
            addLog(`⚠️ Stage completed but only ${actuallyCompleted} steps done`);
            return prev;
          }
        });
      } else if (data.status === 'error') {
        setError(data.message || 'Generation failed');
        setCurrentStatus('❌ Error occurred');
        addLog(`❌ Error: ${data.message || 'Unknown error'}`);
      }
    });

    // File created
    eventSource.addEventListener('file_created', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      addLog(`📄 File created: ${data.filename || data.path}`);
    });

    // Stage started
    eventSource.addEventListener('stage_started', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      addLog(`🚀 ${data.message || 'Stage started'}`);
    });

    // Error handler - reconnect on error
    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      setIsConnected(false);
      
      // Don't close - browser will auto-reconnect
      if (eventSource.readyState === EventSource.CLOSED) {
        setCurrentStatus('Connection lost - reconnecting...');
        addLog('⚠️ Connection lost, attempting to reconnect...');
      }
    };

    // Cleanup on unmount
    return () => {
      console.log('🔌 Closing SSE connection');
      eventSource.close();
    };
  }, [jobId, backendUrl]);

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-50), `[${timestamp}] ${message}`]); // Keep last 50 logs
  };

  if (!jobId) return null;

  // Minimized view
  if (isMinimized) {
    return (
      <div 
        className="fixed bottom-4 left-4 z-50 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl p-3 cursor-pointer hover:bg-gray-800 transition-all"
        onClick={() => setIsMinimized(false)}
      >
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${isComplete ? 'bg-green-500' : error ? 'bg-red-500' : 'bg-blue-500 animate-pulse'}`} />
          <span className="text-white text-sm font-medium">
            {isComplete ? '✅ Thesis Complete' : error ? '❌ Error' : `📚 Generating... ${progress}%`}
          </span>
          <button 
            className="text-gray-400 hover:text-white ml-2"
            onClick={(e) => { e.stopPropagation(); onClose(); }}
          >
            ✕
          </button>
        </div>
      </div>
    );
  }

  // Full view
  return (
    <div className="fixed bottom-4 left-4 z-50 w-96 max-h-[80vh] bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-3 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-white font-semibold text-sm">📚 Thesis Generation</span>
        </div>
        <div className="flex items-center gap-2">
          <button 
            className="text-gray-400 hover:text-white text-lg"
            onClick={() => setIsMinimized(true)}
            title="Minimize"
          >
            −
          </button>
          <button 
            className="text-gray-400 hover:text-white"
            onClick={onClose}
            title="Close"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-4 py-2 bg-gray-850">
        <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-500 ${isComplete ? 'bg-green-500' : error ? 'bg-red-500' : 'bg-blue-500'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Current status */}
      <div className="px-4 py-2 border-b border-gray-700">
        <div className="text-xs text-gray-400">Current Status</div>
        <div className="text-sm text-white truncate">{currentStatus}</div>
        {currentAgent && (
          <div className="text-xs text-blue-400 mt-1">🤖 {currentAgent}</div>
        )}
      </div>

      {/* Steps list */}
      <div className="flex-1 overflow-y-auto px-4 py-2 max-h-48">
        <div className="text-xs text-gray-400 mb-2">Generation Steps</div>
        <div className="space-y-1">
          {steps.map(step => (
            <div 
              key={step.id} 
              className={`flex items-center justify-between text-xs py-1 px-2 rounded ${
                step.status === 'running' ? 'bg-blue-900/30 text-blue-300' :
                step.status === 'completed' ? 'bg-green-900/20 text-green-400' :
                step.status === 'error' ? 'bg-red-900/20 text-red-400' :
                'text-gray-500'
              }`}
            >
              <div className="flex items-center gap-2">
                <span>
                  {step.status === 'pending' && '⏳'}
                  {step.status === 'running' && '🔄'}
                  {step.status === 'completed' && '✅'}
                  {step.status === 'error' && '❌'}
                </span>
                <span>{step.name}</span>
              </div>
              {step.wordCount && (
                <span className="text-gray-500">{step.wordCount.toLocaleString()} words</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Logs */}
      <div className="border-t border-gray-700 px-4 py-2 max-h-32 overflow-y-auto bg-black/30">
        <div className="text-xs text-gray-400 mb-1">Activity Log</div>
        <div className="text-xs font-mono text-gray-500 space-y-0.5">
          {logs.slice(-10).map((log, i) => (
            <div key={i} className="truncate">{log}</div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Footer */}
      {isComplete && (
        <div className="px-4 py-3 bg-green-900/30 border-t border-green-800">
          <div className="text-green-400 text-sm font-medium">
            🎉 Thesis generation complete!
          </div>
          <div className="text-green-300 text-xs mt-1">
            Check the Files panel to view your thesis.
          </div>
        </div>
      )}

      {error && (
        <div className="px-4 py-3 bg-red-900/30 border-t border-red-800">
          <div className="text-red-400 text-sm font-medium">
            ❌ Error occurred
          </div>
          <div className="text-red-300 text-xs mt-1">
            {error}
          </div>
        </div>
      )}
    </div>
  );
}
