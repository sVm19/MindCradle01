import mixpanel from 'mixpanel-browser';

const MIXPANEL_TOKEN = import.meta.env.VITE_MIXPANEL_TOKEN || '40463eebaef314c16e491842f0a591ae';

/**
 * Initializes Mixpanel.
 * @param consentRequired If true, sets opt_out_tracking_by_default to true.
 */
export const initMixpanel = (consentRequired: boolean) => {
  mixpanel.init(MIXPANEL_TOKEN, {
    debug: import.meta.env.DEV,
    track_pageview: false,
    opt_out_tracking_by_default: consentRequired,
  });
};

export { mixpanel };
