import { useState, useEffect } from 'react';
// Context imports
import { useDataContext } from '../context/useDataContext';
import TableEntity from '../utilities/TableEntity';

// Fetch hooks
import { useFetchLoadAssistant } from './fetch_hooks/useFetchLoadAssistant';
import { useFetchUploadTable } from './fetch_hooks/useFetchUploadTable';
import { useFetchTableData } from './fetch_hooks/useFetchTableData';
import { useFetchReinitiateThread } from './fetch_hooks/useFetchReinitiateThread';

import { useFetchTables } from './fetch_hooks/useFetchTables';
import { useDeleteTable } from './fetch_hooks/useDeleteTable';

// Task polling 
import { useTasks } from '../context/useTaskContext';



export const useTableUploadSelect = () => {

  // Context
  const { tables, setTables, setCurrentTable, get_table} = useDataContext();
  
  // Fetch functions
  const { fetchUploadTable } = useFetchUploadTable();
  const { fetchTableData } = useFetchTableData();
  const { fetchLoadAssistant } = useFetchLoadAssistant();
  const { fetchReinitiateThread } = useFetchReinitiateThread();
  const { fetchTables } = useFetchTables()
  const { deleteTable } = useDeleteTable();
  
  // Handles task polling
  const { addTask } = useTasks();

  const addTableToDatabase = async (file: File) => {
    try {
      const data = await fetchUploadTable(file);
      if (data?.task) {
        addTask({
          task_id: data.task.task_id,
          table_name: data.task.table_name,
          description: data.task.description,
          status: data.task.status,
          result: data.task.result,
        });
      }

    } catch (error) {
      console.error('Error adding table:', error);
      throw error;
    }
  };

  const loadTableFromDatabase = async (
    tableName: string,
    page?: number,
    pageSize?: number
  ): Promise<void> => {
    const table = get_table(tableName);

    const resolvedPage = page ?? table?.data.page;
    const resolvedPageSize = pageSize ?? table?.data.page_size;
  
    try {
      const tableData = await fetchTableData(tableName, resolvedPage, resolvedPageSize);
  
      setTables((prevTables) => {
        const updatedTable = {
          ...prevTables[tableName],
          data: tableData,
        };
        return {
          ...prevTables,
          [tableName]: updatedTable,
        };
      });

    } catch (error) {
      console.error('Error loading table:', error);
      throw error;
    }
  };
  
  const loadAssistant = async (tableName: string) => {
    try {
      const loadAssistant = await fetchLoadAssistant(tableName);

      console.log('loadAssistant:', loadAssistant);


    } catch (error) {
      console.error('Error loading summary data:', error);
      throw error;
    }


  };
  
  const loadTablesFromDatabase = async () => {
    try {
      const tablesFromApi = await fetchTables();
  
      setTables((prevTables) => {
        const updatedTables = { ...prevTables };
  
        tablesFromApi.forEach((table: string) => {
          if (!updatedTables[table]) {
            updatedTables[table] = new TableEntity(table);
          }
        });

        return updatedTables; // Return the combined result
      });

    } catch (error) {
      console.error('Error loading tables:', error);
      throw error;
    }
  };

  const removeTableFromDatabase = async (tableName: string) => {
    try {

      await deleteTable(tableName);
      setTables((prevTables) => {
        const updatedTables = { ...prevTables };
        delete updatedTables[tableName];
        return updatedTables;
      });
      await loadTablesFromDatabase();
      setCurrentTable(null);

    } catch (error) {
      console.error('Error removing table:', error);
      throw error;
    }
  };

  const reinitiateThread = async (tableName: string) => {
    try {
      await fetchReinitiateThread(tableName);
    } catch (error) {
      console.error('Error reinitiating thread:', error);
      throw error;
    }
  };
  

  return { addTableToDatabase, loadTableFromDatabase, loadAssistant, loadTablesFromDatabase, removeTableFromDatabase, reinitiateThread };
};
