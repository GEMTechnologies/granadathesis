'use client';

import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Loader2, Lock, User, Mail, Shield, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { cn } from '../../lib/utils';

interface LoginScreenProps {
    onLoginSuccess: (token: string, user: any) => void;
}

type AuthMode = 'login' | 'register';

export function LoginScreen({ onLoginSuccess }: LoginScreenProps) {
    const [mode, setMode] = useState<AuthMode>('login');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showPassword, setShowPassword] = useState(false);

    // Form State
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [username, setUsername] = useState('');
    const [invitationCode, setInvitationCode] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
            const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';

            const payload: any = {
                email,
                password
            };

            if (mode === 'register') {
                payload.username = username;
                payload.invitation_code = invitationCode;
            }

            console.log(`🔐 Attempting ${mode}...`, { email, endpoint });

            // Use native fetch to avoid interceptor loops
            const response = await fetch(`${backendUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Authentication failed');
            }

            console.log('✅ Auth success!', data);

            // Save token
            if (data.access_token) {
                localStorage.setItem('auth_token', data.access_token);
                localStorage.setItem('auth_user', JSON.stringify(data.user));

                // Callback to parent to lift the gate
                onLoginSuccess(data.access_token, data.user);
            }

        } catch (err: any) {
            console.error('Auth error:', err);
            setError(err.message || 'Something went wrong. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-in fade-in duration-500">
            <Card className="w-full max-w-md bg-white/95 border-none shadow-2xl rounded-3xl overflow-hidden relative">
                {/* Decorative Header */}
                <div className="bg-primary/5 p-6 pb-8 text-center relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary to-transparent opacity-50" />
                    <div className="w-16 h-16 bg-white rounded-2xl shadow-lg flex items-center justify-center mx-auto mb-4 relative z-10">
                        <Lock className="w-8 h-8 text-primary" />
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight text-gray-900">
                        {mode === 'login' ? 'Welcome Back' : 'Join Research Platform'}
                    </h2>
                    <p className="text-sm text-muted-foreground mt-2 max-w-[80%] mx-auto">
                        {mode === 'login'
                            ? 'Enter your credentials to access your secure research workspace.'
                            : 'Enter your invitation details to create a secure account.'}
                    </p>
                </div>

                {/* Form Container */}
                <div className="p-6 pt-2">
                    {/* Tabs */}
                    <div className="flex bg-muted/50 p-1 rounded-xl mb-6">
                        <button
                            onClick={() => { setMode('login'); setError(null); }}
                            className={cn(
                                "flex-1 py-2 text-sm font-semibold rounded-lg transition-all",
                                mode === 'login' ? "bg-white shadow text-primary" : "text-muted-foreground hover:text-primary/80"
                            )}
                        >
                            Sign In
                        </button>
                        <button
                            onClick={() => { setMode('register'); setError(null); }}
                            className={cn(
                                "flex-1 py-2 text-sm font-semibold rounded-lg transition-all",
                                mode === 'register' ? "bg-white shadow text-primary" : "text-muted-foreground hover:text-primary/80"
                            )}
                        >
                            Register
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">

                        {/* Username (Register Only) */}
                        {mode === 'register' && (
                            <div className="space-y-1.5 animate-in slide-in-from-left-2 duration-300">
                                <label className="text-xs font-semibold text-gray-600 ml-1">Full Name</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                    <input
                                        type="text"
                                        required
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        className="w-full pl-9 pr-4 py-2.5 bg-muted/30 border border-border/50 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary focus:outline-none transition-all text-sm"
                                        placeholder="John Doe"
                                    />
                                </div>
                            </div>
                        )}

                        {/* Invitation Code (Register Only) */}
                        {mode === 'register' && (
                            <div className="space-y-1.5 animate-in slide-in-from-right-2 duration-300">
                                <label className="text-xs font-semibold text-gray-600 ml-1 flex items-center justify-between">
                                    Invitation Code
                                    <span className="text-[10px] text-primary bg-primary/10 px-1.5 py-0.5 rounded-full">Required</span>
                                </label>
                                <div className="relative">
                                    <Shield className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                    <input
                                        type="text"
                                        required
                                        value={invitationCode}
                                        onChange={(e) => setInvitationCode(e.target.value)}
                                        className="w-full pl-9 pr-4 py-2.5 bg-muted/30 border border-border/50 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary focus:outline-none transition-all text-sm"
                                        placeholder="Enter secure code"
                                    />
                                </div>
                            </div>
                        )}

                        {/* Email */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-gray-600 ml-1">Email Address</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full pl-9 pr-4 py-2.5 bg-muted/30 border border-border/50 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary focus:outline-none transition-all text-sm"
                                    placeholder="name@example.com"
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-gray-600 ml-1">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full pl-9 pr-10 py-2.5 bg-muted/30 border border-border/50 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary focus:outline-none transition-all text-sm"
                                    placeholder="••••••••"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors focus:outline-none"
                                >
                                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                        </div>

                        {/* Error Message */}
                        {error && (
                            <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-xs font-medium flex items-center gap-2 animate-in zoom-in-95">
                                <AlertCircle className="w-4 h-4 shrink-0" />
                                {error}
                            </div>
                        )}

                        {/* Submit Button */}
                        <Button
                            type="submit"
                            className="w-full h-11 rounded-xl text-sm font-semibold shadow-lg shadow-primary/25 mt-2"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    {mode === 'login' ? 'Signing in...' : 'Creating Account...'}
                                </>
                            ) : (
                                mode === 'login' ? 'Sign In' : 'Create Account'
                            )}
                        </Button>
                    </form>
                </div>

                {/* Footer */}
                <div className="bg-muted/30 p-4 text-center border-t border-border/40">
                    <p className="text-[10px] text-muted-foreground">
                        Protected by Secure Research Architecture
                    </p>
                </div>
            </Card>
        </div>
    );
}
