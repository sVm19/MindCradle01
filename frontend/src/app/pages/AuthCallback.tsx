import { useEffect } from 'react';
import { useNavigate } from 'react-router';

export default function AuthCallback() {
  const navigate = useNavigate();
  
  useEffect(() => {
    navigate('/', { replace: true });
  }, [navigate]);
  
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center bg-bg text-text">
      <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin mb-4" />
      <p className="text-sm font-medium tracking-wide opacity-80">Completing sign in...</p>
    </div>
  );
}
