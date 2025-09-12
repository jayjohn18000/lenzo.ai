# Frontend Dashboard Data Flow Analysis

## Complete File Mapping & Data Flow

### 🎯 **DATA FLOW OVERVIEW**
```
Backend API → Frontend API Client → React Hooks → UI Components → User Display
```

---

## 📁 **FILE STRUCTURE & RESPONSIBILITIES**

### **1. BACKEND DATA SOURCES**
- **`backend/api/v1/routes.py`** - Main API endpoints
  - `/api/v1/query` - Query processing endpoint
  - `/api/v1/usage` - Usage statistics endpoint  
  - `/api/v1/health` - Health check endpoint
  - `/api/v1/jobs/{job_id}` - Job status polling

### **2. FRONTEND API LAYER**
- **`frontend/lib/api.ts`** - Main API client with authentication
  - `APIClient.query()` - Handles query requests with job polling
  - `APIClient.getUsageStats()` - Fetches usage statistics
  - `APIClient.getHealth()` - Health check
  - `FALLBACK_DATA` - Dummy data when backend unavailable

- **`frontend/types/api.ts`** - TypeScript interfaces
  - `QueryRequest` - Request format
  - `QueryResponse` - Response format
  - `UsageStats` - Usage statistics format
  - `ModelMetrics` - Individual model data
  - `ModelComparison` - Comparison data

### **3. REACT HOOKS LAYER**
- **`frontend/hooks/use-api.ts`** - React hooks for API calls
  - `useQuery()` - Query execution hook
  - `useUsageStats()` - Usage statistics hook
  - `useHealthCheck()` - Health monitoring hook

### **4. UI COMPONENTS LAYER**
- **`frontend/app/page.tsx`** - Main dashboard page
- **`frontend/app/dashboard/page.tsx`** - Dashboard page
- **`frontend/components/QueryInterface.tsx`** - Query input component
- **`frontend/components/ModelMetrics.tsx`** - Model metrics display
- **`frontend/components/charts/confidence-chart.tsx`** - Confidence visualization
- **`frontend/app/dashboard/StatsCards.tsx`** - Statistics cards

### **5. UTILITY LAYERS**
- **`frontend/lib/safe-formatters.ts`** - Data formatting utilities
- **`frontend/lib/safe-formatters.ts`** - Safe number/percentage formatting

---

## 🔄 **DETAILED DATA FLOW**

### **QUERY FLOW**
```
1. User Input (page.tsx) 
   ↓
2. QueryRequest → APIClient.query() (lib/api.ts)
   ↓
3. HTTP POST /api/v1/query (backend/routes.py)
   ↓
4. Job Creation → 202 Response with job_id
   ↓
5. Polling /api/v1/jobs/{job_id} until completion
   ↓
6. QueryResponse → React State (page.tsx)
   ↓
7. UI Rendering with ModelMetrics, ModelComparison
```

### **USAGE STATISTICS FLOW**
```
1. Dashboard Mount (dashboard/page.tsx)
   ↓
2. fetchUsageStats() → Direct fetch to /api/v1/usage
   ↓
3. Backend generates random data (routes.py:575-620)
   ↓
4. UsageStats → React State
   ↓
5. StatsCards.tsx → UI Display
```

---

## ⚠️ **CURRENT ISSUES & VALIDATION GAPS**

### **1. DATA VALIDATION MISSING**
- ❌ No validation between API response and TypeScript interfaces
- ❌ No data range validation (confidence 0-1, percentages 0-100)
- ❌ No schema validation for API responses

### **2. ERROR HANDLING GAPS**
- ❌ Fallback data masks real API failures
- ❌ No distinction between network errors vs data errors
- ❌ Silent failures in data transformation

### **3. DATA CONSISTENCY ISSUES**
- ❌ Multiple data sources (API vs fallback vs random backend data)
- ❌ Inconsistent data formats between endpoints
- ❌ No data freshness validation

---

## 🛠️ **RECOMMENDED VALIDATION CHECKPOINTS**

### **Checkpoint 1: API Response Validation**
```typescript
// Add to lib/api.ts
function validateQueryResponse(data: any): QueryResponse {
  if (!data.request_id || !data.answer || typeof data.confidence !== 'number') {
    throw new Error("Invalid query response structure");
  }
  if (data.confidence < 0 || data.confidence > 1) {
    throw new Error("Confidence must be 0-1 range");
  }
  return data as QueryResponse;
}
```

### **Checkpoint 2: Usage Stats Validation**
```typescript
// Add to hooks/use-api.ts
function validateUsageStats(data: any): UsageStats {
  if (!data.total_requests || typeof data.total_requests !== 'number') {
    throw new Error("Invalid usage stats structure");
  }
  if (data.avg_confidence < 0 || data.avg_confidence > 1) {
    throw new Error("Average confidence must be 0-1 range");
  }
  return data as UsageStats;
}
```

### **Checkpoint 3: Model Metrics Validation**
```typescript
// Add to types/api.ts
function validateModelMetrics(metrics: ModelMetrics[]): ModelMetrics[] {
  return metrics.map(metric => {
    if (metric.confidence < 0 || metric.confidence > 1) {
      throw new Error(`Model ${metric.model} confidence out of range: ${metric.confidence}`);
    }
    return metric;
  });
}
```

---

## 🚨 **REPLACE DUMMY DATA WITH PROPER ERRORS**

### **Current Fallback Data Issues:**
- `FALLBACK_DATA` in `lib/api.ts` contains fake statistics
- `useUsageStats` hook provides empty fallback data
- Backend `/usage` endpoint generates random data

### **Proposed Error Messages:**
```typescript
// Instead of dummy data, show:
"I am a dumb fuck and I cannot map the path correctly."
"API connection failed - check backend status"
"Data validation failed - invalid response format"
"Network error - unable to fetch statistics"
```

---

## 📊 **DATA FLOW VALIDATION MATRIX**

| Stage | File | Input Validation | Output Validation | Error Handling |
|-------|------|------------------|-------------------|----------------|
| API Client | `lib/api.ts` | ❌ None | ❌ None | ⚠️ Fallback data |
| Type Definitions | `types/api.ts` | ❌ None | ❌ None | ❌ None |
| React Hooks | `hooks/use-api.ts` | ❌ None | ❌ None | ⚠️ Empty fallback |
| UI Components | `page.tsx` | ❌ None | ❌ None | ⚠️ Silent failures |
| Formatters | `safe-formatters.ts` | ✅ Basic | ✅ Basic | ✅ Fallback values |

---

## 🎯 **IMMEDIATE ACTION ITEMS**

1. **Add data validation at each checkpoint**
2. **Replace all dummy/fallback data with proper error messages**
3. **Add schema validation for API responses**
4. **Implement data range validation**
5. **Add error boundaries in React components**
6. **Create data consistency checks between endpoints**

---

## 🔍 **DEBUGGING CHECKLIST**

When debugging dashboard issues:
- [ ] Check API response structure matches TypeScript interfaces
- [ ] Validate data ranges (confidence 0-1, percentages 0-100)
- [ ] Verify authentication headers are present
- [ ] Check for network vs data errors
- [ ] Validate data transformation steps
- [ ] Check for silent failures in data flow
