import React, { useEffect } from 'react';
import { useTasks } from '../context/useTaskContext'
import { useDataContext } from '../context/useDataContext';
import { useFileSidePanelOperations } from '../hooks/useFileSidePanelOperations';


const SelectPdfWindow = ({ setShowPdf } : { setShowPdf: React.Dispatch<React.SetStateAction<boolean>> }) => {
  const { pdfs, currentPdf, setCurrentPdf } = useDataContext();
  const { tasks, removeTask } = useTasks();
  const { loadPdfFromDatabase, loadPdfsFromDatabase, removePdfFromDatabase } = useFileSidePanelOperations();

  useEffect(() => {
    loadPdfsFromDatabase();
  }, []);

  function isLoading(name: string): boolean {
    const task = tasks.find((task) => task.table_name === name);
    if (!task) {
      return false;
    }
    if (task) {
      return task.status !== "Completed" && task.status !== "Failed";
    }
    return false;
  }


  const handlePdfClick = async (pdfName: string) => {
    await loadPdfFromDatabase(pdfName);
    setCurrentPdf(pdfName);
    setShowPdf(true)
  };

  return (
      <div className="file-list-container">
        {Object.keys(pdfs).length > 0 ? (
          <ul className="file-list">
            {Object.entries(pdfs).map(([name], index) => (
              <li className={(name === currentPdf?.name ? "file-item-selected" : "file-item")}
                key={index} 
                  onClick={() => handlePdfClick(name)}
                  >
                    {String(name)}
                    <div className="file-icon" >
                      {isLoading(name) ? (
                        <span className="loader"></span>
                      ) 
                      : (
                        <>
                        <span className="delete-icon" onClick={(event) => {event.stopPropagation(); setShowPdf(false); removePdfFromDatabase(name) }}>X</span>
                        </>
                      )}
                    </div>
              </li>
            ))}
          </ul>
        ) : (
          <p>No PDFs found</p>
        )}
      </div>
  );
};

export default SelectPdfWindow;
