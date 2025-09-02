// frontend/app/api/route/route.ts - CORRECTED VERSION WITH TIMEOUT HANDLING
export async function POST(req: Request) {
  const body = await req.json();
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
  
  // Transform the request to match your enhanced API
  const transformedBody = {
    prompt: body.prompt || "Test question",
    category: body.category || "general",  // Add this
    expected_traits: ["accurate", "clear"], // Add this
    options: {
      rubric: {},
      require_citations: false
    }
  };
  
  console.log('🔗 Calling: http://127.0.0.1:8000/api/v1/query');
  console.log('📦 Request body:', transformedBody);

  try {
    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 90000); // 90 second timeout
    
    const r = await fetch(`${backend}/api/v1/query`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json"
      },
      body: JSON.stringify(transformedBody),
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    console.log(`📡 Response status: ${r.status}`);
    
    if (!r.ok) {
      const errorText = await r.text();
      console.error('❌ Backend error:', errorText);
      
      if (r.status === 403 || r.status === 401) {
        throw new Error(`Authentication required - Status ${r.status}. The enhanced routes may require API key authentication.`);
      }
      
      if (r.status === 422) {
        throw new Error(`Validation error - Status ${r.status}. Check request format: ${errorText}`);
      }
      
      throw new Error(`Backend error: ${r.status} - ${errorText}`);
    }

    const data = await r.json();
    console.log('✅ Success response:', data);
    
    // Transform the enhanced API response to match your frontend expectations
    const transformedResponse = {
      prompt: transformedBody.prompt,
      responses: data.model_details?.map(detail => ({
        model: detail.model,
        response: detail.response
      })) || [{ 
        model: data.winner_model || 'unknown', 
        response: data.answer || 'No response'
      }],
      ranking: data.model_details?.map(detail => ({
        model: detail.model,
        aggregate: { score_mean: detail.confidence },
        judgments: []
      })) || [{
        model: data.winner_model || 'unknown',
        aggregate: { score_mean: data.confidence || 0.8 },
        judgments: []
      }],
      winner: { 
        model: data.winner_model || 'unknown', 
        score: data.confidence || 0.8 
      },
      // Include the enhanced data for your dashboard
      enhanced_data: {
        model_details: data.model_details || [],
        reasoning: data.reasoning || '',
        total_cost: data.total_cost || 0,
        response_time_ms: data.response_time_ms || 0
      }
    };
    
    return new Response(JSON.stringify(transformedResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    
  } catch (error) {
    console.error('🚨 Request failed:', error);
    
    let errorMessage = 'Unknown error';
    let statusCode = 500;
    
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        errorMessage = 'Request timeout - Backend took longer than 30 seconds to respond. This suggests an issue with the AI model API calls.';
        statusCode = 504;
      } else {
        errorMessage = error.message;
      }
    }
    
    // Return a fallback response that won't break your frontend
    const fallbackResponse = {
      prompt: body.prompt || 'Error occurred',
      responses: [{ 
        model: 'error-handler', 
        response: `Request failed: ${errorMessage}. Please check backend logs and ensure API keys are configured.`
      }],
      ranking: [{
        model: 'error-handler',
        aggregate: { score_mean: 0.0 },
        judgments: []
      }],
      winner: { 
        model: 'error-handler', 
        score: 0.0 
      },
      error: {
        message: errorMessage,
        timestamp: new Date().toISOString(),
        debug_info: "Check that your backend is running and OpenRouter API key is configured"
      }
    };
    
    return new Response(JSON.stringify(fallbackResponse), {
      status: statusCode,
      headers: { "Content-Type": "application/json" },
    });
  }
}