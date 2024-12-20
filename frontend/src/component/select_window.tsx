import React, { useEffect, useState, useRef } from 'react';
import { useTasks } from '../context/useTaskContext'
import { useDataContext } from '../context/useDataContext';
import { useTableUploadSelect } from '../hooks/useTableUploadSelect';


const SelectWindow = ({ setShowTable } : { setShowTable: React.Dispatch<React.SetStateAction<boolean>> }) => {
  const { tables, currentTable, setCurrentTable } = useDataContext();
  const { tasks, removeTask } = useTasks(); // Access polling state directly
  const { loadAssistant, loadTableFromDatabase, loadTablesFromDatabase, removeTableFromDatabase, reinitiateThread } = useTableUploadSelect();

  useEffect(() => {
    loadTablesFromDatabase();
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


  const handleTableClick = async (tableName: string) => {
    await loadTableFromDatabase(tableName);
    setCurrentTable(tableName);
    setShowTable(true)
  };

  return (
      <div className="file-list-container">
        {Object.keys(tables).length > 0 ? (
          <ul className="file-list">
            {Object.entries(tables).map(([name], index) => (
              <li className={(name === currentTable?.name ? "file-item-selected" : "file-item")}
                key={index} 
                  onClick={() => handleTableClick(name)}
                  >
                    {String(name)}
                    <div className="file-icon" >
                      {isLoading(name) ? (
                        <span className="loader"></span>
                      ) 
                      : (
                        <>
                        <span className="delete-icon" onClick={(event) => {event.stopPropagation(); setShowTable(false); removeTableFromDatabase(name);}}>X</span>
                        <span className="Reinitiate-thread" onClick={(event) => {event.stopPropagation(); reinitiateThread(name);}}> O </span>
                        </>
                      )}
                    </div>
              </li>
            ))}
          </ul>
        ) : (
          <p>No tables found</p>
        )}
      </div>
  );
};

export default SelectWindow;
