// src/hooks/useTableSelection.ts
import { useDataContext } from '../context/useDataContext';
import { TableCellContextObject } from '../utilities/TableEntity';

export const useTableSelection = () => {

  const { currentTable, currentTableName, tableSelections, setTableSelections} = useDataContext();
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


  interface CtidsResponse {
    success: boolean;
    data: string[];
  }
  const setCellViaCtid = (ctids: CtidsResponse) => {
    if (!currentTableName || !currentTable) {
      console.warn('No current table selected.');
      return;
    }

    const { success, data } = ctids;
  
    const currentSelection = tableSelections[currentTableName] || {
      selectedCells: [],
      selectedRows: [],
      selectedColumns: [],
    };
  
    // Helper function to create a valid TableCellContextObject
    const createCellObject = (ctid: string): TableCellContextObject => ({
      ctid: "(0,6)",
      column: "brand",
      row: 5,
      value: "dodge",
      tenstackRowNumber: 5,
    });

  
    // Iterate over each ctid in the list and toggle selection
    let updatedSelectedCells = [...currentSelection.selectedCells];
    console.log("ctids type:", typeof data);
    console.log("ctids value:", data);

    data.forEach((ctid) => {
      const isAlreadySelected = updatedSelectedCells.some((cell) => cell.ctid === ctid);
  
      if (isAlreadySelected) {
        // Remove if already selected
        updatedSelectedCells = updatedSelectedCells.filter((cell) => cell.ctid !== ctid);
      } else {
        // Add if not already selected
        updatedSelectedCells.push(createCellObject(ctid));
      }
    });
  
    // Update state with the new selection
    setTableSelections((prevSelections) => ({
      ...prevSelections,
      [currentTableName]: {
        ...currentSelection,
        selectedCells: updatedSelectedCells,
      },
    }));
  
    console.log('Updated Selected Cells:', updatedSelectedCells);
  };
  
  
  // Handle Cell Click
  const handleCellClick = (
    column: string,
    value: any,
    ctid: string,
    row: number,
    tenstackRowNumber: number
  ) => {
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

  

  return { handleColumnClick, handleCellClick, handleRowClick, setCellViaCtid };
};
