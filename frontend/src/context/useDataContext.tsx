import React, { createContext, useState, useContext, useEffect } from 'react';
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
  get_pdf: (pdfName: string) => PdfEntity | undefined;
  currentPdf: PdfEntity | null;
  setCurrentPdf: React.Dispatch<React.SetStateAction<PdfEntity | null>>;

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
  const [tableSelections, setTableSelections] = useState<Record<string, TableSelection>>({});
  const currentTable = currentTableName ? tables[currentTableName] : null;
  const get_table = (tableName: string) => get(tables, tableName);


  const [pdfs, setPdfs] = useState<Record<string, PdfEntity>>({});
  const [currentPdf, setCurrentPdf] = useState<PdfEntity | null>(null);
  const get_pdf = (pdfName: string): PdfEntity | undefined => get(pdfs, pdfName);

  // useEffect(() => {
  //     console.log("pdfs: ", pdfs);
  //     console.log("currentPdf: ", currentPdf);
  //   }, [pdfs, currentPdf]);


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
        get_pdf,
        currentPdf,
        setCurrentPdf,
        

      }}
    >
      {children}
    </DataContext.Provider>
  );
}


