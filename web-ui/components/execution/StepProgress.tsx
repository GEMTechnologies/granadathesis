import React from 'react';

interface Step {
    id: string;
    name: string;
    status: 'pending' | 'running' | 'done' | 'error';
    icon?: string;
}

interface StepProgressProps {
    steps: Step[];
    title?: string;
}

export const StepProgress: React.FC<StepProgressProps> = ({ steps, title = "Task Progress" }) => {
    return (
        <div className="step-progress">
            <h3 className="step-progress-title">{title}</h3>
            <div className="step-list">
                {steps.map((step, index) => (
                    <div
                        key={step.id}
                        className={`step-item step-${step.status}`}
                    >
                        {/* Checkbox */}
                        <div className="step-checkbox">
                            {step.status === 'done' && (
                                <svg viewBox="0 0 24 24" className="check-icon">
                                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" fill="currentColor" />
                                </svg>
                            )}
                            {step.status === 'running' && (
                                <div className="spinner" />
                            )}
                            {step.status === 'pending' && (
                                <div className="empty-box" />
                            )}
                            {step.status === 'error' && (
                                <svg viewBox="0 0 24 24" className="error-icon">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="currentColor" />
                                </svg>
                            )}
                        </div>

                        {/* Step info */}
                        <div className="step-content">
                            <span className="step-icon">{step.icon}</span>
                            <span className="step-name">{step.name}</span>
                        </div>

                        {/* Connection line */}
                        {index < steps.length - 1 && <div className="step-connector" />}
                    </div>
                ))}
            </div>

            <style jsx>{`
        .step-progress {
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
          border-radius: 12px;
          padding: 16px;
          border: 1px solid rgba(255,255,255,0.1);
        }
        
        .step-progress-title {
          color: #fff;
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 16px;
          padding-bottom: 8px;
          border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .step-list {
          display: flex;
          flex-direction: column;
          gap: 0;
        }
        
        .step-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 0;
          position: relative;
        }
        
        .step-checkbox {
          width: 24px;
          height: 24px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          transition: all 0.3s ease;
        }
        
        .step-pending .step-checkbox {
          border: 2px solid #4a5568;
          background: transparent;
        }
        
        .step-running .step-checkbox {
          border: 2px solid #3b82f6;
          background: rgba(59, 130, 246, 0.1);
        }
        
        .step-done .step-checkbox {
          border: 2px solid #10b981;
          background: #10b981;
        }
        
        .step-error .step-checkbox {
          border: 2px solid #ef4444;
          background: rgba(239, 68, 68, 0.1);
        }
        
        .check-icon {
          width: 16px;
          height: 16px;
          color: white;
        }
        
        .error-icon {
          width: 16px;
          height: 16px;
          color: #ef4444;
        }
        
        .spinner {
          width: 14px;
          height: 14px;
          border: 2px solid rgba(59, 130, 246, 0.3);
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .empty-box {
          width: 8px;
          height: 8px;
          border-radius: 2px;
          background: #4a5568;
        }
        
        .step-content {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
        }
        
        .step-icon {
          font-size: 16px;
        }
        
        .step-name {
          color: #e2e8f0;
          font-size: 13px;
          font-weight: 500;
        }
        
        .step-pending .step-name {
          color: #718096;
        }
        
        .step-running .step-name {
          color: #3b82f6;
        }
        
        .step-done .step-name {
          color: #10b981;
        }
        
        .step-connector {
          position: absolute;
          left: 11px;
          top: 34px;
          width: 2px;
          height: 20px;
          background: rgba(255,255,255,0.1);
        }
        
        .step-done + .step-connector,
        .step-done .step-connector {
          background: #10b981;
        }
      `}</style>
        </div>
    );
};

// Parse step data from backend agent_stream
export function parseStepsFromMetadata(metadata: any): Step[] {
    if (metadata?.steps) {
        return metadata.steps;
    }

    // Default steps
    return [
        { id: 'plan', name: 'Planning', icon: '📋', status: 'pending' },
        { id: 'search', name: 'Internet Search', icon: '🌐', status: 'pending' },
        { id: 'academic', name: 'Academic Sources', icon: '📚', status: 'pending' },
        { id: 'write', name: 'Writing', icon: '✍️', status: 'pending' },
        { id: 'verify', name: 'Verification', icon: '🔍', status: 'pending' },
    ];
}

export default StepProgress;
