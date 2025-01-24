import React, { useEffect } from 'react';
import { useTasks } from '../context/useTaskContext'
import { useDataContext } from '../context/useDataContext';
import { useFileSidePanelOperations } from '../hooks/useFileSidePanelOperations';


interface SelectPdfWindowProps {
  togglePdfVisibility: () => void;
}

const SelectPdfWindow: React.FC<SelectPdfWindowProps> = ({ togglePdfVisibility }) => {
  const { pdfs, currentPdf, setCurrentPdf } = useDataContext();
  const { tasks, removeTask } = useTasks();
  const { loadPdfFromDatabase, loadPdfsFromDatabase, removePdfFromDatabase } = useFileSidePanelOperations();

  useEffect(() => {
    loadPdfsFromDatabase();
  }, []);

  // useEffect(() => {
  //   console.log("pdfs: ", pdfs);
  //   console.log("currentPdf: ", currentPdf);
  // }, [pdfs, currentPdf]);


  function isLoading(name: string): boolean {
    const task = tasks.find((task) => task.name === name);
    if (!task) {
      return false;
    }
    if (task) {
      return task.status !== "Completed" && task.status !== "Failed";
    }
    return false;
  }


  const handlePdfClick = async (pdfName: string) => {
    if (pdfName === currentPdf?.name) {
      loadPdfFromDatabase(null);
      setCurrentPdf(null);
      return;
    }
    loadPdfFromDatabase(pdfName);
    setCurrentPdf(pdfs[pdfName]);
    togglePdfVisibility();
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
                        <span className="delete-icon" onClick={(event) => {event.stopPropagation(); togglePdfVisibility(); removePdfFromDatabase(name) }}>X</span>
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
