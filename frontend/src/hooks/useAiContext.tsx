// src/hooks/useAiContext.ts
import { useState } from 'react';
import { AiContextObject } from '../utilities/types';

type UseAiContextParams = {
  tableName: string;
  tableRows: any[];
};

export const useAiContext = ({ tableName, tableRows }: UseAiContextParams) => {
  const [aiContextArray, setAiContextArray] = useState<AiContextObject[]>([]);

  const handleCellClick = (
    column: string,
    row: number,
    value: any,
    isRowNumberColumn: boolean
  ) => {
    if (isRowNumberColumn) {
      const rowData = tableRows[row];

      setAiContextArray((prevArray) => {
        const allValuesExist = Object.entries(rowData).every(([key, value]) =>
          prevArray.some(
            (obj) =>
              obj.tableName === tableName &&
              obj.column === key &&
              obj.row === row &&
              obj.value === value
          )
        );

        if (allValuesExist) {
          return prevArray.filter(
            (obj) => !(obj.tableName === tableName && obj.row === row)
          );
        } else {
          const newEntries = Object.entries(rowData)
            .filter(
              ([key, value]) =>
                !prevArray.some(
                  (obj) =>
                    obj.tableName === tableName &&
                    obj.column === key &&
                    obj.row === row &&
                    obj.value === value
                )
            )
            .map(([key, value]) => ({
              tableName,
              column: key,
              row,
              value,
            }));
          return [...prevArray, ...newEntries];
        }
      });
    } else {
      const newObject: AiContextObject = { tableName, column, row, value };

      setAiContextArray((prevArray) => {
        const exists = prevArray.some(
          (obj) =>
            obj.tableName === tableName &&
            obj.column === column &&
            obj.row === row
        );

        if (exists) {
          return prevArray.filter(
            (obj) =>
              !(
                obj.tableName === tableName &&
                obj.column === column &&
                obj.row === row
              )
          );
        } else {
          return [...prevArray, newObject];
        }
      });
    }
  };

  const ifExists = (column: string, row: number) => {
    return aiContextArray.some(
      (obj) => obj.column === column && obj.row === row && obj.tableName === tableName
    );
  };

  return { aiContextArray, handleCellClick, ifExists };
};


export const isRowFullySelected = (rowIndex: number, aiContextArray: AiContextObject[], reactTable: any, tableName: string) => {
    // Get all column IDs except for the row number column
    const columnIds = reactTable
      .getAllColumns()
      .filter((col: any) => col.id !== 'rowNumber')
      .map((col: any) => col.id);
  
    // Check if every column in the row has a corresponding entry in aiContextArray
    return columnIds.every((columnId: string) =>
      aiContextArray.some(
        (obj) =>
          obj.tableName === tableName &&
          obj.column === columnId &&
          obj.row === rowIndex
      )
    );
  };