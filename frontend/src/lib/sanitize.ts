import DOMPurify from 'dompurify';

export const sanitizeForDisplay = (text: string): string => {
    // For displaying user text in UI
    return DOMPurify.sanitize(text, { 
        ALLOWED_TAGS: [],  // No HTML
        ALLOWED_ATTR: [] 
    });
};

export const sanitizeForInput = (text: string): string => {
    // When user is editing
    return text.slice(0, 5000);  // Just limit length
};
