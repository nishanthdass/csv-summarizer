import React, { createContext, useState, useContext, useEffect } from 'react';
import { useFetchTables } from '../hooks/fetch_hooks/useFetchTables';
import { useFetchTableData } from '../hooks/fetch_hooks/useFetchTableData';
import { useFetchUploadTable } from '../hooks/fetch_hooks/useFetchUploadTable';
import { useDeleteTable } from '../hooks/fetch_hooks/useDeleteTable';
import { useTableSelection } from '../hooks/useTableSelection';
import { useFetchTableSummaryData } from '../hooks/fetch_hooks/useFetchTableSummary';
import { TableData, TableRowContextObject, TableSummaryData } from '../utilities/types';
import { useTasks } from '../context/useTaskContext'
import { set } from 'lodash';

interface DataContextType {
  tables: string[];
  setTables: React.Dispatch<React.SetStateAction<string[]>>;
  currentTable: string | null;
  setCurrentTable: React.Dispatch<React.SetStateAction<string | null>>;
  addTable: (file: File) => Promise<void>;
  tableData: TableData | null;
  setTableData: React.Dispatch<React.SetStateAction<TableData | null>>;
  loadTableData: (tableName: string, page?: number, pageSize?: number) => Promise<void>;
  removeTable: (tableName: string) => Promise<void>;
  refresh: () => Promise<void>;
  tableSelectArray: TableRowContextObject[];
  tableConversation: Record<string, string[]>
  handleCellClick: (
    column: string,
    row: number,
    value: any,
    isRowNumberColumn: boolean,
    tenstackRowNumber: number | null
  ) => void;
  handleColumnClick: (column: string, columnIndex: number) => void;
  ifExists: (column: string, tenstackRowNumber: number) => boolean;

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
  const [tables, setTables] = useState<string[]>([]);
  const [currentTable, setCurrentTable] = useState<string | null>(null);
  const [tableData, setTableData] = useState<TableData | null>(null);
  const [paginationSettings, setPaginationSettings] = useState<Record<string, { page: number; pageSize: number }>>({});
  const [summaries, setSummaries] = useState<Record<string, TableSummaryData>>({});
  const [tableConversation, setTableConversation] = useState<Record<string, string[]>>({});


  // Fetch Data
  const { refresh } = useFetchTables();
  const { fetchTableData } = useFetchTableData();
  const { fetchTableSummaryData } = useFetchTableSummaryData();
  const { fetchUploadTable } = useFetchUploadTable();
  const { deleteTable } = useDeleteTable(refresh);

  // Table cell row Selection
  const { tableSelectArray, columnSelectArray, handleCellClick, handleColumnClick, ifExists } = useTableSelection({ currentTable, tableRows: tableData?.rows || [] });

  const { pollingState } = useTasks();

  


  // Sets table on initial load and upload of file
  const loadTables = async () => {
    const data = await refresh();
    setTables(data);
  
    const summaryPromises = data.map(async (table: string) => {
      if (!summaries[table]) {
        const summary = await loadTableSummary(table);
        return { [table]: summary };
      } else if (summaries[table].results === null) {
        const summary = await loadTableSummary(table);
        return { [table]: summary };
      }
      return null; // Return null for tables we don't need to update
    });
  
    // Filter out null values
    const resolvedSummaries = (await Promise.all(summaryPromises)).filter(Boolean);
  
    setSummaries((prev) => ({
      ...prev,
      ...Object.assign({}, ...resolvedSummaries),
    }));
  };
  
  useEffect(() => {
    loadTables();
  }, [refresh, currentTable, pollingState]);


  useEffect(() => {
    for (const column of columnSelectArray) {
      setTableConversation((prev) => ({
        ...prev,
        [column.currentTable]: [
          ...(prev[column.currentTable] || []), 
          summaries[column.currentTable]?.results[column.column],
        ],
      }));
    }
  }, [summaries, columnSelectArray]);
  


  // Loads table data for the current table
  const loadTableData = async (tableName: string, pageOverride?: number, pageSizeOverride?: number) => {
    setCurrentTable(tableName);
    const tableSettings = paginationSettings[tableName] || { page: 1, pageSize: 10 };
    const resolvedPage = pageOverride ?? tableSettings.page;
    const resolvedPageSize = pageSizeOverride ?? tableSettings.pageSize;

    setPaginationSettings((prev) => ({
      ...prev,
      [tableName]: { page: resolvedPage, pageSize: resolvedPageSize },
    }));

    try {
      const data = await fetchTableData(tableName, resolvedPage, resolvedPageSize);
      setTableData((prev) => ({
        ...prev!,
        ...data,
      }));
    } catch (error) {
      console.error('Error loading table data:', error);
    }
  };

  // load table summary from database
  const loadTableSummary = async (tableName: string) => {
    try {
      const summary = await fetchTableSummaryData(tableName);
      return summary;
    } catch (error) {
      console.error('Error loading table summary:', error);
    }
  }
  

  // handles upload of table
  const addTable = async (file: File) => {
    try {
      await fetchUploadTable(file);
    } catch (error) {
      console.error('Error adding table:', error);
      throw error;
    }
  };

  // handles deletion of table
  const removeTable = async (tableName: string) => {
    await deleteTable(tableName);
    setTables((prev) => prev.filter((t) => t !== tableName));
    if (currentTable === tableName) {
      setCurrentTable(null);
      setTableData(null);
    }
    setPaginationSettings((prev) => {
      const { [tableName]: _, ...rest } = prev;
      return rest;
    });

    setSummaries((prev) => {
      const { [tableName]: _, ...rest } = prev;
      return rest;
    })
  };

  return (
    <DataContext.Provider
      value={{
        tables,
        setTables,
        currentTable,
        setCurrentTable,
        addTable,
        tableData,
        setTableData,
        loadTableData,
        removeTable,
        refresh: loadTables,
        tableSelectArray,
        tableConversation,
        handleCellClick,
        handleColumnClick,
        ifExists,
      }}
    >
      {children}
    </DataContext.Provider>
  );
}
