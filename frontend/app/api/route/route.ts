// frontend/app/api/route/route.ts - DIRECT BACKEND PASSTHROUGH
export async function POST(req: Request) {
  const body = await req.json();
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
  
  console.log('🔗 Calling backend:', `${backend}/api/v1/query`);
  console.log('📦 Request body:', body);

  try {
    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 90000); // 90 second timeout
    
    const response = await fetch(`${backend}/api/v1/query`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        // Forward API key if available
        ...(process.env.NEXT_PUBLIC_API_KEY && {
          "Authorization": `Bearer ${process.env.NEXT_PUBLIC_API_KEY}`
        })
      },
      body: JSON.stringify(body), // Direct passthrough
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    console.log(`📡 Response status: ${response.status}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Backend error:', errorText);
      
      if (response.status === 403 || response.status === 401) {
        throw new Error(`Authentication required - Status ${response.status}. Please configure API key.`);
      }
      
      if (response.status === 422) {
        throw new Error(`Validation error - Status ${response.status}. Check request format: ${errorText}`);
      }
      
      throw new Error(`Backend error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    console.log('✅ Backend response:', data);
    
    // Direct passthrough - no transformation needed
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    
  } catch (error) {
    console.error('🚨 Request failed:', error);
    
    let errorMessage = 'Unknown error';
    let statusCode = 500;
    
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        errorMessage = 'Request timeout - Backend took longer than 90 seconds to respond.';
        statusCode = 504;
      } else {
        errorMessage = error.message;
      }
    }
    
    // Return error response
    return new Response(JSON.stringify({
      error: {
        message: errorMessage,
        timestamp: new Date().toISOString(),
        debug_info: "Check that your backend is running and API key is configured"
      }
    }), {
      status: statusCode,
      headers: { "Content-Type": "application/json" },
    });
  }
}