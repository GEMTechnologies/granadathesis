'use client';

import React, { useState, useEffect } from 'react';
import { X, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Alert } from '../ui/alert';
import {
    ThesisParameters,
    DEFAULT_PARAMETERS,
    GenderDistribution,
    AgeDistribution,
    EducationDistribution,
    ValidationResult
} from '../../lib/thesisParameters';
import {
    validateThesisParameters,
    normalizePercentages,
    calculateCounts
} from '../../lib/parameterValidation';

interface ParameterCollectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (parameters: ThesisParameters) => void;
    workflowCommand: string;
    workflowDescription: string;
    initialParameters?: Partial<ThesisParameters>;
}

export function ParameterCollectionModal({
    isOpen,
    onClose,
    onSubmit,
    workflowCommand,
    workflowDescription,
    initialParameters
}: ParameterCollectionModalProps) {
    const [parameters, setParameters] = useState<ThesisParameters>({
        ...DEFAULT_PARAMETERS,
        ...initialParameters
    });
    const [validation, setValidation] = useState<ValidationResult>({ isValid: false, errors: [], warnings: [] });
    const [showPreview, setShowPreview] = useState(false);
    const [hasInteracted, setHasInteracted] = useState(false);
    const [hasTriedSubmit, setHasTriedSubmit] = useState(false);

    // Update parameters if initialParameters changes (e.g. modal re-opened with new info)
    useEffect(() => {
        if (isOpen && initialParameters) {
            setParameters(prev => ({
                ...prev,
                ...initialParameters
            }));
        }
    }, [isOpen, initialParameters]);

    // Validate on parameter change
    useEffect(() => {
        const result = validateThesisParameters(parameters);
        setValidation(result);
    }, [parameters]);

    if (!isOpen) return null;

    const needsDemographics = [
        'generate-full-thesis',
        'generate-chapter3',
        'generate-chapter4',
        'generate-dataset',
        'uoj_phd',
        'uoj_general'
    ].includes(workflowCommand);

    const needsStudyTools = [
        'generate-full-thesis',
        'generate-study-tools',
        'uoj_phd',
        'uoj_general'
    ].includes(workflowCommand);

    const handleSubmit = () => {
        setHasTriedSubmit(true);
        if (validation.isValid) {
            onSubmit(parameters);
            onClose();
            // Reset state for next time
            setHasInteracted(false);
            setHasTriedSubmit(false);
        }
    };

    const updateGender = (field: keyof GenderDistribution, value: number) => {
        const newGender = { ...parameters.genderDistribution, [field]: value };
        setParameters({ ...parameters, genderDistribution: newGender });
    };

    const updateAge = (field: keyof AgeDistribution, value: number) => {
        const newAge = { ...parameters.ageDistribution, [field]: value };
        setParameters({ ...parameters, ageDistribution: newAge });
    };

    const updateEducation = (field: keyof EducationDistribution, value: number) => {
        const newEducation = { ...parameters.educationDistribution, [field]: value };
        setParameters({ ...parameters, educationDistribution: newEducation });
    };

    const autoNormalizeGender = () => {
        const normalized = normalizePercentages(parameters.genderDistribution) as GenderDistribution;
        setParameters({ ...parameters, genderDistribution: normalized });
    };

    const autoNormalizeAge = () => {
        const normalized = normalizePercentages(parameters.ageDistribution) as AgeDistribution;
        setParameters({ ...parameters, ageDistribution: normalized });
    };

    const autoNormalizeEducation = () => {
        const normalized = normalizePercentages(parameters.educationDistribution) as EducationDistribution;
        setParameters({ ...parameters, educationDistribution: normalized });
    };

    const genderCounts = calculateCounts(parameters.sampleSize, parameters.genderDistribution as Record<string, number>);
    const ageCounts = calculateCounts(parameters.sampleSize, parameters.ageDistribution as Record<string, number>);
    const educationCounts = calculateCounts(parameters.sampleSize, parameters.educationDistribution as Record<string, number>);

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto m-4 p-6 bg-background">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <h2 className="text-2xl font-bold">Configure Parameters</h2>
                        <p className="text-sm text-muted-foreground mt-1">{workflowDescription}</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-muted rounded-lg transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Validation Messages - Only show if user interacted or tried to submit */}
                {(hasInteracted || hasTriedSubmit) && validation.errors.length > 0 && (
                    <Alert className="mb-4 border-destructive bg-destructive/10">
                        <AlertCircle className="w-4 h-4 text-destructive" />
                        <div className="ml-2">
                            <p className="font-semibold text-destructive">Please fix the following errors:</p>
                            <ul className="list-disc list-inside text-sm mt-1">
                                {validation.errors.map((error, i) => (
                                    <li key={i} className="text-destructive">{error}</li>
                                ))}
                            </ul>
                        </div>
                    </Alert>
                )}

                {validation.warnings.length > 0 && validation.errors.length === 0 && (
                    <Alert className="mb-4 border-yellow-500 bg-yellow-500/10">
                        <Info className="w-4 h-4 text-yellow-600" />
                        <div className="ml-2">
                            <p className="font-semibold text-yellow-600">Warnings:</p>
                            <ul className="list-disc list-inside text-sm mt-1">
                                {validation.warnings.map((warning, i) => (
                                    <li key={i} className="text-yellow-600">{warning}</li>
                                ))}
                            </ul>
                        </div>
                    </Alert>
                )}

                <div className="space-y-6">
                    {/* Basic Information */}
                    <section>
                        <h3 className="text-lg font-semibold mb-3">Basic Information</h3>
                        <div className="space-y-3">
                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    Research Topic <span className="text-destructive">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={parameters.topic}
                                    onChange={(e) => {
                                        setParameters({ ...parameters, topic: e.target.value });
                                        setHasInteracted(true);
                                    }}
                                    placeholder="e.g., Impact of Climate Change on Agriculture in South Sudan"
                                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Case Study / Location (Optional)</label>
                                <input
                                    type="text"
                                    value={parameters.caseStudy || ''}
                                    onChange={(e) => setParameters({ ...parameters, caseStudy: e.target.value })}
                                    placeholder="e.g., Juba County, South Sudan"
                                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Custom Instructions (Optional)</label>
                                <textarea
                                    value={parameters.customInstructions || ''}
                                    onChange={(e) => setParameters({ ...parameters, customInstructions: e.target.value })}
                                    placeholder="e.g., Focus on biometric data collection, use specific references if available, or suggest a particular direction for the writers..."
                                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary min-h-[80px]"
                                />
                                <p className="text-[10px] text-muted-foreground mt-1">
                                    These instructions will be passed to all AI writers to guide the generation process.
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* Demographics Section */}
                    {needsDemographics && (
                        <>
                            {/* Sample Size */}
                            <section>
                                <h3 className="text-lg font-semibold mb-3">Sample Size</h3>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="number"
                                        value={parameters.sampleSize}
                                        onChange={(e) => setParameters({ ...parameters, sampleSize: parseInt(e.target.value) || 0 })}
                                        min="30"
                                        max="1000"
                                        className="w-32 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                    <span className="text-sm text-muted-foreground">respondents (30-1000)</span>
                                </div>
                            </section>

                            {/* Gender Distribution */}
                            <section>
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-lg font-semibold">Gender Distribution</h3>
                                    <Button onClick={autoNormalizeGender} variant="outline" size="sm">
                                        Auto-Normalize to 100%
                                    </Button>
                                </div>
                                <div className="grid grid-cols-3 gap-4">
                                    {Object.entries(parameters.genderDistribution).map(([key, value]) => (
                                        <div key={key}>
                                            <label className="block text-sm font-medium mb-1 capitalize">{key}</label>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="number"
                                                    value={value}
                                                    onChange={(e) => updateGender(key as keyof GenderDistribution, parseFloat(e.target.value) || 0)}
                                                    min="0"
                                                    max="100"
                                                    step="0.1"
                                                    className="w-20 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                                />
                                                <span className="text-sm">%</span>
                                                <span className="text-xs text-muted-foreground">({genderCounts[key]} ppl)</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Age Distribution */}
                            <section>
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-lg font-semibold">Age Distribution</h3>
                                    <Button onClick={autoNormalizeAge} variant="outline" size="sm">
                                        Auto-Normalize to 100%
                                    </Button>
                                </div>
                                <div className="grid grid-cols-3 gap-4">
                                    {Object.entries(parameters.ageDistribution).map(([key, value]) => (
                                        <div key={key}>
                                            <label className="block text-sm font-medium mb-1">{key} years</label>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="number"
                                                    value={value}
                                                    onChange={(e) => updateAge(key as keyof AgeDistribution, parseFloat(e.target.value) || 0)}
                                                    min="0"
                                                    max="100"
                                                    step="0.1"
                                                    className="w-20 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                                />
                                                <span className="text-sm">%</span>
                                                <span className="text-xs text-muted-foreground">({ageCounts[key]} ppl)</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Education Distribution */}
                            <section>
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-lg font-semibold">Education Distribution</h3>
                                    <Button onClick={autoNormalizeEducation} variant="outline" size="sm">
                                        Auto-Normalize to 100%
                                    </Button>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    {Object.entries(parameters.educationDistribution).map(([key, value]) => (
                                        <div key={key}>
                                            <label className="block text-sm font-medium mb-1 capitalize">{key}</label>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="number"
                                                    value={value}
                                                    onChange={(e) => updateEducation(key as keyof EducationDistribution, parseFloat(e.target.value) || 0)}
                                                    min="0"
                                                    max="100"
                                                    step="0.1"
                                                    className="w-20 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                                />
                                                <span className="text-sm">%</span>
                                                <span className="text-xs text-muted-foreground">({educationCounts[key]} ppl)</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Response Rate */}
                            <section>
                                <h3 className="text-lg font-semibold mb-3">Response Rate</h3>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="number"
                                        value={parameters.responseRate || 90}
                                        onChange={(e) => setParameters({ ...parameters, responseRate: parseFloat(e.target.value) || 90 })}
                                        min="70"
                                        max="100"
                                        step="0.1"
                                        className="w-24 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                    <span className="text-sm">% (70-100%)</span>
                                </div>
                            </section>
                        </>
                    )}

                    {/* Study Tools Section */}
                    {needsStudyTools && (
                        <section>
                            <h3 className="text-lg font-semibold mb-3">Study Tools Configuration</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Items per Objective</label>
                                    <input
                                        type="number"
                                        value={parameters.itemsPerObjective || 3}
                                        onChange={(e) => setParameters({ ...parameters, itemsPerObjective: parseInt(e.target.value) || 3 })}
                                        min="2"
                                        max="5"
                                        className="w-24 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                    <span className="text-xs text-muted-foreground ml-2">(2-5)</span>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Likert Scale</label>
                                    <select
                                        value={parameters.likertScale || 5}
                                        onChange={(e) => setParameters({ ...parameters, likertScale: parseInt(e.target.value) as 3 | 5 | 7 })}
                                        className="w-32 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    >
                                        <option value="3">3-point</option>
                                        <option value="5">5-point</option>
                                        <option value="7">7-point</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Interview Questions</label>
                                    <input
                                        type="number"
                                        value={parameters.interviewQuestions || 10}
                                        onChange={(e) => setParameters({ ...parameters, interviewQuestions: parseInt(e.target.value) || 10 })}
                                        min="5"
                                        max="20"
                                        className="w-24 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                    <span className="text-xs text-muted-foreground ml-2">(5-20)</span>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">FGD Questions</label>
                                    <input
                                        type="number"
                                        value={parameters.fgdQuestions || 8}
                                        onChange={(e) => setParameters({ ...parameters, fgdQuestions: parseInt(e.target.value) || 8 })}
                                        min="5"
                                        max="15"
                                        className="w-24 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                    <span className="text-xs text-muted-foreground ml-2">(5-15)</span>
                                </div>
                            </div>
                        </section>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="flex items-center justify-between mt-8 pt-6 border-t">
                    <div className="flex items-center gap-2">
                        {validation.isValid && (
                            <div className="flex items-center gap-2 text-green-600">
                                <CheckCircle2 className="w-4 h-4" />
                                <span className="text-sm font-medium">All parameters valid</span>
                            </div>
                        )}
                    </div>
                    <div className="flex gap-3">
                        <Button onClick={onClose} variant="outline">
                            Cancel
                        </Button>
                        <Button
                            onClick={handleSubmit}
                            disabled={!validation.isValid}
                            className={cn(
                                "min-w-32",
                                !validation.isValid && "opacity-50 cursor-not-allowed"
                            )}
                        >
                            Generate Thesis
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
}
