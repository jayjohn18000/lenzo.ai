// frontend/app/api/jobs/stats/route.ts - API PROXY FOR JOB STATS
import { NextRequest, NextResponse } from "next/server";
import { fetchWrapper } from "@/lib/api/fetch-wrapper";

export async function GET(_request: NextRequest) {
  try {
    console.log("📊 [PROXY] Fetching job stats");
    
    const response = await fetchWrapper.get('/dev/jobs/stats', {
      timeout: 5000,
      retries: 1
    });

    console.log("✅ [PROXY] Job stats fetched successfully", {
      status: response.status,
      elapsed: `${response.elapsed.toFixed(1)}ms`
    });

    return NextResponse.json(response.data, {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });

  } catch (error: any) {
    console.error("❌ [PROXY] Failed to fetch job stats:", {
      error: error.message,
      status: error.status,
      url: error.url
    });

    // Return default values on error
    const defaultData = {
      pending_jobs: 0,
      processing_jobs: 0,
      worker_active: false,
      total_processed: "0"
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
