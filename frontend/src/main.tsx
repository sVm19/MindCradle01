import { createRoot } from "react-dom/client";
import App from "./app/App.tsx";
import "./styles/index.css";
import ReactGA from 'react-ga4';

ReactGA.initialize('G-YOUR-GOOGLE-ANALYTICS-ID');


  createRoot(document.getElementById("root")!).render(<App />);

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => {
        if (import.meta.env.DEV) {
          console.log('ServiceWorker registration successful with scope: ', reg.scope);
        }
      })
      .catch(err => {
        if (import.meta.env.DEV) {
          console.error('ServiceWorker registration failed: ', err);
        }
      });
  });
}

  