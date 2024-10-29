import React, { useState, useEffect, useRef, useCallback } from 'react';
import UploadWindow from './component/upload_window';
import SelectWindow from './component/select_window';
import TenstackTable from './component/tanstack_table';
import Pagination from './component/pagination';
import { useResizableSidebar } from './hooks/useResizableSidebar';
import sidepanelIcon from './assets/hide.png';
import { set } from 'lodash';

type TableData = {
  header: { [key: string]: string };
  rows: any[];
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
};

function App() {
  const [tables, setTables] = useState<string[]>([]); // Use string[] for filenames
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const { sidebarWidth, handleMouseDown } = useResizableSidebar(440, setSidebarOpen, sidebarOpen);


  const [table, setTable] = useState<TableData>({
    header: {} as { [key: string]: string },
    rows: [],
    page: 1,
    page_size: 10,
    total_rows: 0,
    total_pages: 0,
  });

  const sidebarContentRef = useRef<HTMLDivElement | null>(null);


  const [zoomLevel, setZoomLevel] = useState(1);

  // Functions to update zoom level in response to external triggers
  const handleZoomIn = useCallback(() => setZoomLevel((prev) => Math.min(prev + 0.1, 2)), []);
  const handleZoomOut = useCallback(() => setZoomLevel((prev) => Math.max(prev - 0.1, 0.5)), []);
  const handleResetZoom = useCallback(() => setZoomLevel(1), []);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const get_tables = async () => {
    try {
      const request = await fetch('http://localhost:8000/get-tables', {
        method: 'GET',
      });
      if (request.ok) {
        const data = await request.json();
        setTables(data);
      } else {
        console.error('Error getting Tables');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };

  useEffect(() => {
    get_tables();
  }, []);

  const get_table = async (tableName: string, page: number = 1, pageSize: number = 10) => {
    setSelectedFile(null);
    handleResetZoom();
    setSelectedFile(tableName);

    try {
      const request = await fetch('http://localhost:8000/get-table', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ table_name: tableName, page, page_size: pageSize }),
      });
      if (request.ok) {
        const data = await request.json();
        setTable(data);
      } else {
        console.error('Error getting table');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };

  
  return (
    <div className="App">
      <div className={`sidebar ${sidebarOpen ? '' : 'sidebar-closed'}`} style={{ width: `${sidebarWidth}px` }}>
        <div className="sidebar-content" ref={sidebarContentRef}>
          <UploadWindow onSuccessfulUpload={get_tables} />
          <SelectWindow tables={tables} onTableSelect={(table_name) => get_table(table_name)} />
        </div>

        <div className="sidebar-options">
          <div className="sidebar-button" onClick={toggleSidebar}>
            <img
              src={sidepanelIcon}
              alt="Toggle Sidebar"
              style={{
                transform: sidebarOpen ? 'scaleX(1)' : 'scaleX(-1)',
                transition: 'transform 1s ease',
              }}
            />
          </div>
        </div>
        <div
          className={`resizer${sidebarOpen ? '' : ' resizer-closed'}`}
          {...(sidebarOpen ? { onMouseDown: handleMouseDown } : {})}
        ></div>
      </div>
      

      <div className="main-content" style={{ marginLeft: sidebarOpen ? '0px' : `calc(-${sidebarWidth}px + 20px)` }}>
        {selectedFile && (
            <TenstackTable
              tableName={selectedFile}
              table={table}
              fetchData={(page, pageSize) => get_table(selectedFile!, page, pageSize)}
              zoomLevel={zoomLevel}
            />
        )}

        {selectedFile && (
          <div className="pagination-container">
            <Pagination
              currentPage={table.page}
              pageSize={table.page_size}
              totalPages={table.total_pages}
              onPageChange={(page: number) => get_table(selectedFile!, page, table.page_size)}
              onPageSizeChange={(pageSize: number) => get_table(selectedFile!, table.page, pageSize)}
              onZoomIn={handleZoomIn}
              onZoomOut={handleZoomOut}
              onResetZoom={handleResetZoom}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
