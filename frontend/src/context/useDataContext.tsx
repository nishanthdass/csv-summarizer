import React, { createContext, useState, useContext } from 'react';
import TableEntity, { TableSelection } from '../utilities/TableEntity';
import PdfEntity from '../utilities/PdfEntity';
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

  pdfs: Record<string, PdfEntity>;
  setPdfs: React.Dispatch<React.SetStateAction<Record<string, PdfEntity>>>;
  currentPdf: PdfEntity | null;
  currentPdfName: string | null;
  setCurrentPdf: (pdfName: string | null) => void;
  get_pdf: (pdfName: string) => PdfEntity;

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
  const [pdfs, setPdfs] = useState<Record<string, PdfEntity>>({});
  
  const [currentTableName, setCurrentTableName] = useState<string | null>(null);
  const [currentPdfName, setCurrentPdfName] = useState<string | null>(null);

  const currentTable = currentTableName ? tables[currentTableName] : null;
  const currentPdf = currentPdfName ? pdfs[currentPdfName] : null;

  const get_table = (tableName: string) => get(tables, tableName);
  const get_pdf = (pdfName: string) => get(pdfs, pdfName);

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

        pdfs,
        setPdfs,
        currentPdf,
        currentPdfName,
        setCurrentPdf: setCurrentPdfName,
        get_pdf

      }}
    >
      {children}
    </DataContext.Provider>
  );
}


