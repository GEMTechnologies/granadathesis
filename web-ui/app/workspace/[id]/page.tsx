'use client';

import React from 'react';
import { ManusStyleLayout } from '@/components/layout/ManusStyleLayout';

export default function WorkspacePage({ params }: { params: { id: string } }) {
    return <ManusStyleLayout workspaceId={params.id} />;
}
