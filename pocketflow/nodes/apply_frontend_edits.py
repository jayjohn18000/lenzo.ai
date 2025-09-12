# pocketflow/nodes/apply_frontend_edits.py
from pocketflow.store import SharedStore
from pocketflow.utils import (
    file_exists,
    ensure_import,
    ensure_text_block,
    replace_in_file,
)
import os


class ApplyFrontendEdits:
    name = "apply_frontend_edits"

    def run(self, store: SharedStore) -> None:
        t = store.context["ticket"]
        ttype = t.get("type")
        if ttype == "fix_api_proxy":
            self._fix_api_proxy(store)
        elif ttype == "fix_data_scaling":
            self._fix_data_scaling(store)
        elif ttype == "add_frontend_auth":
            self._add_frontend_auth(store)
        else:
            raise ValueError(f"Unknown frontend ticket type: {ttype}")

    def _fix_api_proxy(self, store: SharedStore) -> None:
        """Fix frontend API proxy to match backend contract"""
        repo = store.repo_root
        proxy_path = os.path.join(repo, "frontend", "app", "api", "route", "route.ts")

        assert file_exists(proxy_path), f"missing API proxy file: {proxy_path}"

        # Replace the entire proxy with a direct passthrough
        new_proxy_content = """// frontend/app/api/route/route.ts - DIRECT BACKEND PASSTHROUGH
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
}"""

        with open(proxy_path, "w", encoding="utf-8") as f:
            f.write(new_proxy_content)

        store.context["apply_frontend_edits.fix_api_proxy"] = {
            "proxy_fixed": True,
            "direct_passthrough": True,
        }

    def _fix_data_scaling(self, store: SharedStore) -> None:
        """Fix data scaling and transformation issues"""
        repo = store.repo_root

        # Fix confidence scaling in dashboard
        dashboard_path = os.path.join(repo, "frontend", "app", "dashboard", "page.tsx")
        if file_exists(dashboard_path):
            # Fix confidence scaling - ensure it's 0-100, not 0-1
            replace_in_file(
                dashboard_path,
                r"const targetConfidence = data\.confidence \? data\.confidence \* 100 : 85;",
                r"const targetConfidence = data.confidence ? Math.min(100, Math.max(0, data.confidence * 100)) : 85;",
            )

            # Fix confidence display formatting
            replace_in_file(
                dashboard_path,
                r"formatPercentage01\(result\.confidence\)",
                r"formatPercentage01(result.confidence * 100)",
            )

            # Fix model metrics confidence scaling
            replace_in_file(
                dashboard_path,
                r"formatPercentage01\(metric\.confidence\)",
                r"formatPercentage01(metric.confidence * 100)",
            )

        # Fix main page confidence scaling
        main_page_path = os.path.join(repo, "frontend", "app", "page.tsx")
        if file_exists(main_page_path):
            # Fix confidence animation target
            replace_in_file(
                main_page_path,
                r"const targetConfidence = data\.confidence \? data\.confidence \* 100 : 85;",
                r"const targetConfidence = data.confidence ? Math.min(100, Math.max(0, data.confidence * 100)) : 85;",
            )

        store.context["apply_frontend_edits.fix_data_scaling"] = {
            "confidence_scaling_fixed": True,
            "dashboard_updated": file_exists(dashboard_path),
            "main_page_updated": file_exists(main_page_path),
        }

    def _add_frontend_auth(self, store: SharedStore) -> None:
        """Add API key authentication to frontend requests"""
        repo = store.repo_root

        # Update environment configuration
        env_example_path = os.path.join(repo, "frontend", ".env.example")
        env_example_content = """# NextAGI Frontend Environment Variables

# Backend API Configuration
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000

# API Authentication
NEXT_PUBLIC_API_KEY=your_api_key_here

# Development Settings
NODE_ENV=development
"""

        with open(env_example_path, "w", encoding="utf-8") as f:
            f.write(env_example_content)

        # Update API client to include authentication
        api_client_path = os.path.join(repo, "frontend", "lib", "api", "client.ts")
        if file_exists(api_client_path):
            # Add API key to request headers
            replace_in_file(
                api_client_path,
                r"headers: \{\s*'Content-Type': 'application/json',",
                r"""headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),""",
            )

        # Update main API client
        main_api_path = os.path.join(repo, "frontend", "lib", "api.ts")
        if file_exists(main_api_path):
            # Add API key support
            replace_in_file(
                main_api_path,
                r"const API_BASE_URL = process\.env\.NEXT_PUBLIC_BACKEND_URL \|\| 'http://127\.0\.0\.1:8000';",
                r"""const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;""",
            )

            # Add API key to headers
            replace_in_file(
                main_api_path,
                r"headers: \{\s*'Content-Type': 'application/json',",
                r"""headers: {
          'Content-Type': 'application/json',
          ...(API_KEY && { 'Authorization': `Bearer ${API_KEY}` }),""",
            )

        store.context["apply_frontend_edits.add_frontend_auth"] = {
            "env_example_created": True,
            "api_client_updated": file_exists(api_client_path),
            "main_api_updated": file_exists(main_api_path),
        }
