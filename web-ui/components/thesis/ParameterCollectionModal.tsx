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
    workspaceId?: string;
    sessionId?: string;
}

export function ParameterCollectionModal({
    isOpen,
    onClose,
    onSubmit,
    workflowCommand,
    workflowDescription,
    initialParameters,
    workspaceId,
    sessionId
}: ParameterCollectionModalProps) {
    const [parameters, setParameters] = useState<ThesisParameters>({
        ...DEFAULT_PARAMETERS,
        ...initialParameters
    });
    const [validation, setValidation] = useState<ValidationResult>({ isValid: false, errors: [], warnings: [] });
    const [hasInteracted, setHasInteracted] = useState(false);
    const [hasTriedSubmit, setHasTriedSubmit] = useState(false);
    const [newSpecificObjective, setNewSpecificObjective] = useState('');
    const [customOutlineText, setCustomOutlineText] = useState('');
    const [customOutlineError, setCustomOutlineError] = useState<string | null>(null);
    const [outlineTemplates, setOutlineTemplates] = useState<Array<{ id: string; name: string; description?: string }>>([]);
    const [outlineTemplatesLoading, setOutlineTemplatesLoading] = useState(false);
    const [outlineTemplatesError, setOutlineTemplatesError] = useState<string | null>(null);
    const [selectedOutlineTemplate, setSelectedOutlineTemplate] = useState('');
    const [goodUploads, setGoodUploads] = useState<File[]>([]);

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const isGoodFlow = workflowCommand === 'good';

    // Update parameters if initialParameters changes (e.g. modal re-opened with new info)
    useEffect(() => {
        if (isOpen && initialParameters) {
            setParameters(prev => ({
                ...prev,
                ...initialParameters
            }));
            if (initialParameters.customOutline) {
                try {
                    setCustomOutlineText(JSON.stringify(initialParameters.customOutline, null, 2));
                    setCustomOutlineError(null);
                } catch {
                    setCustomOutlineText('');
                }
            }
        }
    }, [isOpen, initialParameters]);

    useEffect(() => {
        if (!isOpen || !isGoodFlow) return;
        const currentYear = new Date().getFullYear();
        setParameters(prev => ({
            ...prev,
            country: prev.country?.trim() ? prev.country : 'South Sudan',
            caseStudy: prev.caseStudy?.trim() ? prev.caseStudy : 'Juba, Central Equatoria State, South Sudan',
            literatureYearStart: prev.literatureYearStart ?? currentYear - 5,
            literatureYearEnd: prev.literatureYearEnd ?? currentYear
        }));
    }, [isOpen, isGoodFlow]);

    useEffect(() => {
        if (!isOpen) return;
        const loadTemplates = async () => {
            try {
                setOutlineTemplatesLoading(true);
                setOutlineTemplatesError(null);
                const response = await fetch(`${backendUrl}/api/outlines/templates`);
                if (!response.ok) {
                    throw new Error('Failed to load outline templates');
                }
                const data = await response.json();
                setOutlineTemplates(data.templates || []);
            } catch (err) {
                setOutlineTemplatesError('Could not load outline templates.');
            } finally {
                setOutlineTemplatesLoading(false);
            }
        };
        loadTemplates();
    }, [isOpen, backendUrl]);

    // Validate on parameter change
    useEffect(() => {
        if (!isOpen) return;
        if (isGoodFlow) {
            const errors: string[] = [];
            const warnings: string[] = [];
            if (!parameters.topic || parameters.topic.trim().length === 0) {
                errors.push('Title or question is required');
            }
            if (parameters.literatureYearStart && parameters.literatureYearEnd) {
                if (parameters.literatureYearStart > parameters.literatureYearEnd) {
                    errors.push('Literature year start must be less than or equal to end year');
                }
            }
            setValidation({ isValid: errors.length === 0, errors, warnings });
            return;
        }
        const result = validateThesisParameters(parameters);
        setValidation(result);
    }, [parameters, isGoodFlow, isOpen]);

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

    const handleSubmit = async () => {
        setHasTriedSubmit(true);
        if (!validation.isValid) return;

        if (isGoodFlow) {
            let uploadedMaterials: string[] = [];
            if (goodUploads.length > 0) {
                try {
                    const uploads: string[] = [];
                    for (const file of goodUploads) {
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('workspace_id', workspaceId || 'default');
                        formData.append('session_id', sessionId || 'default');
                        const response = await fetch(`${backendUrl}/api/upload`, {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        if (data?.success) {
                            uploads.push(data.relative_path || data.path || file.name);
                        }
                    }
                    uploadedMaterials = uploads;
                } catch (err) {
                    // Upload failures should not block saving the config
                    console.error('Good flow upload failed:', err);
                }
            }
            const nextParams = {
                ...parameters,
                uploadedMaterials
            };
            onSubmit(nextParams);
            onClose();
            setGoodUploads([]);
            setHasInteracted(false);
            setHasTriedSubmit(false);
            return;
        }

        onSubmit(parameters);
        onClose();
        // Reset state for next time
        setHasInteracted(false);
        setHasTriedSubmit(false);
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

    const handleOutlineTextChange = (value: string) => {
        setCustomOutlineText(value);
        if (!value.trim()) {
            setCustomOutlineError(null);
            setParameters({ ...parameters, customOutline: undefined });
            return;
        }
        try {
            const parsed = JSON.parse(value);
            setCustomOutlineError(null);
            setParameters({ ...parameters, customOutline: parsed });
        } catch (err) {
            setCustomOutlineError('Invalid JSON outline. Please fix formatting.');
        }
    };

    const handleOutlineFile = (file?: File) => {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            const text = String(reader.result || '');
            handleOutlineTextChange(text);
        };
        reader.readAsText(file);
    };

    const handleTemplateSelect = async (templateId: string) => {
        setSelectedOutlineTemplate(templateId);
        if (!templateId) return;
        try {
            const response = await fetch(`${backendUrl}/api/outlines/templates/${templateId}`);
            if (!response.ok) {
                throw new Error('Template fetch failed');
            }
            const data = await response.json();
            if (data.outline) {
                handleOutlineTextChange(JSON.stringify(data.outline, null, 2));
            }
        } catch (err) {
            setCustomOutlineError('Failed to load template. Please try again.');
        }
    };

    const genderCounts = calculateCounts(parameters.sampleSize, parameters.genderDistribution as Record<string, number>);
    const ageCounts = calculateCounts(parameters.sampleSize, parameters.ageDistribution as Record<string, number>);
    const educationCounts = calculateCounts(parameters.sampleSize, parameters.educationDistribution as Record<string, number>);
    const specificObjectives = parameters.specificObjectives || [];
    const hasObjectivesPreview = (parameters.generalObjective && parameters.generalObjective.trim().length > 0)
        || specificObjectives.length > 0;

    const addSpecificObjective = () => {
        const trimmed = newSpecificObjective.trim();
        if (!trimmed) {
            return;
        }
        if (isGoodFlow && specificObjectives.length >= 5) {
            return;
        }
        const nextObjectives = [...specificObjectives, trimmed];
        setParameters({ ...parameters, specificObjectives: nextObjectives });
        setNewSpecificObjective('');
        setHasInteracted(true);
    };

    const removeSpecificObjective = (index: number) => {
        const nextObjectives = specificObjectives.filter((_, i) => i !== index);
        setParameters({ ...parameters, specificObjectives: nextObjectives });
        setHasInteracted(true);
    };

    const handleGoodFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        if (files.length === 0) return;
        setGoodUploads(prev => [...prev, ...files]);
    };

    const removeGoodFile = (index: number) => {
        setGoodUploads(prev => prev.filter((_, i) => i !== index));
    };

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
                    {isGoodFlow ? (
                        <section>
                            <h3 className="text-lg font-semibold mb-3">Custom Love Flow Inputs</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        Title or Question <span className="text-destructive">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={parameters.topic}
                                        onChange={(e) => {
                                            setParameters({ ...parameters, topic: e.target.value });
                                            setHasInteracted(true);
                                        }}
                                        placeholder="e.g., Impact of social media on students' mental health"
                                        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Select Country</label>
                                        <input
                                            type="text"
                                            value={parameters.country || ''}
                                            onChange={(e) => setParameters({ ...parameters, country: e.target.value })}
                                            placeholder="South Sudan"
                                            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Case Study Info</label>
                                        <input
                                            type="text"
                                            value={parameters.caseStudy || ''}
                                            onChange={(e) => setParameters({ ...parameters, caseStudy: e.target.value })}
                                            placeholder="Juba, Central Equatoria State, South Sudan"
                                            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Study Type</label>
                                    <select
                                        value={parameters.studyType || ''}
                                        onChange={(e) => {
                                            const value = e.target.value;
                                            setParameters({ ...parameters, studyType: value, researchDesign: value });
                                        }}
                                        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    >
                                        <option value="">Select study type</option>
                                        <option value="quantitative">Quantitative</option>
                                        <option value="qualitative">Qualitative</option>
                                        <option value="mixed_methods">Mixed Methods</option>
                                        <option value="case_study">Case Study</option>
                                        <option value="survey">Survey</option>
                                        <option value="ethnographic">Ethnographic</option>
                                        <option value="phenomenological">Phenomenological</option>
                                        <option value="grounded_theory">Grounded Theory</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Population (Optional)</label>
                                    <input
                                        type="text"
                                        value={parameters.population || ''}
                                        onChange={(e) => setParameters({ ...parameters, population: e.target.value })}
                                        placeholder="e.g., Secondary school students in Luri Payam"
                                        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Literature Year Start</label>
                                        <input
                                            type="number"
                                            value={parameters.literatureYearStart ?? ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                setParameters({ ...parameters, literatureYearStart: Number.isNaN(value) ? undefined : value });
                                            }}
                                            placeholder="2021"
                                            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Literature Year End</label>
                                        <input
                                            type="number"
                                            value={parameters.literatureYearEnd ?? ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                setParameters({ ...parameters, literatureYearEnd: Number.isNaN(value) ? undefined : value });
                                            }}
                                            placeholder="2026"
                                            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Objectives (Optional, max 5)</label>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={newSpecificObjective}
                                            onChange={(e) => setNewSpecificObjective(e.target.value)}
                                            placeholder="Add a specific objective"
                                            className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                        <Button type="button" onClick={addSpecificObjective} disabled={specificObjectives.length >= 5}>
                                            Add
                                        </Button>
                                    </div>
                                    {specificObjectives.length > 0 && (
                                        <div className="mt-2 space-y-2">
                                            {specificObjectives.map((obj, index) => (
                                                <div key={index} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
                                                    <span>{obj}</span>
                                                    <button
                                                        type="button"
                                                        onClick={() => removeSpecificObjective(index)}
                                                        className="text-destructive"
                                                    >
                                                        Remove
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Upload Materials (Optional)</label>
                                    <input
                                        type="file"
                                        multiple
                                        onChange={handleGoodFileSelect}
                                        className="block w-full text-sm"
                                    />
                                    {goodUploads.length > 0 && (
                                        <div className="mt-2 space-y-1 text-xs">
                                            {goodUploads.map((file, index) => (
                                                <div key={`${file.name}-${index}`} className="flex items-center justify-between rounded border px-2 py-1">
                                                    <span>{file.name}</span>
                                                    <button
                                                        type="button"
                                                        onClick={() => removeGoodFile(index)}
                                                        className="text-destructive"
                                                    >
                                                        Remove
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </section>
                    ) : (
                        <>
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
                                <label className="block text-sm font-medium mb-1">Research Design (Optional)</label>
                                <select
                                    value={parameters.researchDesign || ''}
                                    onChange={(e) => {
                                        setParameters({ ...parameters, researchDesign: e.target.value });
                                        setHasInteracted(true);
                                    }}
                                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                >
                                    <option value="">Auto (based on topic)</option>
                                    <option value="quantitative">Quantitative</option>
                                    <option value="qualitative">Qualitative</option>
                                    <option value="mixed_methods">Mixed Methods</option>
                                    <option value="survey">Survey</option>
                                    <option value="case_study">Case Study</option>
                                    <option value="ethnographic">Ethnographic</option>
                                    <option value="phenomenological">Phenomenological</option>
                                    <option value="grounded_theory">Grounded Theory</option>
                                    <option value="descriptive">Descriptive</option>
                                    <option value="correlational">Correlational</option>
                                    <option value="longitudinal">Longitudinal</option>
                                    <option value="cross_sectional">Cross-sectional</option>
                                    <option value="experimental">Experimental</option>
                                    <option value="quasi_experimental">Quasi-experimental</option>
                                    <option value="clinical">Clinical</option>
                                </select>
                                <p className="text-[10px] text-muted-foreground mt-1">
                                    This choice guides the methodology narrative and study tools.
                                </p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Chapter 2 Paragraphs per Section (Optional)</label>
                                <input
                                    type="number"
                                    value={parameters.chapter2Paragraphs || ''}
                                    onChange={(e) => {
                                        const value = parseInt(e.target.value, 10);
                                        setParameters({ ...parameters, chapter2Paragraphs: Number.isNaN(value) ? undefined : value });
                                        setHasInteracted(true);
                                    }}
                                    min="1"
                                    max="12"
                                    placeholder="e.g., 3"
                                    className="w-32 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                                <p className="text-[10px] text-muted-foreground mt-1">
                                    Applies to all Chapter 2 sections unless overridden below.
                                </p>
                            </div>
                            <div className="rounded-lg border border-dashed p-3">
                                <p className="text-xs font-medium">Chapter 2 Paragraph Overrides (Optional)</p>
                                <p className="text-[10px] text-muted-foreground mb-2">
                                    Leave a field blank to keep the global Chapter 2 paragraphs value or defaults.
                                </p>
                                <div className="grid grid-cols-2 gap-3 text-xs">
                                    <label className="flex flex-col gap-1">
                                        Intro
                                        <input
                                            type="number"
                                            min="1"
                                            max="12"
                                            value={parameters.chapter2ParagraphPlan?.intro || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                const plan = { ...(parameters.chapter2ParagraphPlan || {}) };
                                                plan.intro = Number.isNaN(value) ? undefined : value;
                                                setParameters({ ...parameters, chapter2ParagraphPlan: plan });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 2"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Framework Intro
                                        <input
                                            type="number"
                                            min="1"
                                            max="12"
                                            value={parameters.chapter2ParagraphPlan?.frameworkIntro || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                const plan = { ...(parameters.chapter2ParagraphPlan || {}) };
                                                plan.frameworkIntro = Number.isNaN(value) ? undefined : value;
                                                setParameters({ ...parameters, chapter2ParagraphPlan: plan });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 2"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Theory per Objective
                                        <input
                                            type="number"
                                            min="1"
                                            max="12"
                                            value={parameters.chapter2ParagraphPlan?.theoryPerObjective || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                const plan = { ...(parameters.chapter2ParagraphPlan || {}) };
                                                plan.theoryPerObjective = Number.isNaN(value) ? undefined : value;
                                                setParameters({ ...parameters, chapter2ParagraphPlan: plan });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 5"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Conceptual Framework
                                        <input
                                            type="number"
                                            min="1"
                                            max="12"
                                            value={parameters.chapter2ParagraphPlan?.conceptualFramework || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                const plan = { ...(parameters.chapter2ParagraphPlan || {}) };
                                                plan.conceptualFramework = Number.isNaN(value) ? undefined : value;
                                                setParameters({ ...parameters, chapter2ParagraphPlan: plan });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 4"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Empirical Intro
                                        <input
                                            type="number"
                                            min="1"
                                            max="12"
                                            value={parameters.chapter2ParagraphPlan?.empiricalIntro || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                const plan = { ...(parameters.chapter2ParagraphPlan || {}) };
                                                plan.empiricalIntro = Number.isNaN(value) ? undefined : value;
                                                setParameters({ ...parameters, chapter2ParagraphPlan: plan });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 2"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Empirical per Variable
                                        <input
                                            type="number"
                                            min="1"
                                            max="12"
                                            value={parameters.chapter2ParagraphPlan?.empiricalPerVariable || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                const plan = { ...(parameters.chapter2ParagraphPlan || {}) };
                                                plan.empiricalPerVariable = Number.isNaN(value) ? undefined : value;
                                                setParameters({ ...parameters, chapter2ParagraphPlan: plan });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 8"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Research Gap
                                        <input
                                            type="number"
                                            min="1"
                                            max="12"
                                            value={parameters.chapter2ParagraphPlan?.gap || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                const plan = { ...(parameters.chapter2ParagraphPlan || {}) };
                                                plan.gap = Number.isNaN(value) ? undefined : value;
                                                setParameters({ ...parameters, chapter2ParagraphPlan: plan });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 3"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                </div>
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
                            <div>
                                <label className="block text-sm font-medium mb-1">Custom Outline (Optional JSON)</label>
                                <div className="mb-2">
                                    <label className="block text-[10px] text-muted-foreground mb-1">Template (Optional)</label>
                                    <select
                                        value={selectedOutlineTemplate}
                                        onChange={(e) => handleTemplateSelect(e.target.value)}
                                        className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary text-xs"
                                    >
                                        <option value="">Choose a template</option>
                                        {outlineTemplatesLoading && (
                                            <option value="" disabled>Loading templates...</option>
                                        )}
                                        {outlineTemplates.map((template) => (
                                            <option key={template.id} value={template.id}>
                                                {template.name}
                                            </option>
                                        ))}
                                    </select>
                                    {outlineTemplatesError && (
                                        <p className="text-[10px] text-red-600 mt-1">{outlineTemplatesError}</p>
                                    )}
                                </div>
                                <textarea
                                    value={customOutlineText}
                                    onChange={(e) => handleOutlineTextChange(e.target.value)}
                                    placeholder={`{\n  \"chapters\": [\n    {\"number\": 1, \"title\": \"Introduction\", \"sections\": [\"Background\", \"Problem\"]}\n  ]\n}`}
                                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary min-h-[120px] font-mono text-xs"
                                />
                                {customOutlineError && (
                                    <p className="text-[10px] text-red-600 mt-1">{customOutlineError}</p>
                                )}
                                <div className="mt-2 flex items-center gap-3">
                                    <input
                                        type="file"
                                        accept="application/json"
                                        onChange={(e) => handleOutlineFile(e.target.files?.[0])}
                                        className="text-xs"
                                    />
                                    <span className="text-[10px] text-muted-foreground">
                                        Upload `outline.json` or paste JSON here.
                                    </span>
                                </div>
                            </div>
                            <div className="rounded-lg border border-dashed p-3">
                                <p className="text-xs font-medium">Length Targets (Optional)</p>
                                <p className="text-[10px] text-muted-foreground mb-2">
                                    Set a target page length or word count to guide the generators.
                                </p>
                                <div className="grid grid-cols-3 gap-3 text-xs">
                                    <label className="flex flex-col gap-1">
                                        Target Pages
                                        <input
                                            type="number"
                                            min="5"
                                            max="400"
                                            value={parameters.targetPages || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                setParameters({ ...parameters, targetPages: Number.isNaN(value) ? undefined : value });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 60"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Words per Page
                                        <input
                                            type="number"
                                            min="200"
                                            max="700"
                                            value={parameters.wordsPerPage || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                setParameters({ ...parameters, wordsPerPage: Number.isNaN(value) ? undefined : value });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 300"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Target Word Count
                                        <input
                                            type="number"
                                            min="1000"
                                            max="200000"
                                            value={parameters.targetWordCount || ''}
                                            onChange={(e) => {
                                                const value = parseInt(e.target.value, 10);
                                                setParameters({ ...parameters, targetWordCount: Number.isNaN(value) ? undefined : value });
                                                setHasInteracted(true);
                                            }}
                                            placeholder="e.g., 18000"
                                            className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </label>
                                </div>
                                <p className="text-[10px] text-muted-foreground mt-2">
                                    If both pages and words per page are provided, the target word count is calculated.
                                </p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">General Objective (Optional)</label>
                                <input
                                    type="text"
                                    value={parameters.generalObjective || ''}
                                    onChange={(e) => {
                                        setParameters({ ...parameters, generalObjective: e.target.value });
                                        setHasInteracted(true);
                                    }}
                                    placeholder="e.g., To examine the drivers of conflict in Sudan and South Sudan."
                                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Specific Objectives (Optional)</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={newSpecificObjective}
                                        onChange={(e) => setNewSpecificObjective(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.preventDefault();
                                                addSpecificObjective();
                                            }
                                        }}
                                        placeholder="Type an objective and click Add"
                                        className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                    <Button type="button" variant="outline" onClick={addSpecificObjective}>
                                        Add
                                    </Button>
                                </div>
                                {specificObjectives.length > 0 && (
                                    <ul className="mt-2 space-y-2 text-sm">
                                        {specificObjectives.map((obj, i) => (
                                            <li key={`${i}-${obj}`} className="flex items-start justify-between gap-3 rounded-lg border px-3 py-2">
                                                <span>{i + 1}. {obj}</span>
                                                <button
                                                    type="button"
                                                    onClick={() => removeSpecificObjective(i)}
                                                    className="text-xs text-destructive hover:underline"
                                                >
                                                    Remove
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                                <p className="text-[10px] text-muted-foreground mt-1">
                                    If provided, these objectives will be used instead of auto-generating objectives.
                                </p>
                            </div>
                        </div>
                    </section>
                    {hasObjectivesPreview && (
                        <section>
                            <h3 className="text-lg font-semibold mb-3">Objectives Preview</h3>
                            <div className="space-y-2 text-sm">
                                <div>
                                    <p className="font-medium">General Objective</p>
                                    <p className="text-muted-foreground">
                                        {parameters.generalObjective && parameters.generalObjective.trim().length > 0
                                            ? parameters.generalObjective.trim()
                                            : 'Auto-generate general objective'}
                                    </p>
                                </div>
                                <div>
                                    <p className="font-medium">Specific Objectives</p>
                                    {specificObjectives.length > 0 ? (
                                        <ul className="list-decimal list-inside text-muted-foreground">
                                            {specificObjectives.map((obj, i) => (
                                                <li key={`${i}-${obj}`}>{obj}</li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <p className="text-muted-foreground">Auto-generate specific objectives</p>
                                    )}
                                </div>
                            </div>
                        </section>
                    )}

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
                        </>
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
