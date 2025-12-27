'use client';

import React, { useState, useMemo } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import {
    Loader2,
    CheckCircle2,
    Circle,
    FileText,
    ChevronRight,
    ChevronDown,
    Clock
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TaskNode {
    task_id: string;
    task_name: string;
    task_status?: string;
    task_summary?: string;
    mode: 'PLANNING' | 'EXECUTION' | 'VERIFICATION';
    progress: number;
    status: 'pending' | 'running' | 'completed' | 'error';
    parent_task_id?: string;
    children: TaskNode[];
    timestamp: string;
    content?: string; // Markdown content
}

interface TaskProgressPanelProps {
    agentName?: string;
    documentTitle?: string;
    tasks: TaskNode[];
    currentFile?: string;
    totalSteps?: number;
    completedSteps?: number;
}

const ModeBadge = ({ mode }: { mode: string }) => {
    const config = {
        PLANNING: {
            bg: 'bg-blue-50 dark:bg-blue-950',
            text: 'text-blue-700 dark:text-blue-300',
            border: 'border-blue-200 dark:border-blue-800',
        },
        EXECUTION: {
            bg: 'bg-green-50 dark:bg-green-950',
            text: 'text-green-700 dark:text-green-300',
            border: 'border-green-200 dark:border-green-800',
        },
        VERIFICATION: {
            bg: 'bg-purple-50 dark:bg-purple-950',
            text: 'text-purple-700 dark:text-purple-300',
            border: 'border-purple-200 dark:border-purple-800',
        },
    };

    const { bg, text, border } = config[mode as keyof typeof config] || config.PLANNING;

    return (
        <Badge
            variant="outline"
            className={cn(
                'text-xs font-medium px-2 py-0.5',
                bg, text, border
            )}
        >
            {mode}
        </Badge>
    );
};

const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
        case 'completed':
            return <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />;
        case 'running':
            return <Loader2 className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin flex-shrink-0" />;
        case 'error':
            return <Circle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />;
        default:
            return <Circle className="w-4 h-4 text-gray-400 dark:text-gray-600 flex-shrink-0" />;
    }
};

const TaskItem = ({
    task,
    level = 0,
    index,
    showContent = false
}: {
    task: TaskNode;
    level?: number;
    index: number;
    showContent?: boolean;
}) => {
    const [expanded, setExpanded] = useState(true);
    const hasChildren = task.children && task.children.length > 0;
    const hasContent = task.content && task.content.length > 0;

    // Generate section number (e.g., "1.1", "2.3.1")
    const sectionNumber = `${index + 1}`;

    return (
        <div className={cn(
            'space-y-1',
            level > 0 && 'ml-4 pl-3 border-l border-gray-200 dark:border-gray-700'
        )}>
            {/* Task Header */}
            <div className="group flex items-start gap-2 py-1.5 px-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                {/* Expand/Collapse Button */}
                {(hasChildren || hasContent) && (
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="mt-0.5 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                    >
                        {expanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
                        ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
                        )}
                    </button>
                )}

                {/* Status Icon */}
                <div className="mt-0.5">
                    <StatusIcon status={task.status} />
                </div>

                {/* Task Content */}
                <div className="flex-1 min-w-0 space-y-1">
                    {/* Task Title Row */}
                    <div className="flex items-center gap-2 flex-wrap">
                        {level === 0 && (
                            <span className="text-xs font-bold text-blue-600 dark:text-blue-400 font-mono">
                                #{sectionNumber}
                            </span>
                        )}
                        <h4 className={cn(
                            'font-medium truncate',
                            level === 0 ? 'text-sm' : 'text-xs',
                            task.status === 'completed' && 'text-gray-700 dark:text-gray-300'
                        )}>
                            {task.task_name}
                        </h4>
                        <ModeBadge mode={task.mode} />
                    </div>

                    {/* Task Status */}
                    {task.task_status && task.status === 'running' && (
                        <div className="flex items-center gap-1.5">
                            <Clock className="w-3 h-3 text-gray-400" />
                            <p className="text-xs text-gray-600 dark:text-gray-400">
                                {task.task_status}
                            </p>
                        </div>
                    )}

                    {/* Task Summary */}
                    {task.task_summary && task.status === 'completed' && (
                        <p className="text-xs text-gray-600 dark:text-gray-400 italic leading-relaxed">
                            {task.task_summary}
                        </p>
                    )}

                    {/* Progress Bar */}
                    {task.status === 'running' && task.progress > 0 && task.progress < 1 && (
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                            <div
                                className="bg-blue-600 dark:bg-blue-400 h-full transition-all duration-300 ease-out"
                                style={{ width: `${task.progress * 100}%` }}
                            />
                        </div>
                    )}
                </div>
            </div>

            {/* Content Preview */}
            {expanded && hasContent && showContent && (
                <div className="ml-9 mt-2 p-3 bg-gray-50 dark:bg-gray-800/30 rounded-md border border-gray-200 dark:border-gray-700">
                    <div className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                        {task.content.split('\n').slice(0, 5).map((line, i) => (
                            <p key={i} className="mb-1">{line}</p>
                        ))}
                        {task.content.split('\n').length > 5 && (
                            <p className="text-gray-500 italic">...</p>
                        )}
                    </div>
                </div>
            )}

            {/* Child Tasks */}
            {expanded && hasChildren && (
                <div className="space-y-1 mt-1">
                    {task.children.map((child, idx) => (
                        <TaskItem
                            key={child.task_id}
                            task={child}
                            level={level + 1}
                            index={idx}
                            showContent={showContent}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export const TaskProgressPanel: React.FC<TaskProgressPanelProps> = ({
    agentName = "Agent's Computer",
    documentTitle = "Task Progress Document",
    tasks,
    currentFile,
    totalSteps = 0,
    completedSteps = 0
}) => {
    // Build task tree from flat list
    const taskTree = useMemo(() => {
        const taskMap = new Map<string, TaskNode>();
        const rootTasks: TaskNode[] = [];

        // First pass: create map
        tasks.forEach(task => {
            taskMap.set(task.task_id, { ...task, children: [] });
        });

        // Second pass: build hierarchy
        tasks.forEach(task => {
            const node = taskMap.get(task.task_id)!;
            if (task.parent_task_id) {
                const parent = taskMap.get(task.parent_task_id);
                if (parent) {
                    parent.children.push(node);
                } else {
                    rootTasks.push(node);
                }
            } else {
                rootTasks.push(node);
            }
        });

        return rootTasks;
    }, [tasks]);

    if (tasks.length === 0) {
        return null;
    }

    const hasActiveTask = tasks.some(t => t.status === 'running');
    const completionPercentage = totalSteps > 0
        ? Math.round((completedSteps / totalSteps) * 100)
        : 0;

    return (
        <Card className="h-full flex flex-col shadow-lg border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
                <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            <FileText className="w-4 h-4 text-gray-600 dark:text-gray-400 flex-shrink-0" />
                            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">
                                {agentName}
                            </h3>
                        </div>
                        {currentFile && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate font-mono">
                                {currentFile}
                            </p>
                        )}
                    </div>

                    {hasActiveTask && (
                        <Loader2 className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin flex-shrink-0 mt-0.5" />
                    )}
                </div>
            </div>

            {/* Document Title */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
                <h2 className="text-base font-bold text-gray-900 dark:text-gray-100 leading-tight">
                    {documentTitle}
                </h2>
            </div>

            {/* Task List */}
            <ScrollArea className="flex-1">
                <div className="px-4 py-3 space-y-2">
                    {taskTree.map((task, idx) => (
                        <TaskItem
                            key={task.task_id}
                            task={task}
                            index={idx}
                            showContent={true}
                        />
                    ))}
                </div>
            </ScrollArea>

            {/* Footer - Progress Indicator */}
            {totalSteps > 0 && (
                <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-600 dark:text-gray-400 font-medium">
                            Progress
                        </span>
                        <div className="flex items-center gap-2">
                            <span className="font-mono text-gray-700 dark:text-gray-300">
                                {completedSteps}/{totalSteps}
                            </span>
                            <span className="text-gray-500">
                                ({completionPercentage}%)
                            </span>
                        </div>
                    </div>
                    <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-blue-600 dark:bg-blue-400 h-full transition-all duration-500 ease-out"
                            style={{ width: `${completionPercentage}%` }}
                        />
                    </div>
                </div>
            )}
        </Card>
    );
};

export default TaskProgressPanel;
