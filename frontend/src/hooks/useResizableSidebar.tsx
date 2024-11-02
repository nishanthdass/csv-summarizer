import { set } from 'lodash';
import { useState, useCallback, useEffect } from 'react';

export function useResizableSidebar(initialWidth: number, setSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>, sidebarOpen: boolean) {
  const [sidebarWidth, setSidebarWidth] = useState(initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const [startX, setStartX] = useState(0); // To track initial mouse position
  const [prevPosition, setPrevPosition] = useState(null as number | null);

  useEffect(() => {
    if (!sidebarOpen) {
      setPrevPosition(sidebarWidth);
      setSidebarWidth(initialWidth);

    } else {
      setSidebarWidth(prevPosition || initialWidth);
    }
  }, [sidebarOpen, initialWidth]);


  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsResizing(true);
    setStartX(e.clientX); // Capture the initial mouse X position
    document.body.style.userSelect = 'none';
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (isResizing) {
        const dx = e.clientX - startX; // Difference in X position from initial position
        const newWidth = sidebarWidth + dx; // Update sidebar width based on the mouse movement

        if (newWidth <= 2800) {
          setSidebarWidth(newWidth);
          setStartX(e.clientX);
        }

        if (newWidth < 420) {
          console.log('Sidebar closed');
          handleMouseUp();
          setSidebarOpen(false);
          setSidebarWidth(newWidth + 50);
        }
      }
    },
    [isResizing, sidebarWidth, startX, setSidebarOpen]
  );

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
    document.body.style.userSelect = 'auto'; // Re-enable text selection after resizing
  }, []);

  useEffect(() => {
    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  return { sidebarWidth, handleMouseDown };
}
