import { set } from 'lodash';
import React, { useEffect, useState } from 'react';

type SelectWindowProps = {
  tables: string[]; // Accept an array of strings instead of File[]
  onTableSelect: (tableName: string) => void; // Updated to handle string
  onDeleteTable: (tableName: string) => void;
};

const SelectWindow: React.FC<SelectWindowProps> = ({ tables, onTableSelect, onDeleteTable }) => {
  const [table, setTable] = useState<string | null>(null);
  const [deleteTable, setDeleteTable] = useState<string | null>(null);

  


  useEffect(() => {
    if (table) {
      // console.log("Selected table:", table);
      onTableSelect(table);  // Pass the selected file to the parent component
    }
  }, [table]);
  
  useEffect(() => {
    if (deleteTable) {
      // console.log("Delete table:", deleteTable);
      onDeleteTable(deleteTable);
      setDeleteTable(null);
      if (table === deleteTable) {
        console.log(table, deleteTable);
        setTable(null);
        
      }

    }
  }, [deleteTable]);

  return (
      <div className="file-list-container">
        {tables.length > 0 ? (
          <ul className="file-list">
            {tables.map((f, index) => (
              <li className={(f === table ? "file-item-selected" : "file-item")}
                  key={index} 
                  onClick={() => setTable(f)}>
                    {String(f)}
                    <div className="delete-file-icon" onClick={(event) => {event.stopPropagation(); setDeleteTable(f)}}>X</div>
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
