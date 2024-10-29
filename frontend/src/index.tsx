import React from 'react';
import ReactDOM from 'react-dom/client';  // Updated import for createRoot
import './App.css';
import App from './App';

// Get the root element from the DOM
const rootElement = document.getElementById('root');

// Create a root and render the app inside it
const root = ReactDOM.createRoot(rootElement as HTMLElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
