import React, { useEffect, useMemo } from 'react';
import { useDataContext } from '../context/useDataContext';
import { useTableSelection } from '../hooks/useTableSelection';
import { useUIContext } from '../context/useUIcontext';
import { alterId, revertId } from '../utilities/helper';


import {
  useReactTable,
  ColumnResizeMode,
  createColumnHelper,
  getCoreRowModel,
  flexRender,
  ColumnResizeDirection,
} from '@tanstack/react-table';
import { table } from 'console';
import { get, set } from 'lodash';


const columnHelper = createColumnHelper<any>();

const TenstackTable = () => {

    const [columnResizeMode, setColumnResizeMode] = React.useState<ColumnResizeMode>('onChange');
    const [columnResizeDirection, setColumnResizeDirection] = React.useState<ColumnResizeDirection>('ltr');

    const { currentTable, currentTableName, tableSelections, tableSqlSelections, setTableSelections} = useDataContext();
    const {  handleColumnClick, handleCellClick, handleRowClick } = useTableSelection();
    const { tableZoomLevel } = useUIContext();

    const currentSelection = tableSelections[currentTableName || ''] || {
      selectedCells: [],
      selectedRows: [],
      selectedColumns: [],
    };

    const currentSqlSelection = tableSqlSelections[currentTableName || ''] || {
      selectedCells: [],
      selectedRows: [],
      selectedColumns: [],
    };



    useEffect(() => {
      const selectedSqlRows = currentSqlSelection.selectedRows.map((row) => row.ctid);
      const selectedSqlCells = currentSqlSelection.selectedCells;

      for (const ctid of selectedSqlRows) {
        const getRowIndex = currentTable?.data.rows.findIndex((row) => row.ctid === ctid);
        if (getRowIndex !== undefined && getRowIndex !== -1 && currentTable) {
          const tenstackRowNumber =
            getRowIndex + (currentTable.data.page - 1) * currentTable.data.page_size;
          const foundRow = currentTable.data.rows[getRowIndex];
          const isRowAlreadySelected = currentSelection.selectedRows.some(
            (row) => row.ctid === ctid
          );
  
          if (!isRowAlreadySelected && foundRow) {
            // Build the array of cell objects for the row
            const newCells = Object.entries(foundRow)
              .filter(([key]) => key !== 'ctid')
              .map(([column, value]) => ({
                column,
                ctid,
                row: getRowIndex,
                value,
                tenstackRowNumber,
              }));
  
            if (newCells.length > 0 && ctid) {
                setTableSelections((prevTableSelections) => {
                  const oldTableSelection =
                    prevTableSelections[currentTableName || ''] || {
                      selectedCells: [],
                      selectedRows: [],
                      selectedColumns: [],
                    };
  
                  return {
                    ...prevTableSelections,
                    [currentTableName || '']: {
                      selectedCells: [
                        ...oldTableSelection.selectedCells,
                        ...newCells,
                      ],
                      selectedRows: [
                        ...oldTableSelection.selectedRows,
                        { ctid },
                      ],
                      selectedColumns: [...oldTableSelection.selectedColumns],
                    },
                  };
                });
            }
          }
        }
      }

      console.log("selectedSqlCells: ", selectedSqlCells);

      interface Cell {
        column: string;
        ctid: string;
        row: number;
        value: any;
        tenstackRowNumber: number;
      }
      
      const newCells: Cell[] = [];

      for (const cell of selectedSqlCells) {
        const { column, ctid, row, value, tenstackRowNumber } = cell;

        const getRowIndex = currentTable?.data.rows.findIndex((row) => row.ctid === ctid);
        if (getRowIndex !== undefined && getRowIndex !== -1 && currentTable) {
          const tenstackRowNumber = getRowIndex + (currentTable.data.page - 1) * currentTable.data.page_size;
          const foundRow = currentTable.data.rows[getRowIndex];
          const isCellAlreadySelected = currentSelection.selectedCells.some(
            (cell) => cell.ctid === ctid
          );
  
          if (!isCellAlreadySelected && foundRow) {
            // Build the array of cell objects for the row
            const getSqlCell = {
              column: column ?? '', 
              ctid: ctid ?? '',
              row: getRowIndex,
              value,
              tenstackRowNumber,
            };
            newCells.push(getSqlCell);
          }
        }
      }
      setTableSelections((prevTableSelections) => {
        const oldTableSelection =
          prevTableSelections[currentTableName || ''] || {
            selectedCells: [],
            selectedRows: [],
            selectedColumns: [],
          };
      
        return {
          ...prevTableSelections,
          [currentTableName || '']: {
            selectedCells: [...oldTableSelection.selectedCells, ...newCells],
            selectedRows: [...oldTableSelection.selectedRows],
            selectedColumns: [...oldTableSelection.selectedColumns],
          },
        };
      });

    }, [currentSqlSelection, currentTable]);

    const zoomLevel = useMemo(() => {
        if (currentTable?.name) {
          return tableZoomLevel[currentTable.name] || 1;
        }
        return 1;
      }, [currentTable?.name, tableZoomLevel]);

    // Prepare data
    const data = useMemo(() => {
        if (!currentTable) return [];
        return currentTable.data.rows.map((row, index) => ({
        ...row,
        ctid: row.ctid,
        tenstackRowNumber: index + (currentTable.data.page - 1) * currentTable.data.page_size,
        }));
    }, [currentTable]);

    // Prepare columns
    const columns = useMemo(() => {
        if (!currentTable) return [];

        return [
        columnHelper.display({
            id: 'rowNumber',                                              // Insert column to show row number
            header: '#',
            cell: (info) => info.row.index + (currentTable.data.page - 1) * currentTable.data.page_size + 1,
            enableResizing: false,
            size: 0,
        }),
        ...Object.keys(currentTable.data.header).map((key) =>
            columnHelper.accessor(key, {
                id: alterId(currentTable.name, key),                        // Unique name allows for simple column resizing using ReactTable
                header: () => key.charAt(0).toUpperCase() + key.slice(1),
                cell: (info) => info.getValue(),
                enableResizing: true,
            }) 
        ),
        ];
    }, [currentTable]);


    // Initialize react-table
    const reactTable = useReactTable({
      data,
      columns,
      columnResizeMode,
      columnResizeDirection,
      getCoreRowModel: getCoreRowModel(),
    });

    // Memoize the table style per table based on zoom level
    const tableStyle = useMemo(
      () => ({
        transform: `scale(${zoomLevel})`,
        transformOrigin: 'top left',
        width: reactTable.getCenterTotalSize(),
      }),
      [zoomLevel, reactTable.getCenterTotalSize()]
    );

    const getCellClass = (
      columnId?: string,
      rowIndex?: number,
      ctid?: string,
      isRowNumberColumn?: boolean
    ): string => {
      if (!currentTable) return '';
    
      const isRowSelected = ctid
        ? currentSelection.selectedRows.some((row) => row.ctid === ctid)
        : false;
    
      const isColumnSelected = columnId
        ? currentSelection.selectedColumns.some((col) => col.column === revertId(columnId, currentTable.name))
        : false;
    
      const isCellSelected =
        columnId && ctid
          ? currentSelection.selectedCells.some(
              (cell) =>
                cell.column === revertId(columnId, currentTable.name) &&
                cell.ctid === ctid
            )
          : false;
    
      // Determine the class based on selection state
      if (isCellSelected) return 'selected-cell';
      if (isRowSelected) return 'selected-row';
      if (isColumnSelected) return 'selected-column';
    
      // Default classes for odd/even rows
      if (isRowNumberColumn === undefined) return '';
      if (rowIndex === undefined) return '';
    
      return !isRowNumberColumn ? 'header-column-cells':
        isRowNumberColumn
        ? 'row-number-cell'
        : rowIndex % 2 === 0
        ? 'even-row'
        : 'odd-row';
    };
    
    

  return (
    <div className="table-container">
      <div style={{ direction: columnResizeDirection }}>
        <table style={tableStyle}>
          <thead>
            {reactTable.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const isRowNumberColumn = header.index === 0;
                const cellClassName = getCellClass(
                  header.id,
                  header.index,
                  undefined,
                  isRowNumberColumn
                )

                return (
                  <th
                    key={header.id}
                    className={cellClassName}
                    onClick={() => {
                      if (!isRowNumberColumn && currentTable) {
                        handleColumnClick(revertId(header.id, currentTable.name), header.index);
                      }
                    }}
                    colSpan={header.colSpan}
                    style={{
                      width: header.getSize(),
                    }}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {!isRowNumberColumn && (
                      <div
                        onDoubleClick={() => header.column.resetSize()}
                        onMouseDown={header.getResizeHandler()}
                        onTouchStart={header.getResizeHandler()}
                        className={`tbl_resizer ${columnResizeDirection} ${
                          header.column.getIsResizing() ? 'isResizing' : ''
                        }`}
                        style={{
                          transform:
                            columnResizeMode === 'onEnd' && header.column.getIsResizing()
                              ? `translateX(${
                                  (columnResizeDirection === 'rtl' ? -1 : 1) *
                                  (reactTable.getState().columnSizingInfo.deltaOffset ?? 0)
                                }px)`
                              : '',
                        }}
                      />
                    )}
                  </th>
                );
              })}
            </tr>
            ))}
          </thead>
          <tbody>
            {reactTable.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const ctid = cell.row.original.ctid;
                  const columnId = cell.column.id;
                  const tenstackRowNumber = cell.row.original.tenstackRowNumber;
                  const isRowNumberColumn = columnId === 'rowNumber';
                  const cellClassName = getCellClass(columnId, row.index, ctid, isRowNumberColumn);

                  return (
                    <td
                      key={cell.id}
                      onClick={() => {
                        if (!isRowNumberColumn && currentTable) {
                          handleCellClick(revertId(columnId, currentTable.name), cell.getValue(), ctid, row.index, tenstackRowNumber);
                        } else if (isRowNumberColumn && currentTable) {
                          handleRowClick(ctid, row.index, tenstackRowNumber);
                        }
                      }}
                      className={cellClassName}
                      style={{
                        width: cell.column.getSize(),
                        position: 'relative',
                        textAlign: 'center',
                        padding: '0 4px',
                        cursor: !isRowNumberColumn ? 'pointer' : 'default',
                      }}
                    >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TenstackTable;

