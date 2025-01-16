import {  useEffect, useCallback } from 'react';
import { TableData } from '../../utilities/TableEntity';
import { PdfData } from '../../utilities/PdfEntity';

export const useFetchDataDatabase = () => {
  const fetchTables = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/get-tables');
      if (response.ok) {
        const data = await response.json();
        return data;
      } else {
        console.error('Error fetching tables');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  }, []);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);


  const fetchPdfs = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/get-pdfs');
      if (response.ok) {
        const data = await response.json();
        return data;
      } else {
        console.error('Error fetching pdfs');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  }, []);

  useEffect(() => {
    fetchPdfs();
  }, [fetchPdfs]);


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

  const fetchPdfData = useCallback(async (pdfName: string): Promise<PdfData> => {
    try {
      const response = await fetch('http://localhost:8000/get-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pdfName: pdfName}),
      });

      if (!response.ok) {
        throw new Error(`Error fetching table data: ${response.statusText}`);
      }

      const data: PdfData = await response.json();
      return data;
    } catch (error) {
      console.error('Error:', error);
      throw new Error('Failed to fetch table data');
    }
  }, []);

  return { fetchTables, fetchPdfs, fetchTableData, fetchPdfData };
};


