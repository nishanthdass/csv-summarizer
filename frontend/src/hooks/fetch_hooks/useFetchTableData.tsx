import { useState, useCallback } from 'react';
import { TableData } from '../../utilities/TableEntity';

export const useFetchTableData = () => {

  const fetchTableData = useCallback(async (tableName: string, page: number, pageSize: number): Promise<TableData> => {
    try {
      const response = await fetch('http://localhost:8000/get-table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table_name: tableName, page, page_size: pageSize }),
      });

      if (!response.ok) {
        throw new Error(`Error fetching table data: ${response.statusText}`);
      }

      const data: TableData = await response.json();
      return data;
    } catch (error) {
      console.error('Error:', error);
      throw new Error('Failed to fetch table data');
    }
  }, []);

  return { fetchTableData };
};
