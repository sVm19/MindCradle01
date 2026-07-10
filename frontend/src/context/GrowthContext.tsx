import React, { createContext, useContext, useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { growth, ActiveAssignment } from '@/lib/api';

interface GrowthContextType {
  assignments: Record<string, string>;
  isLoading: boolean;
  variantOf: (experimentName: string, defaultVariant: string) => string;
  trackEvent: (eventName: string, properties?: Record<string, any>) => Promise<boolean>;
}

const GrowthContext = createContext<GrowthContextType | undefined>(undefined);

export const GrowthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Fetch active A/B test assignments when authenticated user changes
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!user) {
        setAssignments({});
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const response = await growth.getActiveAssignments();
        const assignmentsMap: Record<string, string> = {};
        if (response && response.assignments) {
          response.assignments.forEach((item: ActiveAssignment) => {
            assignmentsMap[item.experiment_name] = item.variant;
          });
        }
        setAssignments(assignmentsMap);
      } catch (error) {
        console.error('Failed to load growth assignments:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAssignments();
  }, [user]);

  // Resolve assigned variant of an experiment
  const variantOf = (experimentName: string, defaultVariant: string): string => {
    return assignments[experimentName] || defaultVariant;
  };

  // Track event telemetry helper
  const trackEvent = async (eventName: string, properties: Record<string, any> = {}): Promise<boolean> => {
    if (!user) return false;
    try {
      // Inject standard properties
      const enrichedProperties = {
        ...properties,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        referrer: document.referrer,
      };
      
      // Auto-inject any active experiment context if name matches
      Object.entries(assignments).forEach(([expName, variant]) => {
        if (eventName.includes(expName) || expName.includes(eventName)) {
          enrichedProperties['experiment_name'] = expName;
          enrichedProperties['variant'] = variant;
        }
      });

      await growth.trackEvent(eventName, enrichedProperties);
      return true;
    } catch (error) {
      console.error(`Failed to track growth event: ${eventName}`, error);
      return false;
    }
  };

  return (
    <GrowthContext.Provider value={{ assignments, isLoading, variantOf, trackEvent }}>
      {children}
    </GrowthContext.Provider>
  );
};

export const useGrowth = () => {
  const context = useContext(GrowthContext);
  if (!context) {
    throw new Error('useGrowth must be used within a GrowthProvider');
  }
  return context;
};
