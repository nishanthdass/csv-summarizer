import { useState, useCallback } from 'react';
import { TableSummaryData } from '../../utilities/types';

export const useFetchTableSummaryData = () => {
  const [tableSummaryData, setTableSummaryData] = useState<TableSummaryData | null>(null);

  const fetchTableSummaryData = useCallback(async (tableName: string): Promise<TableSummaryData> => {
    try {
      const response = await fetch('http://localhost:8000/get-table-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table_name: tableName }),
      });

      if (!response.ok) {
        throw new Error(`Error fetching table data: ${response.statusText}`);
      }

      const data: TableSummaryData = await response.json();
      return data;
    } catch (error) {
      console.error('Error:', error);
      throw new Error('Failed to fetch table data');
    }
  }, []);

  return { tableSummaryData, fetchTableSummaryData };
};
