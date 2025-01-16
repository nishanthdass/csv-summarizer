// Context imports
import { useDataContext } from '../context/useDataContext';
import TableEntity from '../utilities/TableEntity';
import PdfEntity from '../utilities/PdfEntity';
// Fetch hooks
import { useFetchUploadDeleteFile } from './fetch_hooks/useFetchUploadDeleteFile';
import { useFetchDataDatabase } from './fetch_hooks/useFetchDataDatabase';

// Task polling 
import { useTasks } from '../context/useTaskContext';
import { get } from 'lodash';

export const useFileSidePanelOperations = () => {
  // Context
  const { tables, setTables, setCurrentTable, get_table, pdfs, setPdfs, setCurrentPdf, get_pdf} = useDataContext();

  // Fetch functions
  const { fetchPdfData, fetchTableData, fetchPdfs, fetchTables } = useFetchDataDatabase();
  const { fetchUploadFile, fetchDeleteFile } = useFetchUploadDeleteFile();


  const addFileToDatabase = async (file: File) => {
    try {
      const data = await fetchUploadFile(file);

    } catch (error) {
      console.error('Error adding table:', error);
      throw error;
    }
  };


  const removeTableFromDatabase = async (tableName: string) => {
    try {
      await fetchDeleteFile(tableName);
      setTables((prevTables) => {
        const updatedTables = { ...prevTables };
        delete updatedTables[tableName];
        return updatedTables;
      });
      await loadTablesFromDatabase();

    } catch (error) {
      console.error('Error removing table:', error);
      throw error;
    }
  };


  const removePdfFromDatabase = async (pdfName: string) => {
    try {
      await fetchDeleteFile(pdfName);
      setPdfs((prevPdfs) => {
        const updatedPdfs = { ...prevPdfs };
        delete updatedPdfs[pdfName];
        return updatedPdfs;
      });
      await loadPdfsFromDatabase();

    } catch (error) {
      console.error('Error removing table:', error);
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


  const loadPdfsFromDatabase = async () => {
    try {
      const pdfsFromApi = await fetchPdfs();
  
      setPdfs((prevPdfs) => {
        const updatedPdfs = { ...prevPdfs };
  
        pdfsFromApi.forEach((pdf: string) => {
          if (!updatedPdfs[pdf]) {
            updatedPdfs[pdf] = new PdfEntity(pdf);
          }
        });
  
        return updatedPdfs;
      });
  
    } catch (error) {
      console.error('Error loading pdfs:', error);
      throw error;
    }
  }


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


  const loadPdfFromDatabase = async (
    pdfName: string
  ): Promise<void> => {
    const table = get_pdf(pdfName);
  
    try {
      const pdfData = await fetchPdfData(pdfName);
  
      setPdfs((prefPdfs) => {
        const updatedPdf = {
          ...prefPdfs[pdfName],
        };
        return {
          ...prefPdfs,
          [pdfName]: updatedPdf,
        };
      });

    } catch (error) {
      console.error('Error loading table:', error);
      throw error;
    }
  };
  
  
  return {  addFileToDatabase, 
            loadTablesFromDatabase, loadPdfsFromDatabase, 
            removeTableFromDatabase, removePdfFromDatabase, 
            loadTableFromDatabase, loadPdfFromDatabase
          };
};
