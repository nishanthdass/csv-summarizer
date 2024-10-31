import React, { useState, useRef, useCallback } from 'react';
import UploadWindow from './component/upload_window';
import SelectWindow from './component/select_window';
import TenstackTable from './component/tanstack_table';
import Pagination from './component/pagination';
import { useResizableSidebar } from './hooks/useResizableSidebar';
import { useFetchTables } from './hooks//fetch_hooks/useFetchTables';
import { useFetchTableData } from './hooks/fetch_hooks/useFetchTableData';
import sidepanelIcon from './assets/hide.png';
import { TableData } from './utilities/types';
import { tab } from '@testing-library/user-event/dist/tab';

function App() {
  // handle sidebar and resizing
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const { sidebarWidth, handleMouseDown } = useResizableSidebar(440, setSidebarOpen, sidebarOpen);
  const sidebarContentRef = useRef<HTMLDivElement | null>(null);
  
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  
  // handle zoom
  const [zoomLevel, setZoomLevel] = useState(1);
  const handleZoomIn = useCallback(() => setZoomLevel((prev) => Math.min(prev + 0.1, 2)), []);
  const handleZoomOut = useCallback(() => setZoomLevel((prev) => Math.max(prev - 0.1, 0.5)), []);
  const handleResetZoom = useCallback(() => setZoomLevel(1), []);


  // Fetch and set tables
  const { tables, refresh } = useFetchTables();
  const { tableData, fetchTableData } = useFetchTableData();
  const [ table, setTable] = useState<string | null>(null);

  const loadTable = (tableName: string) => {
    setTable(null);
    handleResetZoom();
    setTable(tableName);
    fetchTableData(tableName);
  };


  return (
    <div className="App">
      <div className={`sidebar ${sidebarOpen ? '' : 'sidebar-closed'}`} style={{ width: `${sidebarWidth}px` }}>
        <div className="sidebar-content" ref={sidebarContentRef}>
          <UploadWindow onSuccessfulUpload={refresh} />
          <SelectWindow tables={tables} onTableSelect={loadTable} />
        </div>
        <div className="sidebar-options">
          <div className="sidebar-button" onClick={toggleSidebar}>
            <img src={sidepanelIcon} alt="Toggle Sidebar" style={{ transform: sidebarOpen ? 'scaleX(1)' : 'scaleX(-1)' }} />
          </div>
        </div>
        <div className={`resizer${sidebarOpen ? '' : ' resizer-closed'}`} {...(sidebarOpen ? { onMouseDown: handleMouseDown } : {})}></div>
      </div>
      <div className="main-content" style={{ marginLeft: sidebarOpen ? '0px' : `calc(-${sidebarWidth}px + 20px)` }}>
        {table && tableData && (
          <TenstackTable
            tableName={table}
            table={tableData}
            fetchData={(page, pageSize) => fetchTableData(table!, page, pageSize)}
            zoomLevel={zoomLevel}
          />
        )}
        {table && (
          <Pagination
            currentPage={tableData?.page || 1}
            pageSize={tableData?.page_size || 10}
            totalPages={tableData?.total_pages || 1}
            onPageChange={(page: number) => fetchTableData(table!, page, tableData?.page_size)}
            onPageSizeChange={(pageSize: number) => fetchTableData(table!, tableData?.page, pageSize)}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onResetZoom={handleResetZoom}
          />
        )}
      </div>
    </div>
  );
}

export default App;
