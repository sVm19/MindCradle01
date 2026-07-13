import { createRoot } from "react-dom/client";
import App from "./app/App.tsx";
import "./styles/index.css";
import ReactGA from 'react-ga4';

ReactGA.initialize('G-YOUR-GOOGLE-ANALYTICS-ID');


  createRoot(document.getElementById("root")!).render(<App />);

if ('serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js')
        .catch(err => {
          console.error('ServiceWorker registration failed: ', err);
        });
    });
  } else {
    // In development, unregister any active service worker to prevent caching dev assets
    navigator.serviceWorker.getRegistrations().then(registrations => {
      for (const registration of registrations) {
        registration.unregister().then(success => {
          if (success) {
            console.log('Unregistered active service worker for development mode');
          }
        });
      }
    });
  }
}

  