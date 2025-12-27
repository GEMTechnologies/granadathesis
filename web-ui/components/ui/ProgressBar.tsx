'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  percentage: number;
  label?: string;
  showPercentage?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'error';
  animated?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ProgressBar({
  percentage,
  label,
  showPercentage = true,
  variant = 'default',
  animated = true,
  size = 'md'
}: ProgressBarProps) {
  // Clamp percentage between 0 and 100
  const clampedPercentage = Math.min(Math.max(percentage, 0), 100);

  const variantConfig = {
    default: 'bg-blue-600 dark:bg-blue-500',
    success: 'bg-green-600 dark:bg-green-500',
    warning: 'bg-yellow-600 dark:bg-yellow-500',
    error: 'bg-red-600 dark:bg-red-500'
  };

  const sizeConfig = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-3'
  };

  return (
    <div className="w-full">
      {label && (
        <div className="flex items-center justify-between mb-1.5">
          <p className="text-xs font-medium" style={{ color: 'var(--color-text, #161616)' }}>
            {label}
          </p>
          {showPercentage && (
            <p className="text-xs font-semibold" style={{ color: 'var(--color-text-secondary, #525252)' }}>
              {Math.round(clampedPercentage)}%
            </p>
          )}
        </div>
      )}
      
      <div
        className={cn(
          'w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden transition-all',
          sizeConfig[size]
        )}
        style={{
          backgroundColor: 'var(--color-border, #E0E0E0)'
        }}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all',
            variantConfig[variant],
            animated && 'animate-pulse'
          )}
          style={{
            width: `${clampedPercentage}%`,
            transitionDuration: '0.3s'
          }}
        />
      </div>
    </div>
  );
}

interface MultiProgressBarProps {
  steps: {
    label: string;
    percentage: number;
    variant?: 'default' | 'success' | 'warning' | 'error';
  }[];
  totalPercentage?: number;
}

export function MultiProgressBar({ steps, totalPercentage }: MultiProgressBarProps) {
  const total = totalPercentage ?? steps.reduce((sum, step) => sum + step.percentage, 0) / steps.length;

  return (
    <div className="space-y-2">
      <div className="space-y-1.5">
        {steps.map((step, idx) => (
          <ProgressBar
            key={idx}
            percentage={step.percentage}
            label={step.label}
            variant={step.variant || 'default'}
            showPercentage={true}
            size="sm"
          />
        ))}
      </div>
      
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <ProgressBar
          percentage={total}
          label="Overall Progress"
          showPercentage={true}
          variant={total === 100 ? 'success' : 'default'}
          size="md"
        />
      </div>
    </div>
  );
}
