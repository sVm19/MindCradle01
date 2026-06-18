export const validateEmail = (email: string): boolean => {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email) && email.length <= 255;
};

export const validatePassword = (password: string): string | null => {
  if (password.length < 8) return "Min 8 characters";
  if (!/[A-Z]/.test(password)) return "Need uppercase letter";
  if (!/[0-9]/.test(password)) return "Need number";
  if (!/[!@#$%^&*]/.test(password)) return "Need special character";
  return null;
};

export const validateMood = (mood: number): boolean => {
  return Number.isInteger(mood) && mood >= 1 && mood <= 10;
};

export const validateJournal = (text: string): boolean => {
  return text.length > 0 && text.length <= 5000;
};
