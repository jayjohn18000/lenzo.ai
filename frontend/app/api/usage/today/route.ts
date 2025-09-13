// frontend/app/api/usage/today/route.ts - API PROXY FOR TODAY'S USAGE
import { NextRequest, NextResponse } from "next/server";

export async function GET(_request: NextRequest) {
  try {
    console.log("📊 [PROXY] Fetching today's usage stats");
    
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const apiKey = process.env.NEXT_PUBLIC_API_KEY || 'nextagi_test-key-123';
    
    const response = await fetch(`${backendUrl}/api/v1/usage/today`, {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    
    console.log("✅ [PROXY] Today's usage stats fetched successfully", {
      status: response.status,
      data
    });

    return NextResponse.json(data, {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });

  } catch (error: any) {
    console.error("❌ [PROXY] Failed to fetch today's usage stats:", {
      error: error.message,
      stack: error.stack
    });

    // Return default values on error
    const defaultData = {
      requests: 0,
      cost: 0,
      avg_confidence: 0,
      date: new Date().toISOString().split('T')[0]
    };

    return NextResponse.json(defaultData, {
      status: 200, // Return 200 with default data instead of error
      headers: {
        'Content-Type': 'application/json',
        'X-Error': 'proxy-fallback'
      }
    });
  }
}
