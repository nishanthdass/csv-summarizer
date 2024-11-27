import React, { useMemo } from 'react';
import { TenstackTableProps } from '../utilities/types';
import { useTableSelection } from '../hooks/useTableSelection';
import { useDataContext } from '../context/useDataContext';
import { isRowFullySelected } from '../hooks/useTableSelection';


import {
  useReactTable,
  ColumnResizeMode,
  createColumnHelper,
  getCoreRowModel,
  flexRender,
  ColumnResizeDirection,
} from '@tanstack/react-table';

const columnHelper = createColumnHelper<any>();

const TenstackTable: React.FC<TenstackTableProps> = ({ zoomLevel }) => {
  const [columnResizeMode, setColumnResizeMode] = React.useState<ColumnResizeMode>('onChange');
  const [columnResizeDirection, setColumnResizeDirection] = React.useState<ColumnResizeDirection>('ltr');

  const { currentTable, tableData } = useDataContext();

  const { tableSelectArray, handleCellClick, handleColumnClick, ifExists } = useDataContext();

  // Prepare columns
  const columns = useMemo(() => {
    if (!tableData) return [];
    return [
      columnHelper.display({
        id: 'rowNumber',
        header: '#',
        cell: (info) => info.row.index + (tableData.page - 1) * tableData.page_size + 1,
        enableResizing: false,
        size: 0,
      }),
      ...Object.keys(tableData.header).map((key) =>
        columnHelper.accessor(key, {
          header: () => key.charAt(0).toUpperCase() + key.slice(1),
          cell: (info) => info.getValue(),
          enableResizing: true,
        })
      ),
    ];
  }, [tableData]);

  // Prepare data
  const data = useMemo(() => {
    if (!tableData) return [];
    return tableData.rows.map((row, index) => ({
      ...row,
      tenstackRowNumber: index + (tableData.page - 1) * tableData.page_size,
    }));
  }, [tableData]);

  // Initialize react-table
  const reactTable = useReactTable({
    data,
    columns,
    columnResizeMode,
    columnResizeDirection,
    getCoreRowModel: getCoreRowModel(),
  });

  // Helper to calculate cell class
  const getCellClass = (
    columnId: string,
    rowIndex: number,
    rowNumber: number,
    isRowNumberColumn: boolean
  ) => {
    const isRowSelected = isRowFullySelected(rowIndex, rowNumber, tableSelectArray, reactTable, currentTable);
    const isCellSelected = ifExists(columnId, rowNumber) && !isRowNumberColumn;

    return isCellSelected
      ? 'selected-cell'
      : isRowSelected
      ? 'selected-row'
      : isRowNumberColumn
      ? 'row-number-cell'
      : rowIndex % 2 === 0
      ? 'even-row'
      : 'odd-row';
  };

  return (
    <div className="table-container">
      <div style={{ direction: columnResizeDirection }}>
        <table
          style={{
            transform: `scale(${zoomLevel})`,
            transformOrigin: 'top left',
            width: reactTable.getCenterTotalSize(),
          }}
        >
          <thead>
            {reactTable.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className={header.index === 0 ? 'row-number-cell' : ''}
                    onClick={() =>
                        handleColumnClick(header.id, header.index)
                    }
                    colSpan={header.colSpan}
                    style={{
                      backgroundColor: '#E0E0E0',
                      width: header.getSize(),
                      position: 'relative',
                      textAlign: 'center',
                    }}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                    {header.index !== 0 && (
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
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {reactTable.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const columnId = cell.column.id;
                  const rowNumber = cell.row.original.tenstackRowNumber;
                  const isRowNumberColumn = columnId === 'rowNumber';
                  const cellClassName = getCellClass(columnId, row.index, rowNumber, isRowNumberColumn);

                  return (
                    <td
                      key={cell.id}
                      onClick={() =>
                        handleCellClick(columnId, row.index, cell.getValue(), isRowNumberColumn, rowNumber)
                      }
                      className={cellClassName}
                      style={{
                        width: cell.column.getSize(),
                        position: 'relative',
                        textAlign: 'center',
                        padding: '0 4px',
                        cursor: isRowNumberColumn ? 'pointer' : 'default',
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
