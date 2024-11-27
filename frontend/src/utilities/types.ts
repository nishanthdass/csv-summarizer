
export type TableData = {
    header: { [key: string]: string };
    rows: any[];
    page: number;
    page_size: number;
    total_rows: number;
    total_pages: number;
  };

  export type TableSummaryData = {
    table_name: string;
    results: Record<string, any>; // Object with keys as column names
  };
  

export type TenstackTableProps = {
    zoomLevel: number;
  };
  
export type TableRowContextObject = {
    currentTable: string | null;
    column: string;
    row: number;
    value: any;
    tenstackRowNumber?: number | null;
  };

export type TableColumnContextObject = {
    currentTable: string;
    column: string;
    columnIndex: number;
  };

export interface Task {
  task_id: string;
  table_name: string;
  description: string;
  status: string;
  result?: any;
}