'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { ProgressBar } from './ui/ProgressBar';

interface ProcessStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  startTime?: Date;
  endTime?: Date;
  description?: string;
  substeps?: ProcessStep[];
  percentage?: number;
}

interface ProcessPlannerProps {
  title?: string;
  steps: ProcessStep[];
  totalPercentage?: number;
  isCompact?: boolean;
  onlyShowActive?: boolean;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />;
    case 'running':
      return <Loader2 className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin" />;
    case 'error':
      return <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />;
    default:
      return <Clock className="w-4 h-4 text-gray-400 dark:text-gray-600" />;
  }
};

const getStatusBadgeColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800';
    case 'running':
      return 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800';
    case 'error':
      return 'bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800';
    default:
      return 'bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800';
  }
};

const getDurationText = (startTime?: Date, endTime?: Date) => {
  if (!startTime) return null;
  const end = endTime || new Date();
  const durationMs = end.getTime() - startTime.getTime();
  const seconds = Math.floor(durationMs / 1000);
  
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
};

function ProcessStepItem({ step, level = 0, isCompact = false }: { step: ProcessStep; level?: number; isCompact?: boolean }) {
  const [expanded, setExpanded] = useState(level === 0); // Auto-expand top level
  const hasSubsteps = step.substeps && step.substeps.length > 0;
  const durationText = getDurationText(step.startTime, step.endTime);

  return (
    <div className={cn('space-y-1', level > 0 && 'ml-4 pl-3 border-l border-gray-200 dark:border-gray-700')}>
      {/* Step Header */}
      <div className="group flex items-start gap-2 py-2 px-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
        {/* Expand Button */}
        {hasSubsteps && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-0.5 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
          >
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
          </button>
        )}
        {!hasSubsteps && <div className="w-5" />}

        {/* Status Icon */}
        <div className="mt-0.5 flex-shrink-0">
          {getStatusIcon(step.status)}
        </div>

        {/* Step Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className={cn(
              'font-medium',
              step.status === 'completed' && 'text-gray-700 dark:text-gray-300'
            )}>
              {step.name}
            </h4>
            <Badge variant="outline" className={cn('text-xs', getStatusBadgeColor(step.status))}>
              {step.status}
            </Badge>
            {durationText && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {durationText}
              </span>
            )}
          </div>

          {/* Progress Bar for Running Step */}
          {step.status === 'running' && step.percentage !== undefined && (
            <div className="mt-1.5">
              <ProgressBar
                percentage={step.percentage}
                showPercentage={true}
                variant="default"
                size="sm"
              />
            </div>
          )}

          {/* Description */}
          {step.description && !isCompact && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {step.description}
            </p>
          )}
        </div>
      </div>

      {/* Substeps */}
      {hasSubsteps && expanded && (
        <div className="space-y-0">
          {step.substeps?.map((substep) => (
            <ProcessStepItem
              key={substep.id}
              step={substep}
              level={level + 1}
              isCompact={isCompact}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ProcessPlanner({
  title = 'Process Timeline',
  steps,
  totalPercentage,
  isCompact = false,
  onlyShowActive = false
}: ProcessPlannerProps) {
  // Filter to show only active/running/pending steps
  const displaySteps = onlyShowActive
    ? steps.filter(s => s.status !== 'completed' && s.status !== 'error')
    : steps;

  // Calculate overall progress
  const completedCount = steps.filter(s => s.status === 'completed').length;
  const overallPercentage = totalPercentage ?? (completedCount / Math.max(steps.length, 1)) * 100;

  const runningSteps = steps.filter(s => s.status === 'running');
  const hasRunningSteps = runningSteps.length > 0;

  return (
    <Card className="bg-white dark:bg-gray-950">
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text, #161616)' }}>
            {title}
          </h3>
          
          {/* Overall Progress */}
          <ProgressBar
            percentage={overallPercentage}
            label={`Progress: ${completedCount}/${steps.length} steps`}
            showPercentage={true}
            variant={overallPercentage === 100 ? 'success' : 'default'}
            size="md"
          />
        </div>

        {/* Status Summary */}
        <div className="grid grid-cols-4 gap-2 text-xs">
          {[
            { label: 'Pending', count: steps.filter(s => s.status === 'pending').length, color: 'text-gray-500' },
            { label: 'Running', count: runningSteps.length, color: 'text-blue-600 dark:text-blue-400' },
            { label: 'Done', count: completedCount, color: 'text-green-600 dark:text-green-400' },
            { label: 'Error', count: steps.filter(s => s.status === 'error').length, color: 'text-red-600 dark:text-red-400' }
          ].map((item) => (
            <div key={item.label} className="text-center p-2 rounded-md" style={{
              backgroundColor: 'var(--color-bg, #F4F4F4)'
            }}>
              <p className={cn('font-bold', item.color)}>{item.count}</p>
              <p className="text-gray-600 dark:text-gray-400">{item.label}</p>
            </div>
          ))}
        </div>

        {/* Current Running Step Highlight */}
        {hasRunningSteps && (
          <div className="rounded-md p-2 border border-blue-200 dark:border-blue-800" style={{
            backgroundColor: 'var(--color-primary-bg, #EDF5FF)'
          }}>
            <p className="text-xs font-semibold" style={{ color: 'var(--color-primary, #0F62FE)' }}>
              Currently: {runningSteps[0].name}
              {runningSteps.length > 1 && ` (+ ${runningSteps.length - 1} more)`}
            </p>
          </div>
        )}

        {/* Steps List */}
        <div className="space-y-0 max-h-64 overflow-y-auto">
          {displaySteps.length > 0 ? (
            displaySteps.map((step) => (
              <ProcessStepItem
                key={step.id}
                step={step}
                level={0}
                isCompact={isCompact}
              />
            ))
          ) : (
            <p className="text-xs text-gray-500 text-center py-4">
              {onlyShowActive ? 'No active steps' : 'No steps available'}
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}
