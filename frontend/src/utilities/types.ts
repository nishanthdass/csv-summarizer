
export type TableData = {
    header: { [key: string]: string };
    rows: any[];
    page: number;
    page_size: number;
    total_rows: number;
    total_pages: number;
  };
  

export type TenstackTableProps = {
    tableName: string;
    table: { 
      header: { [key: string]: string }; 
      rows: any[]; 
      page: number; 
      page_size: number; 
      total_rows: number; 
      total_pages: number;
    };
    fetchData: (page: number, pageSize: number) => void;
    zoomLevel: number;
  };
  
export type AiContextObject = {
    tableName: string;
    column: string;
    row: number;
    value: any;
  };
  