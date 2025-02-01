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


    useEffect(() => {
      if (!tableSelections) return;
      if (!currentTable) return;
      
    }, [tableSelections])

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
            id: 'rowNumber',
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

    let isRowSelected = false;
    if (ctid) {
      const selectedRowData = currentSelection.selectedRows.find((row) => row.ctid === ctid);
      isRowSelected = Boolean(selectedRowData);
      if (isRowSelected && selectedRowData && !isRowNumberColumn) {
        return 'selected-cell';
      } else if (isRowSelected && selectedRowData && isRowNumberColumn) {
        return 'selected-row';
      }
    }
  
    const isColumnSelected = columnId
      ? currentSelection.selectedColumns.some((col) => col.columnName === columnId)
      : false;
  
    const isCellSelected =
      columnId && ctid
        ? currentSelection.selectedCells.some(
            (cell) =>
              cell.columnName === columnId &&
              cell.ctid === ctid
          )
        : false;

  
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
                        handleColumnClick(header.index, header.id, currentTable.data.page);
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
                  // console.log(cell);
                  const ctid = cell.row.original.ctid;
                  const columnId = cell.column.id;
                  const isRowNumberColumn = columnId === 'rowNumber';
                  const cellClassName = getCellClass(columnId, row.index, ctid, isRowNumberColumn);

                  return (
                    <td
                      key={cell.id}
                      onClick={() => {
                        if (!isRowNumberColumn && currentTable) {
                          handleCellClick(ctid, cell.getValue(), cell.column.id );
                        } else if (isRowNumberColumn && currentTable) {
                          handleRowClick(ctid);
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

