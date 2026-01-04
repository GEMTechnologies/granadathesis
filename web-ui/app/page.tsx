'use client';

import React from 'react';
import { ManusStyleLayout } from '../components/layout/ManusStyleLayout';

import { redirect } from 'next/navigation';

export default function HomePage() {
  redirect('/workspace/default');
  return null;
}
