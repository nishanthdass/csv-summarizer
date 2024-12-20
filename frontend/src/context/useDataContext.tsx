import React, { createContext, useState, useContext } from 'react';
import TableEntity, { TableSelection } from '../utilities/TableEntity';
import { get } from 'lodash';


interface DataContextType {
  tables: Record<string, TableEntity>;
  setTables: React.Dispatch<React.SetStateAction<Record<string, TableEntity>>>;
  currentTable: TableEntity | null;
  currentTableName: string | null;
  setCurrentTable: (tableName: string | null) => void;
  get_table: (tableName: string) => TableEntity;
  tableSelections: Record<string, TableSelection>;
  setTableSelections: React.Dispatch<React.SetStateAction<Record<string, TableSelection>>>;
}
const DataContext = createContext<DataContextType | undefined>(undefined);

export function useDataContext() {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error('useDataContext must be used within a DataProvider');
  }
  return context;
}

export function DataProvider({ children }: { children: React.ReactNode }) {

  // Set Tables
  const [tables, setTables] = useState<Record<string, TableEntity>>({});
  const [currentTableName, setCurrentTableName] = useState<string | null>(null);
  const currentTable = currentTableName ? tables[currentTableName] : null;
  const get_table = (tableName: string) => get(tables, tableName);

  const [tableSelections, setTableSelections] = useState<Record<string, TableSelection>>({});

  return (
    <DataContext.Provider
      value={{
        tables,
        setTables,
        currentTable,
        currentTableName,
        setCurrentTable: setCurrentTableName,
        get_table,
        tableSelections,
        setTableSelections,
      }}
    >
      {children}
    </DataContext.Provider>
  );
}


