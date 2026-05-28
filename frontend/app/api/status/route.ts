import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET() {
  const res = await fetch(`${API_BASE}/status`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST() {
  const res = await fetch(`${API_BASE}/clear`, { method: 'POST' });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
