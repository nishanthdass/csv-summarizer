import React, { useState, useRef, useCallback, useEffect } from 'react';

// Components
import UploadWindow from './component/upload_window';
import SelectCsvWindow from './component/select_csv_window';
import SelectPdfWindow from './component/select_pdf_window';
import TenstackTable from './component/tanstack_table';
import Pagination from './component/pagination';
import AnalysisTab from './component/analysis_tab';
import AboutProject from './component/about_project';
import PdfViewer from './component/pdf_viewer';

// hooks
import { useResizableSidebar } from './hooks/useResizableSidebar';
import { SessionProvider } from './context/useSessionContext';
import { TaskProvider } from './context/useTaskContext';
import { DataProvider, useDataContext } from './context/useDataContext';
import { UIProvider } from './context/useUIcontext';
import { ChatWebsocketProvider } from './context/useChatWebsocket';

// icons
import pageHomeToggleIcon from './assets/question.png';
import pageHomeToggleIconOrange from './assets/question-orange.png';
import pageBrowserToggleIcon from './assets/csv.png';
import pageBrowserToggleIconOrange from './assets/csv-orange.png';
import databaseTableIcon from './assets/folder.png';
import chatBotIcon from './assets/chatbotA.png';
import graphIcon from './assets/curve.png';
import sidepanelIcon from './assets/hide.png';
import pdfToggleIcon from './assets/pdf-document.png';
import pdfToggleIconOrange from './assets/pdf-document-orange.png';
import { Session } from 'inspector';



function App() {

  return (
    
      <ChatWebsocketProvider url="ws://localhost:8000/ws/chat-client">
        <SessionProvider>
          <UIProvider>
            <TaskProvider>
                <DataProvider>
                    <AppContent />
                </DataProvider>
            </TaskProvider>
          </UIProvider>
        </SessionProvider>
      </ChatWebsocketProvider>
  );
}
function AppContent() {
  const { currentTable, currentPdf } = useDataContext();
  
  // Sidebar and resizing
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const { sidebarWidth, handleMouseDown } = useResizableSidebar(440, setSidebarOpen, sidebarOpen);
  const sidebarContentRef = useRef<HTMLDivElement | null>(null);
  const [selectedSidebarContent, setSelectedSidebarContent] = useState<string>('table');

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Component visibility
  const [showAboutProject, setShowAboutProject] = useState<boolean>(true);
  const [showTable, setShowTable] = useState<boolean>(false);
  const [showPdf, setShowPdf] = useState<boolean>(false);

  const toggleAboutProjectVisibility = () => {
    if (!showAboutProject) {
      setShowTable(false);
      setShowPdf(false);
      setShowAboutProject((prev) => !prev);
    }
  };

  const toggleTableVisibility = () => {
    if (!showTable) {
      setShowAboutProject(false);
      setShowPdf(false);
      setShowTable((prev) => !prev);
    }
  };

  const togglePdfVisibility = () => {
    if (!showPdf) {
      setShowAboutProject(false);
      setShowTable(false);
      setShowPdf((prev) => !prev);
    }
  };

  // const isEnabled = currentTable !== null;

  // useEffect(() => {
  //   console.log("Current Pdf: ", currentPdf);
  //   console.log("Show PDF: ", showPdf);
  //   console.log("Show About Project: ", showAboutProject);
  //   console.log("Show Table: ", showTable);
  // }, [currentPdf, showPdf, showAboutProject, showTable]);


  return (
    <div className="App">
      <div className={`sidebar ${sidebarOpen ? '' : 'sidebar-closed'}`} style={{ width: `${sidebarWidth}px` }}>


        {selectedSidebarContent === 'table' && (
          <div className="sidebar-tables" ref={sidebarContentRef}>
            <div className="upload-section">
              <h2>Upload CSV & PDF Files</h2>
                <UploadWindow />
            </div>
            <div className="load-csv-section">
              <h2>Select CSV File</h2>
                <SelectCsvWindow setShowTable={setShowTable}/>
            </div>
            <div className="load-csv-section">
              <h2>Select PDF File</h2>
                <SelectPdfWindow setShowPdf={setShowPdf}/>
            </div>
          </div>
        )}
        {selectedSidebarContent === 'graph' && (
          <div className="sidebar-graph" ref={sidebarContentRef}>
            <h2>Chatbot</h2>
            <AnalysisTab />
          </div>
        )}

        <div className="sidebar-options">
          <button className="sidebar-table-button" onClick={() => selectedSidebarContent === 'table' ? toggleSidebar() : setSelectedSidebarContent('table')}>
            <img src={databaseTableIcon} alt="Table Options" />
          </button>
          <button className="sidebar-graph-button" 
            onClick={() => selectedSidebarContent === 'graph' ? toggleSidebar() : setSelectedSidebarContent('graph')}
          >
            <img src={graphIcon} alt="Graph Options" />
          </button>
          
          <div className="sidebar-bottom-options">  


            {currentTable && (
              <div className="page-toggle-button" onClick={toggleTableVisibility}>
                <div className='toggle-icon-container'>
                <img
                  src={pageBrowserToggleIcon}
                  alt="Toggle page"
                  className={`toggle-icon ${showTable ? 'fade-out' : 'fade-in'}`}
                />
                <img
                  src={pageBrowserToggleIconOrange}
                  alt="Toggle page"
                  className={`toggle-icon ${!showTable ? 'fade-out' : 'fade-in'}`}
                />
                </div>
              </div>
            )}
            {!currentTable && (
              <div className="page-toggle-button grayed-out">
                <div className='toggle-icon-container'>
                  <img src={pageBrowserToggleIcon} alt="Toggle page" />
                </div>
              </div>
            )}

            {currentPdf && (
              <div className="page-toggle-button" onClick={togglePdfVisibility}>
                <div className='toggle-icon-container'>
                <img
                  src={pdfToggleIcon}
                  alt="Toggle page"
                  className={`toggle-icon ${showPdf ? 'fade-out' : 'fade-in'}`}
                />
                <img
                  src={pdfToggleIconOrange}
                  alt="Toggle page"
                  className={`toggle-icon ${!showPdf ? 'fade-out' : 'fade-in'}`}
                />
                </div>
              </div>
            )}
            {!currentPdf && (
              <div className="page-toggle-button grayed-out">
                <div className='toggle-icon-container'>
                  <img src={pdfToggleIcon} alt="Toggle page" />
                </div>
              </div>
            )}

              <div className="page-toggle-button" onClick={toggleAboutProjectVisibility}>
                <div className='toggle-icon-container'>
                <img
                  src={pageHomeToggleIconOrange}
                  alt="Toggle page"
                  className={`toggle-icon ${!showAboutProject ? 'fade-out' : 'fade-in'}`}
                />
                <img
                  src={pageHomeToggleIcon}
                  alt="Toggle page"
                  className={`toggle-icon ${showAboutProject ? 'fade-out' : 'fade-in'}`}
                />
                </div>
              </div>


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
        {showPdf && <PdfViewer />}
        {showAboutProject && <AboutProject />}


      </div>
    </div>
  );
}

export default App;
