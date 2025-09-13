// frontend/app/api/usage/stats/route.ts - API PROXY FOR USAGE STATS
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const days = searchParams.get('days') || '7';
    
    console.log("📊 [PROXY] Fetching usage stats", { days });
    
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const apiKey = process.env.NEXT_PUBLIC_API_KEY || 'nextagi_test-key-123';
    
    const response = await fetch(`${backendUrl}/api/v1/usage?days=${days}`, {
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
    
    console.log("✅ [PROXY] Usage stats fetched successfully", {
      status: response.status,
      days,
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
    console.error("❌ [PROXY] Failed to fetch usage stats:", {
      error: error.message,
      stack: error.stack
    });

    // Return default values on error
    const defaultData = {
      total_requests: 0,
      total_tokens: 0,
      total_cost: 0,
      avg_response_time: 0,
      avg_confidence: 0,
      top_models: [],
      daily_usage: [],
      data_available: false,
      message: "Unable to fetch usage statistics"
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
