import React, { useEffect, useState } from 'react';

type SelectWindowProps = {
  tables: string[]; // Accept an array of strings instead of File[]
  onTableSelect: (tableName: string) => void; // Updated to handle string
};

const SelectWindow: React.FC<SelectWindowProps> = ({ tables, onTableSelect }) => {
  const [table, setTable] = useState<string | null>(null);

  useEffect(() => {
    if (table) {
      onTableSelect(table);  // Pass the selected file to the parent component
    }
  }, [table]);

  return (
      <div className="file-list-container">
        {tables.length > 0 ? (
          <ul className="file-list">
            {tables.map((f, index) => (
              <li className={(f === table ? "file-item-selected" : "file-item")}
                  key={index} 
                  onClick={() => setTable(f)}>
                    {String(f)}
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
