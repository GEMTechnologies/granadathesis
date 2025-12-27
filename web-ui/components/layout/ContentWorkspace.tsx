'use client';

import React, { useState } from 'react';
import { 
  BarChart3, Code2, PlayCircle, Target, 
  TrendingUp, Download, Maximize2, RefreshCw,
  FileText, Layers, Activity, Sparkles,
  CheckCircle2, Clock, AlertCircle, Loader2
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface ContentTab {
  id: string;
  label: string;
  icon: React.ReactNode;
  component: React.ReactNode;
}

interface ContentWorkspaceProps {
  children?: React.ReactNode;
  defaultTab?: string;
}

export function ContentWorkspace({ children, defaultTab = 'overview' }: ContentWorkspaceProps) {
  const [activeTab, setActiveTab] = useState(defaultTab);

  const tabs: ContentTab[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <Layers className="w-4 h-4" />,
      component: children || <OverviewPanel />
    },
    {
      id: 'charts',
      label: 'Charts & Visualizations',
      icon: <BarChart3 className="w-4 h-4" />,
      component: <ChartsPanel />
    },
    {
      id: 'analysis',
      label: 'Analysis',
      icon: <TrendingUp className="w-4 h-4" />,
      component: <AnalysisPanel />
    },
    {
      id: 'code',
      label: 'Code Execution',
      icon: <Code2 className="w-4 h-4" />,
      component: <CodePanel />
    },
    {
      id: 'executions',
      label: 'Executions',
      icon: <PlayCircle className="w-4 h-4" />,
      component: <ExecutionsPanel />
    }
  ];

  const activeTabData = tabs.find(tab => tab.id === activeTab) || tabs[0];

  return (
    <div className="flex flex-col h-full">
      {/* Tab Navigation with Glassmorphism */}
      <div 
        className="flex items-center gap-1 px-4 py-3 border-b overflow-x-auto backdrop-blur-sm"
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          borderColor: 'var(--color-border, #E0E0E0)',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
        } as React.CSSProperties}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
              "hover:scale-105 active:scale-95",
              activeTab === tab.id && "shadow-md"
            )}
            style={{
              backgroundColor: activeTab === tab.id 
                ? 'var(--color-primary-bg, #EDF5FF)' 
                : 'transparent',
              color: activeTab === tab.id 
                ? 'var(--color-primary, #0F62FE)' 
                : 'var(--color-text-secondary, #525252)',
              transform: activeTab === tab.id ? 'translateY(-1px)' : 'none',
            } as React.CSSProperties}
          >
            {tab.icon}
            <span className="font-semibold">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto">
        {activeTabData.component}
      </div>
    </div>
  );
}

// Overview Panel Component
function OverviewPanel() {
  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: 'var(--color-bg, #F4F4F4)' }}>
      {/* Quick Stats with Glassmorphism */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          icon={<Target className="w-6 h-6" />}
          title="Active Objectives"
          value="5"
          change="+2 this week"
          color="blue"
        />
        <StatCard
          icon={<BarChart3 className="w-6 h-6" />}
          title="Charts Created"
          value="12"
          change="+4 today"
          color="green"
        />
        <StatCard
          icon={<Activity className="w-6 h-6" />}
          title="Executions"
          value="28"
          change="+8 this week"
          color="purple"
        />
      </div>

      {/* Recent Activity with Glassmorphism */}
      <div 
        className="rounded-xl p-6 backdrop-blur-sm transition-all hover:shadow-lg"
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          border: '1px solid var(--color-border, #E0E0E0)',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)'
        } as React.CSSProperties}
      >
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5" style={{ color: 'var(--color-primary, #0F62FE)' } as React.CSSProperties} />
          <h3 className="text-lg font-bold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          Recent Activity
        </h3>
        </div>
        <div className="space-y-3">
          <ActivityItem 
            icon={<BarChart3 className="w-4 h-4 text-blue-600" />}
            title="New chart: Research Timeline"
            time="5 minutes ago"
          />
          <ActivityItem 
            icon={<Code2 className="w-4 h-4 text-green-600" />}
            title="Code execution completed"
            time="12 minutes ago"
          />
          <ActivityItem 
            icon={<FileText className="w-4 h-4 text-purple-600" />}
            title="Analysis report generated"
            time="1 hour ago"
          />
        </div>
      </div>
    </div>
  );
}

// Charts Panel Component
function ChartsPanel() {
  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: 'var(--color-bg, #F4F4F4)' }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          Charts & Visualizations
        </h2>
        <div className="flex gap-2">
          <button
            className="p-2 rounded-lg transition-all hover:bg-blue-100 hover:scale-110"
            style={{ color: 'var(--color-primary, #0F62FE)' } as React.CSSProperties}
            title="Refresh Charts"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            className="p-2 rounded-lg transition-all hover:bg-blue-100 hover:scale-110"
            style={{ color: 'var(--color-primary, #0F62FE)' } as React.CSSProperties}
            title="Export All"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Research Progress" type="bar" />
        <ChartCard title="Data Distribution" type="pie" />
        <ChartCard title="Timeline Analysis" type="line" />
        <ChartCard title="Category Breakdown" type="donut" />
      </div>
    </div>
  );
}

// Analysis Panel Component
function AnalysisPanel() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          Data Analysis
        </h2>
        <button
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-white transition-colors"
          style={{ backgroundColor: 'var(--color-primary, #0F62FE)' } as React.CSSProperties}
        >
          <PlayCircle className="w-4 h-4" />
          Run New Analysis
        </button>
      </div>

      <div className="space-y-4">
        <AnalysisCard
          title="Statistical Summary"
          status="completed"
          results="Mean: 45.6, SD: 12.3, N: 150"
        />
        <AnalysisCard
          title="Correlation Analysis"
          status="running"
          results="Processing data..."
        />
        <AnalysisCard
          title="Regression Model"
          status="completed"
          results="R²: 0.85, p < 0.001"
        />
      </div>
    </div>
  );
}

// Code Panel Component
function CodePanel() {
  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: 'var(--color-bg, #F4F4F4)' }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          Code Execution
        </h2>
      </div>

      <div 
        className="rounded-xl p-6 space-y-4 backdrop-blur-sm transition-all hover:shadow-lg"
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          border: '1px solid var(--color-border, #E0E0E0)',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)'
        } as React.CSSProperties}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="w-5 h-5" style={{ color: 'var(--color-primary, #0F62FE)' } as React.CSSProperties} />
            <h3 className="font-bold text-lg" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
            Code Editor
          </h3>
          </div>
          <button
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-semibold transition-all hover:scale-105 hover:shadow-lg"
            style={{ 
              backgroundColor: 'var(--color-success, #24A148)',
              boxShadow: '0 2px 4px rgba(36, 161, 72, 0.3)'
            } as React.CSSProperties}
          >
            <PlayCircle className="w-4 h-4" />
            Execute
          </button>
        </div>
        
        <div 
          className="rounded-lg p-4 font-mono text-sm transition-all hover:shadow-inner"
          style={{
            backgroundColor: '#1E1E1E',
            color: '#D4D4D4',
            minHeight: '200px',
            border: '2px solid #2D2D2D',
            boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)'
          }}
        >
          <pre className="text-xs">{`import pandas as pd
import matplotlib.pyplot as plt

# Load and analyze data
df = pd.read_csv('research_data.csv')
print(df.describe())`}</pre>
        </div>

        <div 
          className="rounded-lg p-4 backdrop-blur-sm transition-all"
          style={{
            backgroundColor: 'rgba(244, 244, 244, 0.8)',
            borderLeft: '4px solid var(--color-success, #24A148)',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)'
          } as React.CSSProperties}
        >
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--color-success, #24A148)' } as React.CSSProperties} />
            <p className="text-sm font-bold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
            Output:
          </p>
          </div>
          <pre className="text-sm font-mono" style={{ color: 'var(--color-text-secondary, #525252)' } as React.CSSProperties}>
            Execution successful. Results saved.
          </pre>
        </div>
      </div>
    </div>
  );
}

// Executions Panel Component
function ExecutionsPanel() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          Execution History
        </h2>
      </div>

      <div className="space-y-3">
        <ExecutionCard
          name="Data Analysis Pipeline"
          status="completed"
          time="2 minutes ago"
          duration="1.2s"
        />
        <ExecutionCard
          name="Chart Generation"
          status="running"
          time="Just now"
          duration="0.8s"
        />
        <ExecutionCard
          name="Statistical Model"
          status="completed"
          time="15 minutes ago"
          duration="3.5s"
        />
      </div>
    </div>
  );
}

// Helper Components with Enhanced Styling
function StatCard({ icon, title, value, change, color }: any) {
  const colorMap: Record<string, string> = {
    blue: 'var(--color-primary, #0F62FE)',
    green: 'var(--color-success, #24A148)',
    purple: '#8A3FFC'
  };

  return (
    <div 
      className="rounded-xl p-6 backdrop-blur-sm transition-all hover:shadow-lg hover:scale-105 cursor-pointer"
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        border: '1px solid var(--color-border, #E0E0E0)',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)'
      } as React.CSSProperties}
    >
      <div className="flex items-center gap-3 mb-3">
        <div 
          className="p-2 rounded-lg transition-transform hover:scale-110"
          style={{ 
            backgroundColor: `${colorMap[color]}20`, 
            color: colorMap[color],
            boxShadow: `0 2px 4px ${colorMap[color]}30`
          }}
        >
          {icon}
        </div>
        <p className="text-sm font-semibold" style={{ color: 'var(--color-text-secondary, #525252)' } as React.CSSProperties}>
          {title}
        </p>
      </div>
      <p className="text-3xl font-bold mb-1" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
        {value}
      </p>
      <p className="text-sm font-medium" style={{ color: 'var(--color-text-muted, #8D8D8D)' } as React.CSSProperties}>
        {change}
      </p>
    </div>
  );
}

function ActivityItem({ icon, title, time }: any) {
  return (
    <div 
      className="flex items-center gap-3 p-3 rounded-lg transition-all hover:shadow-md cursor-pointer"
      style={{
        backgroundColor: 'transparent',
      } as React.CSSProperties}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--color-bg, #F4F4F4)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'transparent';
      }}
    >
      <div 
        className="p-2 rounded-lg transition-transform hover:scale-110"
        style={{ 
          backgroundColor: 'var(--color-bg, #F4F4F4)',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)'
        }}
      >
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-sm font-semibold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          {title}
        </p>
        <p className="text-xs font-medium" style={{ color: 'var(--color-text-muted, #8D8D8D)' } as React.CSSProperties}>
          {time}
        </p>
      </div>
    </div>
  );
}

function ChartCard({ title, type }: any) {
  return (
    <div 
      className="rounded-xl p-6 group backdrop-blur-sm transition-all hover:shadow-xl hover:scale-[1.02] cursor-pointer"
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        border: '1px solid var(--color-border, #E0E0E0)',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)'
      } as React.CSSProperties}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-lg" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          {title}
        </h3>
        <button 
          className="p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-blue-100 hover:scale-110"
          style={{ color: 'var(--color-primary, #0F62FE)' } as React.CSSProperties}
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>
      <div 
        className="rounded-lg flex items-center justify-center transition-all hover:bg-opacity-80"
        style={{
          background: 'linear-gradient(135deg, var(--color-bg, #F4F4F4) 0%, rgba(237, 245, 255, 0.5) 100%)',
          height: '200px',
          border: '1px dashed var(--color-border, #E0E0E0)'
        }}
      >
        <div className="text-center">
          <BarChart3 className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--color-text-muted, #8D8D8D)' } as React.CSSProperties} />
          <p className="text-sm font-medium" style={{ color: 'var(--color-text-muted, #8D8D8D)' } as React.CSSProperties}>
            {type.toUpperCase()} Chart
        </p>
        </div>
      </div>
    </div>
  );
}

function AnalysisCard({ title, status, results }: any) {
  const statusColors = {
    completed: 'var(--color-success, #24A148)',
    running: 'var(--color-primary, #0F62FE)',
    error: 'var(--color-danger, #DA1E28)'
  };

  const statusIcons = {
    completed: <CheckCircle2 className="w-4 h-4" />,
    running: <Loader2 className="w-4 h-4 animate-spin" />,
    error: <AlertCircle className="w-4 h-4" />
  };

  return (
    <div 
      className="rounded-xl p-6 backdrop-blur-sm transition-all hover:shadow-lg hover:scale-[1.02] cursor-pointer"
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        border: '1px solid var(--color-border, #E0E0E0)',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)'
      } as React.CSSProperties}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-bold text-lg" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
          {title}
        </h3>
        <span 
          className="px-3 py-1 rounded-full text-xs font-semibold text-white flex items-center gap-1"
          style={{ backgroundColor: statusColors[status as keyof typeof statusColors] }}
        >
          {statusIcons[status as keyof typeof statusIcons]}
          {status}
        </span>
      </div>
      <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary, #525252)' } as React.CSSProperties}>
        {results}
      </p>
    </div>
  );
}

function ExecutionCard({ name, status, time, duration }: any) {
  return (
    <div 
      className="rounded-xl p-4 flex items-center justify-between backdrop-blur-sm transition-all hover:shadow-lg hover:scale-[1.02] cursor-pointer"
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        border: '1px solid var(--color-border, #E0E0E0)',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)'
      } as React.CSSProperties}
    >
      <div className="flex items-center gap-3">
        <div 
          className={`p-2 rounded-lg transition-transform ${status === 'running' ? 'animate-pulse' : ''}`}
          style={{ 
            backgroundColor: status === 'running' 
              ? 'var(--color-primary-bg, #EDF5FF)' 
              : 'var(--color-bg, #F4F4F4)',
            boxShadow: status === 'running' 
              ? '0 2px 8px rgba(15, 98, 254, 0.3)'
              : '0 2px 4px rgba(0, 0, 0, 0.05)'
          } as React.CSSProperties}
        >
          {status === 'running' ? (
            <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--color-primary, #0F62FE)' } as React.CSSProperties} />
          ) : (
            <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--color-success, #24A148)' } as React.CSSProperties} />
          )}
        </div>
        <div>
          <p className="font-semibold" style={{ color: 'var(--color-text, #161616)' } as React.CSSProperties}>
            {name}
          </p>
          <p className="text-sm font-medium" style={{ color: 'var(--color-text-muted, #8D8D8D)' } as React.CSSProperties}>
            {time} • {duration}
          </p>
        </div>
      </div>
      <button 
        className="px-4 py-2 rounded-lg text-sm font-medium transition-all hover:scale-105"
        style={{ 
          backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
          color: 'var(--color-primary, #0F62FE)'
        } as React.CSSProperties}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'var(--color-primary, #0F62FE)';
          e.currentTarget.style.color = 'white';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'var(--color-primary-bg, #EDF5FF)';
          e.currentTarget.style.color = 'var(--color-primary, #0F62FE)';
        }}
      >
        View Details
      </button>
    </div>
  );
}
