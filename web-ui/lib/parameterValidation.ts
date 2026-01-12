// Parameter validation utilities

import {
    ThesisParameters,
    GenderDistribution,
    AgeDistribution,
    EducationDistribution,
    ValidationResult,
    DEFAULT_CONSTRAINTS
} from './thesisParameters';

/**
 * Validate that percentages in a distribution sum to 100
 */
export function validatePercentageSum(
    distribution: Record<string, number>,
    distributionName: string
): { isValid: boolean; error?: string } {
    const sum = Object.values(distribution).reduce((a, b) => a + b, 0);
    const tolerance = 0.1; // Allow 0.1% tolerance for rounding

    if (Math.abs(sum - 100) > tolerance) {
        return {
            isValid: false,
            error: `${distributionName} must sum to 100% (currently ${sum.toFixed(1)}%)`
        };
    }

    return { isValid: true };
}

/**
 * Validate numeric range
 */
export function validateRange(
    value: number,
    min: number,
    max: number,
    fieldName: string
): { isValid: boolean; error?: string } {
    if (value < min || value > max) {
        return {
            isValid: false,
            error: `${fieldName} must be between ${min} and ${max} (currently ${value})`
        };
    }

    return { isValid: true };
}

/**
 * Validate all thesis parameters
 */
export function validateThesisParameters(params: ThesisParameters): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Required fields
    if (!params.topic || params.topic.trim().length === 0) {
        errors.push('Research topic is required');
    }

    if (params.topic && params.topic.trim().length < 10) {
        warnings.push('Research topic seems very short. Consider providing more detail.');
    }

    if (params.generalObjective && params.generalObjective.trim().length < 10) {
        warnings.push('General objective seems very short. Consider providing more detail.');
    }

    if (params.specificObjectives && params.specificObjectives.length > 0) {
        if (params.specificObjectives.length === 1) {
            warnings.push('Only one specific objective provided. Consider adding more.');
        }
    }

    // Sample size
    const sampleSizeValidation = validateRange(
        params.sampleSize,
        DEFAULT_CONSTRAINTS.sampleSize.min,
        DEFAULT_CONSTRAINTS.sampleSize.max,
        'Sample size'
    );
    if (!sampleSizeValidation.isValid) {
        errors.push(sampleSizeValidation.error!);
    }

    // Gender distribution
    const genderValidation = validatePercentageSum(
        params.genderDistribution,
        'Gender distribution'
    );
    if (!genderValidation.isValid) {
        errors.push(genderValidation.error!);
    }

    // Check for unrealistic gender distributions
    if (params.genderDistribution.male === 100 || params.genderDistribution.female === 100) {
        warnings.push('100% single gender distribution may not be realistic for most studies');
    }

    // Age distribution
    const ageValidation = validatePercentageSum(
        params.ageDistribution,
        'Age distribution'
    );
    if (!ageValidation.isValid) {
        errors.push(ageValidation.error!);
    }

    // Education distribution
    const educationValidation = validatePercentageSum(
        params.educationDistribution,
        'Education distribution'
    );
    if (!educationValidation.isValid) {
        errors.push(educationValidation.error!);
    }

    // Response rate
    if (params.responseRate !== undefined) {
        const responseRateValidation = validateRange(
            params.responseRate,
            DEFAULT_CONSTRAINTS.responseRate.min,
            DEFAULT_CONSTRAINTS.responseRate.max,
            'Response rate'
        );
        if (!responseRateValidation.isValid) {
            errors.push(responseRateValidation.error!);
        }
    }

    // Items per objective
    if (params.itemsPerObjective !== undefined) {
        const itemsValidation = validateRange(
            params.itemsPerObjective,
            DEFAULT_CONSTRAINTS.itemsPerObjective.min,
            DEFAULT_CONSTRAINTS.itemsPerObjective.max,
            'Items per objective'
        );
        if (!itemsValidation.isValid) {
            errors.push(itemsValidation.error!);
        }
    }

    // Interview questions
    if (params.interviewQuestions !== undefined) {
        const interviewValidation = validateRange(
            params.interviewQuestions,
            DEFAULT_CONSTRAINTS.interviewQuestions.min,
            DEFAULT_CONSTRAINTS.interviewQuestions.max,
            'Interview questions'
        );
        if (!interviewValidation.isValid) {
            errors.push(interviewValidation.error!);
        }
    }

    // FGD questions
    if (params.fgdQuestions !== undefined) {
        const fgdValidation = validateRange(
            params.fgdQuestions,
            DEFAULT_CONSTRAINTS.fgdQuestions.min,
            DEFAULT_CONSTRAINTS.fgdQuestions.max,
            'FGD questions'
        );
        if (!fgdValidation.isValid) {
            errors.push(fgdValidation.error!);
        }
    }

    // Chapter 2 paragraphs per section
    if (params.chapter2Paragraphs !== undefined) {
        const chapter2Validation = validateRange(
            params.chapter2Paragraphs,
            DEFAULT_CONSTRAINTS.chapter2Paragraphs.min,
            DEFAULT_CONSTRAINTS.chapter2Paragraphs.max,
            'Chapter 2 paragraphs per section'
        );
        if (!chapter2Validation.isValid) {
            errors.push(chapter2Validation.error!);
        }
    }

    if (params.chapter2ParagraphPlan) {
        const plan = params.chapter2ParagraphPlan;
        const entries: Array<[string, number | undefined, string]> = [
            ['intro', plan.intro, 'Chapter 2 introduction paragraphs'],
            ['frameworkIntro', plan.frameworkIntro, 'Framework introduction paragraphs'],
            ['theoryPerObjective', plan.theoryPerObjective, 'Theory paragraphs per objective'],
            ['conceptualFramework', plan.conceptualFramework, 'Conceptual framework paragraphs'],
            ['empiricalIntro', plan.empiricalIntro, 'Empirical introduction paragraphs'],
            ['empiricalPerVariable', plan.empiricalPerVariable, 'Empirical paragraphs per variable'],
            ['gap', plan.gap, 'Research gap paragraphs']
        ];
        for (const [, value, label] of entries) {
            if (value !== undefined) {
                const planValidation = validateRange(
                    value,
                    DEFAULT_CONSTRAINTS.chapter2Paragraphs.min,
                    DEFAULT_CONSTRAINTS.chapter2Paragraphs.max,
                    label
                );
                if (!planValidation.isValid) {
                    errors.push(planValidation.error!);
                }
            }
        }
    }

    if (params.targetPages !== undefined) {
        const targetPagesValidation = validateRange(
            params.targetPages,
            DEFAULT_CONSTRAINTS.targetPages.min,
            DEFAULT_CONSTRAINTS.targetPages.max,
            'Target pages'
        );
        if (!targetPagesValidation.isValid) {
            errors.push(targetPagesValidation.error!);
        }
    }

    if (params.wordsPerPage !== undefined) {
        const wordsPerPageValidation = validateRange(
            params.wordsPerPage,
            DEFAULT_CONSTRAINTS.wordsPerPage.min,
            DEFAULT_CONSTRAINTS.wordsPerPage.max,
            'Words per page'
        );
        if (!wordsPerPageValidation.isValid) {
            errors.push(wordsPerPageValidation.error!);
        }
    }

    if (params.targetWordCount !== undefined) {
        const targetWordCountValidation = validateRange(
            params.targetWordCount,
            DEFAULT_CONSTRAINTS.targetWordCount.min,
            DEFAULT_CONSTRAINTS.targetWordCount.max,
            'Target word count'
        );
        if (!targetWordCountValidation.isValid) {
            errors.push(targetWordCountValidation.error!);
        }
    }

    return {
        isValid: errors.length === 0,
        errors,
        warnings
    };
}

/**
 * Auto-adjust percentages to sum to 100
 */
export function normalizePercentages<T extends Record<string, number>>(
    distribution: T
): T {
    const sum = Object.values(distribution).reduce((a, b) => a + b, 0);

    if (sum === 0) return distribution;

    const normalized = {} as T;
    const keys = Object.keys(distribution);

    // Normalize all but the last key
    let runningSum = 0;
    for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        const value = Math.round((distribution[key] / sum) * 100 * 10) / 10;
        normalized[key as keyof T] = value as T[keyof T];
        runningSum += value;
    }

    // Last key gets the remainder to ensure exact 100%
    const lastKey = keys[keys.length - 1];
    normalized[lastKey as keyof T] = (100 - runningSum) as T[keyof T];

    return normalized;
}

/**
 * Calculate actual counts from percentages
 */
export function calculateCounts(
    total: number,
    distribution: Record<string, number>
): Record<string, number> {
    const counts: Record<string, number> = {};
    const keys = Object.keys(distribution);

    let runningTotal = 0;
    for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        const count = Math.round((distribution[key] / 100) * total);
        counts[key] = count;
        runningTotal += count;
    }

    // Last category gets the remainder
    const lastKey = keys[keys.length - 1];
    counts[lastKey] = total - runningTotal;

    return counts;
}
