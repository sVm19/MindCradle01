import React, { createContext, useContext, useEffect, useRef } from 'react';
import { useLocation } from 'react-router';
import { useAuth } from '@/lib/auth';
import { ai } from '@/lib/api';

const TelemetryContext = createContext<null>(null);

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  const locationRef = useRef(location.pathname);

  // Track page navigation changes
  useEffect(() => {
    locationRef.current = location.pathname;
    if (!user) return;

    ai.trackInteraction({
      event_type: 'navigation',
      page_path: location.pathname,
      metadata: { referrer: document.referrer },
    }).catch((err) => console.error('Failed to log navigation telemetry:', err));
  }, [location.pathname, user]);

  // Global click event listener
  useEffect(() => {
    if (!user) return;

    const handleGlobalClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      // Capture interactive elements (buttons, anchors, tabs, items with custom actions)
      const interactiveEl = target.closest('button, a, [role="button"], [data-telemetry]');
      if (!interactiveEl) return;

      const elementId = interactiveEl.id || undefined;
      const pagePath = locationRef.current;
      
      // Get element name/label securely
      let elementName = interactiveEl.getAttribute('aria-label') || 
                        interactiveEl.getAttribute('title') || 
                        interactiveEl.textContent?.trim().slice(0, 50) || 
                        interactiveEl.tagName.toLowerCase();
      
      elementName = elementName.replace(/\s+/g, ' ').trim();

      ai.trackInteraction({
        event_type: 'click',
        element_id: elementId,
        element_name: elementName,
        page_path: pagePath,
      }).catch((err) => console.error('Failed to log click telemetry:', err));
    };

    // Global input/textarea blur event listener to capture inputs and placeholders
    const handleInputBlur = (event: FocusEvent) => {
      const target = event.target as HTMLInputElement | HTMLTextAreaElement;
      if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') return;
      if (target.type === 'password') return;

      const placeholder = target.placeholder || target.name || target.id || 'anonymous_field';
      const inputLength = target.value.length;
      if (inputLength === 0) return;

      const pagePath = locationRef.current;

      ai.trackInteraction({
        event_type: 'input_submit',
        page_path: pagePath,
        input_placeholder: placeholder,
        input_length: inputLength,
        metadata: {
          field_type: target.type || 'text',
        }
      }).catch((err) => console.error('Failed to log input telemetry:', err));
    };

    window.addEventListener('click', handleGlobalClick, true);
    window.addEventListener('blur', handleInputBlur, true);

    return () => {
      window.removeEventListener('click', handleGlobalClick, true);
      window.removeEventListener('blur', handleInputBlur, true);
    };
  }, [user]);

  return <TelemetryContext.Provider value={null}>{children}</TelemetryContext.Provider>;
}

export const useTelemetry = () => useContext(TelemetryContext);
