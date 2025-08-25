// components/ProcessingAnimation.tsx - Simple processing animation
"use client";
import { useState, useEffect } from 'react';

interface ProcessingAnimationProps {
  steps: string[];
  isActive: boolean;
  onComplete?: () => void;
  stepDuration?: number;
}

export function ProcessingAnimation({ 
  steps, 
  isActive, 
  onComplete, 
  stepDuration = 800 
}: ProcessingAnimationProps) {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (!isActive) {
      setCurrentStep(0);
      return;
    }

    if (currentStep < steps.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStep(prev => prev + 1);
      }, stepDuration);

      return () => clearTimeout(timer);
    } else if (currentStep === steps.length - 1) {
      const timer = setTimeout(() => {
        onComplete?.();
      }, stepDuration);

      return () => clearTimeout(timer);
    }
  }, [currentStep, isActive, steps.length, stepDuration, onComplete]);

  if (!isActive) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-blue-400">
        <div className="w-5 h-5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
        <span className="text-sm font-medium">{steps[currentStep]}</span>
      </div>
      
      <div className="w-full bg-white/10 rounded-full h-2">
        <div 
          className="h-2 bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-300"
          style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
        />
      </div>
    </div>
  );
}