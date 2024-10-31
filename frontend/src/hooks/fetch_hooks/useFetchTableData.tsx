import { useState, useCallback } from 'react';
import { TableData } from '../../utilities/types';

export const useFetchTableData = () => {
  const [tableData, setTableData] = useState<TableData | null>(null);

  const fetchTableData = useCallback(async (tableName: string, page = 1, pageSize = 10) => {
    try {
      const response = await fetch('http://localhost:8000/get-table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table_name: tableName, page, page_size: pageSize }),
      });
      if (response.ok) {
        const data: TableData = await response.json();  // Specify the expected type here
        setTableData(data);
      } else {
        console.error('Error fetching table data');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  }, []);

  return { tableData, fetchTableData };
};
