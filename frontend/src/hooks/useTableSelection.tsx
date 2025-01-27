// src/hooks/useTableSelection.ts
import React, { useEffect, useState } from 'react';
import { useDataContext } from '../context/useDataContext';
import { TableCellContextObject } from '../utilities/TableEntity';
import { useFetchDataDatabase } from './fetch_hooks/useFetchDataDatabase';
import { useFileSidePanelOperations } from './useFileSidePanelOperations';

export const useTableSelection = () => {
  const { fetchRunSQLQuery } = useFetchDataDatabase();
  const { currentTable, currentTableName, tableSelections, setTableSelections, tableSqlSelections, setTableSqlSelections} = useDataContext();
  const { loadTableFromDatabase } = useFileSidePanelOperations();
  // Handle Column Click



  const handleColumnClick = (column: string, columnIndex: number) => {
    
    if (!currentTableName) {
      console.warn('No current table selected.');
      return;
    }

    const currentSelection = tableSelections[currentTableName] || {
      selectedCells: [],
      selectedRows: [],
      selectedColumns: [],
    };

    const isAlreadySelected = currentSelection.selectedColumns.some(
      (col) => col.column === column && col.columnIndex === columnIndex
    );

    const updatedSelectedColumns = isAlreadySelected
      ? currentSelection.selectedColumns.filter(
          (col) => !(col.column === column && col.columnIndex === columnIndex)
        )
      : [...currentSelection.selectedColumns, { column, columnIndex }];

    setTableSelections((prevSelections) => ({
      ...prevSelections,
      [currentTableName]: {
        ...currentSelection,
        selectedColumns: updatedSelectedColumns,
      },
    }));
  };


  interface SetCellResponse {
    success: boolean;
    data: string[];
  }

  
  const handleChatQueryTableSelect = async (query: string, tableName: string) => {
    if (!currentTableName || !currentTable) {
      console.warn("No current table selected.");
      return;
    }
  
    try {
      // Fetch data matching your query
      const result = await fetchRunSQLQuery(query, tableName);
      const toBeSelectedCells = result.data;
  
      setTableSqlSelections((prevSelections) => {
        const oldSelection = prevSelections[currentTableName] || {
          selectedCells: [],
          selectedRows: [],
          selectedColumns: [],
        };

        let updatedSelectedRows = [...oldSelection.selectedRows];
        let updatedSelectedCells = [...oldSelection.selectedCells];
  
        for (let i = 0; i < toBeSelectedCells.length; i++) {
          const sqlData = toBeSelectedCells[i];
          if (!sqlData) continue;
  
          const keys = Object.keys(sqlData);
          if (keys.length === 1 && keys.includes("ctid")) {

            const ctid = sqlData.ctid;

            const isRowAlreadySelected = updatedSelectedRows.some((row) => row.ctid === ctid );
            const isCellAlreadySelected = updatedSelectedCells.some((cell) => cell.ctid === ctid);

            if (!isRowAlreadySelected) {
              updatedSelectedRows = [...updatedSelectedRows, { ctid }];
            }
          } else if (keys.length > 1 && keys.includes("ctid")) {
            console.log("Keys: ", keys);
            console.log("SQL Data: ", sqlData);
            const ctid = sqlData.ctid;
            for (let j = 0; j < keys.length; j++) {
              const key = keys[j];
              const value = sqlData[key];
              if (key !== "ctid") {
                updatedSelectedCells = [...updatedSelectedCells, { column: key, ctid: ctid, row: null, value: value, tenstackRowNumber: null }];
              }
            }

          }
        }
  
        return {
          ...prevSelections,
          [currentTableName]: {
            ...oldSelection,
            selectedRows: updatedSelectedRows,
            selectedCells: updatedSelectedCells,
          },
        };
      });
    } catch (error) {
      console.error(error);
    }
  };
  
  

  
  
  // Handle Cell Click
  const handleCellClick = (
    column: string,
    value: any,
    ctid: string,
    row: number,
    tenstackRowNumber: number
  ) => {
    console.log("column: ", column, "value: ", value, "ctid: ", ctid, "row: ", row, "tenstackRowNumber: ", tenstackRowNumber);
    if (!currentTableName || !currentTable) {
      console.warn('No current table selected.');
      return;
    }

    const currentSelection = tableSelections[currentTableName] || {
      selectedCells: [],
      selectedRows: [],
      selectedColumns: [],
    };

    const isAlreadySelected = currentSelection.selectedCells.some(
      (cell) => cell.column === column && cell.ctid === ctid
    );

    const updatedSelectedCells = isAlreadySelected
      ? currentSelection.selectedCells.filter(
          (cell) => !(cell.column === column && cell.ctid === ctid)
        )
      : [...currentSelection.selectedCells, { column, ctid, row, value, tenstackRowNumber }];

    // Now, determine if the entire row should be selected
    const getRow = currentTable.data.rows.find((r) => r.ctid === ctid);

    let updatedSelectedRows = currentSelection.selectedRows;

    if (getRow) {
      // Total cells in the row excluding 'ctid'
      const totalCellsInRow = Object.keys(getRow).length - 1;

      // Count selected cells in the row
      const selectedCellsInRow = updatedSelectedCells.filter(
        (cell) => cell.ctid === ctid
      ).length;

      if (selectedCellsInRow === totalCellsInRow) {
        // All cells in the row are selected, add the row to selectedRows
        const isRowAlreadySelected = currentSelection.selectedRows.some((r) => r.ctid === ctid);
        if (!isRowAlreadySelected) {
          updatedSelectedRows = [...currentSelection.selectedRows, { ctid }];
        }
      } else {
        // Not all cells are selected, remove the row from selectedRows if it's there
        updatedSelectedRows = currentSelection.selectedRows.filter((r) => r.ctid !== ctid);
      }
    }

    // Update the tableSelections
    setTableSelections((prevSelections) => ({
      ...prevSelections,
      [currentTableName]: {
        ...currentSelection,
        selectedCells: updatedSelectedCells,
        selectedRows: updatedSelectedRows,
      },
    }));
  };

  // Handle Row Click
  const handleRowClick = (ctid: string, row: number, tenstackRowNumber: number) => {
    if (!currentTableName || !currentTable) {
      console.warn('No current table selected.');
      return;
    }

    const currentSelection = tableSelections[currentTableName] || {
      selectedCells: [],
      selectedRows: [],
      selectedColumns: [],
    };

    console.log("handleRowClick currentSelection: ", currentSelection);

    const isRowAlreadySelected = currentSelection.selectedRows.some(
      (row) => row.ctid === ctid
    );

    const getRow = currentTable.data.rows.find((r) => r.ctid === ctid);

    let updatedSelectedRows = currentSelection.selectedRows;
    let updatedSelectedCells = currentSelection.selectedCells;

    if (getRow && !isRowAlreadySelected) {
      // Add the ctid of the row to the selected rows array
      updatedSelectedRows = [...currentSelection.selectedRows, { ctid }];

      // Add all cells of the row (if not already selected)
      const newCells = Object.entries(getRow)
        .filter(([key]) => key !== 'ctid')
        .map(([key, value]) => ({
          column: key,
          ctid,
          row,
          value,
          tenstackRowNumber,
        }));

      // Avoid duplicates
      updatedSelectedCells = [
        ...currentSelection.selectedCells.filter((cell) => cell.ctid !== ctid),
        ...newCells,
      ];
    } else {
      // Remove the ctid of the row from the selected rows array
      updatedSelectedRows = currentSelection.selectedRows.filter((r) => r.ctid !== ctid);
      // Remove all cells of the row
      updatedSelectedCells = currentSelection.selectedCells.filter((cell) => cell.ctid !== ctid);
    }

    // Update the tableSelections
    setTableSelections((prevSelections) => ({
      ...prevSelections,
      [currentTableName]: {
        ...currentSelection,
        selectedRows: updatedSelectedRows,
        selectedCells: updatedSelectedCells,
      },
    }));
  };

  

  return { handleColumnClick, handleCellClick, handleRowClick, handleChatQueryTableSelect };
};
