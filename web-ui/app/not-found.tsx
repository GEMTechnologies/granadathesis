'use client';

import React from 'react';
import Link from 'next/link';
import { 
  Home, 
  Search, 
  BookOpen, 
  FileText, 
  ArrowLeft,
  AlertCircle,
  Compass
} from 'lucide-react';

export default function NotFound() {
  const quickLinks = [
    { 
      icon: <Home className="w-5 h-5" />, 
      label: 'Home', 
      path: '/',
      description: 'Return to dashboard'
    },
    { 
      icon: <FileText className="w-5 h-5" />, 
      label: 'Workspace', 
      path: '/workspace/objectives',
      description: 'View your projects'
    },
    { 
      icon: <Search className="w-5 h-5" />, 
      label: 'Search Papers', 
      path: '/research/search',
      description: 'Find research papers'
    },
    { 
      icon: <BookOpen className="w-5 h-5" />, 
      label: 'Projects', 
      path: '/projects/thesis',
      description: 'Manage documents'
    },
  ];

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{ backgroundColor: 'var(--color-bg, #F4F4F4)' }}
    >
      <div className="max-w-2xl w-full text-center space-y-8">
        {/* Main Error Display */}
        <div className="space-y-4">
          <div className="flex items-center justify-center gap-4 mb-6">
            <div
              className="p-4 rounded-full"
              style={{
                backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
                boxShadow: '0 4px 12px rgba(15, 98, 254, 0.2)'
              }}
            >
              <AlertCircle 
                className="w-12 h-12"
                style={{ color: 'var(--color-primary, #0F62FE)' }}
              />
            </div>
            <div className="text-left">
              <h1 
                className="text-8xl font-bold leading-none"
                style={{ color: 'var(--color-primary, #0F62FE)' }}
              >
                404
              </h1>
              <p 
                className="text-2xl font-semibold mt-2"
                style={{ color: 'var(--color-text-secondary, #525252)' }}
              >
                Page Not Found
              </p>
            </div>
          </div>

          <p 
            className="text-lg max-w-md mx-auto"
            style={{ color: 'var(--color-text-secondary, #525252)' }}
          >
            Oops! The page you're looking for seems to have wandered off into the academic abyss. 
            Don't worry, even the best researchers sometimes take a wrong turn.
          </p>
        </div>

        {/* Quick Links Grid */}
        <div 
          className="rounded-xl p-6 backdrop-blur-sm"
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            border: '1px solid var(--color-border, #E0E0E0)',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)'
          }}
        >
          <div className="flex items-center gap-2 mb-4 justify-center">
            <Compass className="w-5 h-5" style={{ color: 'var(--color-primary, #0F62FE)' }} />
            <h2 
              className="text-lg font-semibold"
              style={{ color: 'var(--color-text, #161616)' }}
            >
              Quick Navigation
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {quickLinks.map((link) => (
              <Link
                key={link.path}
                href={link.path}
                className="group flex items-start gap-3 p-4 rounded-lg transition-all hover:shadow-md hover:scale-[1.02]"
                style={{
                  backgroundColor: 'var(--color-bg, #F4F4F4)',
                  border: '1px solid var(--color-border, #E0E0E0)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-primary-bg, #EDF5FF)';
                  e.currentTarget.style.borderColor = 'var(--color-primary, #0F62FE)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg, #F4F4F4)';
                  e.currentTarget.style.borderColor = 'var(--color-border, #E0E0E0)';
                }}
              >
                <div 
                  className="p-2 rounded-lg transition-transform group-hover:scale-110"
                  style={{
                    backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
                    color: 'var(--color-primary, #0F62FE)'
                  }}
                >
                  {link.icon}
                </div>
                <div className="text-left flex-1">
                  <p 
                    className="font-semibold mb-1"
                    style={{ color: 'var(--color-text, #161616)' }}
                  >
                    {link.label}
                  </p>
                  <p 
                    className="text-xs"
                    style={{ color: 'var(--color-text-muted, #8D8D8D)' }}
                  >
                    {link.description}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
          <Link
            href="/"
            className="flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all hover:scale-105 hover:shadow-lg"
            style={{
              backgroundColor: 'var(--color-primary, #0F62FE)',
              color: 'white',
              boxShadow: '0 2px 4px rgba(15, 98, 254, 0.3)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-primary-hover, #0050E6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-primary, #0F62FE)';
            }}
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Home
          </Link>
          
          <button
            onClick={() => window.history.back()}
            className="flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all hover:scale-105"
            style={{
              backgroundColor: 'var(--color-panel, #FFFFFF)',
              color: 'var(--color-text, #161616)',
              border: '1px solid var(--color-border, #E0E0E0)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg, #F4F4F4)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-panel, #FFFFFF)';
            }}
          >
            <ArrowLeft className="w-5 h-5" />
            Go Back
          </button>
        </div>

        {/* Helpful Message */}
        <div 
          className="rounded-lg p-4"
          style={{
            backgroundColor: 'var(--color-primary-bg, #EDF5FF)',
            border: '1px solid var(--color-primary, #0F62FE)'
          }}
        >
          <p 
            className="text-sm"
            style={{ color: 'var(--color-text, #161616)' }}
          >
            <strong>Tip:</strong> Use the navigation menu on the left to explore all available features, 
            or search for what you need using the search bar.
          </p>
        </div>
      </div>
    </div>
  );
}

















