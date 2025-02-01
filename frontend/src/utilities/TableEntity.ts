
export type TableData = {
  header: { [key: string]: string };
  rows: any[];
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
};


export interface TableSelection {
  selectedCells: TableCellContextObject[];
  selectedRows: TableRowContextObject[];
  selectedColumns: TableColumnContextObject[];
}


export type TableChatDataObject = {
  chat: string[];
}

export type TableColumnContextObject = {
  columnIndex: number;
  columnName: string;
  page: number;
};

export type TableRowContextObject = {
  ctid: string;
};

export type TableCellContextObject = {
  ctid: string | null;
  value: any | null;
  columnName: string | null;
};

export interface SetCellResponse {
  success: boolean;
  data: string[];
}


export default class TableEntity {
  name: string;
  data: TableData;
  header_summaries: { [key: string]: string } = {};

  constructor(name: string) {
    this.name = name;
    this.data = {
      header: {},
      rows: [],
      page: 1,
      page_size: 10,
      total_rows: 0,
      total_pages: 0,
    };
  }
}
