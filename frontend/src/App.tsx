import React, { useState, useRef, useCallback } from 'react';
import UploadWindow from './component/upload_window';
import SelectWindow from './component/select_window';
import TenstackTable from './component/tanstack_table';
import Pagination from './component/pagination';
import AnalysisTab from './component/analysis_tab';
import Chatbot from './component/chatbot';
import AboutProject from './component/about_project';
import { useResizableSidebar } from './hooks/useResizableSidebar';
import { TaskProvider } from './context/useTaskContext';
import { DataProvider, useDataContext } from './context/useDataContext';
import pageHomeToggleIcon from './assets/question.png';
import pageBrowserToggleIcon from './assets/browser.png';
import databaseTableIcon from './assets/folder.png';
import chatBotIcon from './assets/chatbotA.png';
import graphIcon from './assets/curve.png';
import sidepanelIcon from './assets/hide.png';


function App() {
  return (
    <TaskProvider>
        <DataProvider>
            <AppContent />
        </DataProvider>
    </TaskProvider>
  );
}
function AppContent() {
  const { currentTable } = useDataContext();
  
  // Sidebar and resizing
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const { sidebarWidth, handleMouseDown } = useResizableSidebar(440, setSidebarOpen, sidebarOpen);
  const sidebarContentRef = useRef<HTMLDivElement | null>(null);
  

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Zoom state
  const [zoomLevel, setZoomLevel] = useState(1);
  const handleZoomIn = useCallback(() => setZoomLevel((prev) => Math.min(prev + 0.1, 2)), []);
  const handleZoomOut = useCallback(() => setZoomLevel((prev) => Math.max(prev - 0.1, 0.5)), []);
  const handleResetZoom = useCallback(() => setZoomLevel(1), []);


  const [table, setTable] = useState<string | null>(null);
  const [showTable, setShowTable] = useState<boolean>(false);

  const toggleTableVisibility = () => {
    setShowTable((prev) => !prev);
  };

  // Sidebar content selection
  const [selectedSidebarContent, setSelectedSidebarContent] = useState<string>('table');

  return (
    <div className="App">
      <div className={`sidebar ${sidebarOpen ? '' : 'sidebar-closed'}`} style={{ width: `${sidebarWidth}px` }}>
        {/* Conditional rendering for sidebar content based on selectedSidebarContent */}
        {selectedSidebarContent === 'table' && (
          <div className="sidebar-tables" ref={sidebarContentRef}>
            <div className="upload-section">
              <h2>Upload CSV File</h2>
                <UploadWindow />
            </div>
            <div className="load-csv-section">
              <h2>Select CSV File</h2>
                <SelectWindow setShowTable={setShowTable}/>
            </div>
          </div>
        )}
        
        {selectedSidebarContent === 'graph' && (
          <div className="sidebar-graph" ref={sidebarContentRef}>
            <h2>Insights and Analysis</h2>
            <AnalysisTab table={currentTable} />
          </div>
        )}
        {selectedSidebarContent === 'chatBot' && (
          <div className="sidebar-chat-bot" ref={sidebarContentRef}>
            <div className="chat-messages">
              <h2>Chatbot</h2>
              { table ? 
                <Chatbot table={table} /> : 
                <>
                <h4>Please select a table to start interacting with the chatbot</h4>
                <SelectWindow setShowTable={setShowTable} />
                </>
              }
            </div>
          </div>
        )}
        <div className="sidebar-options">
          {/* Each button sets the selectedSidebarContent to display the respective content */}
          <div className="sidebar-table-button" onClick={() => selectedSidebarContent === 'table' ? toggleSidebar() : setSelectedSidebarContent('table')}>
            <img src={databaseTableIcon} alt="Table Options" />
          </div>
          <div className="sidebar-graph-button" onClick={() => selectedSidebarContent === 'graph' ? toggleSidebar() : setSelectedSidebarContent('graph')}>
            <img src={graphIcon} alt="Graph Options" />
          </div>
          <div className="sidebar-chat-button" onClick={() => selectedSidebarContent === 'chatBot' ? toggleSidebar() : setSelectedSidebarContent('chatBot')}>
            <img src={chatBotIcon} alt="Chat Bot Options" />
          </div>
          <div className="sidebar-bottom-options">
            {currentTable && (
              <div className="page-toggle-button" onClick={toggleTableVisibility}>
                {showTable ? <img src={pageHomeToggleIcon} alt="Toggle page" /> 
                : 
                <img src={pageBrowserToggleIcon} alt="Toggle page" />}
              </div>
            )}
            {!currentTable && (
              <div className="page-toggle-button grayed-out">
                <img src={pageHomeToggleIcon} alt="Toggle page"/>
              </div>
            )}
            <div className='sidebar-toggle-button' onClick={toggleSidebar}>
              <img src={sidepanelIcon} alt="Toggle Sidebar" style={{ transform: sidebarOpen ? 'scaleX(1)' : 'scaleX(-1)' }} />
            </div>
          </div>
        </div>
        <div className={`resizer${sidebarOpen ? '' : ' resizer-closed'}`} {...(sidebarOpen ? { onMouseDown: handleMouseDown } : {})}></div>
      </div>
      <div className="main-content" style={{ marginLeft: sidebarOpen ? '0px' : `calc(-${sidebarWidth}px + 30px)` }}>
        {showTable && < TenstackTable zoomLevel={zoomLevel} /> }
        {showTable && (
          <Pagination
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onResetZoom={handleResetZoom}
          />
        )}
        {!showTable && <AboutProject />}
      </div>
    </div>
  );
}

export default App;
