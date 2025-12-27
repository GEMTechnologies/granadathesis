'use client';

import React from 'react';
import { ManusStyleLayout } from '@/components/layout/ManusStyleLayout';

export default function WorkspacePage({ params }: { params: { id: string } }) {
    // ManusStyleLayout handles its own workspace state
    return <ManusStyleLayout />;
}
