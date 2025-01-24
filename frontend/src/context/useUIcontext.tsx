import React, { createContext, useContext, useState } from 'react';


interface UIContextType {
    tableZoomLevel: Record<string, number>;
    settableZoomLevel: React.Dispatch<React.SetStateAction<Record<string, number>>>
}

const UIContext = createContext<UIContextType | undefined>(undefined);

export function useUIContext() {
  const context = useContext(UIContext);
  if (!context) {
    throw new Error('useUIContext must be used within a UIProvider');
  }
  return context;
}

export function UIProvider({ children }: { children: React.ReactNode }) {
    const [tableZoomLevel, settableZoomLevel] = useState<Record<string, number>>({});

  return (
    <UIContext.Provider
      value={{
        tableZoomLevel,
        settableZoomLevel,
      }}
    >
      {children}
    </UIContext.Provider>
  );
}
