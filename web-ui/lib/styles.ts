// Utility functions for IBM color system
export const ibmColors = {
  bg: 'var(--color-bg)',
  panel: 'var(--color-panel)',
  border: 'var(--color-border)',
  text: 'var(--color-text)',
  textSecondary: 'var(--color-text-secondary)',
  textMuted: 'var(--color-text-muted)',
  primary: 'var(--color-primary)',
  primaryHover: 'var(--color-primary-hover)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-danger)',
};

export function getStyle(property: keyof typeof ibmColors) {
  return { [property === 'bg' ? 'backgroundColor' : property === 'text' ? 'color' : 'borderColor']: ibmColors[property] };
}
