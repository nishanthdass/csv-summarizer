// src/hooks/useTableSelection.ts
import React, { useEffect, useState } from 'react';
import { useDataContext } from '../context/useDataContext';
import { TableCellContextObject } from '../utilities/TableEntity';
import { useFetchDataDatabase } from './fetch_hooks/useFetchDataDatabase';
import { useFileSidePanelOperations } from './useFileSidePanelOperations';
import { set } from 'lodash';

export const useTableSelection = () => {
  const { fetchRunSQLQuery } = useFetchDataDatabase();
  const { currentTable, currentTableName, tableSelections, setTableSelections, tableSqlSelections, setTableSqlSelections} = useDataContext();
  const { loadTableFromDatabase } = useFileSidePanelOperations();
  // Handle Column Click

  if (!currentTableName) {
    return {
      handleColumnClick: () => {},
      handleCellClick: () => {},
      handleRowClick: () => {},
    };
  }

  const tableHeader = currentTable?.data.header || [];

  const currentSelection = tableSelections[currentTableName] || {
      selectedCells: [],
      selectedRows: [],
      selectedColumns: [],
    };


  
  // Handle Column Click
  const handleColumnClick = (
    columnIndex: number, 
    columnName: string, page: 
    number
  ) => {
    insertOrRemoveColumn(columnIndex, columnName, page);
  };


  // Handle Row Click
  const handleRowClick = (
    ctid: string, 
  ) => {
    insertOrRemoveRow(ctid);
  };

  
  // Handle Cell Click
  const handleCellClick = (
    ctid: string,
    value: any,
    columnName: string | null,
  ) => {
    insertOrRemoveCell(ctid, value, columnName);
  };

  const handleSqlQuerySelections = (data: any[]) => {
    if (!currentTableName) {
      console.warn('No current table selected.');
      return;
    }
  
    data.forEach((retrievedData) => {
      // console.log(retrievedData);
      const keys = Object.keys(retrievedData);
      const length = keys.length;
  
      if (length === 1 && keys[0] === 'ctid') {
        const ctid = retrievedData.ctid;
        if (isRowSelected(ctid)) {
          console.log('Row already selected');
        } else {
          insertOrRemoveRow(ctid);
        }
        // insert in selected rows
      } else {
        keys.forEach((key) => {
          if (key !== 'ctid') {
            const ctid = retrievedData.ctid;
            const columnName = `${currentTableName}_${key}`;
            const value = retrievedData[key];
            // insert in selected cells
            if (isCellSelected(ctid, value, columnName)) {
              console.log('Cell already selected');
            } else {
              insertOrRemoveCell(ctid, value, columnName);
            }
          }
        });
      }
    });
  };
  
  const isRowSelected = (ctid: string) => currentSelection.selectedRows.some((row) => row.ctid === ctid)
  const isCellSelected = (ctid: string, value: any, columName: string | null) => currentSelection.selectedCells.some((cell) => cell.ctid === ctid && cell.value === value && cell.columnName === columName)


  const insertOrRemoveColumn = ( columnIndex: number, columnName: string, page: number) => {
    setTableSelections((prevSelections) => {
      const oldSelection = prevSelections[currentTableName] || {
        selectedRows: [],
        selectedCells: [],
        selectedColumns: [],
      };

      const columnAlreadySelected = oldSelection.selectedColumns.some((col) => col.columnIndex === columnIndex && col.columnName === columnName && col.page === page);

      if (columnAlreadySelected) {
        // Remove column selection
        return {
          ...prevSelections,
          [currentTableName]: {
            ...oldSelection,
            selectedColumns: oldSelection.selectedColumns.filter((col) => col.columnIndex !== columnIndex && col.columnName !== columnName || col.page !== page),
          },
        };
      } else {
        return {
          ...prevSelections,
          [currentTableName]: {
            ...oldSelection,
            selectedColumns: [...oldSelection.selectedColumns, { columnIndex, columnName, page }],
          },
        };
      }
    });
  }

  const insertOrRemoveRow = (ctid: string) => {
    setTableSelections((prevSelections) => {
      const oldSelection = prevSelections[currentTableName] || {
        selectedRows: [],
        selectedCells: [],
        selectedColumns: [],
      };
  
      const rowAlreadySelected = oldSelection.selectedRows.some((row) => row.ctid === ctid);
  
      if (rowAlreadySelected) {
        // Remove row selection
        return {
          ...prevSelections,
          [currentTableName]: {
            ...oldSelection,
            selectedRows: oldSelection.selectedRows.filter((row) => row.ctid !== ctid),
          },
        };
      } else {
        // Add row selection
        return {
          ...prevSelections,
          [currentTableName]: {
            ...oldSelection,
            selectedRows: [...oldSelection.selectedRows, { ctid }],
            selectedCells: oldSelection.selectedCells.filter((cell) => cell.ctid !== ctid),
          },
        };
      }
    });
  };
  
  

  const insertOrRemoveCell = (ctid: string, value: any, columnName: string | null ) => {
    setTableSelections((prevSelections) => {
      const oldSelection = prevSelections[currentTableName] || {
        selectedRows: [],
        selectedCells: [],
        selectedColumns: [],
      };
      const cellAlreadySelected = oldSelection.selectedCells.some((cell) => cell.ctid === ctid && cell.value === value && cell.columnName === columnName);

      const numberOfSelectedCells = oldSelection.selectedCells.filter((cell) => cell.ctid === ctid).length;
      const headers = Object.keys(currentTable?.data.header || {});
      const lenHeader = Object.keys(currentTable?.data.header || {}).length;
      const rowAlreadySelected = oldSelection.selectedRows.some((row) => row.ctid === ctid);

      if (!rowAlreadySelected) {
        if (cellAlreadySelected) { 
          console.log('Remove Cell: ', ctid, value, columnName);
          const selectedCells = oldSelection.selectedCells.filter((cell) => cell.columnName !== columnName || cell.ctid !== ctid);
          console.log('selectedCells: ', selectedCells);
          return {
            ...prevSelections,
            [currentTableName]: {
              ...oldSelection,
              selectedCells: oldSelection.selectedCells.filter((cell) => cell.columnName !== columnName || cell.ctid !== ctid),
            },
          };
        }
        else {
          return {
            ...prevSelections,
            [currentTableName]: {
              ...oldSelection,
              selectedCells: [...oldSelection.selectedCells, { ctid, value, columnName }],
            },
          };
        }
      } else {
        return prevSelections;
      }
    });

    setTableSelections((prevSelections) => {
      const oldSelection = prevSelections[currentTableName] || {
        selectedRows: [],
        selectedCells: [],
        selectedColumns: [],
      };

      const cellAlreadySelected = oldSelection.selectedCells.some((cell) => cell.ctid === ctid && cell.value === value && cell.columnName === columnName);

      const numberOfSelectedCells = oldSelection.selectedCells.filter((cell) => cell.ctid === ctid).length;
      const headers = Object.keys(currentTable?.data.header || {});
      const lenHeader = Object.keys(currentTable?.data.header || {}).length;
      const rowAlreadySelected = oldSelection.selectedRows.some((row) => row.ctid === ctid);

      // retrun oldSelection
      if (numberOfSelectedCells === lenHeader) {
        return {
          ...prevSelections,
          [currentTableName]: {
            ...oldSelection,
            selectedRows: [...oldSelection.selectedRows, { ctid }],
            selectedCells: oldSelection.selectedCells.filter((cell) => cell.ctid !== ctid),
          },
      }
      }else if (currentTable && rowAlreadySelected && numberOfSelectedCells === 0) {
          const row = currentTable.data.rows.find((r: any) => r.ctid === ctid);
          const newCells = row
            ? Object.keys(currentTable.data.header).map((colName) => ({
                ctid,
                value: row[colName],                       // safe now
                columnName: `${currentTableName}_${colName}`,
              }))
                .filter((cell) => cell.columnName !== columnName) // keep your original filter
            : [];

      
          return {
            ...prevSelections,
            [currentTableName]: {
              ...oldSelection,
              selectedRows: oldSelection.selectedRows.filter((row) => row.ctid !== ctid),
              selectedCells: [...oldSelection.selectedCells, ...newCells],
            },
          };
      }
      return prevSelections;
    })
  };
  

  return { handleColumnClick, handleCellClick, handleRowClick , handleSqlQuerySelections};
};
