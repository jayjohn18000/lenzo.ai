// frontend/lib/api/fetch-wrapper.ts - CENTRALIZED FETCH WRAPPER
interface FetchOptions extends RequestInit {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

interface FetchResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: Headers;
  url: string;
  elapsed: number;
}

interface FetchError extends Error {
  status?: number;
  statusText?: string;
  url?: string;
  response?: Response;
  data?: any;
}

class FetchWrapper {
  private baseURL: string;
  private defaultTimeout: number;
  private defaultRetries: number;
  private defaultRetryDelay: number;

  constructor(
    baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    options: {
      timeout?: number;
      retries?: number;
      retryDelay?: number;
    } = {}
  ) {
    this.baseURL = baseURL;
    this.defaultTimeout = options.timeout || 10000; // 10 seconds
    this.defaultRetries = options.retries || 2;
    this.defaultRetryDelay = options.retryDelay || 1000; // 1 second
  }

  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private createTimeoutSignal(timeout: number): AbortSignal {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), timeout);
    return controller.signal;
  }

  private async logRequest(
    url: string,
    options: FetchOptions,
    startTime: number
  ): Promise<void> {
    const elapsed = performance.now() - startTime;
    console.log(`🌐 [FETCH] ${options.method || 'GET'} ${url}`, {
      elapsed: `${elapsed.toFixed(1)}ms`,
      headers: options.headers,
      body: options.body ? 'present' : 'none',
      timestamp: new Date().toISOString()
    });
  }

  private async logResponse(
    url: string,
    response: Response,
    startTime: number,
    success: boolean
  ): Promise<void> {
    const elapsed = performance.now() - startTime;
    const logLevel = success ? 'log' : 'error';
    const emoji = success ? '✅' : '❌';
    
    console[logLevel](`${emoji} [FETCH] ${response.status} ${url}`, {
      status: response.status,
      statusText: response.statusText,
      elapsed: `${elapsed.toFixed(1)}ms`,
      headers: Object.fromEntries(response.headers.entries()),
      timestamp: new Date().toISOString()
    });
  }

  private async logError(
    url: string,
    error: any,
    startTime: number,
    attempt: number
  ): Promise<void> {
    const elapsed = performance.now() - startTime;
    console.error(`🚨 [FETCH ERROR] ${url}`, {
      error: error.message,
      type: error.name,
      elapsed: `${elapsed.toFixed(1)}ms`,
      attempt,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
  }

  async fetch<T = any>(
    endpoint: string,
    options: FetchOptions = {}
  ): Promise<FetchResponse<T>> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
    const startTime = performance.now();
    
    const {
      timeout = this.defaultTimeout,
      retries = this.defaultRetries,
      retryDelay = this.defaultRetryDelay,
      ...fetchOptions
    } = options;

    // Prepare headers
    const headers = new Headers({
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    });

    // Add authentication if API key is available
    const apiKey = process.env.NEXT_PUBLIC_API_KEY;
    if (apiKey && !endpoint.startsWith('/dev/')) {
      headers.set('Authorization', `Bearer ${apiKey}`);
    }

    const requestOptions: RequestInit = {
      ...fetchOptions,
      headers,
      signal: this.createTimeoutSignal(timeout),
    };

    let lastError: FetchError | null = null;

    // Retry logic
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        if (attempt > 0) {
          await this.logRequest(url, requestOptions, startTime);
          await this.sleep(retryDelay * attempt); // Exponential backoff
        }

        const response = await fetch(url, requestOptions);
        
        // Log response
        await this.logResponse(url, response, startTime, response.ok);

        if (!response.ok) {
          let errorData: any;
          try {
            errorData = await response.json();
          } catch {
            errorData = await response.text();
          }

          const error: FetchError = new Error(
            `HTTP ${response.status}: ${response.statusText}`
          ) as FetchError;
          error.status = response.status;
          error.statusText = response.statusText;
          error.url = url;
          error.response = response;
          error.data = errorData;

          // Don't retry on client errors (4xx)
          if (response.status >= 400 && response.status < 500) {
            throw error;
          }

          // Retry on server errors (5xx) or network issues
          if (attempt === retries) {
            throw error;
          }

          lastError = error;
          continue;
        }

        // Parse response
        let data: T;
        const contentType = response.headers.get('content-type');
        
        if (contentType?.includes('application/json')) {
          data = await response.json();
        } else {
          data = (await response.text()) as T;
        }

        const elapsed = performance.now() - startTime;

        return {
          data,
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
          url,
          elapsed,
        };

      } catch (error: any) {
        await this.logError(url, error, startTime, attempt + 1);
        
        // Don't retry on abort (timeout) or client errors
        if (error.name === 'AbortError' || 
            (error.status && error.status >= 400 && error.status < 500)) {
          throw error;
        }

        lastError = error as FetchError;

        // If this was the last attempt, throw the error
        if (attempt === retries) {
          throw error;
        }
      }
    }

    // This should never be reached, but just in case
    throw lastError || new Error('Unknown fetch error');
  }

  // Convenience methods
  async get<T = any>(endpoint: string, options: FetchOptions = {}): Promise<FetchResponse<T>> {
    return this.fetch<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T = any>(endpoint: string, data?: any, options: FetchOptions = {}): Promise<FetchResponse<T>> {
    return this.fetch<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T = any>(endpoint: string, data?: any, options: FetchOptions = {}): Promise<FetchResponse<T>> {
    return this.fetch<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T = any>(endpoint: string, options: FetchOptions = {}): Promise<FetchResponse<T>> {
    return this.fetch<T>(endpoint, { ...options, method: 'DELETE' });
  }

  // Health check method
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.get('/dev/health', { timeout: 5000 });
      return response.status === 200;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const fetchWrapper = new FetchWrapper();

// Export class for custom instances
export { FetchWrapper };

// Export types
export type { FetchOptions, FetchResponse, FetchError };
