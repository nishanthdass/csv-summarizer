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


  const fetchTableData = useCallback(async (tableName: string | null, page: number | null, pageSize: number | null): Promise<TableData> => {
    try {
      const response = await fetch('http://localhost:8000/get-table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
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


  const fetchSetPdfData = useCallback(async (pdfName: string | null): Promise<PdfData> => {
    try {
      const response = await fetch(`http://localhost:8000/set-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ pdf_name: pdfName }),
      });
      if (!response.ok) {
        throw new Error(`Error fetching PDF data: ${response.statusText}`);
      }


      const data : PdfData = await response.json();
      return data;
    } catch (error) {
      console.error('Error:', error);
      throw new Error('Failed to fetch PDF data');
    }
  }, []);

  const fetchStartChat = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/chat-server', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error(`Error fetching chat data: ${response.statusText}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error:', error);
      throw new Error('Failed to fetch chat data');
    }
  }, []);

  const fetchRunSQLQuery = useCallback(async (message: string, table_name: string, role: string) => {
    try {
      const response = await fetch('http://localhost:8000/sql-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ query: message, table_name: table_name, role: role }),
      });
      if (!response.ok) {
        throw new Error(`Error fetching SQL query: ${response.statusText}`);
      }
      const data = await response.json();
      console.log("Response: ", data);
      return data;
    } catch (error) {
      console.error('Error:', error);
      throw new Error('Failed to fetch SQL query');
    }
  }, []);
  
  
  return { fetchTables, fetchPdfs, fetchTableData, fetchSetPdfData, fetchStartChat, fetchRunSQLQuery};
};

