'use client';

import * as React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';

export function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = React.useState(false);

    // Avoid hydration mismatch by only rendering after mount
    React.useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return (
            <button className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                <div className="w-5 h-5 flex items-center justify-center text-gray-400">
                    <Sun className="w-4 h-4" />
                </div>
            </button>
        );
    }

    return (
        <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group relative overflow-hidden"
            aria-label="Toggle theme"
        >
            <div className="relative w-5 h-5">
                <Sun className="absolute inset-0 w-5 h-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0 text-amber-500" />
                <Moon className="absolute inset-0 w-5 h-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 text-blue-400" />
            </div>
            <span className="sr-only">Toggle theme</span>
        </button>
    );
}
