// TypeScript interfaces for thesis generation parameters

export interface GenderDistribution {
    male: number;    // percentage
    female: number;  // percentage
    other: number;   // percentage
    [key: string]: number;
}

export interface AgeDistribution {
    '18-25': number;
    '26-35': number;
    '36-45': number;
    '46-55': number;
    '55+': number;
    [key: string]: number;
}

export interface EducationDistribution {
    primary: number;
    secondary: number;
    tertiary: number;
    postgraduate: number;
    [key: string]: number;
}

export interface ThesisParameters {
    // Common
    topic: string;
    caseStudy?: string;
    universityType?: string;

    // Sample & Demographics
    sampleSize: number;
    genderDistribution: GenderDistribution;
    ageDistribution: AgeDistribution;
    educationDistribution: EducationDistribution;

    // Research Design
    researchDesign?: 'quantitative' | 'qualitative' | 'mixed';
    dataCollectionMethods?: string[];
    responseRate?: number;

    // Study Tools
    itemsPerObjective?: number;
    likertScale?: 3 | 5 | 7;
    includeQualitative?: boolean;
    interviewQuestions?: number;
    fgdQuestions?: number;
    customInstructions?: string;
}

export interface ValidationResult {
    isValid: boolean;
    errors: string[];
    warnings: string[];
}

export interface ParameterConstraints {
    sampleSize: { min: number; max: number };
    responseRate: { min: number; max: number };
    itemsPerObjective: { min: number; max: number };
    interviewQuestions: { min: number; max: number };
    fgdQuestions: { min: number; max: number };
}

export const DEFAULT_CONSTRAINTS: ParameterConstraints = {
    sampleSize: { min: 30, max: 1000 },
    responseRate: { min: 70, max: 100 },
    itemsPerObjective: { min: 2, max: 5 },
    interviewQuestions: { min: 5, max: 20 },
    fgdQuestions: { min: 5, max: 15 }
};

export const DEFAULT_PARAMETERS: ThesisParameters = {
    topic: '',
    sampleSize: 385,
    genderDistribution: {
        male: 50,
        female: 50,
        other: 0
    },
    ageDistribution: {
        '18-25': 20,
        '26-35': 30,
        '36-45': 25,
        '46-55': 15,
        '55+': 10
    },
    educationDistribution: {
        primary: 10,
        secondary: 30,
        tertiary: 45,
        postgraduate: 15
    },
    researchDesign: 'mixed',
    dataCollectionMethods: ['questionnaire', 'interview', 'fgd'],
    responseRate: 90,
    itemsPerObjective: 3,
    likertScale: 5,
    includeQualitative: true,
    interviewQuestions: 10,
    fgdQuestions: 8,
    customInstructions: ''
};
