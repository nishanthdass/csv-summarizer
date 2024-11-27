import React, { useEffect, useState } from 'react';
import { useTasks } from '../context/useTaskContext'
import { useDataContext } from '../context/useDataContext';

const SelectWindow = ({ setShowTable } : { setShowTable: React.Dispatch<React.SetStateAction<boolean>> }) => {
  const { tables, setTables, currentTable, setCurrentTable, tableData, loadTableData, removeTable} = useDataContext();
  const [table, setTable] = useState<string | null>(null);
  const { pollingState } = useTasks(); // Access polling state directly

  useEffect(() => {
    if (table) {
      loadTableData(table);
      setShowTable(true);
    }
  }, [table]);
  

  return (
      <div className="file-list-container">
        {tables.length > 0 ? (
          <ul className="file-list">
            {tables.map((f: string, index: number) => (
              <li className={(f === table ? "file-item-selected" : "file-item")}
                  key={index} 
                  onClick={() => setTable(f)}>
                    {String(f)}
                    <div className="file-icon" >
                      {pollingState[f] ? (
                        <span className="loader"></span>
                      ) 
                      : (
                        <span className="delete-icon" onClick={(event) => {event.stopPropagation(); removeTable(f); setShowTable(false); setTable(null); setCurrentTable(null)}}>X</span>
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
