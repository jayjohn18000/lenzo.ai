// lib/chart-utils.ts
export const chartTheme = {
    colors: {
      primary: '#60a5fa',
      secondary: '#34d399', 
      accent: '#fbbf24',
      danger: '#ef4444',
      muted: 'rgba(255, 255, 255, 0.1)'
    },
    fontSize: {
      xs: 10,
      sm: 12,
      md: 14,
      lg: 16
    }
  };
  
  export const formatChartData = (data: any[], xKey: string, yKey: string) => {
    return data.map(item => ({
      name: item[xKey],
      value: item[yKey]
    }));
  };
  
  export const generateMockUsageData = (days: number = 7) => {
    const data = [];
    const now = new Date();
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      data.push({
        name: date.toLocaleDateString('en-US', { weekday: 'short' }),
        date: date.toISOString().split('T')[0],
        requests: Math.floor(Math.random() * 1000) + 1000,
        cost: Math.random() * 50 + 25,
        savings: Math.random() * 20 + 5
      });
    }
    
    return data;
  };