import React, { useState, useRef, useCallback } from 'react';

// Components
import UploadWindow from './component/upload_window';
import SelectWindow from './component/select_window';
import TenstackTable from './component/tanstack_table';
import Pagination from './component/pagination';
import AnalysisTab from './component/analysis_tab';
// import Chatbot from './component/chatbot';
import AboutProject from './component/about_project';

// hooks
import { useResizableSidebar } from './hooks/useResizableSidebar';
import { TaskProvider } from './context/useTaskContext';
import { DataProvider, useDataContext } from './context/useDataContext';
import { UIProvider } from './context/useUIcontext';
import { ChatWebsocketProvider } from './context/useChatWebsocket';

// icons
import pageHomeToggleIcon from './assets/question.png';
import pageBrowserToggleIcon from './assets/browser.png';
import databaseTableIcon from './assets/folder.png';
import chatBotIcon from './assets/chatbotA.png';
import graphIcon from './assets/curve.png';
import sidepanelIcon from './assets/hide.png';


function App() {

  return (
    <ChatWebsocketProvider url="ws://localhost:8000/ws/chat-client">
      <UIProvider>
        <TaskProvider>
            <DataProvider>
                <AppContent />
            </DataProvider>
        </TaskProvider>
      </UIProvider>
    </ChatWebsocketProvider>
  );
}
function AppContent() {
  const { currentTable } = useDataContext();
  
  // Sidebar and resizing
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const { sidebarWidth, handleMouseDown } = useResizableSidebar(440, setSidebarOpen, sidebarOpen);
  const sidebarContentRef = useRef<HTMLDivElement | null>(null);
  const [selectedSidebarContent, setSelectedSidebarContent] = useState<string>('table');

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Table visibility
  const [showTable, setShowTable] = useState<boolean>(false);

  const toggleTableVisibility = () => {
    setShowTable((prev) => !prev);
  };

  const isEnabled = currentTable !== null;


  return (
    <div className="App">
      <div className={`sidebar ${sidebarOpen ? '' : 'sidebar-closed'}`} style={{ width: `${sidebarWidth}px` }}>


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
            <AnalysisTab />
          </div>
        )}

        <div className="sidebar-options">
          <button className="sidebar-table-button" onClick={() => selectedSidebarContent === 'table' ? toggleSidebar() : setSelectedSidebarContent('table')}>
            <img src={databaseTableIcon} alt="Table Options" />
          </button>
          <button className="sidebar-graph-button" 
            onClick={() => selectedSidebarContent === 'graph' ? toggleSidebar() : setSelectedSidebarContent('graph')}
            disabled={!isEnabled}
          >
            <img src={graphIcon} alt="Graph Options" />
          </button>
          
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
        {showTable && < TenstackTable /> }
        {showTable && < Pagination /> }
        {!showTable && <AboutProject />}


      </div>
    </div>
  );
}

export default App;
