// src/hooks/useTableSelection.ts
import { useState } from 'react';
import { TableRowContextObject, TableColumnContextObject } from '../utilities/types';

type useTableSelectionParams = {
  currentTable: string | null;
  tableRows: any[];
};

// Main Hook
export const useTableSelection = ({ currentTable, tableRows }: useTableSelectionParams) => {
  const [tableSelectArray, setTableSelectArray] = useState<TableRowContextObject[]>([]);
  const [columnSelectArray, setColumnSelectArray] = useState<TableColumnContextObject[]>([]);

  const handleColumnClick = (column: string, columnIndex: number) => {
    if (!currentTable) {
      return;
    }
  
    setColumnSelectArray((prevArray) => {
      const newObject: TableColumnContextObject = { currentTable, column, columnIndex };
      const sameColumnExists = prevArray.some(
        (obj) => obj.currentTable === currentTable && obj.column === column
      );
      const anotherColumnExists = prevArray.some(
        (obj) => obj.currentTable === currentTable && obj.column !== column
      );
  
      if (anotherColumnExists) {
        return prevArray.map((obj) =>
          obj.currentTable === currentTable ? newObject : obj
        );
      } else if (sameColumnExists) {
        return prevArray.filter((obj) => obj.currentTable !== currentTable);
      }
      return [...prevArray, newObject];
    });
  };
  
  
  const handleCellClick = (
    column: string,
    row: number,
    value: any,
    isRowNumberColumn: boolean,
    tenstackRowNumber: number | null
  ) => {
    const rowData = tableRows[row];

    setTableSelectArray((prevArray) => {
      if (isRowNumberColumn) {
        // Full Row Selection Logic
        const allValuesExist = Object.entries(rowData).every(
          ([key]) =>
            doesObjectExistForColumn(prevArray, currentTable, key, tenstackRowNumber)
        );

        return allValuesExist
          ? filterRowByTableAndColumn(prevArray, currentTable, tenstackRowNumber)
          : [...prevArray, ...createRowEntries(rowData, currentTable, row, tenstackRowNumber, prevArray)];
      } else {
        // Single Cell Selection Logic
        const newObject: TableRowContextObject = { currentTable, column, row, value, tenstackRowNumber };
        const exists = doesObjectExistForColumn(prevArray, currentTable, column, tenstackRowNumber);

        return exists
          ? prevArray.filter(
              (obj) =>
                !(
                  obj.currentTable === currentTable &&
                  obj.column === column &&
                  obj.tenstackRowNumber === tenstackRowNumber
                )
            )
          : [...prevArray, newObject];
      }
    });
  };

  const ifExists = (column: string, tenstackRowNumber: number) =>
    tableSelectArray.some(
      (obj) =>
        obj.column === column &&
        obj.currentTable === currentTable &&
        obj.tenstackRowNumber === tenstackRowNumber
    );
    
  return { tableSelectArray, columnSelectArray, handleCellClick, handleColumnClick, ifExists };
};

// Utility Functions
export const doesObjectExistForColumn = (
  contextArray: TableRowContextObject[],
  tableName: string | null,
  column: string,
  tenstackRowNumber: number | null
) => {
  return contextArray.some(
    (obj) =>
      obj.currentTable === tableName &&
      obj.column === column &&
      obj.tenstackRowNumber === tenstackRowNumber
  );
};

export const filterRowByTableAndColumn = (
  contextArray: TableRowContextObject[],
  tableName: string | null,
  tenstackRowNumber: number | null
) => {
  return contextArray.filter(
    (obj) => !(obj.currentTable === tableName && obj.tenstackRowNumber === tenstackRowNumber)
  );
};

export const createRowEntries = (
  rowData: any,
  currentTable: string | null,
  row: number,
  tenstackRowNumber: number | null,
  existingArray: TableRowContextObject[]
) => {
  return Object.entries(rowData)
    .filter(
      ([key]) =>
        !doesObjectExistForColumn(existingArray, currentTable, key, tenstackRowNumber)
    )
    .map(([key, value]) => ({
      currentTable,
      column: key,
      row,
      value,
      tenstackRowNumber,
    }));
};

// Utility for Row Selection
export const isRowFullySelected = (
  rowIndex: number,
  tenstackRowNumber: number | null,
  tableSelectArray: TableRowContextObject[],
  reactTable: any,
  tableName: string | null
) => {
  const columnIds = reactTable
    .getAllColumns()
    .filter((col: any) => col.id !== 'rowNumber')
    .map((col: any) => col.id);

  return columnIds.every((columnId: string) =>
    tableSelectArray.some(
      (obj) =>
        obj.currentTable === tableName &&
        obj.column === columnId &&
        obj.row === rowIndex &&
        obj.tenstackRowNumber === tenstackRowNumber
    )
  );
};
